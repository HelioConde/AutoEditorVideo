#!/usr/bin/env python3
"""Otaku Multicena: exactly 3 original BR 90-120s Shorts, public after QA.

Shares the existing AutoEditorVideo/Remotion still-image renderer and the
official caption+thumbnail engines with previous channel batches. Never
touches the paused 50-video queue, anime copyright footage or other channels.
"""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import remaining_static_90s_20261107 as renderer
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS

MANIFEST=ROOT/"conteudos"/"otaku-br-three-public-20261107.json"
OUTPUT_ROOT=ROOT/"cloud-otaku-br-public-three-20261107"
OWNER="otaku_br_3_public_20261107"
CHANNEL="br"
CHANNEL_ID="UCXGYTuBYn-0Ziqin5ajKhOw"
IDS=("5012-solo-leveling-igris","5013-blue-lock-isagi","5014-mob-psycho-emocoes")
WORKFLOW="Otaku Multicena BR - three original 90s Shorts public"
MODEL="gpt-image-2"
PER_VIDEO_CALLS=8
MAX_CALLS=24

# Reuse the successful AutoEditorVideo media engine, without changing the
# standalone EN, Gamer, Alchemy configurations or their render/upload plans.
renderer.VOICES["br"]="pt-BR-AntonioNeural"
renderer.CATEGORY["br"]="24"
renderer.PROFILE["br"]="original"
renderer.COVER["br"]="default"
renderer.OUTPUT_ROOT=OUTPUT_ROOT

class BRBlocked(ValueError):
    pass

def output()->Path:
    return OUTPUT_ROOT/CHANNEL

def validate()->list[dict]:
    data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (data.get("schema")!="autoeditorvideo/otaku-br-3-public-20261107/v1"
            or data.get("production_owner")!=OWNER
            or data.get("channel")!="br"
            or data.get("channel_id")!=CHANNEL_ID
            or KNOWN_IDS.get("br")!=CHANNEL_ID
            or data.get("target_total")!=3
            or data.get("publication_target")!="public_after_automated_technical_QA"
            or data.get("requested_by_creator_publication") is not True
            or data.get("unrelated_queue_50_paused_and_untouched") is not True
            or data.get("excludes")!=["en","games","kids","alchemy"]
            or data.get("max_image_requests_per_short")!=PER_VIDEO_CALLS):
        raise BRBlocked("MANIFEST_OWNER_PUBLICATION_OR_CHANNEL_MISMATCH")
    rows=data.get("episodes",[])
    if tuple(r.get("id") for r in rows)!=IDS:
        raise BRBlocked("EXPECTED_EXACT_3_NEW_BR_EPISODES")
    titles=set()
    for row in rows:
        assert_reserved(CHANNEL,row["id"],OWNER)
        if (row.get("channel")!=CHANNEL or row.get("channel_id")!=CHANNEL_ID
                or row.get("language")!="pt-BR"
                or row.get("made_for_kids") is not False
                or row.get("visibility_intent")!="public_after_automated_qa"
                or row.get("production_state",{}).get("youtube_id") is not None):
            raise BRBlocked("DESTINATION_OR_ALREADY_UPLOADED_GUARD")
        title=row.get("title","")
        if not 15<=len(title)<=100 or title.casefold() in titles:
            raise BRBlocked("TITLE_DUPLICATE_OR_INVALID")
        titles.add(title.casefold())
        if not 1<=len(row.get("cover_text",""))<=42 or not row.get("description"):
            raise BRBlocked("SEO_NOT_READY")
        if ("geradas por IA" not in row["description"]
                and "produzidas por IA" not in row["description"]):
            raise BRBlocked("AI_ART_DISCLOSURE_MISSING")
        tags=row.get("tags",[])
        if len(tags)<8 or len(",".join(tags))>500 or any(
                t.lower().startswith(("autoeditorvideo","5012-","5013-","5014-"))
                for t in tags):
            raise BRBlocked("PUBLIC_TAG_LIMIT_OR_TECHNICAL_TAG")
        scenes=row.get("scenes",[])
        if (len(scenes)!=8
                or [s.get("number") for s in scenes]!=list(range(1,9))
                or any(not s.get("editorial_beat") or not s.get("visual_instruction")
                       for s in scenes)
                or row.get("narration_script")!=" ".join(s["editorial_beat"] for s in scenes)
                or not 245<=len(row["narration_script"].split())<=350):
            raise BRBlocked("NARRATION_OR_8_STORY_BEATS_INVALID")
        if not row.get("visual_bible") or not row.get("topic_source_urls"):
            raise BRBlocked("VISUAL_BIBLE_OR_FACT_CHECK_MISSING")
    return rows

