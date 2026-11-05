#!/usr/bin/env python3
"""Redo the original 6 illustrated Shorts without another paid image call.

Reads exact GitHub render artifact 42044136670, extracts the existing AI artwork
from the original MP4s (BEFORE the old burned-in captions' vertical band),
generates fresh PT-BR CTA narration, re-times accessible subtitles, renders
new MP4s and cinematic bold-serif top-title thumbnails. NEVER uploads videos.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import textwrap

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from games_alchemy_ai_six import (_sha,_probe,_run,_speak,render_video,
                                   validate_media,PilotError)

PLAN=ROOT/"conteudos"/"lote-6-games-alchemy-recut-v2.json"
SOURCE=ROOT/"source-games-alchemy-six"
OUTPUT=ROOT/"cloud-games-alchemy-recut-v2"
OWNER="games_alchemy_six_shorts_v2_20261105"
ORIGIN_RUN=42044136670
ORDER=["game-001-gta4-gta5","game-002-primeira-noite-minecraft",
       "game-003-minecraft-sem-amarelo","alchemy-001-chatgpt-gifs",
       "alchemy-002-images-26-consistencia","alchemy-003-gif-animado-tutorial"]
WHITE_SERIF_FONT="/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
CANVAS=(720,1280)
PROHIBITED_SPOKEN=[
    "essas cenas são", "essas imagens são", "imagens geradas por",
    "não é gameplay", "não é uma partida", "não é uma gravação",
    "este é um guia visual ilustrado", "neste vídeo, estamos explicando",
    "não estamos apresentando um teste", "não se trata de gameplay",
    "visuais ilustrativos", "ilustrações geradas por ia",
]

class RecutError(ValueError):
    pass

def validate_manifest() -> dict:
    data=json.loads(PLAN.read_text(encoding="utf-8"))
    if data.get("schema")!="autoeditorvideo/games-alchemy-six-recut-v2/v1":
        raise RecutError("BAD_V2_MANIFEST_SCHEMA")
    if data.get("owner")!=OWNER or data.get("source_run")!=ORIGIN_RUN:
        raise RecutError("SOURCE_RUN_OR_OWNER_MISMATCH")
    rows=data.get("projects",[])
    if len(rows)!=6 or [r.get("source_episode_id") for r in rows]!=ORDER:
        raise RecutError("EXACT_SIX_EPISODES_REQUIRED")
    ids={"games":KNOWN_IDS["games"],"alchemy":KNOWN_IDS["alchemy"]}
    for row in rows:
        if row.get("channel") not in ids or row.get("channel_id")!=ids[row["channel"]]:
            raise RecutError("CHANNEL_ID_MISMATCH")
        if row.get("revised_episode_id")!=row["source_episode_id"]+"-v2":
            raise RecutError("INCORRECT_REVISION_ID")
        assert_reserved(row["channel"],row["revised_episode_id"],OWNER)
        script=row.get("narration","")
        if not (65<=len(script.split())<=115):
            raise RecutError("SPOKEN_SCRIPT_LENGTH_OUT_OF_RANGE")
        if not re.search(r"\bse inscreve\b",script,re.I):
            raise RecutError("SUBSCRIBE_CALL_TO_ACTION_MISSING")
        if any(phrase in script.lower() for phrase in PROHIBITED_SPOKEN):
            raise RecutError("PRODUCTION_DISCLOSURE_IN_NARRATION")
        if not re.search(r"(?:ilustra|visuais).*(?:ia|gameplay)|(?:ia|gameplay).*(?:ilustra|visuais)",
                         row.get("description",""),re.I|re.S):
            raise RecutError("DESCRIPTION_VISUAL_DISCLOSURE_MISSING")
        cover=row["thumbnail"]
        if len(cover["lines"])!=2 or any(len(x)>18 for x in cover["lines"]):
            raise RecutError("THUMB_TITLE_NOT_BRIEF_TWO_LINE")
        if not 1<=cover["scene_index"]<=5:
            raise RecutError("THUMB_SCENE_INDEX_INVALID")
    return data

def guard_render() -> None:
    if os.getenv("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        raise RecutError("WRONG_REPOSITORY")
    if os.getenv("GITHUB_REF")!="refs/heads/main":
        raise RecutError("MAIN_ONLY")
    if os.getenv("GITHUB_EVENT_NAME")!="push" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        raise RecutError("ONE_SHOT_FIRST_PUSH_ONLY")
    if os.getenv("GITHUB_WORKFLOW")!="Gamer + Alchemy - redo 6 CTA Shorts + cinematic covers":
        raise RecutError("WRONG_WORKFLOW")
    if os.getenv("RECUT_V2_APPROVED")!="true":
        raise RecutError("EXPLICIT_CREATOR_APPROVAL_REQUIRED")
    if os.getenv("SOURCE_RUN_ID")!=str(ORIGIN_RUN):
        raise RecutError("ONLY_ORIGINAL_ARTIFACT_ALLOWED")

def extract_frame(mp4:Path,seconds:float,out:Path) -> None:
    from PIL import Image,ImageOps
    temp=out.with_suffix(".temp.png")
    _run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error","-y",
          "-ss",f"{seconds:.3f}","-i",str(mp4),"-frames:v","1",str(temp)])
    try:
        with Image.open(temp) as raw:
            if raw.size!=CANVAS:
                raise RecutError("SOURCE_VIDEO_DIMENSIONS_CHANGED")
            # Original 5-word subtitles were burned into the lower video
            # (around y=900-1050). Crop ABOVE them and preserve portrait
            # proportions to avoid their text bleeding into the V2.
            clean=raw.convert("RGB").crop((140,0,580,782))
            clean=clean.resize(CANVAS,Image.Resampling.LANCZOS)
            clean.save(out,"PNG")
    finally:
        temp.unlink(missing_ok=True)

def write_safe_subtitles(words:list[dict],destination:Path,duration:float)->None:
    # Each subtitle is capped at 2 lines of <=25 characters; no clipping.
    header=(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\nWrapStyle: 2\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,DejaVu Sans,39,&H00FFFFFF,&H00FFFFFF,&H00070711,&H80000000,"
        "1,0,0,0,100,100,0,0,1,3,1,2,55,55,260,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    def stamp(s:float)->str:
        cent=max(0,round(s*100))
        h,part=divmod(cent,360000)
        m,part=divmod(part,6000)
        sec,cs=divmod(part,100)
        return f"{h}:{m:02}:{sec:02}.{cs:02}"
    chunks=[]
    i=0
    while i<len(words):
        current=[]
        length=0
        while i<len(words):
            s=str(words[i].get("text","")).strip()
            if not s:
                i+=1
                continue
            projected=length+len(s)+(1 if current else 0)
            if current and (len(current)>=6 or projected>40):
                break
            if len(s)>26:  # a single extremely long word is rare; cap font-safe.
                raise RecutError("CAPTION_TOKEN_TOO_LONG")
            current.append(words[i]);length=projected;i+=1
        if current:
            chunks.append(current)
    if len(chunks)<8:
        raise RecutError("WORD_TIMING_TOO_FEW_CHUNKS")
    events=[header]
    for chunk in chunks:
        content=" ".join(str(x["text"]).strip() for x in chunk)
        lines=textwrap.wrap(content,width=24,break_long_words=False,break_on_hyphens=False)
        if len(lines)>2:
            raise RecutError("CAPTION_OUTSIDE_TWO_LINE_SAFE_ZONE")
        clean="\\N".join(lines).replace("{","(").replace("}",")").replace("\\\\","")
        start=max(0,chunk[0]["start"]-.02)
        end=min(duration+.15,max(chunk[-1]["end"]+.10,start+.3))
        events.append(f"Dialogue: 0,{stamp(start)},{stamp(end)},Default,,0,0,0,,{clean}\n")
    destination.write_text("".join(events),encoding="utf-8-sig")

def cinematic_cover(frame:Path,destination:Path,lines:list[str])->None:
    from PIL import Image,ImageDraw,ImageFont
    with Image.open(frame) as raw:
        im=raw.convert("RGBA")
    w,h=im.size
    overlay=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    # Dark cinematic sky behind WHITE Serif uppercase header.
    for y in range(0,380):
        opacity=round(185*(1-y/380)**1.6)
        d.line([(0,y),(w-1,y)],fill=(0,0,0,opacity),width=1)
    im=Image.alpha_composite(im,overlay).convert("RGB")
    draw=ImageDraw.Draw(im)
    for row,line in enumerate(lines):
        line=line.upper()
        size=78
        while size>=32:
            font=ImageFont.truetype(WHITE_SERIF_FONT,size)
            bb=draw.textbbox((0,0),line,font=font,stroke_width=4)
            if bb[2]-bb[0]<=660:
                break
            size-=1
        if size<32:
            raise RecutError("COVER_TITLE_TOO_WIDE")
        draw.text((w//2,25+95*row),line,anchor="mt",fill="white",
                  font=font,stroke_width=4,stroke_fill="#090711")
    destination.parent.mkdir(parents=True,exist_ok=True)
    im.save(destination,"JPEG",quality=92,optimize=True)
    with Image.open(destination) as img:
        if img.size!=CANVAS or img.format!="JPEG":
            raise RecutError("COVER_SIZE_INVALID")

def render_all() -> None:
    manifest=validate_manifest()
    guard_render()
    if OUTPUT.exists():
        raise RecutError("V2_OUTPUT_ALREADY_EXISTS_NO_REPLAY")
    if not SOURCE.is_dir():
        raise RecutError("SOURCE_ARTIFACT_MISSING")
    original=json.loads((SOURCE/"summary.json").read_text(encoding="utf-8"))
    if (original.get("schema")!="autoeditorvideo/six-ai-illustrated-review/v1" or
        original.get("count")!=6 or len(original.get("videos",[]))!=6):
        raise RecutError("ORIGINAL_SUMMARY_BAD")
    indexed={x["id"]:x for x in original["videos"]}
    OUTPUT.mkdir(parents=True)
    summary={"schema":"autoeditorvideo/games-alchemy-six-recut-v2-output/v1",
             "source_run":ORIGIN_RUN,"owner":OWNER,"publication":"not_performed",
             "quality_review":"requires_visual_and_audio_review","videos":[]}
    for row in manifest["projects"]:
        id=row["source_episode_id"]
        src=SOURCE/id/"final.mp4"
        if id not in indexed or not src.is_file() or _sha(src)!=indexed[id]["sha256"]:
            raise RecutError("SOURCE_MP4_SHA256_MISMATCH_"+id)
        folder=OUTPUT/(id+"-v2")
        folder.mkdir(parents=True)
        secs=_probe(src)
        frames=[]
        for i in range(5):
            image=folder/f"frame-{i+1:02d}.png"
            extract_frame(src,secs*(i+.5)/5,image)
            frames.append(image)
        cover=folder/"thumb.jpg"
        cinematic_cover(frames[row["thumbnail"]["scene_index"]-1],cover,row["thumbnail"]["lines"])
        voice=folder/"narration.mp3"
        words=asyncio.run(_speak(row["narration"],voice))
        duration=_probe(voice)
        if not 24<=duration<=90:
            raise RecutError("VOICE_DURATION_NOT_SHORT")
        subtitles=folder/"legendas.ass"
        write_safe_subtitles(words,subtitles,duration)
        video=folder/"final.mp4"
        render_video(frames,voice,subtitles,video,duration)
        qa=validate_media(video,cover,frames,duration)
        qa.update({"source_video_sha256":indexed[id]["sha256"],
                   "recut_revision":"v2","speech_cta_at_end":True,
                   "spoken_ai_disclosure":False,
                   "subtitle_lines_max":2,
                   "caption_recut_crops_previous_burned_subtitles":True,
                   "manual_review_required":True})
        meta={
            "id":row["revised_episode_id"],"channel":row["channel"],
            "channel_id":row["channel_id"],"title":row["title"],
            "description":row["description"],"tags":row["tags"],
            "categoryId":"20" if row["channel"]=="games" else "28",
            "containsSyntheticMedia":True,"ai_visuals_only":True,
            "visibility":"private","original_private_youtube_video_id":row["origin_video_id"],
            "revision":"v2","narration_policy":"topic_cta_not_tech_disclosure",
            "thumb_style":"white_uppercase_serif_top_black_outline",
            "mp4_sha256":qa["mp4_sha256"],"cover_sha256":qa["cover_sha256"]
        }
        (folder/"metadata.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
        (folder/"qa.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding="utf-8")
        summary["videos"].append({
            "id":row["revised_episode_id"],"channel":row["channel"],
            "video_path":row["revised_episode_id"]+"/final.mp4",
            "cover_path":row["revised_episode_id"]+"/thumb.jpg",
            "title":row["title"],"sha256":qa["mp4_sha256"]
        })
        for f in folder.glob("frame-*.png"):
            f.unlink(missing_ok=True)
        for f in folder.glob("clip-*.mp4"):
            f.unlink(missing_ok=True)
        for temp in ["joined.mp4","list.txt","legendas.ass","narration.mp3"]:
            (folder/temp).unlink(missing_ok=True)
        print("RECUT_V2_RENDERED_"+row["revised_episode_id"],flush=True)
    if len(summary["videos"])!=6:
        raise RecutError("PARTIAL_RENDER")
    (OUTPUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ALL_SIX_V2_CTA_SHORTS_AND_WHITE_SERIF_THUMBNAILS_RENDERED_NO_UPLOAD",flush=True)

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("validate","render"),default="validate")
    args=p.parse_args()
    try:
        validate_manifest()
        if args.action=="validate":
            print("SIX_REVISED_CTA_SCRIPTS_VALIDATED",flush=True)
        else:
            render_all()
        return 0
    except Exception as exc:
        message=str(exc) if isinstance(exc,(PilotError,RecutError)) else type(exc).__name__
        print("SIX_RECUT_V2_BLOCKED_"+message,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
