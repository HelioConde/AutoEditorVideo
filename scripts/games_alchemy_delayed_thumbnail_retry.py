#!/usr/bin/env python3
"""Retry existing custom Shorts thumbnails AFTER the videos have been uploaded.

NO video insertion, title editing, AI generation or public visibility changes.
Only six pinned YouTube IDs; each thumbnail comes from the original artifact.
The first video per channel is an isolated test; subsequent thumbs are sent
ONLY if YouTube API acknowledges that first test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from games_alchemy_ai_upload import get_youtube, UploadBlocked
from youtube_channel_registry import KNOWN_IDS
from PIL import Image
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

ARTIFACT = ROOT / "cloud-games-alchemy-ai-six"
PUBLICATION = ROOT / "conteudos" / "games-alchemy-six-private-upload-result-20261105.json"
RESULT_NAME = "delayed-thumbnail-retry-receipts.json"
SOURCE_RUN = 42044136670
FIRST = {
    "games": "game-002-primeira-noite-minecraft",
    "alchemy": "alchemy-001-chatgpt-gifs",
}
ALL = {
    "games": ["game-002-primeira-noite-minecraft", "game-001-gta4-gta5",
              "game-003-minecraft-sem-amarelo"],
    "alchemy": ["alchemy-001-chatgpt-gifs", "alchemy-002-images-26-consistencia",
               "alchemy-003-gif-animado-tutorial"],
}
WAIT_AFTER_UPLOADING_SECONDS = 75
WAIT_AFTER_THUMB_SET_SECONDS = 10

class ThumbnailRetryBlocked(Exception):
    pass

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def check_environment(channel: str) -> None:
    e = os.environ
    if channel not in ALL:
        raise ThumbnailRetryBlocked("UNEXPECTED_CHANNEL")
    if e.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise ThumbnailRetryBlocked("WRONG_REPOSITORY")
    if e.get("GITHUB_REF") != "refs/heads/main":
        raise ThumbnailRetryBlocked("NOT_MAIN")
    if e.get("GITHUB_EVENT_NAME") != "push" or e.get("GITHUB_RUN_ATTEMPT") != "1":
        raise ThumbnailRetryBlocked("ONE_SHOT_PUSH_ONLY")
    if e.get("GITHUB_WORKFLOW") != "Gamer + Alchemy - delayed thumbnail retry for six private Shorts":
        raise ThumbnailRetryBlocked("UNEXPECTED_WORKFLOW")
    if e.get("DELAYED_THUMBNAIL_RETRY_APPROVED") != "true":
        raise ThumbnailRetryBlocked("CREATOR_APPROVAL_REQUIRED")
    if e.get("SOURCE_RENDER_RUN_ID") != str(SOURCE_RUN):
        raise ThumbnailRetryBlocked("INCORRECT_ORIGINAL_ARTIFACT")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise ThumbnailRetryBlocked("NO_CHANNEL_SPECIFIC_OAUTH")
    if not ARTIFACT.is_dir():
        raise ThumbnailRetryBlocked("ORIGINAL_ARTIFACT_NOT_DOWNLOADED")

def validate_files(channel: str) -> list[dict]:
    source=json.loads(PUBLICATION.read_text(encoding="utf-8"))
    summary=json.loads((ARTIFACT/"summary.json").read_text(encoding="utf-8"))
    if (source.get("status")!="all_six_verified_private_on_correct_youtube_channels" or
        source.get("original_render",{}).get("workflow_run")!=SOURCE_RUN or
        source.get("channel_ids",{}).get(channel)!=KNOWN_IDS[channel] or
        summary.get("count")!=6 or
        summary.get("publication")!="not_performed"):
        raise ThumbnailRetryBlocked("ORIGINAL_VIDEO_MANIFEST_NOT_VERIFIED")
    originals={row["id"]:row for row in source["videos"] if row["channel"]==channel}
    produced={row["id"]:row for row in summary["videos"] if row["channel"]==channel}
    selected=[]
    for id in ALL[channel]:
        row=originals.get(id)
        render=produced.get(id)
        if not row or not render or not row.get("confirmed_private"):
            raise ThumbnailRetryBlocked("YOUTUBE_VIDEO_ID_NOT_CONFIRMED")
        video_id=row["youtube_video_id"]
        if not re.fullmatch(r"[a-zA-Z0-9_-]{11}",video_id):
            raise ThumbnailRetryBlocked("INVALID_VIDEO_ID")
        folder=ARTIFACT/id
        cover=folder/"thumb.jpg"
        qa=json.loads((folder/"qa.json").read_text(encoding="utf-8"))
        if not cover.is_file() or sha(cover)!=qa.get("cover_sha256"):
            raise ThumbnailRetryBlocked("THUMBNAIL_HASH_MISMATCH")
        if cover.stat().st_size>2_000_000 or cover.stat().st_size<10_000:
            raise ThumbnailRetryBlocked("THUMBNAIL_SIZE_INVALID")
        with Image.open(cover) as img:
            if img.format!="JPEG" or img.size!=(720,1280):
                raise ThumbnailRetryBlocked("THUMBNAIL_FORMAT_MISMATCH")
            img.verify()
        selected.append({"id":id,"video_id":video_id,"cover":cover})
    return selected

def owned_video(youtube,video_id:str,channel:str) -> dict:
    res=youtube.videos().list(part="snippet,status",id=video_id).execute()
    items=res.get("items") or []
    if len(items)!=1:
        raise ThumbnailRetryBlocked("VIDEO_ID_NOT_FOUND_BY_OWNER")
    item=items[0]
    if item.get("snippet",{}).get("channelId")!=KNOWN_IDS[channel]:
        raise ThumbnailRetryBlocked("CROSS_CHANNEL_VIDEO_BLOCKED")
    if item.get("status",{}).get("privacyStatus")!="private":
        raise ThumbnailRetryBlocked("VIDEO_NO_LONGER_PRIVATE")
    return item

def apply(youtube,video_id:str,cover:Path) -> tuple[bool,str]:
    try:
        result=youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(cover),mimetype="image/jpeg",resumable=False)
        ).execute(num_retries=0)
        # 200 from the API is an acknowledgement, NOT Studio visibility proof.
        return bool(result.get("items")), "youtube_api_acknowledged" if result.get("items") else "api_empty_items"
    except HttpError as exc:
        status=getattr(exc.resp,"status",0)
        reason="unknown"
        try:
            raw=json.loads(exc.content.decode("utf-8",errors="replace"))
            err=(raw.get("error",{}).get("errors") or [{}])[0]
            reason=re.sub(r"[^A-Za-z0-9_]", "",str(err.get("reason","unknown")))[:48]
        except Exception:
            pass
        return False,f"youtube_http_{status}_{reason}"
    except Exception as exc:
        return False,f"transport_{type(exc).__name__}"

def run(channel:str) -> int:
    check_environment(channel)
    selected=validate_files(channel)
    youtube=get_youtube(channel,dict(os.environ))
    # Authenticate & verify private status for ALL 3 before touching any thumbnail.
    for s in selected:
        owned_video(youtube,s["video_id"],channel)
    receipts=[]
    report=ARTIFACT/channel/RESULT_NAME
    report.parent.mkdir(parents=True,exist_ok=True)
    if report.exists():
        raise ThumbnailRetryBlocked("RECEIPTS_ALREADY_EXIST_NO_REPLAY")
    print(f"THUMB_RETRY_{channel.upper()}_WAIT_AFTER_UPLOAD_{WAIT_AFTER_UPLOADING_SECONDS}S",flush=True)
    time.sleep(WAIT_AFTER_UPLOADING_SECONDS)
    first_failed=False
    for idx,item in enumerate(selected):
        record={"channel":channel,"episode":item["id"],"video_id":item["video_id"],
                "cover_sha256":sha(item["cover"]),"api_acknowledged":False,
                "visual_in_studio":"not_verified","private_preserved":False}
        if first_failed:
            record["result"]="skipped_after_test_failed"
            receipts.append(record)
            continue
        before=owned_video(youtube,item["video_id"],channel)
        old_thumb=(before.get("snippet",{}).get("thumbnails") or {}).get("high",{}).get("url")
        ok,reason=apply(youtube,item["video_id"],item["cover"])
        record["api_acknowledged"]=ok
        record["result"]=reason
        if ok:
            time.sleep(WAIT_AFTER_THUMB_SET_SECONDS)
            after=owned_video(youtube,item["video_id"],channel)
            new_thumb=(after.get("snippet",{}).get("thumbnails") or {}).get("high",{}).get("url")
            record["snippet_thumbnail_url_changed"]=bool(new_thumb and new_thumb!=old_thumb)
            record["snippet_has_thumbnail_url"]=bool(new_thumb)
            record["private_preserved"]=True
        else:
            record["private_preserved"]=True  # verified immediately before thumbnail attempt
        receipts.append(record)
        report.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(f"THUMB_{channel}_{item['id']}_{reason}",flush=True)
        if idx==0 and not ok:
            first_failed=True
    report.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if first_failed:
        raise ThumbnailRetryBlocked("FIRST_TEST_FAILED_OTHER_THUMBS_NOT_TOUCHED")
    if len(receipts)!=3 or not all(x["api_acknowledged"] and x["private_preserved"] for x in receipts):
        raise ThumbnailRetryBlocked("SOME_THUMBS_NOT_ACKNOWLEDGED")
    print(f"THREE_{channel.upper()}_THUMBNAIL_API_ACKNOWLEDGEMENTS_NO_STUDIO_VISIBILITY_CLAIM",flush=True)
    return 0

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--channel",choices=("games","alchemy"),required=True)
    args=parser.parse_args()
    try:
        return run(args.channel)
    except Exception as exc:
        reason=str(exc) if isinstance(exc,ThumbnailRetryBlocked) else type(exc).__name__
        print("THUMBNAIL_RETRY_BLOCKED_"+reason,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
