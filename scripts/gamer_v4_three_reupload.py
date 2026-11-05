#!/usr/bin/env python3
"""Re-upload exactly 3 *existing* V4 Gamer MP4s privately, once.

Creator explicitly requested resending three stuck-processing Gamer Shorts.
Uses a DIFFERENT single-request, non-resumable YouTube upload path, not the
previous chunked-resumable path that produced RedirectMissingLocation.
Never generates, edits, or deletes MP4s. Never touches the Alchemy channel.
All uploads remain PRIVATE. Failed/ambiguous responses are reconciled by
the unique reupload tag before proceeding; no blind videos.insert retry.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from datetime import datetime, timezone

from googleapiclient.http import MediaFileUpload
from games_alchemy_ai_upload import get_youtube, set_thumbnail
from youtube_channel_registry import KNOWN_IDS, get_channel
from production_reservations import assert_reserved

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/"gamer-original-v4-files"
OUTPUT=ROOT/"gamer-three-reupload-receipts"
OWNER="gamer_v4_three_processing_reupload_20261105"
TAG="autoeditorvideo-gamer-v4-reupload-once-20261105"
MAIN_RUN=42074829801
SOURCE_ARTIFACT=13439442112
WORKFLOW="Gamer - reupload exactly three V4 Shorts using non-resumable YouTube"
TARGETS=[
 ("game-001-gta4-gta5-v4", "game-001-gta4-gta5-v4-reenvio1", "CY9v9742DqY"),
 ("game-002-primeira-noite-minecraft-v4", "game-002-primeira-noite-minecraft-v4-reenvio1", "vG5tqbqirRo"),
 ("game-003-minecraft-sem-amarelo-v4", "game-003-minecraft-sem-amarelo-v4-reenvio1", "0PzFrTqWUQk"),
]
RECEIPT=OUTPUT/"gamer-v4-three-new-private-receipts.json"
WAIT_SECONDS=75
CHANNEL=KNOWN_IDS["games"]

class RetryBlocked(ValueError): pass

def sha(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()

def preflight()->list[dict]:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or e.get("GITHUB_REF")!="refs/heads/main"
        or e.get("GITHUB_EVENT_NAME")!="push"
        or e.get("GITHUB_RUN_ATTEMPT")!="1"
        or e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise RetryBlocked("ONE_AUTHORIZED_MAIN_PUSH_ONLY")
    if (e.get("GAMER_V4_THREE_REUPLOAD_APPROVED")!="true"
        or e.get("ORIGINAL_RENDER_RUN")!=str(MAIN_RUN)
        or e.get("SOURCE_ARTIFACT_ID")!=str(SOURCE_ARTIFACT)
        or not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise RetryBlocked("EXACT_CREATOR_APPROVAL_AND_OAUTH_REQUIRED")
    config=get_channel("games")
    if (config["youtube_channel_id"]!=CHANNEL
        or config["youtube_environment"]!="youtube-private-upload"
        or config["oauth_token_secret_name"]!="YOUTUBE_GAMES_TOKEN_JSON"):
        raise RetryBlocked("GAMER_CHANNEL_ISOLATION_FAILED")
    if not ASSETS.is_dir() or RECEIPT.exists():
        raise RetryBlocked("SOURCE_NOT_DOWNLOADED_OR_ALREADY_ATTEMPTED")
    original=json.loads((ASSETS/"summary.json").read_text(encoding="utf-8"))
    if (original.get("schema")!="autoeditorvideo/games-alchemy-six-native-remotion-v4/v1"
        or original.get("owner")!="games_alchemy_six_reference_v4_20261105"
        or original.get("source_run")!=42044136670
        or original.get("visual_profile")!="gamer-alchemy-reference"
        or original.get("cover_template")!="gamer-alchemy-reference"
        or len(original.get("videos",[]))!=6):
        raise RetryBlocked("WRONG_V4_ARTIFACT")
    byid={row["id"]:row for row in original["videos"]}
    jobs=[]
    for original_id,reservation_id,previous_id in TARGETS:
        assert_reserved("games",reservation_id,OWNER)
        row=byid.get(original_id)
        if row is None or row.get("channel")!="games":
            raise RetryBlocked("EPISODE_NOT_IN_GAMER_ARTIFACT")
        folder=ASSETS/original_id
        video,cover,metadata,qa=(folder/"final.mp4",folder/"thumb.jpg",
                                 folder/"metadata.json",folder/"qa.json")
        if any(not p.is_file() for p in (video,cover,metadata,qa)):
            raise RetryBlocked("V4_FILES_MISSING")
        meta=json.loads(metadata.read_text(encoding="utf-8"))
        report=json.loads(qa.read_text(encoding="utf-8"))
        if (meta.get("id")!=original_id or meta.get("channel")!="games"
            or meta.get("channel_id")!=CHANNEL
            or meta.get("revision")!="v4"
            or meta.get("original_private_video_id")!=previous_id
            or meta.get("visibility")!="private"
            or meta.get("containsSyntheticMedia") is not True
            or meta.get("cover_template")!="gamer-alchemy-reference"
            or report.get("structural_qa")!="passed"
            or report.get("visual_profile")!="gamer-alchemy-reference"
            or report.get("cover_template")!="gamer-alchemy-reference"
            or report.get("caption_max_group_words",99)>3
            or report.get("script_cta") is not True
            or report.get("highlight_by_word_boundaries") is not True
            or sha(video)!=row.get("sha256")
            or sha(video)!=meta.get("video_sha256")
            or sha(cover)!=meta.get("cover_sha256")
            or sha(cover)!=report.get("cover_sha256")):
            raise RetryBlocked("V4_PROVENANCE_QA_FAILED_"+original_id)
        jobs.append({"id":original_id,"reservation":reservation_id,
                     "previous_id":previous_id,"meta":meta,
                     "mp4":video,"cover":cover})
    if len(jobs)!=3:
        raise RetryBlocked("NOT_EXACTLY_THREE_GAMER_SHORTS")
    return jobs

def owner_videos(youtube)->list[dict]:
    r=youtube.channels().list(part="contentDetails",mine=True).execute()
    items=r.get("items",[])
    if len(items)!=1 or items[0].get("id")!=CHANNEL:
        raise RetryBlocked("WRONG_OWNER_YOUTUBE_ID")
    uploads=items[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not uploads:
        raise RetryBlocked("UPLOAD_PLAYLIST_UNAVAILABLE")
    ids=[];cursor=None
    for _ in range(6):
        kwargs={"part":"contentDetails","playlistId":uploads,"maxResults":50}
        if cursor:kwargs["pageToken"]=cursor
        chunk=youtube.playlistItems().list(**kwargs).execute()
        ids.extend(v["contentDetails"]["videoId"] for v in chunk.get("items",[])
                   if v.get("contentDetails",{}).get("videoId"))
        cursor=chunk.get("nextPageToken")
        if not cursor:break
    all_rows=[]
    for start in range(0,len(ids),50):
        result=youtube.videos().list(part="snippet,status",
                                   id=",".join(ids[start:start+50])).execute()
        all_rows.extend(result.get("items",[]))
    return all_rows

def find_reupload(youtube,title:str,episode:str)->list[str]:
    rows=owner_videos(youtube)
    matches=[]
    for row in rows:
        sn=row.get("snippet",{})
        tags=sn.get("tags",[])
        if (sn.get("channelId")==CHANNEL
            and sn.get("title")==title
            and TAG in tags
            and "autoeditorvideo-id-"+episode in tags
            and row.get("status",{}).get("privacyStatus")=="private"):
            matches.append(row["id"])
    if len(matches)>1:
        raise RetryBlocked("MULTIPLE_NEW_REUPLOADS_DETECTED_STOP")
    return matches

def confirm_owner_private(youtube,video_id:str)->dict:
    rows=youtube.videos().list(part="snippet,status,processingDetails,contentDetails",
                               id=video_id).execute().get("items",[])
    if (len(rows)!=1 or rows[0].get("snippet",{}).get("channelId")!=CHANNEL
        or rows[0].get("status",{}).get("privacyStatus")!="private"):
        raise RetryBlocked("YOUTUBE_PRIVATE_IDENTITY_NOT_CONFIRMED")
    row=rows[0]
    return {"upload_status":row.get("status",{}).get("uploadStatus"),
            "processing_status":row.get("processingDetails",{}).get("processingStatus"),
            "duration":row.get("contentDetails",{}).get("duration")}

def insert_nonresumable(youtube,job:dict)->str:
    meta=job["meta"]
    data={
      "snippet":{"title":meta["title"],"description":meta["description"],
                 "tags":list(dict.fromkeys(meta["tags"]+[TAG,"autoeditorvideo-id-"+job["id"]])),
                 "categoryId":"20","defaultLanguage":"pt-BR"},
      "status":{"privacyStatus":"private","selfDeclaredMadeForKids":False,
                "containsSyntheticMedia":True}
    }
    media=MediaFileUpload(str(job["mp4"]),mimetype="video/mp4",resumable=False)
    result=youtube.videos().insert(part="snippet,status",body=data,media_body=media,
                                   notifySubscribers=False).execute(num_retries=0)
    video_id=(result or {}).get("id")
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        raise RetryBlocked("NO_NEW_YOUTUBE_ID")
    return video_id

def store(receipts:list[dict])->None:
    OUTPUT.mkdir(parents=True,exist_ok=True)
    RECEIPT.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def run()->None:
    jobs=preflight()
    youtube=get_youtube("games",dict(os.environ))
    # Explicitly confirm all three original uploads still belong to Gamer.
    for job in jobs:
        confirm_owner_private(youtube,job["previous_id"])
    receipts=[]
    for job in jobs:
        existing=find_reupload(youtube,job["meta"]["title"],job["id"])
        if existing:
            id=existing[0]
            reused=True
        else:
            try:
                id=insert_nonresumable(youtube,job)
                reused=False
            except Exception:
                # A response can be lost after YouTube accepts an insert;
                # never insert again. Reconcile owner uploads once.
                time.sleep(15)
                found=find_reupload(youtube,job["meta"]["title"],job["id"])
                if len(found)!=1:
                    raise RetryBlocked("AMBIGUOUS_UPLOAD_DO_NOT_REPEAT_"+job["id"]) from None
                id=found[0]
                reused=True
        video_state=confirm_owner_private(youtube,id)
        entry={"episode":job["reservation"],"source_v4_episode":job["id"],
               "old_youtube_id":job["previous_id"],
               "new_youtube_id":id,
               "new_url":"https://www.youtube.com/watch?v="+id,
               "channel":"games","channel_id":CHANNEL,
               "privacy":"private","confirmed_private":True,
               "source_mp4_sha256":sha(job["mp4"]),
               "upload_method":"single_request_non_resumable",
               "accepted_before_call_returned":reused,
               "thumbnail_api_acknowledged":False,
               "processing_check":video_state,"studio_check":"not_verified",
               "recorded_utc":datetime.now(timezone.utc).isoformat()}
        receipts.append(entry)
        store(receipts)  # write ID before the 75-second thumbnail step
        print("GAMER_NEW_REUPLOAD_PRIVATE_"+job["id"]+"_"+id,flush=True)
        if not reused:
            time.sleep(WAIT_SECONDS)
        entry["thumbnail_api_acknowledged"]=set_thumbnail(youtube,id,job["cover"])
        entry["thumbnail_wait_seconds"]=WAIT_SECONDS if not reused else 0
        entry["processing_check"]=confirm_owner_private(youtube,id)
        store(receipts)
        print("GAMER_REUPLOAD_THUMB_"+job["id"]+"_"+("ACCEPTED" if entry["thumbnail_api_acknowledged"] else "NOT_ACKNOWLEDGED"),flush=True)
    if len(receipts)!=3 or len({x["new_youtube_id"] for x in receipts})!=3:
        raise RetryBlocked("THREE_UNIQUE_NEW_UPLOADS_NOT_CONFIRMED")
    print("ALL_THREE_GAMER_REUPLOADS_PRIVATE_CONFIRMED",flush=True)
    if any(not row["thumbnail_api_acknowledged"] for row in receipts):
        print("WARNING_THUMBNAILS_NEED_SEPARATE_RETRY_NOT_VIDEO_REUPLOAD",flush=True)

if __name__=="__main__":
    try:
        run()
    except Exception as exc:
        reason=str(exc) if isinstance(exc,RetryBlocked) else type(exc).__name__
        print("GAMER_REUPLOAD_BLOCKED_"+reason,file=sys.stderr)
        raise SystemExit(2)
