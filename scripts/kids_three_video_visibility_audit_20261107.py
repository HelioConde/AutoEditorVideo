#!/usr/bin/env python3
"""Read-only YouTube API audit for three Emanuelly Kids video IDs.

This is NOT a renderer/uploader. It cannot create/delete/change YouTube videos.
Inspect owner, upload/processing statuses, visibility, contentDetails duration,
and upload-playlist presence to diagnose a creator seeing only two in Studio.
Never print access tokens, personal account info or full API error bodies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_channel_registry import KNOWN_IDS
from kids_static_90s_upload_20261107 import youtube_client

CHANNEL="kids"
EXPECTED_ID="UCxEzVW2Uy44OUVurTQSg_Eg"
IDS=("d7hjFP6Ky6w","ax0ude5BUhE","It-7R1o9k7Q")
NAMES=("O Elefantinho e a Água Escondida","Adivinhe o Animal pela Sombra",
       "3 Dinossauros com Segredos Incríveis")
DEST=Path("kids-three-studio-visibility-audit-20261107.json")

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!="Emanuelly Kids - diagnose 3 YouTube video visibility read only"
            or e.get("KIDS_READONLY_AUDIT_APPROVED")!="yes"):
        raise ValueError("KIDS_READONLY_AUDIT_UNAUTHORIZED")
    if (KNOWN_IDS["kids"]!=EXPECTED_ID
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise ValueError("EXPECTED_CHANNEL_OAUTH_UNAVAILABLE")
    if e.get("PROXY_API_KEY") or e.get("PROXY_ACCOUNTS_JSON"):
        raise ValueError("IMAGE_SECRETS_FORBIDDEN")
    check=json.loads(Path("conteudos/kids-three-studio-visibility-audit-20261107.json").read_text(encoding="utf-8"))
    if check != {
        "schema":"autoeditorvideo/kids-three-video-visibility-readonly/v1",
        "youtube_channel_id":EXPECTED_ID,"video_ids":list(IDS),
        "source_verification_run_id":42396980506,
        "allowed_operations":["channels.list","videos.list","playlistItems.list"],
        "videos_insert":False,"videos_update":False,"thumbnails_set":False,
        "new_image_generation":False
    }:
        raise ValueError("READONLY_AUDIT_MANIFEST_MISMATCH")

def inspect():
    guard()
    youtube=youtube_client()
    owned=youtube.channels().list(part="id,contentDetails",mine=True).execute()
    rows=owned.get("items") or []
    if len(rows)!=1 or rows[0].get("id")!=EXPECTED_ID:
        raise ValueError("KIDS_CHANNEL_OWNER_MISMATCH")
    uploads=rows[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not uploads:
        raise ValueError("OWN_UPLOADS_PLAYLIST_UNAVAILABLE")
    listing=[]
    next_page=None
    for _ in range(6):
        kwargs={"part":"contentDetails","playlistId":uploads,"maxResults":50}
        if next_page:kwargs["pageToken"]=next_page
        page=youtube.playlistItems().list(**kwargs).execute()
        listing.extend(x.get("contentDetails",{}).get("videoId")
                       for x in page.get("items",[])
                       if x.get("contentDetails",{}).get("videoId"))
        next_page=page.get("nextPageToken")
        if not next_page:break
    api=youtube.videos().list(
        part="snippet,status,contentDetails,processingDetails",
        id=",".join(IDS)
    ).execute()
    actual={v["id"]:v for v in api.get("items",[])}
    report={"schema":"autoeditorvideo/kids-three-video-visibility-audit-result/v1",
            "channel_id":EXPECTED_ID,"queried_video_ids":list(IDS),
            "upload_playlist_scan_complete":not bool(next_page),
            "upload_playlist_ids_checked":len(listing),
            "videos":[]}
    for vid,name in zip(IDS,NAMES):
        item=actual.get(vid)
        if not item:
            row={"id":vid,"short_title":name,"api_result":"video_id_not_returned",
                 "appears_in_uploads_playlist":vid in listing}
        else:
            snippet=item.get("snippet",{})
            status=item.get("status",{})
            details=item.get("processingDetails",{})
            content=item.get("contentDetails",{})
            row={
                "id":vid,"short_title":name,
                "api_result":"found",
                "matches_authenticated_channel":snippet.get("channelId")==EXPECTED_ID,
                "title":snippet.get("title"),
                "privacy_status":status.get("privacyStatus"),
                "upload_status":status.get("uploadStatus"),
                "failure_reason":status.get("failureReason"),
                "rejection_reason":status.get("rejectionReason"),
                "made_for_kids":status.get("madeForKids"),
                "processing_status":details.get("processingStatus"),
                "processing_failure_reason":details.get("processingFailureReason"),
                "file_details_available":details.get("fileDetailsAvailability"),
                "processing_progress":details.get("processingProgress"),
                "duration_iso8601":content.get("duration"),
                "region_restriction":content.get("regionRestriction"),
                "appears_in_uploads_playlist":vid in listing,
                "published_at":snippet.get("publishedAt"),
            }
        report["videos"].append(row)
        print("KIDS_VIDEO_AUDIT_"+vid+"_"+
              row["api_result"]+"_"+
              str(row.get("privacy_status","unknown"))+"_"+
              str(row.get("upload_status","unknown"))+"_"+
              str(row.get("processing_status","unknown"))+"_"+
              ("IN_UPLOADS_LIST" if row["appears_in_uploads_playlist"] else "NOT_IN_UPLOADS_LIST"),flush=True)
    DEST.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("KIDS_VISIBILITY_AUDIT_REPORT_WRITTEN",flush=True)

if __name__=="__main__":
    try:inspect()
    except Exception as exc:
        print("KIDS_VISIBILITY_AUDIT_BLOCKED_"+type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
