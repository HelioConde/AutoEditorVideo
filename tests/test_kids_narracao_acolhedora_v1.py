"""Teste hermético: 13 falas Kids com pausas reais e sincronização do vídeo."""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import piloto_canais_3x2_v3 as pilot
import produzir_piloto_canais_v3 as producer
import kids_narracao_acolhedora_v1 as pacing


def load_star():
    data = pilot.load_manifest()
    return data["channels"][1], data["channels"][1]["episodes"][0]


def test_star_script_has_warm_pauses_and_no_early_reveal():
    channel, episode = load_star()
    beats = episode["kids_pacing"]["segments"]
    assert channel["voice_locale"] == "pt-BR"
    assert len(beats) == 13
    assert episode["planned_duration_seconds"] == 55
    assert beats[-1]["text"].startswith("Obrigada")
    assert any("Você encontrou" in b["text"] for b in beats)
    assert sum(b["pause_after_s"] for b in beats) >= 10
    assert all(b["pause_after_s"] >= 1.5 for b in beats if b["cue"].endswith("-question"))
    assert [b["cue"] for b in beats if b["scene"] == "04"] == [
        "yellow-question", "yellow-answer", "blue-reveal",
        "blue-question", "blue-answer",
    ]
    assert episode["narration_beats"] == [scene["narration"] for scene in episode["scenes"]]
    assert channel["default_made_for_kids"] is True
    assert "comente" not in episode["script"].casefold()


def test_games_and_other_kids_stories_unchanged():
    data = pilot.load_manifest()
    assert all("kids_pacing" not in ep for ep in data["channels"][0]["episodes"])
    assert all("kids_pacing" not in ep for ep in data["channels"][1]["episodes"][1:])
    assert all(ep["planned_duration_seconds"] == 38 for ep in data["channels"][0]["episodes"])
    assert all(ep["planned_duration_seconds"] == 28 for ep in data["channels"][1]["episodes"][1:])


def test_pause_schema_requires_room_for_children_to_answer():
    data = pilot.load_manifest()
    episode = data["channels"][1]["episodes"][0]
    episode["kids_pacing"]["segments"][3]["pause_after_s"] = .1
    with pytest.raises(ValueError, match="1,5s"):
        pilot.validate(data)


def test_pause_script_consistency_is_immutable():
    data = pilot.load_manifest()
    data["channels"][1]["episodes"][0]["kids_pacing"]["segments"][3]["text"] = "Outro roteiro?"
    with pytest.raises(ValueError, match="diverge"):
        pilot.validate(data)


def test_kids_pacing_does_not_allow_overlong_pause():
    data = pilot.load_manifest()
    data["channels"][1]["episodes"][0]["kids_pacing"]["segments"][3]["pause_after_s"] = 9
    with pytest.raises(ValueError, match="2,5"):
        pilot.validate(data)


def test_voice_chunks_are_composed_with_real_pcm_silence(tmp_path, monkeypatch):
    channel, episode = load_star()

    async def fake_segment(text, voice, rate, *, segment_dir, index, synthesizer):
        # Three seconds of actual spoken audio per segment.
        return segment_dir / f"{index:02d}.mp3", [
            {"start": .15, "end": .48, "text": "teste"},
            {"start": .75, "end": 1.22, "text": "de"},
            {"start": 1.50, "end": 2.25, "text": "fala"},
        ]

    monkeypatch.setattr(pacing, "_fetch_segment", fake_segment)
    monkeypatch.setattr(pacing, "_decode_pcm", lambda path: b"\0\0" * (pacing.RATE * 3))

    recorded = {}
    def fake_encode(pcm, wav, mp3):
        recorded["pcm"] = pcm
        mp3.write_bytes(b"fake MP3 " * 300)
    def fake_probe(path):
        return len(recorded["pcm"]) / (pacing.RATE * 2)

    async def not_needed(*args):
        raise AssertionError("Fake segment cache must avoid real TTS")

    result = asyncio.run(pacing.assemble_paced_voice(
        episode, "pt-BR-FranciscaNeural", "-15%", tmp_path,
        synthesizer=not_needed, encode=fake_encode, probe=fake_probe,
    ))
    assert result["target_reached"] is True
    assert 45 <= result["seconds"] <= 55
    marker = result["marker"]
    assert marker["locale"] == "pt-BR"
    assert marker["pacing_schema"] == pacing.SCHEMA
    assert len(marker["segments"]) == 13
    assert round(marker["pause_total_s"], 1) == 13.1
    assert len(marker["words"]) == 39
    assert marker["segments"][0]["start_s"] == 0
    for i, item in enumerate(marker["segments"]):
        assert item["end_s"] - item["speech_end_s"] == pytest.approx(
            item["pause_after_s"], abs=.002
        )
        if i:
            assert item["start_s"] == pytest.approx(marker["segments"][i - 1]["end_s"], abs=.002)
        # No subtitle should extend into the response pause.
        item_words = [w for w in marker["words"] if w["segment"] == i]
        assert max(w["end"] for w in item_words) < item["speech_end_s"]

    pacing.commit_voice(tmp_path, result)
    assert (tmp_path / "narracao.mp3").is_file()
    assert (tmp_path / "marcacoes-voz.json").is_file()
    assert marker["mp3_sha256"] == hashlib.sha256(
        (tmp_path / "narracao.mp3").read_bytes()
    ).hexdigest()

    frames = round((result["seconds"] + .45) * 30)
    scenes, captions, visual_beats = pacing.scene_props(episode, marker, frames)
    assert len(scenes) == 5 and len(visual_beats) == 13
    assert scenes[-1]["endFrame"] == frames
    assert all(a["endFrame"] == b["startFrame"] for a, b in zip(scenes, scenes[1:]))
    assert visual_beats[7]["cue"] == "blue-reveal"
    assert visual_beats[7]["sceneIndex"] == 3
    assert all(c["endFrame"] > c["startFrame"] for c in captions)
    for i, b in enumerate(visual_beats):
        relevant = [c for c in captions if
                    b["startFrame"] <= c["startFrame"] < b["endFrame"]]
        assert relevant
        assert relevant[-1]["endFrame"] <= round(marker["segments"][i]["speech_end_s"] * 30) + 1


