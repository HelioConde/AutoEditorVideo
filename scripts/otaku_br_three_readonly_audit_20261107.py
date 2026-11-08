#!/usr/bin/env python3
"""Read-only authenticated YouTube status audit of three Otaku BR original Shorts.

Never generates an image, creates a video, changes privacy, edits a thumbnail
or publishes content. Uses owner's BR OAuth only to inspect three exact titles
and first returned YouTube video ID, including processing/upload state.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cloud_youtube_private_5011 import authorized_youtube

EXPECTED_CHANNEL="UCXGYTuBYn-0Ziqin5ajKhOw"
VIDEO_ID="alHbSHUN0dA"
SOURCE_RUN_ID=42432267960
IDS=("5012-solo-leveling-igris","5013-blue-lock-isagi","5014-mob-psycho-emocoes")
MANIFEST=Path("conteudos/otaku-br-three-public-20261107.json")
LAUNCH=Path("conteudos/otaku-br-three-public-readonly-20261107.json")
OUTPUT=Path("otaku-br-three-youtube-real-status-20261107.json")

def guard()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!="Otaku Multicena BR - read only status of 3 original Shorts"
            or e.get("OTAKU_BR_READ_ONLY_AUTHORIZED")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_BR_TOKEN_JSON")
            or any(e.get(x) for x in ("PROXY_ACCOUNTS_JSON","PROXY_API_KEY",
                       "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
                       "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON"))):
        raise ValueError("EXACT_BR_READ_ONLY_OAUTH_REQUIRED")
    d=json.loads(LAUNCH.read_text(encoding="utf-8"))
    assert d=={
        "schema":"autoeditorvideo/otaku-br-3-public-readonly-inspection/v1",
        "run_id":SOURCE_RUN_ID,
        "channel_id":EXPECTED_CHANNEL,
        "video_ids":[VIDEO_ID],
        "episode_ids":list(IDS),
        "read_only":True,
        "allowed_operations":["channels.list","playlistItems.list","videos.list"],
        "upload_new_video":False,
        "update_existing_video":False,
        "change_visibility":False,
        "regenerate_images":False
    }

def inspect()->None:
    guard()
    rows=json.loads(MANIFEST.read_text(encoding="utf-8"))["episodes"]
    if tuple(x["id"] for x in rows)!=IDS:
        raise ValueError("THREE_ORIGINAL_TITLES_CHANGED")
    api,playlist=authorized_youtube(os.environ,"br")
    owner_titles={r["title"]:r["id"] for r in rows}
    report={"schema":"autoeditorvideo/otaku-br-three-current-youtube-status/v1",
            "source_run_id":SOURCE_RUN_ID,"channel_id":EXPECTED_CHANNEL,
            "first_uploaded_id":VIDEO_ID,"videos":[]}
    titles_found={k:[] for k in IDS}
    page=None
    scanned=0
    for _ in range(100):
        query={"part":"snippet,contentDetails","playlistId":playlist,"maxResults":50}
        if page:query["pageToken"]=page
        response=api.playlistItems().list(**query).execute()
        items=response.get("items",[])
        scanned+=len(items)
        for x in items:
            snippet=x.get("snippet",{})
            ep=owner_titles.get(snippet.get("title"))
            if ep:
                id=(x.get("contentDetails") or {}).get("videoId")
                if id and id not in titles_found[ep]:titles_found[ep].append(id)
        page=response.get("nextPageToken")
        if not page:break
    if page:
        raise ValueError("UPLOADS_HISTORY_NOT_EXHAUSTIVELY_CHECKED")
    ids={VIDEO_ID}
    for matches in titles_found.values():ids.update(matches)
    details={}
    for id in ids:
        result=api.videos().list(part="snippet,status,processingDetails,contentDetails",
                                 id=id).execute()
        found=result.get("items",[])
        if len(found)==1:
            v=found[0]
            details[id]={
                "channel_verified":v.get("snippet",{}).get("channelId")==EXPECTED_CHANNEL,
                "title":v.get("snippet",{}).get("title"),
                "privacy":v.get("status",{}).get("privacyStatus"),
                "upload_status":v.get("status",{}).get("uploadStatus"),
                "made_for_kids":v.get("status",{}).get("madeForKids"),
                "self_declared_made_for_kids":v.get("status",{}).get("selfDeclaredMadeForKids"),
                "processing":v.get("processingDetails",{}).get("processingStatus"),
                "processing_failure_reason":v.get("processingDetails",{}).get("processingFailureReason"),
                "youtube_duration":v.get("contentDetails",{}).get("duration")
            }
    for row in rows:
        ep=row["id"]
        matched=titles_found[ep]
        if ep==IDS[0] and VIDEO_ID in details and VIDEO_ID not in matched:
            matched=matched+[VIDEO_ID]
        report["videos"].append({
            "episode_id":ep,"title":row["title"],
            "matched_youtube_ids":matched,
            "current_status":[{"id":id,**details.get(id,{"missing_from_owner_api":True})}
                              for id in matched]
        })
        print("OTAKU_BR_READONLY_EPISODE_"+ep+"_MATCH_COUNT_"+str(len(matched)),flush=True)
        for id in matched:
            v=details.get(id)
            if v:
                print("OTAKU_BR_READONLY_YOUTUBE_VIDEO_"+id+"_"+
                      str(v["privacy"])+"_"+
                      str(v["upload_status"])+"_"+
                      str(v["processing"])+"_"+
                      str(v["youtube_duration"]),flush=True)
    report["own_upload_playlist_items_scanned"]=scanned
    report["first_video_in_owner_api"]=VIDEO_ID in details
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OTAKU_BR_THREE_READ_ONLY_AUDIT_COMPLETED_NO_MUTATIONS",flush=True)

if __name__=="__main__":
    try:inspect()
    except Exception as ex:
        print("OTAKU_BR_THREE_READONLY_BLOCKED_"+type(ex).__name__,file=sys.stderr)
        raise SystemExit(2)
