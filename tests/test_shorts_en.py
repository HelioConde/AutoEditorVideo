"""Offline tests for English-channel assets and strict YouTube account isolation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import renderizar_shorts_en as renderer
import publicar_shorts_en as uploader


def test_five_english_scripts_are_distinct_and_translated():
    english = renderer.load_english()
    original = json.loads((ROOT / "conteudos" / "testes-animados-5.json").read_text(encoding="utf-8"))
    assert len(english) == len(original["episodes"]) == 5
    assert {e["id"] for e in english} == {e["id"] for e in original["episodes"]}
    for en, pt in zip(english, original["episodes"]):
        assert en["script"] != pt["script"]
        assert en["title"] != pt["title"]
        assert 50 <= len(en["script"].split()) < 145
        meta = renderer.english_metadata(en)
        assert meta["idioma"] == "en"
        assert "English narration" in meta["descricao"]
        assert "#Shorts" in meta["descricao"]
        assert "ã" not in en["cover"]


def test_planning_english_writes_separate_metadata_without_voice(tmp_path, monkeypatch):
    monkeypatch.setattr(renderer, "OUT", tmp_path)
    monkeypatch.setattr(renderer, "production_storyboard", lambda *args: pytest.fail("should not read scenes"))
    monkeypatch.setattr(renderer, "ensure_voice", lambda *args, **kwargs: pytest.fail("should not call TTS"))
    episode = renderer.load_english()[0]
    result = renderer.process(episode, "planejar", profile="equilibrado",
                              model="gpt-image-1.5", overwrite=False)
    assert result["status"] == "planejado"
    en = tmp_path / episode["id"] / "en-US" / "metadata-en.json"
    assert en.is_file()
    assert json.loads(en.read_text(encoding="utf-8"))["idioma"] == "en"


def test_english_voice_cache_has_separate_script_fingerprint(tmp_path, monkeypatch):
    episode = renderer.load_english()[0]
    calls = []

    def fake_voice(item, folder, *, create, voice):
        calls.append((item["script"], voice))
        folder.mkdir(parents=True, exist_ok=True)
        audio, subs = folder / "voz-master.mp3", folder / "legendas.ass"
        audio.write_bytes(b"MP3" * 2000)
        subs.write_text("Dialogue: 0,0:00:00.00,0:00:00.30,Main,,0,0,0,,Test", encoding="utf-8")
        return audio, subs

    monkeypatch.setattr(renderer, "ensure_voice", fake_voice)
    a, b = renderer.audio_for(episode, tmp_path, create=True)
    assert a.is_file() and b.is_file()
    assert (tmp_path / "voice-script-sha256.txt").is_file()
    assert calls[0][1] == "en-US-GuyNeural"
    with pytest.raises(RuntimeError, match="Roteiro ingles mudou"):
        renderer.audio_for({**episode, "script": episode["script"] + " New line."},
                           tmp_path, create=False)


def test_authenticated_channel_cannot_be_original_one():
    assert uploader.verify_channel_identity(
        [{"id": "UC" + "a" * 22, "snippet": {"title": "Otaku Archives"}}],
        "UC" + "a" * 22,
    ) == "Otaku Archives"
    with pytest.raises(RuntimeError, match="CONTA ERRADA"):
        uploader.verify_channel_identity(
            [{"id": "UC" + "b" * 22, "snippet": {"title": "Arquivo Otaku"}}],
            "UC" + "a" * 22,
        )
    with pytest.raises(RuntimeError, match="CONTA ERRADA"):
        uploader.verify_channel_identity([], "UC" + "a" * 22)


def test_upload_does_not_repeat_previous_id(tmp_path, monkeypatch):
    monkeypatch.setattr(uploader, "STATE", tmp_path / "en" / "estado.json")
    row = {"id": "003", "sha": "sha003", "path": tmp_path / "not_read.mp4",
           "meta": {"titulo": "Title"}}
    existing = {"video_id": "youtube-example", "status": "enviado"}
    saved = {"items": {"sha003": existing}}
    class NeverYoutube:
        def videos(self):
            pytest.fail("Duplicate videos.insert must never run")
    assert uploader.upload(NeverYoutube(), row, "private", saved) == existing


def test_upload_separates_title_language_and_privacy(tmp_path, monkeypatch):
    monkeypatch.setattr(uploader, "STATE", tmp_path / "en" / "estado.json")
    monkeypatch.setitem(sys.modules, "googleapiclient", SimpleNamespace())
    monkeypatch.setitem(
        sys.modules, "googleapiclient.http",
        SimpleNamespace(MediaFileUpload=lambda *args, **kwargs: object())
    )
    captured = {}
    class Request:
        def next_chunk(self):
            return None, {"id": "myEnglishVideo"}
    class Videos:
        def insert(self, **kwargs):
            captured.update(kwargs)
            return Request()
    class Youtube:
        def videos(self):
            return Videos()
    item = renderer.load_english()[0]
    row = {"id": item["id"], "sha": "unique-en-sha",
           "path": tmp_path / "english.mp4",
           "meta": renderer.english_metadata(item)}
    saved = {"schema": "youtube-en", "items": {}}
    result = uploader.upload(Youtube(), row, "private", saved)
    assert result["video_id"] == "myEnglishVideo"
    assert captured["body"]["snippet"]["defaultLanguage"] == "en"
    assert captured["body"]["status"]["privacyStatus"] == "private"
    assert "Light and L" in captured["body"]["snippet"]["description"]
    assert uploader.read_json(uploader.STATE)["items"]["unique-en-sha"]["status"] == "enviado"
    assert uploader.TOKEN.name == "youtube-en-token.json"
    assert uploader.STATE.name == "estado.json"
    # STATE is intentionally monkeypatched into a temporary EN directory.
    assert uploader.STATE.parent.name == "en"
    assert uploader.TOKEN.name != "youtube-token.json"


def test_preflight_must_not_authenticate(tmp_path, monkeypatch):
    row = {"id": "003", "sha": "n", "path": tmp_path, "meta": {"titulo": "Test"}}
    monkeypatch.setattr(uploader, "candidates", lambda *_args: [row])
    monkeypatch.setattr(uploader, "STATE", tmp_path / "estado.json")
    monkeypatch.setattr(uploader, "channel_auth", lambda: pytest.fail("preflight must be offline"))
    assert uploader.main(["--acao", "verificar"]) == 0



def test_otaku_reframe_episode_one_hooks_and_metadata():
    manifest = ROOT / "conteudos" / "otaku-reframe-ep01-en.json"
    items = renderer.load_english(manifest)
    assert len(items) == 1
    ep = items[0]
    assert ep["id"] == "101-death-note-ep01"
    assert ep["channel"] == "Otaku Reframe"
    assert ep["script"].startswith("One name. One death.")
    assert ep["script"].endswith("Follow Otaku Reframe for part two.")
    assert "But here's the terrifying twist" in ep["script"]
    assert 50 <= len(ep["script"].split()) <= 145
    assert len(ep["scenes"]) >= 10
    assert all(s["target_unchanged_shot_max_seconds"] <= 4.8 for s in ep["scenes"])
    assert ep["scenes"][0]["role"] == "hook"
    assert ep["scenes"][-1]["role"] == "cta"
    assert "#OtakuReframe" in renderer.english_metadata(ep)["descricao"]
    assert "Otaku Reframe" in renderer.english_metadata(ep)["tags"]


def test_english_neural_voice_does_not_require_images(tmp_path, monkeypatch):
    ep = renderer.load_english(ROOT / "conteudos" / "otaku-reframe-ep01-en.json")[0]
    monkeypatch.setattr(renderer, "OUT", tmp_path)
    monkeypatch.setattr(renderer, "production_storyboard", lambda *args: pytest.fail("voice needs no visuals"))
    monkeypatch.setattr(renderer, "audio_for", lambda *args, **kwargs: (tmp_path / "v.mp3", tmp_path / "s.ass"))
    monkeypatch.setattr(renderer, "audio_duration", lambda *_: 56.0)
    result = renderer.process(ep, "voz", profile="vivo", model="gpt-image-1.5", overwrite=False)
    assert result["status"] == "voz_pronta"
