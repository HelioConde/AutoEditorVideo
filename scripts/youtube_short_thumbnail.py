#!/usr/bin/env python3
"""One-shot YouTube Shorts thumbnail attachment, original AutoEditorVideo JPG.

A thumbnail is a SEPARATE YouTube API write after videos.insert. Never calls
videos.insert, modifies privacy/scheduling, or generates/re-encodes the MP4.
No upstream error body, OAuth token, or request header enters logs.
"""
from __future__ import annotations
from pathlib import Path
import time
from PIL import Image
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

class ThumbnailBlocked(ValueError):
    pass

def validate_cover(path:Path)->dict:
    if not path.is_file():
        raise ThumbnailBlocked("THUMBNAIL_FILE_MISSING")
    size=path.stat().st_size
    if not 1000<=size<=50_000_000:
        raise ThumbnailBlocked("THUMBNAIL_FILE_SIZE_INVALID")
    try:
        with Image.open(path) as im:
            if im.format!="JPEG":
                raise ThumbnailBlocked("THUMBNAIL_MUST_BE_JPEG")
            w,h=im.size
            if w<360 or h<640 or abs(w/h-9/16)>0.025:
                raise ThumbnailBlocked("THUMBNAIL_NOT_VERTICAL_9_16")
            im.verify()
    except ThumbnailBlocked:
        raise
    except (OSError,ValueError,SyntaxError):
        raise ThumbnailBlocked("THUMBNAIL_DECODE_INVALID") from None
    return {"width":w,"height":h,"bytes":size}

def wait_for_processing(youtube,video_id:str,*,attempts:int=12,delay:float=6,sleeper=time.sleep)->str:
    """Prove final processing and requested private visibility, not just upload.

    Non-succeeded statuses cause no thumbnail write. Bounded polling is OK;
    throttling/403 never cause an unbounded request/retry loop.
    """
    if not isinstance(video_id,str) or len(video_id)!=11:
        raise ThumbnailBlocked("INVALID_VIDEO_ID")
    for i in range(attempts):
        try:
            res=youtube.videos().list(part="processingDetails,status",id=video_id).execute()
        except HttpError as exc:
            status=getattr(getattr(exc,"resp",None),"status",0)
            if status in (400,401,403,404,429):
                raise ThumbnailBlocked(f"PROCESSING_READ_HTTP_{status}") from None
            raise ThumbnailBlocked("PROCESSING_READ_HTTP_OTHER") from None
        except Exception:
            raise ThumbnailBlocked("PROCESSING_READ_FAILED") from None
        items=res.get("items") or []
        if len(items)!=1 or items[0].get("id")!=video_id:
            raise ThumbnailBlocked("VIDEO_NOT_FOUND_FOR_ACCOUNT")
        if (items[0].get("status") or {}).get("privacyStatus")!="private":
            raise ThumbnailBlocked("VIDEO_PRIVACY_CHANGED_NOT_PRIVATE")
        stage=(items[0].get("processingDetails") or {}).get("processingStatus")
        if stage=="succeeded":
            return stage
        if stage in ("failed","terminated"):
            raise ThumbnailBlocked("VIDEO_PROCESSING_FAILED")
        if stage not in ("processing","pending"):
            raise ThumbnailBlocked("VIDEO_PROCESSING_UNVERIFIED")
        if i<attempts-1:
            sleeper(delay)
    raise ThumbnailBlocked("VIDEO_PROCESSING_STILL_PENDING")

def attach_thumbnail(youtube,video_id:str,cover:Path,*,waiter=wait_for_processing)->dict:
    size=validate_cover(cover)
    waiter(youtube,video_id)
    try:
        image=MediaFileUpload(str(cover),mimetype="image/jpeg",resumable=False)
        resp=youtube.thumbnails().set(videoId=video_id,media_body=image).execute()
    except HttpError as exc:
        status=getattr(getattr(exc,"resp",None),"status",0)
        if status in (400,401,403,404,429):
            raise ThumbnailBlocked(f"THUMBNAIL_SET_HTTP_{status}") from None
        raise ThumbnailBlocked("THUMBNAIL_SET_HTTP_OTHER") from None
    except Exception:
        raise ThumbnailBlocked("THUMBNAIL_SET_FAILED") from None
    items=resp.get("items") if isinstance(resp,dict) else None
    if not isinstance(items,list) or not items:
        raise ThumbnailBlocked("THUMBNAIL_NOT_ACKNOWLEDGED_BY_API")
    print("[THUMBNAIL] API_ACKNOWLEDGED_SHORTS_COVER",flush=True)
    return {"status":"api_acknowledged","video_id":video_id,"width":size["width"],"height":size["height"]}