def test_changed_pause_invalidates_old_voice_cache(tmp_path, monkeypatch):
    channel, episode = load_star()
    monkeypatch.setattr(producer, "OUT", tmp_path)
    folder = producer.folder_of(channel, episode)
    folder.mkdir(parents=True)
    fake_audio = b"pretend mp3" * 150
    (folder / "narracao.mp3").write_bytes(fake_audio)
    (folder / "marcacoes-voz.json").write_text(json.dumps({
        "schema": "piloto-canais/voice-boundaries/v3",
        "voice": "pt-BR-FranciscaNeural", "rate": "-15%",
        "script_sha256": producer.hash_script(episode["script"]),
        "pacing_schema": pacing.SCHEMA,
        "pacing_sha256": "old-pauses",
        "words": [{"start": 0, "end": .3, "text": "Oi"}],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="Ritmo e pausas Kids mudaram"):
        producer.read_voice(channel, episode)


def test_backup_preserves_previous_narration_and_qa(tmp_path):
    original = b"previous published-quality voice" * 110
    (tmp_path / "narracao.mp3").write_bytes(original)
    (tmp_path / "marcacoes-voz.json").write_text('{"previous":true}', encoding="utf-8")
    next_audio = tmp_path / "new.partial.mp3"
    next_audio.write_bytes(b"next voice" * 220)
    result = {"audio_temp": next_audio, "marker": {"new": True}}
    pacing.commit_voice(tmp_path, result)
    sha = hashlib.sha256(original).hexdigest()[:12]
    backup = tmp_path / "historico-voz"
    assert (backup / f"narracao-{sha}.mp3").read_bytes() == original
    assert json.loads((backup / f"marcacoes-{sha}.json").read_text())["previous"] is True
    assert json.loads((tmp_path / "marcacoes-voz.json").read_text())["new"] is True


def test_over_59_2_seconds_fails_without_replacing_voice(tmp_path, monkeypatch):
    channel, episode = load_star()
    async def fake_segment(text, voice, rate, *, segment_dir, index, synthesizer):
        return segment_dir / f"{index:02d}.mp3", [{"start": .3, "end": .8, "text": "fala"}]
    monkeypatch.setattr(pacing, "_fetch_segment", fake_segment)
    monkeypatch.setattr(pacing, "_decode_pcm", lambda path: b"\0\0" * (pacing.RATE * 4))
    with pytest.raises(ValueError, match="ultrapassa"):
        asyncio.run(pacing.assemble_paced_voice(
            episode, "pt-BR-FranciscaNeural", "-15%", tmp_path,
            synthesizer=lambda *args: None,
        ))
    assert not (tmp_path / "narracao.mp3").exists()
    assert not (tmp_path / "narracao-acolhedora.partial.mp3").exists()


def test_render_props_use_kids_beats_not_inferred_word_ratios(tmp_path, monkeypatch):
    channel, episode = load_star()
    words = []
    segments = []
    clock = 0.0
    for i, beat in enumerate(episode["kids_pacing"]["segments"]):
        segments.append({
            **beat, "segment": i, "start_s": clock,
            "speech_end_s": clock + 3, "end_s": clock + 3 + beat["pause_after_s"],
        })
        words.append({"start": clock + .3, "end": clock + 1.1,
                      "text": "palavra", "segment": i})
        clock += 3 + beat["pause_after_s"]
    marker = {"words": words, "segments": segments}
    voice = tmp_path / "voice.mp3"
    voice.write_bytes(b"mp3" * 900)
    monkeypatch.setattr(producer, "read_voice", lambda *_a: (voice, marker))
    monkeypatch.setattr(producer, "audio_seconds", lambda *_a: clock)
    monkeypatch.setattr(producer, "ffprobe_capture", lambda *_a: None)
    for filename in ("Wondertrail _Main Theme_.mp3", "Wondertrail _Main Theme_2.mp3"):
        (tmp_path / filename).write_bytes(b"ID3" + b"\\x00" * 120_000)
    props, path, target = producer.prepare_props(channel, episode, root=tmp_path)
    assert props["music"]["volume"] < 0.12
    assert props["music"]["source_name"] == "Wondertrail _Main Theme_.mp3"
    assert path.is_file()
    assert props["kidsBeats"][7]["cue"] == "blue-reveal"
    assert props["kidsBeats"][8]["cue"] == "blue-question"
    assert len(props["captions"]) == 13
    assert len(props["scenes"]) == 5
    assert props["durationFrames"] <= 1800
    assert (target / "narracao.mp3").is_file()


def test_no_youtube_upload_and_no_other_channel_voice_changes():
    source = (ROOT / "scripts" / "kids_narracao_acolhedora_v1.py").read_text(encoding="utf-8")
    assert "videos().insert" not in source
    assert "youtube.upload" not in source
    assert producer.BR_VOICES["games"] == ("pt-BR-AntonioNeural", "+2%")
    assert producer.BR_VOICES["kids"] == ("pt-BR-FranciscaNeural", "-15%")


def test_62_2_second_report_is_fixed_without_cutting_questions():
    """Regressão: relato real = 49.1s de fala + 13.1s de pausas."""
    _, episode = load_star()
    beats = episode["kids_pacing"]["segments"]
    speech = 49.1
    pauses, report = pacing.plan_child_friendly_pauses(beats, speech)
    assert report["natural_duration_seconds"] == pytest.approx(62.2, abs=.01)
    assert speech + sum(pauses) <= pacing.ADAPTIVE_MAX_SECONDS + .01
    assert report["all_questions_preserved"] is True
    assert 3.5 <= report["saved_seconds"] <= 4.0
    assert 8.9 <= report["applied_pause_seconds"] < 10.0
    for original, effective in zip(beats, pauses):
        if original["cue"].endswith("-question"):
            assert effective == pytest.approx(1.8)
        else:
            assert 0.35 <= effective <= original["pause_after_s"]


def test_real_62_second_chunks_compose_and_keep_captions_in_speech(tmp_path, monkeypatch):
    """Exercises actual PCM silence, word offsets, and synced visual beats."""
    _, episode = load_star()

    async def cache_only(text, voice, rate, *, segment_dir, index, synthesizer):
        return segment_dir / f"{index:02d}.mp3", [
            {"start": .25, "end": .5, "text": "olha"},
            {"start": .6, "end": .9, "text": "aqui"},
        ]

    monkeypatch.setattr(pacing, "_fetch_segment", cache_only)
    def fake_decode(path):
        # 12 x 3.8s + 1 x 3.5s = 49.1 seconds of real speech.
        sec = 3.5 if path.stem == "13" else 3.8
        return b"\0\0" * round(pacing.RATE * sec)
    monkeypatch.setattr(pacing, "_decode_pcm", fake_decode)

    capture = {}
    def fake_encode(pcm, wav_path, mp3_path):
        capture["seconds"] = len(pcm) / (pacing.RATE * 2)
        mp3_path.write_bytes(b"MP3 (fake)" * 200)

    async def should_not_call(*args):
        raise AssertionError("Do not re-synthesize cached speech")

    result = asyncio.run(pacing.assemble_paced_voice(
        episode, "pt-BR-FranciscaNeural", "-15%", tmp_path,
        synthesizer=should_not_call, encode=fake_encode,
        probe=lambda _path: capture["seconds"],
    ))
    marker = result["marker"]
    assert 58 <= result["seconds"] <= 58.6
    assert marker["pause_adaptation"]["natural_duration_seconds"] == pytest.approx(62.2)
    assert marker["pause_total_s"] < 10
    assert marker["pause_adaptation"]["all_questions_preserved"]
    for item in marker["segments"]:
        if item["cue"].endswith("-question"):
            assert item["pause_after_s"] == 1.8
        assert item["end_s"] - item["speech_end_s"] == pytest.approx(
            item["pause_after_s"], abs=.001
        )
    scenes, captions, beats = pacing.scene_props(
        episode, marker, round((result["seconds"] + .45) * pacing.FPS)
    )
    assert len(scenes) == 5 and len(beats) == 13
    assert all(a["endFrame"] == b["startFrame"] for a, b in zip(scenes, scenes[1:]))
    assert beats[7]["cue"] == "blue-reveal"
    assert captions[-1]["endFrame"] < scenes[-1]["endFrame"]


def test_adaptive_pause_planning_fails_if_speech_itself_too_long():
    _, episode = load_star()
    beats = episode["kids_pacing"]["segments"]
    with pytest.raises(ValueError, match="reduzir cerca de"):
        pacing.plan_child_friendly_pauses(beats, 53.0)
