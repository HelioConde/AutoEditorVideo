"""Narracao Acolhedora: pausa real, resposta depois da pergunta e cache valido."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kids_narracao_acolhedora as cozy
import piloto_canais_3x2_v3 as pilot
import produzir_piloto_canais_v3 as producer


def sample():
    manifest = pilot.load_manifest()
    return manifest["channels"][1], manifest["channels"][1]["episodes"][0]


async def fake_tts(script, voice, rate):
    assert voice == "pt-BR-FranciscaNeural"
    assert rate == "-15%"
    tokens = script.split()
    return f"words:{len(tokens)}".encode(), [
        {"start": i*.4, "end": i*.4 + .34, "text": token}
        for i, token in enumerate(tokens)
    ]


def fake_decode(blob: bytes) -> bytes:
    n = int(blob.decode().split(":")[1])
    return bytes(n * int(.4 * cozy.SAMPLE_RATE) * cozy.FRAME_BYTES)


def fake_encode(pcm: bytes) -> bytes:
    assert len(pcm) % cozy.FRAME_BYTES == 0
    return b"VALID-MOCK-MP3" * 250


def composed(ep=None):
    if ep is None:
        _, ep = sample()
    return asyncio.run(cozy.compose_timeline(
        ep, "pt-BR-FranciscaNeural", "-15%", fake_tts,
        decode=fake_decode, encode=fake_encode,
    ))


def test_kids_blue_star_has_natural_child_dialogue_and_real_question_holds():
    channel, ep = sample()
    beats = cozy.validate_timeline(ep)
    assert ep["narration_style"] == cozy.STYLE
    assert ep["planned_duration_seconds"] == 52
    assert len(beats) == 13
    assert beats[0]["text"].startswith("Onde está")
    assert "Obrigada" in beats[-1]["text"]
    assert all(beat["pause_after_s"] >= 1.5 for beat in beats
               if beat["id"] in cozy.QUESTION_BEATS)
    assert sum(b["pause_after_s"] for b in beats) == pytest.approx(11.8)
    assert beats.index(next(x for x in beats if x["id"] == "blue-yes")) > beats.index(
        next(x for x in beats if x["id"] == "blue-question"))
    assert ep["script"].count("(pausa)") == 0
    assert channel["default_made_for_kids"] is True


def test_pcm_silence_actual_timing_and_caption_gap():
    channel, ep = sample()
    audio, marker = composed(ep)
    assert len(audio) > 1000
    assert marker["style"] == cozy.STYLE
    assert marker["timeline_sha256"] == cozy.timeline_fingerprint(ep)
    assert 45 <= marker["duration_pcm_s"] <= 55
    assert marker["total_pause_s"] == pytest.approx(11.8)
    assert len(marker["segments"]) == 13
    assert marker["words"]
    question = next(s for s in marker["segments"] if s["id"] == "red-question")
    next_beat = next(s for s in marker["segments"] if s["id"] == "red-no")
    assert next_beat["start"] - question["speech_end"] == pytest.approx(1.8, abs=.0001)
    assert all(w["end"] <= question["speech_end"] for w in marker["words"]
               if w["beat_id"] == "red-question")
    # Captions stop on the words, not across 1.8 seconds of silence.
    frames = int((marker["duration_pcm_s"]+.45)*30)
    captions = producer._caption_groups(marker["words"], frames)
    for c in captions:
        assert c["text"]
    red_last_word = max(w["end"] for w in marker["words"] if w["beat_id"] == "red-question")
    assert red_last_word <= question["speech_end"]
    assert not any(c["startFrame"] < round((question["speech_end"]+.9)*30) <
                   c["endFrame"] for c in captions)
    scenes = producer._kids_scenes_with_pauses(ep, marker, frames)
    assert len(scenes) == 13
    assert scenes[0]["startFrame"] == 0
    assert scenes[-1]["endFrame"] == frames
    assert all(a["endFrame"] == b["startFrame"] for a,b in zip(scenes, scenes[1:]))
    assert [s["beat"] for s in scenes] == [s["id"] for s in ep["narration_timeline"]]
    assert scenes[3]["headline"] == "SERÁ A VERMELHA?"


def test_rushed_questions_and_mixed_channels_are_rejected():
    _, ep = sample()
    edited = copy.deepcopy(ep)
    next(b for b in edited["narration_timeline"] if b["id"] == "red-question")[
        "pause_after_s"] = .2
    with pytest.raises(ValueError, match="tempo para a crianca"):
        cozy.validate_timeline(edited)
    edited = copy.deepcopy(ep)
    edited["narration_timeline"][0]["text"] = "Outro inicio."
    with pytest.raises(ValueError, match="divergentes"):
        cozy.validate_timeline(edited)
    _, gamer = pilot.load_manifest()["channels"][0], pilot.load_manifest()["channels"][0]["episodes"][0]
    with pytest.raises(ValueError, match="exclusivo"):
        cozy.validate_timeline(gamer)


def test_60_second_limit_prevents_slow_voice_from_being_created():
    _, ep = sample()
    async def fake_slow(script, voice, rate):
        return await fake_tts(script, voice, rate)
    def slow_decode(blob):
        n = int(blob.decode().split(":")[1])
        return bytes(n * int(.65*cozy.SAMPLE_RATE) * cozy.FRAME_BYTES)
    with pytest.raises(ValueError, match="Limite 59.15s"):
        asyncio.run(cozy.compose_timeline(
            ep, "pt-BR-FranciscaNeural", "-15%", fake_slow,
            decode=slow_decode, encode=fake_encode,
        ))


def test_voice_cache_metadata_and_new_timeline_is_required(tmp_path, monkeypatch):
    channel, ep = sample()
    monkeypatch.setattr(producer, "OUT", tmp_path)
    async def fake_compose(episode, voice, rate, synth):
        return await cozy.compose_timeline(
            episode, voice, rate, synth, decode=fake_decode, encode=fake_encode
        )
    monkeypatch.setattr(producer, "_synthesize", fake_tts)
    monkeypatch.setattr(producer, "compose_kids_timeline", fake_compose)
    result = producer.create_voice(channel, ep)
    assert result["status"] == "voz_gerada_requer_revisao"
    voice, meta = producer.read_voice(channel, ep)
    assert voice.read_bytes().startswith(b"VALID-MOCK-MP3")
    assert meta["style"] == cozy.STYLE
    assert meta["script_sha256"] == producer.hash_script(ep["script"])
    assert len(meta["segments"]) == 13
    assert producer.create_voice(channel, ep)["status"] == "cache_ptbr_aprovado_tecnicamente"

    changed = copy.deepcopy(ep)
    changed["narration_timeline"][3]["pause_after_s"] += .1
    with pytest.raises(ValueError, match="Pausas ou falas Kids mudaram"):
        producer.read_voice(channel, changed)
    # Render QA cannot be reused if only pause timings change.
    assert cozy.timeline_fingerprint(changed) != cozy.timeline_fingerprint(ep)


def test_no_internet_upload_or_oauth_in_new_voice_builder():
    source = (ROOT / "scripts" / "kids_narracao_acolhedora.py").read_text(encoding="utf-8")
    assert "videos().insert" not in source
    assert "publishAt" not in source
    assert "googleapiclient" not in source
    assert "youtube-en-token.json" not in source
