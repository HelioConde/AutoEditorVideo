#!/usr/bin/env python3
"""Native AutoEditorVideo re-render: existing Remotion caption style and cover generator.

Six already-reserved Gamer/Alchemy Shorts use the EXISTING original artwork
captured from the prior AI video. Audio and timestamps come from narracao_shorts
and legendas_precisas. Captions are rendered by the SAME ArquivoOtakuMaster
Remotion composition as the other AutoEditorVideo Shorts: 2-3 words at once,
spoken word in yellow, dark card, safe 1080x1920 margins. Covers use
capa_cinematografica.render_cover, never a parallel PIL thumbnail routine.
No image-generation calls and NO YouTube API calls.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from narracao_shorts import ensure_voice
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover, STYLE as COVER_STYLE
from games_alchemy_ai_six import _probe, _sha

SOURCE_RUN=42044136670
SOURCE=ROOT/"source-games-alchemy-six"
OUTPUT=ROOT/"cloud-games-alchemy-reference-v4"
MOTION=ROOT/"motion-remotion"
PLAN=ROOT/"conteudos"/"lote-6-games-alchemy-recut-v2.json"
OWNER="games_alchemy_six_reference_v4_20261105"
IDS=[
 "game-001-gta4-gta5","game-002-primeira-noite-minecraft",
 "game-003-minecraft-sem-amarelo","alchemy-001-chatgpt-gifs",
 "alchemy-002-images-26-consistencia","alchemy-003-gif-animado-tutorial"
]
FPS=30
# Explicitly select the AI-art sections that fit the narration; avoid
# the off-topic final scene in the first Alchemy GIF and GTA videos.
SCENE_TIMES={
  "game-001-gta4-gta5": [.08,.31,.39,.62,.34],
  "game-002-primeira-noite-minecraft": [.08,.29,.54,.78,.88],
  "game-003-minecraft-sem-amarelo": [.07,.30,.51,.70,.89],
  "alchemy-001-chatgpt-gifs": [.06,.20,.39,.56,.31],
  "alchemy-002-images-26-consistencia": [.07,.31,.55,.78,.88],
  "alchemy-003-gif-animado-tutorial": [.06,.29,.52,.69,.88]
}

class NativeRecutBlocked(ValueError):pass

def validate_plan()->dict:
    d=json.loads(PLAN.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/games-alchemy-six-recut-v2/v1" or
        d.get("source_run")!=SOURCE_RUN or
        [row.get("source_episode_id") for row in d.get("projects",[])]!=IDS):
        raise NativeRecutBlocked("INVALID_SOURCE_MANIFEST")
    for p in d["projects"]:
        ch=p["channel"]
        if ch not in ("games","alchemy") or p["channel_id"]!=KNOWN_IDS[ch]:
            raise NativeRecutBlocked("WRONG_CHANNEL")
        assert_reserved(ch,p["source_episode_id"]+"-v4",OWNER)
        script=p["narration"].lower()
        if "se inscreve" not in script:
            raise NativeRecutBlocked("CTA_NOT_FOUND")
        if any(x in script for x in ("não é gameplay","ilustrações feitas por ia",
                                      "não é uma gravação", "este vídeo foi criado por ia")):
            raise NativeRecutBlocked("SPOKEN_PRODUCTION_TEXT")
        if "🎨" not in p["description"]:
            raise NativeRecutBlocked("DESCRIPTION_SYNTHETIC_MEDIA_DISCLOSURE_MISSING")
        if len(p["thumbnail"]["lines"])!=2:
            raise NativeRecutBlocked("THUMBNAIL_TITLE_REQUIRED")
    return d

def guard()->None:
    e=os.environ
    if e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        raise NativeRecutBlocked("WRONG_REPOSITORY")
    if e.get("GITHUB_REF")!="refs/heads/main" or e.get("GITHUB_EVENT_NAME")!="push":
        raise NativeRecutBlocked("SINGLE_MAIN_PUSH_ONLY")
    if e.get("GITHUB_RUN_ATTEMPT")!="1":
        raise NativeRecutBlocked("NO_RERUN")
    if e.get("GITHUB_WORKFLOW")!="Gamer + Alchemy - approved reference style six V4 private Shorts":
        raise NativeRecutBlocked("WRONG_WORKFLOW")
    if e.get("REFERENCE_V4_APPROVED")!="true" or e.get("SOURCE_RUN_ID")!=str(SOURCE_RUN):
        raise NativeRecutBlocked("APPROVAL_OR_ORIGIN_REQUIRED")

def command(args:list[str],*,cwd:Path|None=None,timeout:int=300)->None:
    result=subprocess.run(args,check=False,cwd=cwd,timeout=timeout,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    if result.returncode:
        # No secret exposure: do not log terminal output or TTS payload.
        raise NativeRecutBlocked("RENDER_COMMAND_FAILED_"+str(result.returncode))

def extract_art(video:Path,time_point:float,dest:Path)->None:
    from PIL import Image
    raw=dest.with_suffix(".raw.png")
    command(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
             "-ss",f"{time_point:.3f}","-i",str(video),"-frames:v","1",
             str(raw)],timeout=60)
    try:
        with Image.open(raw) as im:
            if im.size!=(720,1280):
                raise NativeRecutBlocked("SOURCE_FRAME_DIMENSIONS_CHANGED")
            # Old captions begin below the 780px boundary. Use clean top
            # 768px, center-cropped to original master aspect ratio (2:3).
            clean=im.convert("RGB").crop((104,0,616,768))
            clean.resize((1024,1536),Image.Resampling.LANCZOS).save(dest,"PNG")
    finally:
        raw.unlink(missing_ok=True)

def build_scene_props(row:dict,frames:list[Path],voice:Path,captions:list[dict],
                      duration:float,namespace:str)->dict:
    fps=FPS
    n=max(30,math.ceil(duration*fps))
    if len(frames)!=5:
        raise NativeRecutBlocked("FIVE_SCENES_REQUIRED")
    starts=[round(n*i/5) for i in range(6)]
    scenes=[]
    for i,(start,end) in enumerate(zip(starts[:-1],starts[1:])):
        if end<=start:raise NativeRecutBlocked("ZERO_LENGTH_SCENE")
        scenes.append({
          "id":f"{i+1:02}","subject":"objeto",
          "startFrame":start,"endFrame":end,
          "background":f"generated/{namespace}/scene-{i+1:02}-background.png",
          "foreground":f"generated/{namespace}/scene-{i+1:02}-foreground.png",
          "renderMode":"master_static","transitionStyle":"crossfade",
          "shotType":"medium","beatRole":"setup" if i==0 else "answer" if i==3 else "detail"
        })
    return {
      "id":row["source_episode_id"]+"-v4",
      "durationFrames":n,
      "audio":f"generated/{namespace}/voz-master.mp3",
      "scenes":scenes,
      "captions":captions,
      "hook":"\n".join(row["thumbnail"]["lines"]),
      "visualProfile":"gamer-alchemy-reference",
      "animationMode":"cinematica",
      "characterPreset":"equilibrado",
      "editorialProfile":"games-alchemy-native-remotion"
    }

def render()->None:
    from PIL import Image
    plan=validate_plan()
    guard()
    if OUTPUT.exists():
        raise NativeRecutBlocked("OUTPUT_EXISTS_DO_NOT_OVERWRITE")
    if not SOURCE.is_dir() or not (SOURCE/"summary.json").is_file():
        raise NativeRecutBlocked("ORIGINAL_AI_VIDEO_ARTIFACT_MISSING")
    if not (MOTION/"node_modules").is_dir():
        raise NativeRecutBlocked("REMOTION_NOT_INSTALLED")
    summary=json.loads((SOURCE/"summary.json").read_text(encoding="utf-8"))
    if summary.get("count")!=6 or summary.get("publication")!="not_performed":
        raise NativeRecutBlocked("SOURCE_MANIFEST_INVALID")
    original={v["id"]:v for v in summary.get("videos",[])}
    if set(original)!=set(IDS) or set(SCENE_TIMES)!=set(IDS):
        raise NativeRecutBlocked("SOURCE_EPISODES_OR_SCENE_PLAN_MISMATCH")
    for fractions in SCENE_TIMES.values():
        if len(fractions)!=5 or any(not 0.01<=f<=0.95 for f in fractions):
            raise NativeRecutBlocked("INVALID_SCENE_TIMES")
    OUTPUT.mkdir(parents=True)
    output_summary={
      "schema":"autoeditorvideo/games-alchemy-six-native-remotion-v4/v1",
      "source_run":SOURCE_RUN,"owner":OWNER,"renderer":"AutoEditorVideo/ArquivoOtakuMaster",
      "cover_generator":"AutoEditorVideo/scripts/capa_cinematografica.py",
      "captions":"AutoEditorVideo/scripts/legendas_precisas.py:word-boundaries-remotion-yellow-highlight",
      "visual_profile":"gamer-alchemy-reference",
      "cover_template":"gamer-alchemy-reference",
      "no_new_image_api_calls":True,"no_youtube_upload":True,
      "review":"pending_final_review","videos":[]
    }
    for job in plan["projects"]:
        id=job["source_episode_id"]
        revision=id+"-v4"
        path=SOURCE/id/"final.mp4"
        if not path.is_file() or _sha(path)!=original[id].get("sha256"):
            raise NativeRecutBlocked("SOURCE_CHECKSUM_MISMATCH_"+id)
        dest=OUTPUT/revision
        dest.mkdir()
        names=f"native-v4-{revision}"
        public=MOTION/"public"/"generated"/names
        if public.exists():
            raise NativeRecutBlocked("ASSET_NAMESPACE_ALREADY_EXISTS")
        public.mkdir(parents=True)
        length=_probe(path)
        frames=[]
        for i in range(5):
            art=dest/f"scene-{i+1:02}-background.png"
            extract_art(path,length*SCENE_TIMES[id][i],art)
            frames.append(art)
            shutil.copy2(art,public/art.name)
            # The original MasterShort expects a foreground, but this story
            # intentionally uses whole-frame original AI illustrations.
            transparent=public/f"scene-{i+1:02}-foreground.png"
            Image.new("RGBA",(1024,1536),(0,0,0,0)).save(transparent,"PNG")
        voice,ass=ensure_voice({"script":job["narration"]},dest,create=True,engine="edge")
        duration=_probe(voice)
        if not 25<=duration<=90:
            raise NativeRecutBlocked("SHORT_DURATION_INVALID")
        captions=captions_from_markers(voice,job["narration"],duration,fps=FPS)
        if not captions or len(captions)<15 or any(len(x["words"])>3 for x in captions):
            raise NativeRecutBlocked("CAPTION_GROUPS_NOT_NATIVE")
        if not all(x.get("words") for x in captions):
            raise NativeRecutBlocked("WORD_HIGHLIGHT_MARKERS_MISSING")
        if captions[-1]["endFrame"] < int(duration*FPS*.80):
            raise NativeRecutBlocked("FINAL_CTA_CAPTION_MISSING")
        shutil.copy2(voice,public/"voz-master.mp3")
        props=build_scene_props(job,frames,voice,captions,duration,names)
        props_path=dest/"props.json"
        props_path.write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        movie=dest/"final.mp4"
        command(["npm","run","render:master","--",str(movie.resolve()),
                 "--props",str(props_path.resolve()),"--concurrency","2"],
                 cwd=MOTION,timeout=2400)
        if not movie.is_file() or movie.stat().st_size<250000:
            raise NativeRecutBlocked("REMOTION_MP4_NOT_GENERATED")
        actual=_probe(movie)
        if abs(actual-duration)>2.5:
            raise NativeRecutBlocked("VIDEO_AUDIO_DURATION_MISMATCH")
        thumb=dest/"thumb.jpg"
        with Image.open(frames[job["thumbnail"]["scene_index"]-1]) as im:
            cover=render_cover(im," ".join(job["thumbnail"]["lines"]),thumb,
                               zoom=1.02,focus_x=.5,focus_y=.36,
                               template="gamer-alchemy-reference")
        if (cover.get("style")!=COVER_STYLE or cover.get("size")!=[1080,1920]
            or cover.get("template")!="gamer-alchemy-reference"):

            raise NativeRecutBlocked("NOT_OFFICIAL_COVER_ENGINE")
        # Build exact per-channel metadata for a *future* authorized private upload.
        meta={
          "id":revision,"channel":job["channel"],"channel_id":job["channel_id"],
          "title":job["title"],"description":job["description"],
          "tags":job["tags"],"categoryId":"20" if job["channel"]=="games" else "28",
          "revision":"v4","visibility":"private","containsSyntheticMedia":True,
          "ai_visuals_only":True,"original_private_video_id":job["origin_video_id"],
          "cover_generator":"capa_cinematografica.render_cover",
          "caption_renderer":"ArquivoOtakuMaster+legendas_precisas",
          "visual_profile":"gamer-alchemy-reference",
          "cover_template":"gamer-alchemy-reference",
          "video_sha256":_sha(movie),"cover_sha256":_sha(thumb)
        }
        qa={
          "id":revision,"structural_qa":"passed","render_engine":"ArquivoOtakuMaster",
          "caption_groups":len(captions),"caption_max_group_words":max(len(c["words"]) for c in captions),
          "highlight_by_word_boundaries":True,
          "cover_engine":COVER_STYLE,"cover_size":[1080,1920],
          "cover_template":"gamer-alchemy-reference",
          "visual_profile":"gamer-alchemy-reference",
          "scene_fractions":SCENE_TIMES[id],
          "source_artwork_sha256":original[id]["sha256"],
          "script_cta":"se inscreve" in job["narration"].lower(),
          "silent_production_disclosure":True,
          "video_seconds":round(actual,2),"video_sha256":_sha(movie),
          "cover_sha256":_sha(thumb),
          "needs_visual_review":True
        }
        (dest/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (dest/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        output_summary["videos"].append({
          "id":revision,"channel":job["channel"],
          "video":revision+"/final.mp4","cover":revision+"/thumb.jpg",
          "sha256":qa["video_sha256"]
        })
        # Store a reduced review artifact, omit work intermediates.
        for art in frames:art.unlink(missing_ok=True)
        for tmp in (voice,ass,dest/"marcacoes-voz.json",props_path):
            tmp.unlink(missing_ok=True)
        print("NATIVE_V4_VIDEO_RENDERED_"+revision,flush=True)
    if len(output_summary["videos"])!=6:
        raise NativeRecutBlocked("SIX_COMPLETE_REQUIRED")
    (OUTPUT/"summary.json").write_text(
        json.dumps(output_summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ALL_SIX_REFERENCE_V4_PROGRAM_RENDERED_AND_READY_FOR_PRIVATE_UPLOAD",flush=True)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=["validate","render"],default="validate")
    args=ap.parse_args()
    try:
        validate_plan()
        if args.action=="render": render()
        else: print("NATIVE_V4_STYLE_AND_RESERVATIONS_VALIDATED",flush=True)
        return 0
    except Exception as ex:
        tag=str(ex) if isinstance(ex,NativeRecutBlocked) else type(ex).__name__
        print("NATIVE_V4_BLOCKED_"+tag,file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
