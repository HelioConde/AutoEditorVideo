#!/usr/bin/env python3
"""Render ONE five-second Gamer visual-style pilot through AutoEditorVideo.

AI image provider calls: ZERO. Reuse an original AI illustration already
produced and cached by the first six-video batch (GitHub run 42044136670).

The real program:
- scripts/capa_cinematografica.render_cover(template='gamer-alchemy-reference')
- scripts/narracao_shorts.ensure_voice (real WordBoundary timing)
- scripts/legendas_precisas.captions_from_markers
- motion-remotion/src/master-short.tsx (reference visualProfile)

This module NEVER inserts or edits a YouTube video.
"""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from capa_cinematografica import render_cover
from narracao_shorts import ensure_voice
from legendas_precisas import captions_from_markers
from games_alchemy_ai_six import _probe,_sha
from games_alchemy_native_v3 import extract_art

SOURCE=ROOT/"source-games-alchemy-six"
SOURCE_RUN=42044136670
SOURCE_EP="game-002-primeira-noite-minecraft"
DEST=ROOT/"gamer-reference-style-5s"
EP="game-901-estilo-referencia-5s"
OWNER="gamer_reference_style_5s_20261105"
MOTION=ROOT/"motion-remotion"
ASSET_NAME="game-901-estilo-referencia-5s"
FPS=30
DURATION=5
SCRIPT="Você lembra da primeira noite no Minecraft?"
TITLE="PRIMEIRA NOITE"
HOOK="PRIMEIRA\nNOITE"
TAG="autoeditorvideo-reference-test-5s-20261105"
SOURCE_VIDEO_ID="hDKdl0cxtKM"

class PreviewError(ValueError):pass

def validate()->None:
    assert_reserved("games",EP,OWNER)
    if SOURCE_EP==EP or not EP.startswith("game-"):
        raise PreviewError("TEST_EPISODE_ID_INVALID")
    if not SCRIPT or not HOOK or TAG=="":
        raise PreviewError("MISSING_STYLE_PROPERTIES")
    if "\n" not in HOOK:
        raise PreviewError("REFERENCE_TITLE_REQUIRES_TWO_ROWS")

def guard()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!="Gamer - 5 second native cover and highlighted captions test"):
        raise PreviewError("SINGLE_APPROVED_MAIN_PUSH_REQUIRED")
    if e.get("STYLE_5S_APPROVED")!="true" or e.get("SOURCE_RENDER_RUN_ID")!=str(SOURCE_RUN):
        raise PreviewError("ORIGINAL_AI_SOURCE_NOT_PINNED")
    if DEST.exists():
        raise PreviewError("PREVIEW_ALREADY_EXISTS")

def command(args:list[str],*,cwd:Path|None=None,timeout:int=180)->None:
    result=subprocess.run(args,cwd=cwd,check=False,timeout=timeout,
                          capture_output=True,text=True)
    if result.returncode:
        raise PreviewError("MEDIA_COMMAND_FAILED_"+str(result.returncode))

