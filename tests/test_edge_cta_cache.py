"""Edge TTS cache regression: changing spoken CTA invalidates MP3 and ASS.

No external network/audio generation is used by these tests.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import types

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from narracao_shorts import RATE,VOICE,ensure_voice
from roteiro_para_storyboard import select_episode


def _cache(folder:Path,script:str,*,legacy:bool=False)->None:
    folder.mkdir(parents=True,exist_ok=True)
    (folder/"voz-master.mp3").write_bytes(b"EDGE" * 500)
    (folder/"legendas.ass").write_text("old ASS",encoding="utf-8")
    marker={"voice":VOICE,"rate":RATE,
            "words":[{"text":w,"start":i*.1,"end":i*.1+.09}
                     for i,w in enumerate(script.split())]}
    if not legacy:
        marker["script_sha256"]=hashlib.sha256(script.encode("utf-8")).hexdigest()
    (folder/"marcacoes-voz.json").write_text(json.dumps(marker),encoding="utf-8")


def test_jjk_cta_has_no_spoken_channel_name():
    ep=select_episode("401-jujutsu-kaisen-ep01")
    assert ep["cta"]=="Inscreva-se para acompanhar o próximo episódio!"
    assert ep["script"].endswith(ep["cta"])
    assert "Otaku Multicena" not in ep["script"]
    assert "Otaku Multicena" in ep["description_youtube"]


def test_edge_reuses_only_exact_script_cache(tmp_path):
    original="O garoto engoliu o dedo amaldiçoado. Inscreva-se no Otaku Multicena."
    updated="O garoto engoliu o dedo amaldiçoado. Inscreva-se!"
    _cache(tmp_path,original)
    voice,subtitle=ensure_voice({"script":original},tmp_path,create=False)
    assert voice.name=="voz-master.mp3" and subtitle.name=="legendas.ass"
    with pytest.raises(FileNotFoundError,match="desatualizada"):
        ensure_voice({"script":updated},tmp_path,create=False)


def test_legacy_cache_reused_only_for_identical_word_boundaries(tmp_path):
    original="Yuji encontrou um dedo misterioso."
    _cache(tmp_path,original,legacy=True)
    assert ensure_voice({"script":original},tmp_path,create=False)[0].is_file()
    with pytest.raises(FileNotFoundError,match="desatualizada"):
        ensure_voice({"script":"Yuji encontrou uma maldição diferente."},
                     tmp_path,create=False)


def test_edge_recreates_audio_and_captions_after_cta_change(monkeypatch,tmp_path):
    old="Yuji encontrou Sukuna. Inscreva-se no Otaku Multicena."
    new="Yuji encontrou Sukuna. Inscreva-se!"
    _cache(tmp_path,old)
    calls=[]
    class Communicate:
        def __init__(self,text,voice,rate,boundary):
            calls.append(text)
            assert voice==VOICE and rate==RATE
        async def stream(self):
            yield {"type":"audio","data":b"NEW-MP3"*300}
            yield {"type":"WordBoundary","offset":10000000,
                   "duration":3000000,"text":"Yuji"}
    monkeypatch.setitem(sys.modules,"edge_tts",types.SimpleNamespace(Communicate=Communicate))
    voice,captions=ensure_voice({"script":new},tmp_path,create=True)
    assert calls==[new]
    assert voice.read_bytes().startswith(b"NEW-MP3")
    assert "Dialogue:" in captions.read_text(encoding="utf-8")
    marker=json.loads((tmp_path/"marcacoes-voz.json").read_text(encoding="utf-8"))
    assert marker["script_sha256"]==hashlib.sha256(new.encode("utf-8")).hexdigest()
