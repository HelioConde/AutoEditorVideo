#!/usr/bin/env python3
"""READ-ONLY verify any V3 private uploads after the initial ambiguous error.

No videos.insert, no thumbnails.set, no status updates, no image-generation.
Checks exclusive OAuth channel identity and last ~300 uploads for V3 marker.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
from games_alchemy_ai_upload import get_youtube
from games_alchemy_native_v3_upload import EXPECTED, recent_private_v3
from youtube_channel_registry import KNOWN_IDS

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"v3-safe-reconciliation-audit"
OWNER="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - V3 read-only upload reconciliation"

class AuditBlocked(ValueError):pass

def audit(channel:str)->dict:
    e=dict(os.environ)
    if (e.get("GITHUB_REPOSITORY")!=OWNER or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise AuditBlocked("ONE_SHOT_MAIN_PROTECTED_AUDIT_ONLY")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise AuditBlocked("NO_CHANNEL_OAUTH_SECRET")
    youtube=get_youtube(channel,e)
    result=youtube.channels().list(part="snippet",mine=True).execute()
    channels=result.get("items",[])
    if len(channels)!=1 or channels[0].get("id")!=KNOWN_IDS[channel]:
        raise AuditBlocked("CHANNEL_ID_MISMATCH")
    expected=EXPECTED[channel]
    manifest=json.loads((ROOT/"conteudos"/"lote-6-games-alchemy-recut-v2.json").read_text(encoding="utf-8"))
    originals={j["source_episode_id"]:j for j in manifest["projects"]}
    records=[]
    for vid in expected:
        source=vid.removesuffix("-v3")
        job=originals[source]
        ids=recent_private_v3(youtube,channel,job["title"])
        records.append({"episode":vid,"original_title":job["title"],"matching_v3_private_youtube_ids":ids,
                        "status":"already_present" if ids else "not_found_in_recent_300"})
    OUTPUT.mkdir(parents=True,exist_ok=True)
    report={"channel":channel,"channel_id":KNOWN_IDS[channel],
            "purpose":"read_only_reconciliation_after_initial_ambiguous_upload",
            "total_expected":3,"found":sum(bool(x["matching_v3_private_youtube_ids"]) for x in records),
            "episodes":records,"no_video_insert_performed":True}
    (OUTPUT/f"{channel}.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"V3_READ_ONLY_AUDIT_{channel}_found_{report['found']}_of_3",flush=True)
    for row in records:
        print(f"V3_PRIVATE_RECONCILE_{row['episode']}_{row['status']}",flush=True)
    return report

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=tuple(EXPECTED),required=True)
    args=p.parse_args()
    try:
        audit(args.channel)
        return 0
    except Exception as e:
        print("V3_READ_ONLY_AUDIT_BLOCKED_"+(str(e) if isinstance(e,AuditBlocked) else type(e).__name__),file=sys.stderr)
        return 2
if __name__=="__main__":raise SystemExit(main())
