"""VoiceStudio test doubles: no API, no models, no uploads, no generated video."""
from pathlib import Path
import sys

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import voice_studio_adapter as vs
from narracao_shorts import ensure_voice


EP = {"id": "voice-test", "script": "Yuji engoliu um dedo amaldiçoado para salvar seus amigos e virou hospedeiro de Sukuna."}


class Reply:
    def __init__(self, content=b"", data=None, headers=None):
        self.content = content
        self._data = data
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def _stub_post(url, **kwargs):
    if url.endswith("/v1/audio/speech"):
        assert kwargs["json"]["language"] == "pt"
        assert kwargs["json"]["response_format"] == "mp3"
        return Reply(content=b"ID3" + b"x" * 1800, headers={"Content-Type": "audio/mpeg"})
    assert url.endswith("/v1/audio/transcriptions")
    assert ("timestamp_granularities[]", "word") in kwargs["data"]
    assert kwargs["data"].count(("response_format", "verbose_json")) == 1
    words = [
        {"word": word, "start": i * 0.3, "end": i * 0.3 + 0.24}
        for i, word in enumerate(EP["script"].split())
    ]
    return Reply(data={"words": words})


def test_voicestudio_and_edge_are_independent(monkeypatch, tmp_path):
    monkeypatch.setenv("OTAKU_VOICESTUDIO_MODEL", "tts-1")
    monkeypatch.setenv("OTAKU_VOICESTUDIO_VOICE", "default")
    monkeypatch.setattr(vs.requests, "post", _stub_post)
    mp3, ass = ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert mp3.is_file() and ass.is_file()
    assert mp3.name.startswith("voz-voicestudio-")
    assert "Dialogue:" in ass.read_text(encoding="utf-8")
    assert not (tmp_path / "legendas.ass").exists()

    monkeypatch.setattr(vs.requests, "post", lambda *_a, **_k: pytest.fail("cache should be used"))
    assert ensure_voice(EP, tmp_path, create=False, engine="voicestudio") == (mp3, ass)
    (tmp_path / "voz-master.mp3").write_bytes(b"old-edge-voice")
    (tmp_path / "legendas.ass").write_text("edge captions", encoding="utf-8")
    edge, edge_sub = ensure_voice(EP, tmp_path, create=False, engine="edge")
    assert edge.name == "voz-master.mp3"
    assert edge_sub.name == "legendas.ass"


def test_unavailable_voicestudio_does_not_overwrite_edge(monkeypatch, tmp_path):
    edge = tmp_path / "voz-master.mp3"
    edge.write_bytes(b"safe-original")
    (tmp_path / "legendas.ass").write_text("safe-original", encoding="utf-8")
    def fail(*_a, **_k):
        raise requests.exceptions.ConnectionError("offline")
    monkeypatch.setattr(vs.requests, "post", fail)
    with pytest.raises(RuntimeError, match="VoiceStudio local indisponível"):
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert edge.read_bytes() == b"safe-original"
    assert not list(tmp_path.glob("voz-voicestudio-*"))


def test_bad_word_timing_is_rejected():
    with pytest.raises(RuntimeError, match="tempos inválidos"):
        vs._words({"words": [
            {"word": "Yuji", "start": 1.0, "end": 1.1},
            {"word": "engoliu", "start": 0.0, "end": 0.1},
        ]}, "Yuji engoliu")


def test_refuse_remote_server(monkeypatch):
    monkeypatch.setenv("OTAKU_VOICESTUDIO_URL", "https://example.org")
    with pytest.raises(ValueError, match="HTTP local"):
        vs._local_endpoint()
