#!/usr/bin/env python3
"""Private-only one-shot YouTube upload of a 5s Gamer reference-style test.

Reads only the validated artifact generated in the same protected workflow.
Checks exclusive Gamer OAuth and exact channel ID BEFORE inserting. Waits
75 seconds before applying program-generated cover. If upload times out,
searches existing private uploads by the unique marker and NEVER repeats
videos.insert blindly.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from googleapiclient.http import MediaFileUpload
from games_alchemy_ai_upload import get_youtube,confirm_private,set_thumbnail
from gamer_reference_style_5s import DEST, EP, OWNER, TAG, SOURCE_RUN, _sha
from youtube_public_tags import public_tags
from youtube_channel_registry import KNOWN_IDS,get_channel
from production_reservations import assert_reserved

WORKFLOW="Gamer - 5 second native cover and highlighted captions test"
CHANNEL="games"
RECEIPT_NAME="gamer-private-5s-upload-receipt.json"

class UploadBlocked(ValueError):pass

def preflight()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise UploadBlocked("ONE_TIME_GITHUB_MAIN_PUSH_REQUIRED")
    if e.get("STYLE_5S_PRIVATE_UPLOAD_APPROVED")!="true":
        raise UploadBlocked("CREATOR_APPROVAL_REQUIRED")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise UploadBlocked("CHANNEL_OAUTH_SECRETS_MISSING")
    cfg=get_channel(CHANNEL)
    if (cfg.get("youtube_channel_id")!=KNOWN_IDS[CHANNEL] or
        cfg.get("oauth_token_secret_name")!="YOUTUBE_GAMES_TOKEN_JSON" or
        cfg.get("youtube_environment")!="youtube-private-upload"):
        raise UploadBlocked("WRONG_CHANNEL_ENVIRONMENT")
    assert_reserved(CHANNEL,EP,OWNER)
    if (DEST/RECEIPT_NAME).exists():
        raise UploadBlocked("RECEIPT_EXISTS_NO_REUPLOAD")

def check_media()->dict:
    folder=DEST/EP
    summary=json.loads((DEST/"summary.json").read_text(encoding="utf-8"))
    meta=json.loads((folder/"metadata.json").read_text(encoding="utf-8"))
    qa=json.loads((folder/"qa.json").read_text(encoding="utf-8"))
    video=folder/"final.mp4"
    cover=folder/"thumb.jpg"
    if any(not path.is_file() for path in (video,cover)):
        raise UploadBlocked("MEDIA_NOT_GENERATED")
    if (summary.get("schema")!="autoeditorvideo/gamer-reference-5s-output/v1" or
        summary.get("status")!="private_upload_not_yet_performed" or
        summary.get("total")!=1 or summary.get("source_run")!=SOURCE_RUN or
        summary.get("episode")!=EP or summary.get("owner")!=OWNER):
        raise UploadBlocked("RENDER_SOURCE_UNVERIFIED")
    if (meta.get("id")!=EP or meta.get("channel")!=CHANNEL or
        meta.get("channel_id")!=KNOWN_IDS[CHANNEL] or
        meta.get("visibility")!="private" or
        meta.get("test_only") is not True or
        meta.get("containsSyntheticMedia") is not True or
        meta.get("cover_preset")!="gamer-alchemy-reference" or
        TAG not in meta.get("tags",[])):
        raise UploadBlocked("TEST_METADATA_INVALID")
    if (qa.get("result")!="technical_pass" or
        qa.get("size")!=[1080,1920] or
        qa.get("frame_count")!=150 or
        qa.get("design_profile")!="gamer-alchemy-reference" or
        qa.get("cover_template")!="gamer-alchemy-reference" or
        qa.get("caption_highlight_word_boundary") is not True or
        not 4.85<=qa.get("duration_seconds",0)<=5.15):
        raise UploadBlocked("VISUAL_CAPTION_QA_FAILED")
    if (summary.get("video_sha256")!=_sha(video) or
        summary.get("cover_sha256")!=_sha(cover) or
        meta.get("video_sha256")!=_sha(video) or
        meta.get("cover_sha256")!=_sha(cover) or
        qa.get("mp4_sha256")!=_sha(video) or
        qa.get("thumb_sha256")!=_sha(cover)):
        raise UploadBlocked("SOURCE_ARTIFACT_HASH_MISMATCH")
    if "🎨" not in meta.get("description",""):
        raise UploadBlocked("VISUALS_DISCLOSURE_MISSING")
    return {"meta":meta,"video":video,"cover":cover}

def recent_existing(youtube)->list[str]:
    channel=youtube.channels().list(part="contentDetails",mine=True).execute()
    items=channel.get("items") or []
    if len(items)!=1 or items[0].get("id")!=KNOWN_IDS[CHANNEL]:
        raise UploadBlocked("YOUTUBE_WRONG_CHANNEL")
    uploads=items[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not uploads:
        raise UploadBlocked("OWN_UPLOADS_PLAYLIST_MISSING")
    ids=[];page=None
    for _ in range(5):
        kw={"part":"contentDetails","playlistId":uploads,"maxResults":50}
        if page:kw["pageToken"]=page
        response=youtube.playlistItems().list(**kw).execute()
        ids.extend(row.get("contentDetails",{}).get("videoId")
                   for row in response.get("items",[])
                   if row.get("contentDetails",{}).get("videoId"))
        page=response.get("nextPageToken")
        if not page:break
    found=[]
    for start in range(0,len(ids),50):
        response=youtube.videos().list(part="snippet,status",
                             id=",".join(ids[start:start+50])).execute()
        for entry in response.get("items",[]):
            snippet=entry.get("snippet",{})
            if (snippet.get("channelId")==KNOWN_IDS[CHANNEL] and
                entry.get("status",{}).get("privacyStatus")=="private" and
                TAG in snippet.get("tags",[])):
                found.append(entry["id"])
    if len(found)>1:
        raise UploadBlocked("MORE_THAN_ONE_PRIVATE_TEST_VIDEO")
    return found

def persist(record:dict)->None:
    (DEST/RECEIPT_NAME).write_text(
        json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def upload_once(youtube,meta:dict,video:Path)->str:
    body={
        "snippet":{
            "title":meta["title"],"description":meta["description"],
            "tags":public_tags(meta["tags"]),"categoryId":"20","defaultLanguage":"pt-BR",
        },
        "status":{"privacyStatus":"private",
                  "selfDeclaredMadeForKids":False,
                  "containsSyntheticMedia":True}
    }
    req=youtube.videos().insert(
        part="snippet,status",body=body,
        media_body=MediaFileUpload(str(video),mimetype="video/mp4",
            resumable=True,chunksize=8*1024*1024),notifySubscribers=False)
    response=None
    while response is None:
        _,response=req.next_chunk(num_retries=0)
    video_id=response.get("id")
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        raise UploadBlocked("NO_YOUTUBE_VIDEO_ID")
    return video_id

def run()->None:
    preflight()
    files=check_media()
    youtube=get_youtube(CHANNEL,dict(os.environ))
    already=recent_existing(youtube)
    if already:
        video_id=already[0]
        reused=True
    else:
        try:
            video_id=upload_once(youtube,files["meta"],files["video"])
            reused=False
        except Exception:
            # Google's resumable media endpoint may accept the Short and
            # then error while returning the Location header. Never retry
            # insert; inspect the owning channel for the unique marker.
            time.sleep(20)
            recovered=recent_existing(youtube)
            if len(recovered)!=1:
                raise UploadBlocked("AMBIGUOUS_INSERT_NO_RETRY") from None
            video_id=recovered[0]
            reused=True
    if not confirm_private(youtube,video_id,KNOWN_IDS[CHANNEL]):
        raise UploadBlocked("PRIVATE_YOUTUBE_DESTINATION_NOT_CONFIRMED")
    receipt={"episode":EP,"channel":CHANNEL,"channel_id":KNOWN_IDS[CHANNEL],
             "youtube_video_id":video_id,
             "url":"https://www.youtube.com/watch?v="+video_id,
             "privacy":"private","confirmed_private":True,
             "reused_accepted_upload":reused,
             "new_image_generation":False,
             "thumbnail_api_acknowledged":False,
             "thumbnail_studio_visible":"not_verified",
             "video_sha256":_sha(files["video"])}
    persist(receipt)
    if not reused:
        time.sleep(75)
    receipt["thumbnail_api_acknowledged"]=set_thumbnail(
        youtube,video_id,files["cover"])
    receipt["thumbnail_delay_seconds"]=75 if not reused else 0
    persist(receipt)
    if not receipt["thumbnail_api_acknowledged"]:
        raise UploadBlocked("VIDEO_UPLOADED_BUT_THUMBNAIL_NOT_ACKNOWLEDGED")
    print("FIVE_SECOND_NATIVE_STYLE_PRIVATE_YOUTUBE_VIDEO_"+video_id,flush=True)
    print("OFFICIAL_THUMBNAIL_API_ACKNOWLEDGED",flush=True)

def main()->int:
    try:
        run();return 0
    except Exception as e:
        message=str(e) if isinstance(e,UploadBlocked) else type(e).__name__
        print("FIVE_SECOND_PRIVATE_UPLOAD_BLOCKED_"+message,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
