"""Six independent PT-BR Shorts: offline content, safety and render contracts."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import piloto_canais_3x2_v3 as pilot
import produzir_piloto_canais_v3 as producer


def test_six_ptbr_episodes_and_child_audience_is_separated():
    data = pilot.load_manifest()
    assert len(data["channels"]) == 2
    games, kids = data["channels"]
    assert games["youtube_channel_id"] is None
    assert kids["youtube_channel_id"] is None
    assert len(games["episodes"]) == len(kids["episodes"]) == 3
    assert games["default_made_for_kids"] is False
    assert kids["default_made_for_kids"] is True
    assert data["language"] == "pt-BR"
    assert data["upload_enabled"] is False
    assert data["no_automatic_publication"] is True
    for channel in data["channels"]:
        for episode in channel["episodes"]:
            assert episode["script"].startswith(episode["hook"])
            assert len(episode["scenes"]) == 5
            assert set(episode["hook_options"]) == {
                "curiosity", "contradiction", "decision", "mystery", "consequence"
            }
            assert episode["description_youtube"]
            assert "Shorts" in episode["title"]
            assert all(s["character_motion"] for s in episode["scenes"])


def test_kids_does_not_require_gameplay_or_solicit_comments():
    data = pilot.load_manifest()
    kids = data["channels"][1]
    for ep in kids["episodes"]:
        assert ep["footage_origin"] == "original_vector_animation"
        assert ep["intended_learning"]
        assert all(s["asset_source"] == "original_procedural_vector" for s in ep["scenes"])
        text = (ep["script"] + " " + ep["description_youtube"]).casefold()
        assert all(term not in text for term in pilot.KIDS_BLOCKED)
        metadata = pilot.export_metadata(kids, ep)
        assert metadata["selfDeclaredMadeForKids"] is True
        assert metadata["privacyStatus"] == "private"
        assert metadata["channel_id"] is None


def test_games_capture_files_must_be_real_and_no_fake_results(tmp_path):
    data = pilot.load_manifest()
    games = data["channels"][0]
    for ep in games["episodes"]:
        meta = pilot.export_metadata(games, ep)
        assert meta["selfDeclaredMadeForKids"] is False
        assert meta["category"] == "20"
        report = pilot.inspect_episode(games, ep, root=tmp_path)
        assert not report["upload_ready"]
        assert not report["sources_available"]
        assert len(report["source_captures"]) == 5
        assert all(not s["found"] for s in report["source_captures"])
        assert "Gameplay real ausente" in " ".join(report["blockers"])


def test_child_engagement_is_strictly_blocked():
    data = pilot.load_manifest()
    ep = data["channels"][1]["episodes"][0]
    ep["narration_beats"][-1] += " Comente a resposta!"
    ep["scenes"][-1]["narration"] = ep["narration_beats"][-1]
    ep["script"] = " ".join(ep["narration_beats"])
    with pytest.raises(ValueError, match="Kids nao deve pedir"):
        pilot.validate(data)


def test_wrong_kids_classification_and_channel_ID_are_blocked():
    data = pilot.load_manifest()
    data["channels"][1]["default_made_for_kids"] = False
    with pytest.raises(ValueError, match="Made for Kids"):
        pilot.validate(data)
    data = pilot.load_manifest()
    data["channels"][0]["youtube_channel_id"] = "UC" + "a" * 22
    with pytest.raises(ValueError, match="ainda nao foram verificados"):
        pilot.validate(data)


def test_must_have_three_shorts_each_and_exact_5_scenes():
    data = pilot.load_manifest()
    data["channels"][0]["episodes"].pop()
    with pytest.raises(ValueError, match="tres Shorts"):
        pilot.validate(data)
    data = pilot.load_manifest()
    data["channels"][1]["episodes"][1]["scenes"].pop()
    with pytest.raises(ValueError, match="cinco cenas"):
        pilot.validate(data)


def test_prepares_six_local_tickets_without_upload(tmp_path, capsys):
    target = tmp_path / "prepared"
    assert pilot.main(["--acao", "preparar", "--saida", str(target)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["packages_prepared"] == 6
    assert output["videos_rendered"] == 0
    assert output["uploads"] == 0
    for item in output["files"]:
        f = Path(item["package"])
        assert f.is_file()
        ticket = json.loads(f.read_text(encoding="utf-8"))
        assert ticket["metadata"]["channel_id"] is None
        assert ticket["upload_authorized"] is False
        assert ticket["metadata"]["defaultAudioLanguage"] == "pt-BR"


def test_voice_selection_is_brazilian_for_both_channels():
    assert producer.BR_VOICES["games"] == ("pt-BR-AntonioNeural", "+2%")
    assert producer.BR_VOICES["kids"] == ("pt-BR-FranciscaNeural", "-15%")


def test_voice_and_word_boundaries_with_mock_tts_only(tmp_path, monkeypatch):
    data = pilot.load_manifest()
    kids, ep = data["channels"][1], data["channels"][1]["episodes"][0]
    monkeypatch.setattr(producer, "OUT", tmp_path)
    async def fake_tts(script, voice, rate):
        assert voice == "pt-BR-FranciscaNeural"
        assert rate == "-15%"
        return b"MP3" * 1500, [
            {"start": i * .6, "end": i * .6 + .5, "text": "teste"}
            for i in range(20)
        ]
    monkeypatch.setattr(producer, "_synthesize", fake_tts)
    state = producer.create_voice(kids, ep)
    assert state["status"] == "voz_gerada_requer_revisao"
    path, marker = producer.read_voice(kids, ep)
    assert path.stat().st_size > 1000
    assert marker["script_sha256"] == hashlib.sha256(ep["script"].encode()).hexdigest()
    with pytest.raises(ValueError, match="Roteiro mudou"):
        producer.read_voice(kids, {**ep, "script": ep["script"] + " Uma linha nova."})
    assert producer.create_voice(kids, ep)["status"] == "cache_ptbr_aprovado_tecnicamente"


def test_scene_frames_align_with_real_word_times():
    data = pilot.load_manifest()
    episode = data["channels"][1]["episodes"][0]
    words = [
        {"start": i * .5, "end": i * .5 + .35, "text": "palavra"}
        for i in range(65)
    ]
    frames = producer._scenes_with_audio_timings(episode, words, 1050)
    assert len(frames) == 5
    assert frames[0]["startFrame"] == 0
    assert frames[-1]["endFrame"] == 1050
    assert all(a["endFrame"] == b["startFrame"] for a,b in zip(frames, frames[1:]))
    captions = producer._caption_groups(words, 1050)
    assert captions
    assert len(captions[0]["text"].split()) <= 3


def test_voice_generation_and_render_are_distinct_user_actions(tmp_path, monkeypatch):
    data = pilot.load_manifest()
    games, ep = data["channels"][0], data["channels"][0]["episodes"][0]
    monkeypatch.setattr(producer, "OUT", tmp_path)
    with pytest.raises(FileNotFoundError, match="Narração"):
        producer.read_voice(games, ep)
    (tmp_path / "mock.mp3").write_bytes(b"MP3" * 1200)
    monkeypatch.setattr(producer, "read_voice",
                        lambda *_args, **_kwargs: (tmp_path / "mock.mp3",
                          {"words": [{"start": 0, "end": .4, "text": "oi"}] * 65}))
    monkeypatch.setattr(producer, "audio_seconds", lambda *_: 38.0)
    with pytest.raises(FileNotFoundError, match="Captura"):
        producer.render(games, ep, root=tmp_path)
    assert not (tmp_path / "assets" / "gerados" / "piloto-canais-v3" /
                "games" / ep["id"] / "final.mp4").exists()


def test_verify_video_missing_fails_closed(tmp_path):
    assert pilot.verify_video(tmp_path / "never-existed.mp4")["technical_status"] == "missing_or_incomplete"


def test_producers_have_no_upload_or_oauth():
    prod = (ROOT / "scripts" / "produzir_piloto_canais_v3.py").read_text(encoding="utf-8")
    assert "youtube.upload" not in prod
    assert "youtube-en-token.json" not in prod
    assert "videos().insert" not in prod
    assert "publishAt" not in prod