def render()->None:
    from PIL import Image
    validate();guard()
    if not (SOURCE/"summary.json").is_file():
        raise PreviewError("ORIGINAL_MEDIA_MANIFEST_MISSING")
    source=json.loads((SOURCE/"summary.json").read_text(encoding="utf-8"))
    originals={o["id"]:o for o in source.get("videos",[])}
    original=originals.get(SOURCE_EP)
    source_mp4=SOURCE/SOURCE_EP/"final.mp4"
    if (source.get("count")!=6 or source.get("publication")!="not_performed" or
        original is None or not source_mp4.is_file() or
        _sha(source_mp4)!=original.get("sha256")):
        raise PreviewError("SOURCE_VIDEO_HASH_NOT_VERIFIED")
    if not (MOTION/"node_modules").is_dir():
        raise PreviewError("REMOTION_DEPS_NOT_INSTALLED")
    DEST.mkdir(parents=True)
    local=DEST/EP
    local.mkdir()
    assets=MOTION/"public"/"generated"/ASSET_NAME
    if assets.exists():
        raise PreviewError("ASSET_NAMESPACE_ALREADY_EXISTS")
    assets.mkdir(parents=True)
    # Extract original AI art in the 4th scene (safe upper section, no old
    # burned subtitles). No new image calls, no gameplay or real screenshots.
    art=local/"source-art.png"
    length=_probe(source_mp4)
    extract_art(source_mp4,length*.70,art)
    shutil.copy2(art,assets/"background.png")
    Image.new("RGBA",(1024,1536),(0,0,0,0)).save(
        assets/"foreground.png","PNG")
    cover=local/"thumb.jpg"
    with Image.open(art) as im:
        cover_result=render_cover(im,TITLE,cover,zoom=1.02,focus_x=.5,
                                  focus_y=.36,template="gamer-alchemy-reference")
    if (cover_result.get("template")!="gamer-alchemy-reference" or
        cover_result.get("size")!=[1080,1920] or cover.stat().st_size<25000):
        raise PreviewError("COVER_GENERATOR_TEMPLATE_INVALID")
    audio,ass=ensure_voice({"script":SCRIPT},local,create=True)
    duration=_probe(audio)
    if duration>4.9:
        raise PreviewError("VOICE_EXCEEDS_5_SECONDS")
    captions=captions_from_markers(audio,SCRIPT,DURATION,fps=FPS)
    if (not captions or max(len(c.get("words",[])) for c in captions)>3 or
        not any(len(c.get("words",[]))>=2 for c in captions)):
        raise PreviewError("CAPTION_GROUPS_NOT_WORD_SYNCED")
    shutil.copy2(audio,assets/"voz-master.mp3")
    frames=DURATION*FPS
    props={
      "id":EP,"durationFrames":frames,
      "audio":f"generated/{ASSET_NAME}/voz-master.mp3",
      "scenes":[{
        "id":"01","subject":"objeto","startFrame":0,"endFrame":frames,
        "background":f"generated/{ASSET_NAME}/background.png",
        "foreground":f"generated/{ASSET_NAME}/foreground.png",
        "renderMode":"master_static","shotType":"medium","beatRole":"hook",
        "transitionStyle":"hard"
      }],
      "captions":captions,"hook":HOOK,
      "animationMode":"cinematica","characterPreset":"equilibrado",
      "visualProfile":"gamer-alchemy-reference",
      "editorialProfile":"reference-visual-qa-5s"
    }
    props_path=local/"props.json"
    props_path.write_text(json.dumps(props,ensure_ascii=False,indent=2),encoding="utf-8")
    video=local/"final.mp4"
    command(["npm","run","render:master","--",str(video.resolve()),
             "--props",str(props_path.resolve()),"--concurrency","2"],
            cwd=MOTION,timeout=1200)
    measured=_probe(video)
    if abs(measured-DURATION)>.15 or video.stat().st_size<100_000:
        raise PreviewError("NOT_FIVE_SECOND_VIDEO")
    metadata={
      "id":EP,"channel":"games","channel_id":KNOWN_IDS["games"],
      "title":"TESTE 5s - Legenda e capa Minecraft | AutoEditorVideo",
      "description":(
        "TESTE PRIVADO de identidade visual do AutoEditorVideo: "
        "tipografia de miniatura e legendas sincronizadas.\n\n"
        "🎨 Visuais ilustrativos gerados por IA; não são capturas de gameplay.\n"
        "#Minecraft #Shorts"
      ),
      "tags":["Minecraft","Shorts","teste visual",TAG],
      "categoryId":"20","containsSyntheticMedia":True,
      "visibility":"private","test_only":True,
      "no_publication_authorized":True,
      "video_sha256":_sha(video),"cover_sha256":_sha(cover),
      "cover_generator":"capa_cinematografica.py",
      "cover_preset":"gamer-alchemy-reference",
      "caption_renderer":"ArquivoOtakuMaster+legendas_precisas",
      "source":"pre_existing_AI_art_no_new_generations",
    }
    qa={
      "schema":"autoeditorvideo/gamer-reference-5s-qa/v1",
      "id":EP,"duration_seconds":round(measured,3),
      "fps":FPS,"frame_count":frames,"size":[1080,1920],
      "captions":len(captions),
      "caption_max_group_words":max(len(c["words"]) for c in captions),
      "caption_highlight_word_boundary":True,
      "design_profile":"gamer-alchemy-reference",
      "cover_template":"gamer-alchemy-reference",
      "cover_size":[1080,1920],
      "original_source_run":SOURCE_RUN,
      "new_images_generated":False,
      "mp4_sha256":_sha(video),"thumb_sha256":_sha(cover),
      "visual_studio_check":"pending",
      "result":"technical_pass"
    }
    (local/"metadata.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (local/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={"schema":"autoeditorvideo/gamer-reference-5s-output/v1",
             "source_run":SOURCE_RUN,"owner":OWNER,
             "total":1,"status":"private_upload_not_yet_performed",
             "episode":EP,"video_sha256":qa["mp4_sha256"],
             "cover_sha256":qa["thumb_sha256"]}
    (DEST/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for remove in [art,props_path,audio,ass,local/"marcacoes-voz.json"]:
        remove.unlink(missing_ok=True)
    print("GAMER_REFERENCE_5S_OFFICIAL_COVER_AND_REMOTION_CAPTIONS_RENDERED",flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("validate","render"),default="validate")
    a=p.parse_args()
    try:
        validate()
        if a.action=="render":render()
        else:print("GAMER_5S_STYLE_RESERVATION_VALIDATED")
        return 0
    except Exception as e:
        error=str(e) if isinstance(e,PreviewError) else type(e).__name__
        print("GAMER_5S_RENDER_BLOCKED_"+error,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
