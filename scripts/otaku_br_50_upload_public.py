#!/usr/bin/env python3
"""Upload EXACTLY ONE fully rendered Otaku Multicena Short PUBLIC, then its cover.

Only a verified BR OAuth identity is accepted. Preserve receipts in GitHub before
and after thumbnail upload; any ambiguity STOPS the serial chain, no duplicates.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib import request,error

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_br_50_reverso import OUTPUT, validate
from cloud_youtube_private_5011 import authorized_youtube, exists_in_playlist
from youtube_upload_profiles import build_insert_body,upload_notify_subscribers
from youtube_public_tags import public_tags
from youtube_short_thumbnail import validate_cover
from otaku_br_50_maintenance_gate import ensure_unpaused_live

REPO="HelioConde/AutoEditorVideo"
CHANNEL="UCXGYTuBYn-0Ziqin5ajKhOw"
RECEIPTS="dados/otaku-br-50-reverso-recibos"
API=f"https://api.github.com/repos/{REPO}/contents/"
REQUIRES={
  "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
  "GITHUB_REF":"refs/heads/main",
  "GITHUB_RUN_ATTEMPT":"1",
  "PUBLIC_50_BR_AUTHORIZED":"true"
}

class UploadBlocked(ValueError):
    pass

def sha(path:Path)->str:
    hash=hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            hash.update(part)
    return hash.hexdigest()

def gh_call(method:str,path:str,body:dict|None=None)->dict|None:
    token=os.environ.get("GH_TOKEN","")
    if not token:
        raise UploadBlocked("MISSING_GITHUB_RECEIPT_TOKEN")
    url=API+path
    payload=None if body is None else json.dumps(body).encode("utf-8")
    req=request.Request(url,data=payload,method=method,headers={
        "Accept":"application/vnd.github+json",
        "Authorization":"Bearer "+token,
        "Content-Type":"application/json",
        "X-GitHub-Api-Version":"2022-11-28"
    })
    try:
        with request.urlopen(req,timeout=30) as res:
            return json.loads(res.read(150000))
    except error.HTTPError as ex:
        if method=="GET" and ex.code==404:
            return None
        raise UploadBlocked("GITHUB_RECEIPT_API_FAILED_"+str(ex.code)) from None
    except Exception:
        raise UploadBlocked("GITHUB_RECEIPT_UNAVAILABLE") from None

def receipt_path(number:int)->str:
    return f"{RECEIPTS}/{6100+number}-multicena-experimento-novembro.json"

def receipt(number:int)->dict|None:
    data=gh_call("GET",receipt_path(number)+"?ref=main")
    if not data: return None
    try:
        return json.loads(base64.b64decode(data["content"]).decode("utf-8"))
    except Exception:
        raise UploadBlocked("UNREADABLE_PREVIOUS_RECEIPT") from None

def store_receipt(number:int,data:dict)->None:
    path=receipt_path(number)
    current=gh_call("GET",path+"?ref=main")
    payload={
      "message":f"chore(otaku-br): registrar envio unico do Short {number:02d}",
      "branch":"main",
      "content":base64.b64encode(
          (json.dumps(data,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
      ).decode("ascii")
    }
    if current is not None:
        payload["sha"]=current["sha"]
    gh_call("PUT",path,payload)

def preflight(number:int)->tuple[dict,Path,Path,dict]:
    for k,v in REQUIRES.items():
        if os.environ.get(k)!=v:
            raise UploadBlocked("ENVIRONMENT_GUARD_FAILED_"+k)
    if os.environ.get("GITHUB_EVENT_NAME") not in ("push","workflow_dispatch"):
        raise UploadBlocked("INVALID_WORKFLOW_EVENT")
    # Live main-branch creator consent supersedes stale run inputs.
    ensure_unpaused_live()
    if number not in range(1,51):raise UploadBlocked("NUMBER_OUT_OF_RANGE")
    row=validate()[number-1]
    if row["position"]!=number or row["channel_id"]!=CHANNEL:
        raise UploadBlocked("WRONG_CHANNEL_OR_NUMBER")
    if receipt(number):
        raise UploadBlocked("EPISODE_ALREADY_HAS_RECEIPT_DO_NOT_DUPLICATE")
    if number<50:
        previous=receipt(number+1)
        if not previous or previous.get("stage")!="public_processed_cover_acknowledged":
            raise UploadBlocked("PREVIOUS_NUMBER_NOT_COMPLETELY_PUBLISHED")
    folder=OUTPUT/row["id"]
    video=folder/"preview-unreviewed.mp4"
    cover=folder/"thumb.jpg"
    meta_path=folder/"metadata.json"
    qa_path=folder/"qa.json"
    provenance=folder/"original-art-provenance.json"
    if not all(p.is_file() for p in (video,cover,meta_path,qa_path,provenance)):
        raise UploadBlocked("NOT_ALL_MEDIA_AND_QA_ARTIFACTS_PRESENT")
    cover_info=validate_cover(cover)
    meta=json.loads(meta_path.read_text(encoding="utf-8"))
    qa=json.loads(qa_path.read_text(encoding="utf-8"))
    source=json.loads(provenance.read_text(encoding="utf-8"))
    if (meta.get("episode_id")!=row["id"] or meta.get("channel_id")!=CHANNEL
        or meta.get("title")!=row["title"] or meta.get("description")!=row["description"]
        or meta.get("tags")!=row["tags"] or meta.get("containsSyntheticMedia") is not True
        or meta.get("requested_privacy")!="public_after_qa"):
        raise UploadBlocked("RENDERED_MEDIA_METADATA_CHANGED")
    if (qa.get("video_sha256")!=sha(video) or qa.get("cover_sha256")!=sha(cover)
        or qa.get("scene_sha256")!=source.get("scene_sha256")
        or qa.get("publication")!="not_performed"
        or qa.get("technical")!="preview_rendered_unreviewed"):
        raise UploadBlocked("VIDEO_COVER_OR_SCENE_HASH_MISMATCH")
    if source.get("human_visual_review") is not False:
        raise UploadBlocked("UNKNOWN_VISUAL_REVIEW_STATE")
    if video.stat().st_size<200000 or cover_info["width"]!=1080:
        raise UploadBlocked("BAD_MP4_OR_COVER_SIZE")
    # The user has explicitly authorized the 50 original editorial plans,
    # not claimed to have watched generated videos; do not claim human QA.
    return row,video,cover,meta

def verify_processing(youtube,video_id:str,attempts:int=28)->None:
    for i in range(attempts):
        try:
            res=youtube.videos().list(part="status,processingDetails",id=video_id).execute()
        except HttpError as exc:
            sc=getattr(exc.resp,"status",0)
            raise UploadBlocked("VIDEO_PROCESSING_HTTP_"+str(sc)) from None
        items=res.get("items") or []
        if len(items)!=1 or items[0].get("id")!=video_id:
            raise UploadBlocked("VIDEO_NOT_FOUND_AFTER_INSERT")
        status=items[0].get("status") or {}
        if status.get("privacyStatus")!="public":
            raise UploadBlocked("VIDEO_NOT_PUBLIC_AFTER_INSERT")
        state=(items[0].get("processingDetails") or {}).get("processingStatus")
        if state=="succeeded":
            return
        if state in ("failed","terminated"):
            raise UploadBlocked("YOUTUBE_VIDEO_PROCESSING_FAILED")
        if state not in ("processing","pending"):
            raise UploadBlocked("YOUTUBE_VIDEO_PROCESSING_UNCONFIRMED")
        if i<attempts-1:
            time.sleep(12)
    raise UploadBlocked("PROCESSING_STILL_PENDING_STOP_BEFORE_NEXT_SHORT")

def publish(number:int)->dict:
    row,mp4,cover,meta=preflight(number)
    youtube,playlist=authorized_youtube(os.environ,"br")
    # Search ALL uploads, including private/scheduled, before any insert.
    prior=exists_in_playlist(youtube,playlist,"DO_NOT_WRITE_INTERNAL_MARKERS",row["title"])
    if prior:
        raise UploadBlocked("SAME_TITLE_ALREADY_UPLOADED_ID_"+prior+"_STOP")
    prepared=dict(meta)
    prepared["containsSyntheticMedia"]=True
    prepared["tags"]=public_tags(row["tags"])
    body=build_insert_body("br",prepared,privacy="public")
    if body["status"]["privacyStatus"]!="public" or body["status"]["selfDeclaredMadeForKids"]:
        raise UploadBlocked("PUBLIC_ADULT_ANIME_CHANNEL_PROFILE_NOT_VALID")
    # A pause might have happened while earlier checks prepared the upload.
    # Reconfirm immediately before any irreversible YouTube insert.
    ensure_unpaused_live()
    print("[OTAKU BR] VERIFICADO_CHANNEL_PUBLIC_UPLOAD_ONE_NUMBER_"+str(number),flush=True)
    attempt=mp4.parent/"public-upload-result.json"
    media=MediaFileUpload(str(mp4),mimetype="video/mp4",resumable=False)
    try:
        uploaded=youtube.videos().insert(
            part="snippet,status",body=body,
            notifySubscribers=upload_notify_subscribers("br"),
            media_body=media
        ).execute()
    except HttpError as ex:
        status=getattr(ex.resp,"status",0)
        raise UploadBlocked("YOUTUBE_INSERT_FAILED_HTTP_"+str(status)+"_DO_NOT_BLIND_RETRY") from None
    except Exception:
        raise UploadBlocked("YOUTUBE_INSERT_AMBIGUOUS_CHECK_HISTORY_NO_RETRY") from None
    video_id=uploaded.get("id") or ""
    if len(video_id)!=11:
        raise UploadBlocked("MISSING_INSERT_VIDEO_ID_RECONCILE_BEFORE_RETRY")
    preliminary={
      "stage":"uploaded_pending_processing_and_cover","number":number,
      "episode_id":row["id"],"video_id":video_id,
      "video_url":"https://www.youtube.com/watch?v="+video_id,
      "channel_id":CHANNEL,"title":row["title"],"video_sha256":sha(mp4),
      "cover_sha256":sha(cover),"human_visual_review":False,
      "uploaded_utc":datetime.now(timezone.utc).isoformat(),
      "visibility_claim":"public_requested_not_yet_rechecked"
    }
    attempt.write_text(json.dumps(preliminary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Create durable reconciliation evidence immediately, BEFORE any waiting.
    store_receipt(number,preliminary)
    verify_processing(youtube,video_id)
    processed=dict(preliminary,stage="public_processed_pending_cover",
                   visibility_claim="public_verified")
    store_receipt(number,processed)
    attempt.write_text(json.dumps(processed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    try:
        result=youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(cover),mimetype="image/jpeg",resumable=False)
        ).execute()
    except HttpError as exc:
        sc=getattr(exc.resp,"status",0)
        raise UploadBlocked("THUMBNAIL_HTTP_"+str(sc)+"_STOP_SEQUENCE") from None
    except Exception:
        raise UploadBlocked("THUMBNAIL_AMBIGUOUS_STOP_SEQUENCE") from None
    if not isinstance(result,dict) or not result.get("items"):
        raise UploadBlocked("THUMBNAIL_API_NOT_ACKNOWLEDGED_STOP_SEQUENCE")
    verify_processing(youtube,video_id,attempts=1)
    complete=dict(processed,stage="public_processed_cover_acknowledged",
                  thumbnail_api_acknowledged=True,
                  completed_utc=datetime.now(timezone.utc).isoformat(),
                  public_verified=True)
    store_receipt(number,complete)
    attempt.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU BR] PUBLIC_AND_COVER_CONFIRMED "+video_id,flush=True)
    return complete

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--number",type=int,required=True)
    args=parser.parse_args()
    print(json.dumps(publish(args.number),ensure_ascii=False))
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (UploadBlocked,ValueError,OSError) as exc:
        raise SystemExit("[BLOQUEADO UPLOAD BR] "+str(exc)) from None
