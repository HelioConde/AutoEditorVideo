#!/usr/bin/env python3
"""One-shot isolated batch of 15 NEW original Shorts, all private at first."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import remaining_static_90s_20261107 as ordinary
import remaining_static_90s_upload_20261107 as ordinary_upload
import kids_static_90s_20261107 as kids
import kids_static_90s_upload_20261107 as kids_upload
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS

MANIFEST=ROOT/"conteudos"/"lote-15-canais-20261108.json"
LAUNCH=ROOT/"conteudos"/"lote-15-canais-20261108-launch.json"
OWNER="lote15_novos_20261108"
WORKFLOW="AutoEditorVideo - 15 new original Shorts five verified channels private"
OUT=ROOT/"cloud-next-fifteen-20261108"
CHANNELS=("br","en","games","kids","alchemy")
EXPECTED={
 "br":("5015-jujutsu-kaisen-dominio","5016-dungeon-meshi-masmorra","5017-attack-on-titan-muralhas"),
 "en":("7014-fullmetal-troca-equivalente","7015-one-piece-poneglyphs","7016-hunter-nen-restricoes"),
 "games":("game-104-terraria-primeira-noite","game-105-stardew-estacoes","game-106-celeste-dificuldade"),
 "kids":("kids-104-abelhinha-e-as-cores","kids-105-tartaruguinha-e-a-chuva","kids-106-estrelinhas-contam"),
 "alchemy":("alchemy-104-automacao-gatilhos","alchemy-105-agentes-supervisao","alchemy-106-ia-checagem-fontes")
}

class BatchBlocked(ValueError):
    pass

def manifest() -> dict:
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/new-15-five-channels-editorial-v1"
            or d.get("production_owner")!=OWNER
            or d.get("requested_total")!=15 or d.get("per_channel")!=3
            or d.get("channels")!=list(CHANNELS)
            or d.get("default_visibility")!="private"
            or len(d.get("episodes",[]))!=15):
        raise BatchBlocked("WRONG_BATCH_OR_NOT_EXACT_FIFTEEN")
    keys=[(x["channel"],x["id"]) for x in d["episodes"]]
    if (len(set(keys))!=15 or keys!=[(c,i) for c in CHANNELS for i in EXPECTED[c]]):
        raise BatchBlocked("WRONG_ORDER_OR_DUPLICATE_EPISODE")
    return d

def validate(channel: str) -> list[dict]:
    if channel not in CHANNELS:
        raise BatchBlocked("UNKNOWN_CHANNEL")
    d=manifest()
    rows=[x for x in d["episodes"] if x["channel"]==channel]
    if tuple(x["id"] for x in rows)!=EXPECTED[channel]:
        raise BatchBlocked("EXPECTED_THREE_IDS_MISSING")
    for row in rows:
        assert_reserved(channel,row["id"],OWNER)
        if (row["channel_id"]!=KNOWN_IDS[channel]
                or row["language"]!=("en-US" if channel=="en" else "pt-BR")
                or row["made_for_kids"] is not (channel=="kids")
                or row["visibility_intent"]!="private_first_after_QA"
                or row.get("production_state",{}).get("upload")!="not_started"
                or row.get("production_state",{}).get("youtube_id") is not None):
            raise BatchBlocked("CHANNEL_AUDIENCE_STATUS_OR_ROUTING_INCONSISTENT")
        title=row.get("title","")
        scenes=row.get("scenes",[])
        script=row.get("narration_script","")
        tags=row.get("tags",[])
        if (not 12<=len(title)<=100 or not 1<=len(row.get("cover_text",""))<=42
                or not row.get("description") or not 5<=len(tags)<=20
                or len(",".join(tags))>500 or len(scenes)!=8
                or [s["number"] for s in scenes]!=list(range(1,9))
                or any(not s.get("editorial_beat") or not s.get("visual_instruction") for s in scenes)
                or script!=" ".join(s["editorial_beat"] for s in scenes)
                or not 235<=len(script.split())<=380):
            raise BatchBlocked("NARRATION_IMAGES_OR_METADATA_INCOMPLETE_"+row["id"])
        if any("autoeditorvideo" in t.casefold() for t in tags):
            raise BatchBlocked("TECHNICAL_TAG_FORBIDDEN")
        if channel=="games" and "não são capturas de gameplay" not in row["description"].lower():
            raise BatchBlocked("GAMEPLAY_AI_DISCLOSURE_MISSING")
        if channel=="kids":
            if any(word in script.casefold() for word in ("fofinho","fofinhos","emanuelly")):
                raise BatchBlocked("FOFINHOS_SEPARATE_SERIES")
        if channel in ("br","en"):
            # Conceptual anime lore only: NEVER generate or depict named characters without real anchors.
            if any(name in script.casefold() for name in (
               "jinwoo","isagi","maomao","luffy","frieren","light yagami","gojo","sukuna",
               "edward elric","gon freecss","killua","tanjiro","eren yeager")):
                raise BatchBlocked("NAMED_CHARACTER_REQUIRES_IMAGE_ANCHORS")
    return rows

def verify_launch() -> None:
    launch=json.loads(LAUNCH.read_text(encoding="utf-8"))
    if launch!={"schema":"autoeditorvideo/one-shot-fifteen-private/v1",
               "production_owner":OWNER,
               "creator_request_date":"2026-11-08",
               "channels":list(CHANNELS),
               "episodes":{k:list(v) for k,v in EXPECTED.items()},
               "visibility":"private",
               "max_images_per_channel":24,
               "no_blind_reupload":True,
               "manual_visual_review_before_public":True}:
        raise BatchBlocked("LAUNCH_AUTHORIZATION_MISMATCH")
    for c in CHANNELS:
        validate(c)

def image_prompt(row:dict,scene:dict,channel:str)->str:
    mode=("premium original abstract anime-world environment and meaningful symbolic objects, NO human characters"
          if channel in ("br","en") else
          "premium original game-inspired art, NEVER a gameplay screenshot or fake in-game interface"
          if channel=="games" else
          "premium original educational technology conceptual illustration, NEVER a fabricated application screenshot")
    return ("One ORIGINAL 9:16 cinematic STILL illustration 1024x1536 with no text, logo, watermark, "
            "graphics, labels, gibberish, frame borders, UI, official media footage or recognizable licensed "
            "character. Composition safe for headline above and subtitles below. "
            "No deforming people, no copied anime frames. Consistent palette, detailed expressive scenery. "
            +mode+". Topic: "+row["title"]+". Frame "+str(scene["number"])+": "+
            scene["visual_instruction"]+". Narration concept: "+scene["editorial_beat"])

def safe_kids_render() -> None:
    e=os.environ
    if any((e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo",
            e.get("GITHUB_REF")!="refs/heads/main",
            e.get("GITHUB_EVENT_NAME")!="push",
            e.get("GITHUB_RUN_ATTEMPT")!="1",
            e.get("GITHUB_WORKFLOW")!=WORKFLOW,
            e.get("KIDS_BATCH_AUTHORIZED")!="yes",
            e.get("IMAGE_MODEL")!="gpt-image-2",
            e.get("MAX_IMAGE_CALLS")!="24",
            bool(e.get("YOUTUBE_CLIENT_JSON")),
            bool(e.get("YOUTUBE_CHANNEL_TOKEN_JSON")))):
        raise BatchBlocked("KIDS_IMAGE_JOB_NOT_AUTHORIZED_OR_CROSS_SECRET")

def safe_kids_upload() -> None:
    e=os.environ
    if any((e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo",
            e.get("GITHUB_REF")!="refs/heads/main",
            e.get("GITHUB_EVENT_NAME")!="push",
            e.get("GITHUB_RUN_ATTEMPT")!="1",
            e.get("GITHUB_WORKFLOW")!=WORKFLOW,
            e.get("KIDS_UPLOAD_AUTHORIZED")!="yes",
            not e.get("YOUTUBE_CLIENT_JSON"),
            not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"),
            bool(e.get("YOUTUBE_BR_TOKEN_JSON")),
            bool(e.get("PROXY_ACCOUNTS_JSON")),
            kids_upload.RECEIPTS.exists())):
        raise BatchBlocked("KIDS_YOUTUBE_UPLOAD_NOT_EXACT_PRIVATE_AUTHORIZATION")

def install_channel_adapters() -> None:
    ordinary.PLAN=MANIFEST
    ordinary.OWNER=OWNER
    ordinary.WORKFLOW=WORKFLOW
    ordinary.EXPECTED={c:EXPECTED[c] for c in CHANNELS if c!="kids"}
    ordinary.OUTPUT_ROOT=OUT
    ordinary.VOICES["br"]="pt-BR-AntonioNeural"
    ordinary.CATEGORY["br"]="24"
    ordinary.PROFILE["br"]="original"
    ordinary.COVER["br"]="default"
    ordinary.validate=validate
    ordinary.prompt=image_prompt

    ordinary_upload.OWNER=OWNER
    ordinary_upload.EXPECTED=ordinary.EXPECTED
    ordinary_upload.TOKENS["br"]="YOUTUBE_BR_TOKEN_JSON"
    ordinary_upload.WORKFLOW=WORKFLOW
    ordinary_upload.validate=validate
    ordinary_upload.output=ordinary.output

    kids.OWNER=OWNER
    kids.OUT=OUT/"kids"
    kids.IDS=EXPECTED["kids"]
    kids.PLAN=MANIFEST
    kids.check_manifest=lambda:validate("kids")
    kids.safe_environment=safe_kids_render
    kids_upload.OUT=kids.OUT
    kids_upload.RECEIPTS=kids.OUT/"kids-private-youtube-receipts.json"
    kids_upload.check_manifest=kids.check_manifest
    kids_upload.guard=safe_kids_upload

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("validate","render","upload"),required=True)
    p.add_argument("--channel",choices=(*CHANNELS,"all"),required=True)
    a=p.parse_args()
    try:
        verify_launch()
        install_channel_adapters()
        if a.action=="validate":
            print("NEXT_FIFTEEN_RESERVED_VALIDATED_"+a.channel,flush=True)
        elif a.channel=="all":
            raise BatchBlocked("RENDER_AND_UPLOAD_REQUIRE_ONE_ISOLATED_CHANNEL")
        elif a.action=="render":
            if a.channel=="kids":
                kids.render_all()
            else:
                ordinary.produce(a.channel)
        elif a.channel=="kids":
            kids_upload.upload()
        else:
            ordinary_upload.upload(a.channel)
        return 0
    except Exception as exc:
        message=str(exc) if isinstance(exc,BatchBlocked) else type(exc).__name__
        print("NEXT_FIFTEEN_BLOCKED_"+message,file=sys.stderr,flush=True)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
