#!/usr/bin/env python3
"""Direct PUBLIC upload of exactly one new AutoEditorVideo Short.

Uses youtube.upload scope only for videos.insert(privacyStatus=public). Never
touches any existing private videos; never calls videos.update or videos.delete.
Reconciles an ambiguous insert with read-only owner playlist queries, no repeat.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from alchemy_public_direct_20261108 import (
    CHANNEL, EP_ID, OWNER, OUT, WORKFLOW, output, validate
)
from youtube_channel_registry import KNOWN_IDS, get_channel
from kids_static_90s_20261107 import digest, probe
from youtube_public_tags import public_tags
from five_channel_fifteen_upload_20261108 import youtube as verified_youtube

ROOT=Path(__file__).resolve().parents[1]
RECEIPT="youtube-public-upload-receipt.json"

class PublishBlocked(ValueError): pass

def guard()->None:
    env=os.environ
    if (env.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or env.get("GITHUB_REF")!="refs/heads/main"
        or env.get("GITHUB_EVENT_NAME")!="push"
        or env.get("GITHUB_RUN_ATTEMPT")!="1"
        or env.get("GITHUB_WORKFLOW")!=WORKFLOW
        or env.get("PUBLIC_PILOT_UPLOAD_AUTHORIZED")!="yes"
        or get_channel(CHANNEL).get("oauth_token_secret_name")!="YOUTUBE_ALCHEMY_TOKEN_JSON"
        or not env.get("YOUTUBE_CLIENT_JSON")
        or not env.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise PublishBlocked("ONE_SHOT_PUBLIC_EXACT_ALCHEMY_OAUTH_GUARD")
    if any(env.get(k) for k in ("PROXY_API_KEY","PROXY_ACCOUNTS_JSON",
                                "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                                "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON")):
        raise PublishBlocked("CROSS_CHANNEL_OR_IMAGE_SECRETS_FORBIDDEN")
    if (output()/RECEIPT).exists():
        raise PublishBlocked("RECEIPT_ALREADY_EXISTS_NO_BLIND_SECOND_INSERT")

def read_media()->tuple[dict,dict,Path,Path]:
    row=validate()
    out=output()
    report_file=out/"summary.json"
    if not report_file.is_file():
        raise PublishBlocked("AUTOEDITOR_RENDER_ARTIFACT_MISSING")
    summary=json.loads(report_file.read_text(encoding="utf-8"))
    if (summary.get("schema")!="autoeditorvideo/public-single-original-render/v1"
        or summary.get("owner")!=OWNER
        or summary.get("channel")!=CHANNEL
        or summary.get("channel_id")!=KNOWN_IDS[CHANNEL]
        or summary.get("episode_id")!=EP_ID
        or summary.get("video_count")!=1
        or summary.get("technical_qa")!="passed"
        or summary.get("artifact_state")!="rendered_upload_not_performed"):
        raise PublishBlocked("AUTOEDITOR_RENDER_PROVENANCE_INVALID")
    folder=(out/EP_ID).resolve()
    if folder.parent!=out.resolve():
        raise PublishBlocked("UNSAFE_FILE_PATH")
    required=[folder/x for x in ("final.mp4","thumb.jpg","qa.json","metadata.json")]
    if not all(f.is_file() for f in required):
        raise PublishBlocked("INCOMPLETE_RENDERED_VIDEO_ARTIFACTS")
    mp4,cover,qa_file,meta_file=required
    qa=json.loads(qa_file.read_text(encoding="utf-8"))
    meta=json.loads(meta_file.read_text(encoding="utf-8"))
    if (qa.get("schema")!="autoeditorvideo/remaining-static-original-90s-qa/v1"
        or qa.get("channel")!=CHANNEL
        or qa.get("channel_id")!=KNOWN_IDS[CHANNEL]
        or qa.get("episode_id")!=EP_ID
        or qa.get("automated_technical_qa")!="passed"
        or qa.get("word_boundaries_synced") is not True
        or qa.get("image_count")!=8
        or qa.get("public_direct_upload_authorized") is not True
        or meta.get("title")!=row["title"]
        or meta.get("description")!=row["description"]
        or meta.get("tags")!=row["tags"]
        or meta.get("id")!=EP_ID
        or meta.get("channel")!=CHANNEL
        or meta.get("channel_id")!=KNOWN_IDS[CHANNEL]
        or meta.get("privacyStatus")!="public"
        or meta.get("selfDeclaredMadeForKids") is not False
        or meta.get("explicit_creator_public_approval") is not True):
        raise PublishBlocked("QA_METADATA_OR_DIRECT_PUBLIC_APPROVAL_INVALID")
    if (not (digest(mp4)==summary["mp4_sha256"]==qa["mp4_sha256"]==meta["mp4_sha256"])
        or not (digest(cover)==summary["cover_sha256"]==qa["cover_sha256"]==meta["cover_sha256"])):
        raise PublishBlocked("MP4_OR_COVER_SHA256_MISMATCH")
    p=probe(mp4)
    videos=[x for x in p["streams"] if x.get("codec_type")=="video"]
    audios=[x for x in p["streams"] if x.get("codec_type")=="audio"]
    if (not 90<=float(p["format"]["duration"])<=121
        or len(videos)!=1 or not audios
        or videos[0].get("width")!=1080 or videos[0].get("height")!=1920
        or mp4.stat().st_size<300_000 or cover.stat().st_size<25_000):
        raise PublishBlocked("VIDEO_DURATION_DIMENSIONS_AUDIO_OR_COVER_FAIL")
    return row,meta,mp4,cover

def find_existing(api,playlist_id:str,meta:dict)->list[dict]:
    ids=[]
    page=None
    for _ in range(12):
        args={"part":"contentDetails","playlistId":playlist_id,"maxResults":50}
        if page:args["pageToken"]=page
        result=api.playlistItems().list(**args).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId") for x in result.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=result.get("nextPageToken")
        if not page:break
    if page:
        raise PublishBlocked("PLAYLIST_SCAN_INCOMPLETE_REFUSE_NEW_INSERT")
    matches=[]
    for i in range(0,len(ids),50):
        result=api.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute()
        for v in result.get("items",[]):
            snip=v.get("snippet",{})
            if snip.get("title")!=meta["title"]:
                continue
            if (snip.get("channelId")!=KNOWN_IDS[CHANNEL]
                or snip.get("description")!=meta["description"]):
                raise PublishBlocked("SAME_TITLE_NOT_IDENTICAL_OWN_UPLOAD_STOP")
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",v.get("id","")):
                raise PublishBlocked("EXISTING_VIDEO_ID_INVALID")
            matches.append({"video_id":v["id"],"privacy":v.get("status",{}).get("privacyStatus")})
    if len(matches)>1:
        raise PublishBlocked("MORE_THAN_ONE_MATCHING_OLD_UPLOAD_STOP")
    return matches

def save(data:dict)->None:
    target=output()/RECEIPT
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def insert_public(api,meta:dict,mp4:Path)->str:
    from googleapiclient.http import MediaFileUpload
    req=api.videos().insert(
        part="snippet,status",
        body={
            "snippet":{"title":meta["title"],"description":meta["description"],
                       "tags":public_tags(meta["tags"]),
                       "categoryId":meta["categoryId"],
                       "defaultLanguage":"pt-BR"},
            "status":{"privacyStatus":"public",
                      "selfDeclaredMadeForKids":False,
                      "containsSyntheticMedia":True}
        },
        media_body=MediaFileUpload(str(mp4),mimetype="video/mp4",resumable=True,
                                  chunksize=8*1024*1024),
        notifySubscribers=False
    )
    response=None
    while response is None:
        _,response=req.next_chunk(num_retries=0)
    vid=(response or {}).get("id")
    if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):
        raise PublishBlocked("UNCERTAIN_INSERT_RESPONSE_STOP")
    return vid

def verify(api,video_id:str,meta:dict)->tuple[bool,str|None,str|None]:
    result=api.videos().list(part="snippet,status",id=video_id).execute()
    videos=result.get("items",[])
    if len(videos)!=1:
        return False,None,None
    snip=videos[0].get("snippet",{})
    status=videos[0].get("status",{})
    if (snip.get("channelId")!=KNOWN_IDS[CHANNEL]
        or snip.get("title")!=meta["title"]
        or snip.get("description")!=meta["description"]
        or status.get("madeForKids") is not False):
        raise PublishBlocked("YOUTUBE_CHANNEL_TITLE_DESCRIPTION_OR_AUDIENCE_MISMATCH")
    return status.get("privacyStatus")=="public",status.get("privacyStatus"),status.get("uploadStatus")

def upload()->None:
    guard()
    row,meta,mp4,cover=read_media()
    api,playlist=verified_youtube(CHANNEL)
    matches=find_existing(api,playlist,meta)
    record={"schema":"autoeditorvideo/new-public-video-receipt/v1",
            "episode_id":EP_ID,"channel":CHANNEL,"channel_id":KNOWN_IDS[CHANNEL],
            "mp4_sha256":digest(mp4),"requested_privacy":"public",
            "youtube_id":None,"publication_confirmed":False,
            "state":"reconciliation_before_insert",
            "thumbnail_acknowledged":False}
    if matches and matches[0]["privacy"]!="public":
        record["youtube_id"]=matches[0]["video_id"]
        record["state"]="matching_existing_video_not_public_no_reupload"
        save(record)
        raise PublishBlocked("VIDEO_ALREADY_EXISTS_NOT_PUBLIC_DO_NOT_DUPLICATE")
    if matches:
        video_id=matches[0]["video_id"]
        record["state"]="recovered_preexisting_public_video"
    else:
        record["state"]="insert_started_result_uncertain"
        save(record)
        try:
            video_id=insert_public(api,meta,mp4)
        except Exception:
            recovered=None
            for delay in (10,20,35):
                time.sleep(delay)
                found=find_existing(api,playlist,meta)
                if found:
                    recovered=found[0]
                    break
            if recovered is None:
                record["state"]="uncertain_insert_no_retry"
                save(record)
                raise PublishBlocked("YOUTUBE_INSERT_UNCERTAIN_NO_BLIND_REPEAT") from None
            video_id=recovered["video_id"]
            record["state"]="recovered_after_ambiguous_insert"
    record["youtube_id"]=video_id
    record["state"]="youtube_id_received"
    save(record)
    for delay in (0,12,25,40):
        if delay:time.sleep(delay)
        public,visibility,upload_status=verify(api,video_id,meta)
        record["observed_visibility"]=visibility
        record["observed_upload_status"]=upload_status
        record["publication_confirmed"]=bool(public)
        save(record)
        if public:break
    if not record["publication_confirmed"]:
        record["state"]="youtube_did_not_confirm_public_no_reupload"
        save(record)
        raise PublishBlocked("PUBLIC_VISIBILITY_NOT_CONFIRMED_NO_REUPLOAD")
    record["state"]="public_verified"
    save(record)
    try:
        from googleapiclient.http import MediaFileUpload
        thumb=api.thumbnails().set(videoId=video_id,
            media_body=MediaFileUpload(str(cover),mimetype="image/jpeg")).execute()
        record["thumbnail_acknowledged"]=bool(thumb.get("items"))
    except Exception:
        record["thumbnail_manual_review_required"]=True
    save(record)
    print("AUTOEDITOR_ORIGINAL_PUBLIC_VERIFIED_"+CHANNEL+"_"+EP_ID+"_"+video_id,flush=True)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=("validate","upload"),default="validate")
    args=ap.parse_args()
    try:
        if args.action=="validate":
            print("AUTOEDITOR_PUBLIC_YOUTUBE_UPLOAD_AUTHORIZED_"+validate()["id"])
        else:
            upload()
        return 0
    except Exception as exc:
        message=str(exc) if isinstance(exc,PublishBlocked) else type(exc).__name__
        print("AUTOEDITOR_PUBLIC_UPLOAD_BLOCKED_"+message,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
