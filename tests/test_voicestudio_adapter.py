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
    def __init__(self, content=b"", data=None, headers=None, status_code=200):
        self.content = content
        self._data = data
        self.headers = headers or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} response", response=self
            )

    def json(self):
        return self._data


class SessionStub:
    def __init__(self, poster):
        self.poster = poster
        self.trust_env = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, **kwargs):
        return self.poster(url, **kwargs)


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
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(_stub_post))
    mp3, ass = ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert mp3.is_file() and ass.is_file()
    assert mp3.name.startswith("voz-voicestudio-")
    assert "Dialogue:" in ass.read_text(encoding="utf-8")
    assert not (tmp_path / "legendas.ass").exists()

    monkeypatch.setattr(vs, "_client", lambda: pytest.fail("cache should be used"))
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
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(fail))
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


def test_403_model_licence_is_actionable_without_auto_acceptance(monkeypatch, tmp_path):
    """403 is a legal permission gate, not an HTTP proxy or download error."""
    calls = []
    def refused(url, **kwargs):
        calls.append(url)
        return Reply(
            data={
                "error": {
                    "code": "model_licence_required",
                    "message": "Licence not accepted",
                },
                "detail": {
                    "code": "model_licence_required",
                    "models": [{"repo_id": "k2-fsa/OmniVoice"}],
                },
            },
            status_code=403,
        )
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(refused))
    with pytest.raises(RuntimeError, match="LICENÇA PENDENTE") as exc:
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert "k2-fsa/OmniVoice" in str(exc.value)
    assert len(calls) == 1  # No ASR or retry/automatic acceptance.
    assert not list(tmp_path.glob("voz-voicestudio-*"))


def test_403_other_access_shows_server_reason(monkeypatch, tmp_path):
    def refused(url, **kwargs):
        return Reply(data={"detail": "Request refused: unrecognized host name"},
                     status_code=403)
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(refused))
    with pytest.raises(RuntimeError, match="ACESSO NEGADO") as exc:
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert "unrecognized host name" in str(exc.value)


def test_403_asr_licence_reports_asr_stage(monkeypatch, tmp_path):
    def generate_then_refuse(url, **kwargs):
        if url.endswith("/v1/audio/speech"):
            return Reply(content=b"ID3" + b"x" * 1800,
                         headers={"Content-Type": "audio/mpeg"})
        return Reply(data={
            "error": {"code": "model_licence_required"},
            "detail": {"code": "model_licence_required",
                       "models": [{"repo_id": "Systran/faster-whisper-large-v3-turbo"}]}
        }, status_code=403)
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(generate_then_refuse))
    with pytest.raises(RuntimeError, match="transcrição ASR") as exc:
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert "LICENÇA PENDENTE" in str(exc.value)


def test_local_session_ignores_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:12345")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:12345")
    with vs._client() as client:
        assert client.trust_env is False


def test_409_without_asr_model(monkeypatch, tmp_path):
    def generate_then_refuse(url, **kwargs):
        if url.endswith("/v1/audio/speech"):
            return Reply(content=b"ID3" + b"x" * 1800,
                         headers={"Content-Type": "audio/mpeg"})
        return Reply(data={"detail": {"message": "ASR model not installed"}},
                     status_code=409)
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(generate_then_refuse))
    with pytest.raises(RuntimeError, match="MODELO ASR AUSENTE"):
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")


def test_500_omnivoice_silent_sidecar_is_actionable(monkeypatch, tmp_path):
    def timeout(url, **kwargs):
        return Reply(
            data={"detail": ("omnivoice-subprocess sidecar sent nothing "
                             "for 300s, so VoiceStudio stopped it.")},
            status_code=500,
        )
    monkeypatch.setattr(vs, "_client", lambda: SessionStub(timeout))
    with pytest.raises(RuntimeError, match="TIMEOUT DO MOTOR") as exc:
        ensure_voice(EP, tmp_path, create=True, engine="voicestudio")
    assert "-AmostraCurta" in str(exc.value)
    assert "supertonic3" in str(exc.value)
    assert not list(tmp_path.glob("voz-voicestudio-*"))


def test_short_sample_is_separate_and_never_publishes(monkeypatch, tmp_path):
    import testar_vozes as test_cli
    episode = dict(EP)
    episode["id"] = "voice-test"
    monkeypatch.setattr(test_cli, "ROOT", tmp_path)
    monkeypatch.setattr(test_cli, "select_episode", lambda _id: episode)
    calls = []
    def fake_voice(e, folder, *, create, engine):
        calls.append((e["script"], folder, create, engine))
        return folder / "fake.mp3", folder / "fake.ass"
    monkeypatch.setattr(test_cli, "ensure_voice", fake_voice)
    monkeypatch.setattr(
        sys, "argv", ["testar_vozes.py", "--id", "voice-test",
                       "--amostra-curta", "--comparar-edge"]
    )
    assert test_cli.main() == 0
    assert len(calls) == 2
    for script, folder, create, engine in calls:
        assert len(script.split()) < 20
        assert str(folder).endswith("teste-voz-curta")
        assert create is True
    assert {item[3] for item in calls} == {"edge", "voicestudio"}
    assert episode["script"] == EP["script"]  # original episode not mutated
