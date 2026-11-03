"""Offline regression tests for Edge TTS word timing metadata."""
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import narracao_shorts as narration


def test_voice_explicitly_requests_word_boundaries_and_reuses_cache(tmp_path, monkeypatch):
    calls = []

    class FakeCommunicate:
        def __init__(self, text, voice, *, rate, boundary):
            calls.append((text, voice, rate, boundary))

        async def stream(self):
            yield {"type": "audio", "data": b"\x00" * 2048}
            yield {"type": "WordBoundary", "offset": 0, "duration": 3_000_000, "text": "Ola"}
            yield {"type": "WordBoundary", "offset": 3_000_000, "duration": 4_000_000, "text": "mundo"}

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    episode = {"script": "Ola mundo"}
    voice, subtitles = narration.ensure_voice(episode, tmp_path, create=True)
    assert voice.is_file() and subtitles.is_file()
    assert "Dialogue:" in subtitles.read_text(encoding="utf-8")
    assert calls == [("Ola mundo", narration.VOICE, narration.RATE, "WordBoundary")]
    assert narration.ensure_voice(episode, tmp_path, create=False) == (voice, subtitles)
    assert len(calls) == 1


def test_missing_word_boundaries_fails_without_writing_fake_subtitles(tmp_path, monkeypatch):
    class FakeCommunicate:
        def __init__(self, text, voice, *, rate, boundary):
            assert boundary == "WordBoundary"

        async def stream(self):
            yield {"type": "audio", "data": b"\x00" * 2048}
            yield {"type": "SentenceBoundary", "offset": 0, "duration": 7_000_000, "text": "Ola mundo"}

    monkeypatch.setitem(sys.modules, "edge_tts", SimpleNamespace(Communicate=FakeCommunicate))
    with pytest.raises(RuntimeError, match="TTS não retornou alinhamento"):
        narration.ensure_voice({"script": "Ola mundo"}, tmp_path, create=True)
    assert not (tmp_path / "legendas.ass").exists()
    assert not (tmp_path / "voz-master.mp3").exists()
