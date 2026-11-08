#!/usr/bin/env python3
"""Single fully original AutoEditorVideo Short: render with exact alchemy identity.

Separate image-generation job, no YouTube OAuth. Public upload is downstream
and never called unless all QA checks, hashes and channel identity succeed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import five_channel_fifteen_20261108 as base
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from kids_static_90s_20261107 import digest

MANIFEST=ROOT/"conteudos"/"alchemy-publico-direto-20261108.json"
OUT=ROOT/"cloud-alchemy-publico-direto-20261108"
OWNER="public_single_alchemy_20261108"
EP_ID="alchemy-107-automacao-publicou-duplicado"
CHANNEL="alchemy"
WORKFLOW="AutoEditorVideo - Alchemy original direct-public trial"
MODEL="gpt-image-2"
BUDGET=8
base.engine.OUTPUT_ROOT=OUT
base.engine.IMAGE_MODEL=MODEL
base.engine.prompt=base.art_prompt

class PilotBlocked(ValueError):pass

def output()->Path:
    return OUT/CHANNEL

def validate()->dict:
    doc=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (doc.get("schema")!="autoeditorvideo/single-public-original-20261108/v1"
            or doc.get("production_owner")!=OWNER
            or doc.get("channel")!=CHANNEL
            or doc.get("channel_id")!=KNOWN_IDS[CHANNEL]
            or doc.get("images_budget")!=BUDGET
            or doc.get("publication_intent")!="public"
            or doc.get("never_touch_existing_videos") is not True
            or doc.get("never_blind_retry_upload") is not True
            or len(doc.get("episodes",[]))!=1):
        raise PilotBlocked("ORIGINAL_PUBLIC_MANIFEST_CHANGED")
    e=doc["episodes"][0]
    assert_reserved(CHANNEL,EP_ID,OWNER)
    if (e.get("id")!=EP_ID or e.get("channel")!=CHANNEL
            or e.get("channel_id")!=KNOWN_IDS[CHANNEL]
            or e.get("language")!="pt-BR"
            or e.get("made_for_kids") is not False
            or e.get("visibility_intent")!="direct_public_on_new_upload_only_after_technical_QA"
            or e.get("creator_explicit_publication_authorized") is not True
            or e.get("production_state",{}).get("upload")!="not_started"
            or e.get("production_state",{}).get("youtube_id") is not None
            or len(e.get("scenes",[]))!=8
            or [s.get("number") for s in e["scenes"]]!=list(range(1,9))
            or not all(len(s.get("visual_instruction",""))>90 for s in e["scenes"])
            or e.get("narration_script")!=" ".join(s["editorial_beat"] for s in e["scenes"])
            or not 240<=len(e["narration_script"].split())<=320
            or not 10<=len(e.get("title",""))<=100
            or not 5<=len(e.get("cover_text",""))<=42
            or len(",".join(e.get("tags",[])))>500
            or "conceituais" not in e.get("description","").lower()):
        raise PilotBlocked("EDITORIAL_STORY_OR_PUBLIC_PERMISSION_MISMATCH")
    return e

def guard()->None:
    env=os.environ
    if (env.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or env.get("GITHUB_REF")!="refs/heads/main"
        or env.get("GITHUB_EVENT_NAME")!="push"
        or env.get("GITHUB_RUN_ATTEMPT")!="1"
        or env.get("GITHUB_WORKFLOW")!=WORKFLOW
        or env.get("PUBLIC_PILOT_RENDER_AUTHORIZED")!="yes"
        or env.get("IMAGE_MODEL")!=MODEL
        or env.get("MAX_IMAGE_CALLS")!=str(BUDGET)):
        raise PilotBlocked("FIRST_MAIN_PUSH_IMAGE_BUDGET_OR_CHANNEL_GUARD")
    if any(env.get(k) for k in ("YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
        "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON","YOUTUBE_GAMES_TOKEN_JSON",
        "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON")):
        raise PilotBlocked("YOUTUBE_SECRETS_FORBIDDEN_IN_IMAGE_RENDER")

def produce()->None:
    guard()
    e=validate()
    out=output()
    if out.exists():
        raise PilotBlocked("OUTPUT_ALREADY_EXISTS_PREVENT_REGENERATION")
    folder=out/EP_ID
    folder.mkdir(parents=True,exist_ok=False)
    voice,sec,words=base.engine.voice_takes(e,folder,CHANNEL)
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    frames=base.engine.images(e,folder,key,CHANNEL)
    result=base.engine.render_one(e,folder,voice,sec,words,frames,CHANNEL)
    qa_path=folder/"qa.json"
    metadata_path=folder/"metadata.json"
    qa=json.loads(qa_path.read_text(encoding="utf-8"))
    metadata=json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["privacyStatus"]="public"
    metadata["publication_method"]="videos.insert(status.privacyStatus=public)"
    metadata["explicit_creator_public_approval"]=True
    metadata["never_duplicate_previous_upload"]=True
    metadata["selfDeclaredMadeForKids"]=False
    qa["public_direct_upload_authorized"]=True
    qa["manual_visual_review"]=False
    qa["image_count"]=8
    qa["publication_state"]="rendered_not_uploaded"
    qa["pilot_id"]=EP_ID
    qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    metadata_path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={
      "schema":"autoeditorvideo/public-single-original-render/v1",
      "owner":OWNER,"channel":CHANNEL,"channel_id":KNOWN_IDS[CHANNEL],
      "episode_id":EP_ID,"render_engine":"AutoEditorVideo/ArquivoOtakuMaster",
      "video_count":1,"artifact_state":"rendered_upload_not_performed",
      "technical_qa":"passed","video":result,
      "mp4_sha256":digest(folder/"final.mp4"),"cover_sha256":digest(folder/"thumb.jpg")
    }
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for scratch in folder.glob("tts-*"):
        if scratch.is_dir():shutil.rmtree(scratch)
    (folder/"props.json").unlink(missing_ok=True)
    print("AUTOEDITOR_ALCHEMY_ONE_NEW_SHORT_RENDER_QA_PASSED_"+EP_ID,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("validate","render"),default="validate")
    args=p.parse_args()
    try:
        if args.action=="validate":
            print("AUTOEDITOR_ALCHEMY_PUBLIC_READY_"+validate()["id"])
        else:
            produce()
        return 0
    except Exception as e:
        message=str(e) if isinstance(e,PilotBlocked) else type(e).__name__
        print("AUTOEDITOR_ALCHEMY_RENDER_BLOCKED_"+message,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
