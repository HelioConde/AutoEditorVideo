"""Offline QA for real-word caption grouping and strict cache matching."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from legendas_precisas import captions_from_markers, marker_for_voice


def _create_edge(tmp_path,script,words):
    voice=tmp_path/"voz-master.mp3"
    voice.write_bytes(b"MP3"*500)
    (tmp_path/"marcacoes-voz.json").write_text(json.dumps({
        "source":"edge-tts WordBoundary",
        "script_sha256":sha256(script.encode("utf-8")).hexdigest(),
        "words":words
    }),encoding="utf-8")
    return voice


def test_short_captions_use_real_audio_timestamps_and_are_grouped(tmp_path):
    script="Ele engoliu um dedo amaldiçoado. Sukuna despertou agora!"
    parts=script.split()
    words=[{"text":w,"start":i*0.31,"end":i*0.31+.26} for i,w in enumerate(parts)]
    audio=_create_edge(tmp_path,script,words)
    captions=captions_from_markers(audio,script,4.0)
    assert len(captions)==3
    assert captions[0]["text"]=="Ele engoliu um"
    assert captions[0]["startFrame"]==0
    assert captions[0]["words"][1]["startFrame"]==round(.31*30)
    assert captions[1]["text"]=="dedo amaldiçoado."
    assert captions[2]["text"]=="Sukuna despertou agora!"
    assert all(len(c["words"])<=3 for c in captions)
    assert all(c["startFrame"]<c["endFrame"]<=120 for c in captions)


def test_stale_script_or_invalid_words_fail_without_fake_timing(tmp_path):
    original="Yuji encontrou Sukuna."
    words=[{"text":"Yuji","start":0,"end":.23},
           {"text":"encontrou","start":.27,"end":.6},
           {"text":"Sukuna.","start":.65,"end":.95}]
    voice=_create_edge(tmp_path,original,words)
    with pytest.raises(ValueError,match="roteiro atual"):
        captions_from_markers(voice,"Yuji venceu Sukuna.",3)
    broken=json.loads((tmp_path/"marcacoes-voz.json").read_text(encoding="utf-8"))
    broken["words"][1]["start"]=-2
    (tmp_path/"marcacoes-voz.json").write_text(json.dumps(broken),encoding="utf-8")
    with pytest.raises(ValueError,match="Palavra sem"):
        captions_from_markers(voice,original,3)


def test_legacy_audio_without_marker_uses_ass_fallback(tmp_path):
    voice=tmp_path/"voz-master.mp3"
    voice.write_bytes(b"mp3")
    assert captions_from_markers(voice,"Qualquer frase",3) is None


def test_voicestudio_marker_stays_separate(tmp_path):
    voice=tmp_path/("voz-voicestudio-"+"1"*16+".mp3")
    assert marker_for_voice(voice).name=="marcacoes-voicestudio-"+"1"*16+".json"
