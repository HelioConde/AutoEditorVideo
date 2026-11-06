#!/usr/bin/env python3
"""Generate exactly FIVE original illustrated frames for ONE reserved Otaku BR Short.

This job never has YouTube OAuth, never uploads, and never marks human visual
review completed. Fail closed if the image provider or validation fails.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageOps, ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_br_50_reverso import OUTPUT, validate
from gerar_video_codex import proxy_key, check_proxy_accounts, request_image

MODEL="gpt-image-2"
SIZE=(1024,1536)
CHANNEL_ID="UCXGYTuBYn-0Ziqin5ajKhOw"

class ImageBlocked(ValueError):
    pass

def sha(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()

def stage_check(number:int)->dict:
    if os.getenv("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        raise ImageBlocked("WRONG_REPOSITORY")
    if os.getenv("GITHUB_REF")!="refs/heads/main" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        raise ImageBlocked("MAIN_AND_FIRST_ATTEMPT_ONLY")
    if os.getenv("GITHUB_EVENT_NAME") not in ("push","workflow_dispatch"):
        raise ImageBlocked("UNAUTHORIZED_EVENT")
    if os.getenv("IMAGE_MODEL")!=MODEL or os.getenv("MAX_IMAGE_CALLS")!="5":
        raise ImageBlocked("WRONG_MODEL_OR_IMAGE_BUDGET")
    if number not in range(1,51):
        raise ImageBlocked("INVALID_EPISODE_NUMBER")
    item=validate()[number-1]
    if item.get("channel_id")!=CHANNEL_ID or item["position"]!=number:
        raise ImageBlocked("CHANNEL_OR_QUEUE_MISMATCH")
    return item

def prompt_for(row:dict,index:int)->str:
    scene=row["storyboard"][index-1]
    common=(
        "Create ONE ORIGINAL hand-painted 2D anime editorial illustration, "
        "vertical 2:3 1024x1536, to be composited in an original Brazilian "
        "YouTube anime ANALYSIS video. High-quality hand-drawn cel animation "
        "aesthetic, cohesive character designs, crisp anatomy, natural hands, "
        "bold cinematic lighting, expressive faces, vivid background depth, "
        "clear action frozen at an impactful moment. Not a still from the anime; "
        "NOT a screenshot, no existing animation frames, no title, captions, "
        "logos, watermarks, UI, lettering, borders, panels or collage. "
        "All characters and important objects fully in frame, keep the "
        "bottom 22 percent relatively uncluttered for real Remotion captions. "
        "Match costumes, props, scene geography and lighting consistently "
        "throughout the five scenes of THIS same short. "
    )
    return (common+
        f"Franchise and story context: {row['series']}. "
        f"Story to faithfully visualize: {row['narration_script']} "
        f"Unique shot {index}/5; direction: {scene['action']} "
        f"Emphasize this image's DIFFERENT action and camera perspective: {scene['camera']}. "
        f"Episode visual object cues: {row['cover_text']}. "
        "Do not invent new characters or scenes unrelated to the narrated story. "
        "Avoid excessive text, gore or graphic violence.")

def generate(number:int)->dict:
    row=stage_check(number)
    folder=OUTPUT/row["id"]
    folder.mkdir(parents=True,exist_ok=True)
    art=[folder/f"scene-{i:02d}.png" for i in range(1,6)]
    if (folder/"original-art-provenance.json").exists() or any(p.exists() for p in art):
        raise ImageBlocked("EXISTING_ART_REQUIRES_RECONCILIATION_NO_REGENERATION")
    key=proxy_key()
    check_proxy_accounts(key)
    hashes=[]
    try:
        for i,dest in enumerate(art,1):
            raw=request_image(prompt_for(row,i),MODEL,key,"1024x1536")
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                if image.width<512 or image.height<768:
                    raise ImageBlocked("IMAGE_TOO_SMALL")
                canvas=ImageOps.pad(image.convert("RGB"),SIZE,
                                    method=Image.Resampling.LANCZOS,color=(10,12,24))
                if max(ImageStat.Stat(canvas.resize((64,96))).stddev)<15:
                    raise ImageBlocked("IMAGE_VISUALLY_BLANK")
                canvas.save(dest,"PNG",optimize=True)
            hashes.append(sha(dest))
        if len(set(hashes))!=5:
            raise ImageBlocked("DUPLICATE_OR_REPEATED_IMAGES")
        report={
          "episode_id":row["id"],"channel_id":CHANNEL_ID,
          "model":MODEL,"art_original":True,
          "visual_qa":"automated_technical_checks_only",
          "rights_qa":"AI_generated_no_imported_media",
          "human_visual_review":False,
          "scene_count":5,"scene_sha256":hashes,
          "production_order":number,"publication":"not_performed",
          "limitations":"Automated checks do not establish narrative/anatomy/rights quality."
        }
        (folder/"original-art-provenance.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return {"number":number,"scenes":5,"status":"generated_unreviewed",
                "upload_attempts":0}
    except Exception:
        # Do not mistake partial images for a complete episode on a retry.
        for p in art: p.unlink(missing_ok=True)
        raise

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--number",type=int,required=True)
    args=ap.parse_args()
    print(json.dumps(generate(args.number),ensure_ascii=False))
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ImageBlocked,ValueError,OSError,RuntimeError) as exc:
        raise SystemExit("[OTAKU BR IMAGE BLOCKED] "+str(exc)) from None