def guard()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("OTAKU_BR_THREE_RENDER_AUTHORIZED")!="yes"
            or e.get("IMAGE_MODEL")!=MODEL
            or e.get("MAX_IMAGE_CALLS")!=str(MAX_CALLS)):
        raise BRBlocked("ONE_SHOT_OR_IMAGE_BUDGET_GUARD_FAILED")
    if any(e.get(k) for k in ("YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
                             "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                             "YOUTUBE_KIDS_TOKEN_JSON")):
        raise BRBlocked("OAUTH_TOKENS_FORBIDDEN_IN_IMAGE_RENDER")

def art_prompt(row:dict,scene:dict)->str:
    return (
        "Create ONE original premium cinematic anime-inspired editorial "
        "STILL ILLUSTRATION in portrait 1024x1536. This is NOT an official anime "
        "frame or screenshot, not footage and not a reproduction of any existing "
        "copyrighted character design. Use entirely fresh fictional silhouettes, "
        "costume designs, settings and props. No title/text, numerals, logos, "
        "watermarks, manga panel gutters, UI or player overlays. "
        "Keep expressive main subject inside central 65 percent height; "
        "top and bottom must be clean for official AutoEditorVideo captions. "
        "Natural limbs, no extra fingers, duplicated heads, mangled faces, "
        "merged weapons, warped anatomy, or cropped key subjects. "
        "A single frozen moment, not an animation storyboard. "
        "Make eight distinctly composed scenes with the same episode palette. "
        "Visual bible: "+row["visual_bible"]+
        " This exact scene's visible story concept: "+scene["visual_instruction"]
    )

def create_art(row:dict,folder:Path,key:str)->list[Path]:
    from PIL import Image,ImageOps
    from gerar_video_codex import request_image
    result=[]
    for n,scene in enumerate(row["scenes"],1):
        dest=folder/("scene-%02d.png"%n)
        if dest.exists():
            raise BRBlocked("EXISTING_IMAGE_CACHE_NOT_AUTHORIZED")
        raw=request_image(art_prompt(row,scene),MODEL,key,"1024x1536")
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            if im.width<512 or im.height<768:
                raise BRBlocked("GENERATED_ART_TOO_SMALL")
            ImageOps.pad(im.convert("RGB"),(1024,1536),
                         method=Image.Resampling.LANCZOS,
                         color=(15,16,24)).save(dest,"PNG")
        if dest.stat().st_size<30_000:
            raise BRBlocked("GENERATED_ART_BLANK_OR_DAMAGED")
        result.append(dest)
        print("BR_THREE_ART_"+row["id"]+"_%02d_OF_08"%n,flush=True)
    if len({renderer.digest(x) for x in result})!=8:
        raise BRBlocked("DUPLICATED_AI_SCENES")
    return result

def produce()->None:
    guard()
    rows=validate()
    out=output()
    if out.exists():
        raise BRBlocked("OUTPUT_EXISTS_NO_REGENERATION")
    out.mkdir(parents=True)
    ready=[]
    for row in rows:
        folder=out/row["id"]
        folder.mkdir()
        voice,seconds,words=renderer.voice_takes(row,folder,"br")
        ready.append((row,folder,voice,seconds,words))
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    report={
        "schema":"autoeditorvideo/otaku-br-three-public-render/v1",
        "owner":OWNER,"channel":"br","channel_id":CHANNEL_ID,
        "target_count":3,"media_status":"rendered_and_QA_passed_not_uploaded",
        "render_engine":"AutoEditorVideo/ArquivoOtakuMaster",
        "caption_engine":"legendas_precisas/word-boundaries",
        "cover_engine":"capa_cinematografica/render_cover",
        "videos":[]
    }
    for row,folder,voice,sec,words in ready:
        imgs=create_art(row,folder,key)
        record=renderer.render_one(row,folder,voice,sec,words,imgs,"br")
        # Render helper is fail-safe with private default; public publication is
        # an independently authorized step that first uploads privately.
        meta_path=folder/"metadata.json"
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        meta["publication_target"]="public_after_youtube_processed_cover_qa"
        meta["creator_public_authorized"]=True
        meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",
                             encoding="utf-8")
        qa_path=folder/"qa.json"
        qa=json.loads(qa_path.read_text(encoding="utf-8"))
        qa["creator_public_authorized"]=True
        qa["manual_visual_review"]=False
        qa["automated_publication_gates"]=[
            "original_8_distinct_stills","original_editor_remotion",
            "genuine_90_to_120_second_voice","1080x1920_mp4_with_audio",
            "word_boundary_captions","canonical_cover","sha256_integrity",
            "correct_OAuth_BR_channel","youtube_processing_succeeded",
            "youtube_thumbnail_acknowledged","deduplicated_upload"
        ]
        qa_path.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",
                           encoding="utf-8")
        report["videos"].append(record)
        for img in imgs:img.unlink(missing_ok=True)
        for scratch in folder.glob("tts-*"):
            if scratch.is_dir():shutil.rmtree(scratch)
        (folder/"props.json").unlink(missing_ok=True)
        print("BR_THREE_READY_FOR_PUBLICATION_AFTER_QA_"+row["id"],flush=True)
    if len(report["videos"])!=3:
        raise BRBlocked("PARTIAL_RENDER_NOT_UPLOADABLE")
    (out/"summary.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                                    encoding="utf-8")
    print("BR_THREE_ORIGINAL_MP4_QA_READY",flush=True)

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--action",choices=("validate","render"),default="validate")
    args=parser.parse_args()
    try:
        if args.action=="validate":
            print("BR_THREE_RESERVED_EDITORIAL_OK_"+",".join(x["id"] for x in validate()))
        else:
            produce()
        return 0
    except Exception as exc:
        msg=str(exc) if isinstance(exc,BRBlocked) else type(exc).__name__
        print("BR_THREE_RENDER_BLOCKED_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
