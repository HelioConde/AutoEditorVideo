#!/usr/bin/env python3
"""Read-only YouTube status verification of 16 exact uploaded videos, five channels.

No upload/delete/privacy edits/thumbnail calls. OAuth only to list authenticated
channel identity and video statuses. Sanitized result: IDs, titles, privacy,
processing state, duration, audience and ownership, never credentials.
"""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"conteudos"/"youtube-other-videos-readonly-check-20261108.json"
WORKFLOW="AutoEditorVideo - read-only audit of other videos across 5 channels"
RESULTS=ROOT/"youtube-other-video-audit-results"

class AuditBlocked(ValueError):pass

def guard(channel:str)->dict:
    env=os.environ
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/five-channel-other-videos-readonly/v1"
            or d.get("source")!="creator_verification_request_2026-11-08"
            or sorted(d.get("channels",{}))!=["alchemy","br","en","games","kids"]
            or d.get("write_actions_permitted") is not False
            or d.get("allow_video_delete") is not False
            or d.get("allow_visibility_change") is not False):
        raise AuditBlocked("READ_ONLY_MANIFEST_CHANGED")
    cfg=d["channels"].get(channel)
    if not cfg or not cfg.get("channel_id","").startswith("UC"):
        raise AuditBlocked("CHANNEL_NOT_IN_EXACT_AUDIT_MANIFEST")
    from youtube_channel_registry import KNOWN_IDS
    if KNOWN_IDS[channel]!=cfg["channel_id"]:
        raise AuditBlocked("EXACT_CHANNEL_ID_MISMATCH")
    videos=cfg["videos"]
    if (not 1<=len(videos)<=20 or len({x["id"] for x in videos})!=len(videos)
            or any(not isinstance(x.get("name"),str) or len(x["id"])!=11
                   for x in videos)):
        raise AuditBlocked("WRONG_OR_DUPLICATE_VIDEO_ID")
    if (env.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or env.get("GITHUB_REF")!="refs/heads/main"
            or env.get("GITHUB_EVENT_NAME")!="push"
            or env.get("GITHUB_RUN_ATTEMPT")!="1"
            or env.get("GITHUB_WORKFLOW")!=WORKFLOW
            or env.get("CHANNEL_READONLY_AUDIT_AUTHORIZED")!="yes"
            or env.get("AUDIT_CHANNEL")!=channel
            or not env.get("YOUTUBE_CLIENT_JSON")
            or not env.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise AuditBlocked("MAIN_ONLY_AUTHENTICATED_READONLY_AUDIT_REQUIRED")
    if any(env.get(n) for n in ("YOUTUBE_BR_DELETE_TOKEN_JSON",
                                 "PROXY_ACCOUNTS_JSON","PROXY_API_KEY")):
        raise AuditBlocked("DELETE_OR_IMAGE_CREDENTIALS_FORBIDDEN")
    return cfg

def client():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    try:
        data=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        token=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
        parent=data.get("installed") or data.get("web") or {}
        if (not parent.get("client_id") or parent.get("client_id")!=token.get("client_id")
                or not token.get("refresh_token")):
            raise AuditBlocked("OAUTH_CLIENT_AND_TOKEN_MISMATCH")
        scopes=token.get("scopes",[])
        scopes=set(scopes.split()) if isinstance(scopes,str) else set(scopes)
        if "https://www.googleapis.com/auth/youtube.readonly" not in scopes:
            raise AuditBlocked("YOUTUBE_READONLY_SCOPE_REQUIRED")
        credentials=Credentials.from_authorized_user_info(token,scopes=list(scopes))
        if not credentials.valid:credentials.refresh(Request())
        return build("youtube","v3",credentials=credentials,cache_discovery=False)
    except AuditBlocked:raise
    except Exception:
        raise AuditBlocked("GOOGLE_READONLY_AUTH_FAILED") from None

def audit(channel:str):
    cfg=guard(channel)
    yt=client()
    own=yt.channels().list(part="id",mine=True).execute().get("items",[])
    if len(own)!=1 or own[0].get("id")!=cfg["channel_id"]:
        raise AuditBlocked("AUTHENTICATED_YOUTUBE_CHANNEL_WRONG")
    ids=[v["id"] for v in cfg["videos"]]
    result=yt.videos().list(part="snippet,status,contentDetails,processingDetails",
                            id=",".join(ids)).execute().get("items",[])
    actual={v["id"]:v for v in result}
    report={"schema":"autoeditorvideo/youtube-five-channel-readonly-result/v1",
            "channel":channel,"channel_id":cfg["channel_id"],
            "queried_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read_only":True,"videos":[]}
    for entry in cfg["videos"]:
        id=entry["id"]
        v=actual.get(id)
        if not v:
            row={"id":id,"name":entry["name"],"api_result":"not_returned_by_authenticated_api"}
        else:
            sn=v.get("snippet",{})
            st=v.get("status",{})
            pd=v.get("processingDetails",{})
            cd=v.get("contentDetails",{})
            row={"id":id,"name":entry["name"],"api_result":"found",
                 "owned_by_authenticated_channel":sn.get("channelId")==cfg["channel_id"],
                 "title":sn.get("title"),
                 "privacy_status":st.get("privacyStatus"),
                 "upload_status":st.get("uploadStatus"),
                 "processing_status":pd.get("processingStatus"),
                 "processing_failure_reason":pd.get("processingFailureReason"),
                 "upload_failure_reason":st.get("failureReason"),
                 "rejection_reason":st.get("rejectionReason"),
                 "duration":cd.get("duration"),
                 "made_for_kids":st.get("madeForKids"),
                 "published_at":sn.get("publishedAt")}
        report["videos"].append(row)
        print("YOUTUBE_READONLY_OTHER_"+channel+"_"+id+"_"+
              str(row.get("privacy_status","missing"))+"_"+
              str(row.get("upload_status","missing"))+"_"+
              str(row.get("processing_status","missing")),flush=True)
    RESULTS.mkdir(parents=True,exist_ok=True)
    (RESULTS/(channel+".json")).write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("YOUTUBE_READONLY_OTHER_"+channel.upper()+"_AUDIT_OK",flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",choices=["en","games","alchemy","br","kids"],required=True)
    a=ap.parse_args()
    try:audit(a.channel)
    except Exception as exc:
        msg=str(exc) if isinstance(exc,AuditBlocked) else type(exc).__name__
        print("YOUTUBE_READONLY_OTHER_BLOCKED_"+msg,file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
