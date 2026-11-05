#!/usr/bin/env python3
"""Read-only owner audit of six V4 and six V3 YouTube uploads.

Diagnoses "O processamento vai começar em breve"/"Retomar o envio".
Only YouTube videos.list + channels.list; never calls videos.insert/update/delete,
never uploads thumbnails, never changes video visibility. No credentials logged.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from games_alchemy_ai_upload import get_youtube
from youtube_channel_registry import KNOWN_IDS
from googleapiclient.errors import HttpError

IDS={
    "games":{
        "v3":["4n3hrBv3anw","hDKdl0cxtKM","cNrnzmzo50Y"],
        "v4":["CY9v9742DqY","vG5tqbqirRo","0PzFrTqWUQk"],
    },
    "alchemy":{
        "v3":["egIProzaeAs","RUm9CkeAMdw","wIqABXUU8LA"],
        "v4":["xeABjVrX09U","Vg1QNyPbN7s","ujhj3LgdqVc"],
    }
}
OUTPUT=ROOT/"youtube-v3-v4-processing-audit"
WORKFLOW="Gamer + Alchemy - read only YouTube processing status audit"
class AuditError(ValueError):pass

def guard(channel:str)->None:
    e=os.environ
    if (channel not in IDS or
        e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise AuditError("ONLY_PROTECTED_READ_ONLY_MAIN_PUSH_ALLOWED")
    if e.get("READ_ONLY_PROCESSING_AUDIT_APPROVED")!="true":
        raise AuditError("APPROVED_DIAGNOSTIC_MARKER_MISSING")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise AuditError("CANNOT_ACCESS_OWNER_VIDEO_STATUS")

def audit(channel:str)->None:
    guard(channel)
    api=get_youtube(channel,dict(os.environ))
    identity=api.channels().list(part="id",mine=True).execute()
    if [o["id"] for o in identity.get("items",[])] != [KNOWN_IDS[channel]]:
        raise AuditError("OAUTH_CHANNEL_ID_MISMATCH")
    report={"channel":channel,"channel_id":KNOWN_IDS[channel],"read_only":True,
            "sources":["YouTube videos.list(status,processingDetails,contentDetails,fileDetails)"],
            "videos":[]}
    for version, ids in IDS[channel].items():
        data=api.videos().list(part="id,status,processingDetails,contentDetails,fileDetails",
                               id=",".join(ids)).execute()
        index={v["id"]:v for v in data.get("items",[])}
        for vid in ids:
            item=index.get(vid,{})
            status=item.get("status",{})
            processing=item.get("processingDetails",{})
            fileinfo=item.get("fileDetails",{})
            report["videos"].append({
                "version":version,"video_id":vid,
                "found":bool(item),
                "privacy":status.get("privacyStatus"),
                "upload_status":status.get("uploadStatus"),
                "failure_reason":status.get("failureReason"),
                "rejection_reason":status.get("rejectionReason"),
                "processing_status":processing.get("processingStatus"),
                "processing_failure_reason":processing.get("processingFailureReason"),
                "progress":processing.get("processingProgress"),
                "file_details_availability":processing.get("fileDetailsAvailability"),
                "duration_seconds":item.get("contentDetails",{}).get("duration"),
                "file_size_bytes":fileinfo.get("fileSize"),
                "file_name":fileinfo.get("fileName") if fileinfo.get("fileName","").endswith(".mp4") else None,
                "has_custom_thumbnail":item.get("contentDetails",{}).get("hasCustomThumbnail")
            })
    OUTPUT.mkdir(parents=True,exist_ok=True)
    out=OUTPUT/f"{channel}.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for row in report["videos"]:
        print(f"YT_UPLOAD_STATUS channel={channel} version={row['version']} id={row['video_id']} "
              f"found={row['found']} upload={row['upload_status']} processing={row['processing_status']} "
              f"duration={row['duration_seconds']} filesize={row['file_size_bytes']} "
              f"file_available={row['file_details_availability']} reason={row['processing_failure_reason'] or row['failure_reason']}",flush=True)
    print("PROCESSING_DIAGNOSTICS_READ_ONLY_NO_UPLOADS_PERFORMED",flush=True)

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--channel",choices=list(IDS),required=True)
    args=parser.parse_args()
    try:
        audit(args.channel)
        return 0
    except Exception as exc:
        if isinstance(exc,AuditError): reason=str(exc)
        elif isinstance(exc,HttpError): reason="YOUTUBE_HTTP_"+str(getattr(exc.resp,"status","unknown"))
        else:reason=type(exc).__name__
        print("PROCESSING_AUDIT_BLOCKED_"+reason,file=sys.stderr)
        return 2
if __name__=="__main__":raise SystemExit(main())
