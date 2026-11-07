#!/usr/bin/env python3
"""Exactly three Emanuelly Kids private YouTube uploads from approved render artifacts.

Never use Otaku or other channel credentials. Fail closed on all ownership,
original media, duration, metadata and sha256 checks. One attempt only.
The user explicitly requested generation and upload on 2026-11-07; default
private so they can inspect the finished children-directed content in Studio.
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

from kids_static_90s_20261107 import (
    OUT, OWNER, CHANNEL_ID, IDS, check_manifest, probe, digest, KidsBlocked
)
from youtube_new_channels_oauth import validate_token_fields, verify_channel_identity
from youtube_public_tags import public_tags

RECEIPTS = OUT / "kids-private-youtube-receipts.json"

class KidsUploadBlocked(ValueError):
    pass

def guard() -> None:
    env = os.environ
    if (env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "push"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise KidsUploadBlocked("ONLY_FIRST_MAIN_PUSH")
    if env.get("GITHUB_WORKFLOW") != "Emanuelly Kids - 3 original static 90s Shorts private upload":
        raise KidsUploadBlocked("WRONG_GITHUB_WORKFLOW")
    if env.get("KIDS_UPLOAD_AUTHORIZED") != "yes":
        raise KidsUploadBlocked("EXPLICIT_USER_UPLOAD_AUTHORIZATION_MISSING")
    if not env.get("YOUTUBE_CLIENT_JSON") or not env.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise KidsUploadBlocked("KIDS_EXCLUSIVE_OAUTH_SECRETS_MISSING")
    if env.get("YOUTUBE_BR_TOKEN_JSON") or env.get("YOUTUBE_EN_TOKEN_JSON"):
        raise KidsUploadBlocked("CROSS_CHANNEL_SECRETS_FORBIDDEN")
    if RECEIPTS.exists():
        raise KidsUploadBlocked("PREVIOUS_RECEIPTS_EXIST_NEVER_REUPLOAD")

def validate_artifacts() -> list[dict]:
    expected = check_manifest()
    if not (OUT / "summary.json").is_file():
        raise KidsUploadBlocked("THREE_MP4_RENDER_SUMMARY_MISSING")
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    if (summary.get("schema") != "autoeditorvideo/kids-static-90s-batch/v1"
            or summary.get("owner") != OWNER
            or summary.get("target_channel") != CHANNEL_ID):
        raise KidsUploadBlocked("WRONG_RENDER_BATCH")
    items = summary.get("videos", [])
    if [x.get("id") for x in items] != list(IDS):
        raise KidsUploadBlocked("EXACTLY_THREE_KIDS_EPISODES_REQUIRED")
    outputs = []
    for planned, item in zip(expected, items):
        if item["id"] != planned["id"]:
            raise KidsUploadBlocked("MISMATCHED_EPISODE")
        folder = (OUT / item["id"]).resolve()
        if folder.parent != OUT.resolve():
            raise KidsUploadBlocked("ARTIFACT_FOLDER_ESCAPE")
        files = {name: folder / name for name in ("final.mp4", "thumb.jpg",
                                                 "qa.json", "metadata.json")}
        if not all(p.is_file() for p in files.values()):
            raise KidsUploadBlocked("VIDEO_THUMBNAIL_QA_OR_METADATA_MISSING")
        qa = json.loads(files["qa.json"].read_text(encoding="utf-8"))
        meta = json.loads(files["metadata.json"].read_text(encoding="utf-8"))
        if (qa.get("automated_technical_qa") != "passed"
                or qa.get("channel_id") != CHANNEL_ID
                or qa.get("mesh_warp_puppet_disabled") is not True
                or qa.get("word_boundary_captions") is not True
                or qa.get("youtube_privacy") != "private"):
            raise KidsUploadBlocked("RENDER_QA_INCOMPLETE")
        if (meta.get("channel") != "kids"
                or meta.get("id") != item["id"] or meta.get("channel_id") != CHANNEL_ID
                or meta.get("title") != planned["title"]
                or meta.get("description") != planned["description"]
                or meta.get("tags") != planned["tags"]
                or meta.get("selfDeclaredMadeForKids") is not True
                or meta.get("containsSyntheticMedia") is not True
                or meta.get("privacyStatus") != "private"):
            raise KidsUploadBlocked("CHILDRENS_METADATA_MISMATCH")
        if (digest(files["final.mp4"]) != qa["mp4_sha256"]
                or digest(files["thumb.jpg"]) != qa["cover_sha256"]
                or item.get("mp4_sha256") != qa["mp4_sha256"]
                or item.get("cover_sha256") != qa["cover_sha256"]
                or meta.get("mp4_sha256") != qa["mp4_sha256"]):
            raise KidsUploadBlocked("MP4_OR_THUMBNAIL_HASH_MISMATCH")
        streams = probe(files["final.mp4"])
        length = float(streams["format"]["duration"])
        vid = [s for s in streams["streams"] if s.get("codec_type") == "video"]
        audio = [s for s in streams["streams"] if s.get("codec_type") == "audio"]
        if (not 90 <= length <= 121 or len(vid) != 1 or not audio
                or vid[0].get("width") != 1080 or vid[0].get("height") != 1920
                or files["final.mp4"].stat().st_size < 300_000
                or files["thumb.jpg"].stat().st_size < 25000):
            raise KidsUploadBlocked("MEDIA_DURATION_SIZE_OR_AUDIO_QA_FAILED")
        if len(meta["title"]) > 100 or len(",".join(meta["tags"])) > 500:
            raise KidsUploadBlocked("PUBLIC_METADATA_LIMIT_EXCEEDED")
        outputs.append({"episode_id": item["id"], "video": files["final.mp4"],
                        "cover": files["thumb.jpg"], "metadata": meta,
                        "sha256": qa["mp4_sha256"]})
    return outputs

def youtube_client():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        c = json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        t = json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
        validate_token_fields(c, t)
        cred = Credentials.from_authorized_user_info(
            t, scopes=["https://www.googleapis.com/auth/youtube.upload",
                       "https://www.googleapis.com/auth/youtube.readonly"])
        if not cred.valid:
            cred.refresh(Request())
        http = AuthorizedHttp(cred, http=httplib2.Http(timeout=180))
        api = build("youtube", "v3", http=http, cache_discovery=False)
        verified = verify_channel_identity(api, "kids")
        if verified != CHANNEL_ID:
            raise KidsUploadBlocked("WRONG_KIDS_CHANNEL")
        print("KIDS_YOUTUBE_DESTINATION_VERIFIED_" + CHANNEL_ID, flush=True)
        return api
    except KidsUploadBlocked:
        raise
    except Exception:
        raise KidsUploadBlocked("KIDS_OAUTH_MISSING_EXPIRED_OR_WRONG_CHANNEL") from None

def persist(rows: list[dict]) -> None:
    RECEIPTS.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

def insert_private(youtube, item: dict) -> str:
    from googleapiclient.http import MediaFileUpload
    meta = item["metadata"]
    body = {
        "snippet": {
            "title": meta["title"], "description": meta["description"],
            "tags": public_tags(meta["tags"]), "categoryId": "1",
            "defaultLanguage": "pt-BR"
        },
        "status": {
            "privacyStatus": "private", "selfDeclaredMadeForKids": True,
            "containsSyntheticMedia": True
        }
    }
    req = youtube.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(item["video"]), mimetype="video/mp4",
                                   chunksize=8 * 1024 * 1024, resumable=True),
        notifySubscribers=False)
    response = None
    # NEVER retry a potentially accepted video; one request per item.
    while response is None:
        _, response = req.next_chunk(num_retries=0)
    video_id = (response or {}).get("id")
    if not isinstance(video_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise KidsUploadBlocked("VIDEO_ID_NOT_CONFIRMED_STOP_NO_REUPLOAD")
    return video_id

def verify_private(youtube, video_id: str) -> bool:
    try:
        response = youtube.videos().list(part="snippet,status", id=video_id).execute()
        videos = response.get("items") or []
        return (len(videos) == 1
                and videos[0]["snippet"].get("channelId") == CHANNEL_ID
                and videos[0]["status"].get("privacyStatus") == "private"
                and videos[0]["status"].get("madeForKids") is True)
    except Exception:
        return False

def upload() -> None:
    guard()
    videos = validate_artifacts()
    api = youtube_client()
    receipts = []
    for item in videos:
        video_id = insert_private(api, item)
        receipt = {"episode_id": item["episode_id"], "youtube_id": video_id,
                   "channel_id": CHANNEL_ID, "visibility": "private",
                   "made_for_kids": True, "video_sha256": item["sha256"],
                   "thumbnail_acknowledged": False, "confirmed_private": False}
        receipts.append(receipt)
        persist(receipts)  # BEFORE attempting thumbnail or second upload.
        receipt["confirmed_private"] = verify_private(api, video_id)
        persist(receipts)
        if not receipt["confirmed_private"]:
            raise KidsUploadBlocked("UPLOAD_ACCEPTED_BUT_CHANNEL_STATUS_UNCONFIRMED")
        try:
            from googleapiclient.http import MediaFileUpload
            time.sleep(75)  # allow initial YouTube processing
            result = api.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(item["cover"]), mimetype="image/jpeg")).execute()
            receipt["thumbnail_acknowledged"] = bool(result.get("items"))
        except Exception:
            # May be a Shorts thumbnail API limitation or processing delay.
            # Keep already-created ID; NEVER re-insert the same video.
            receipt["thumbnail_acknowledged"] = False
            receipt["thumbnail_review_required"] = True
        persist(receipts)
        print("KIDS_PRIVATE_UPLOADED_" + item["episode_id"] + "_" + video_id,
              flush=True)
    print("KIDS_3_PRIVATE_VIDEOS_UPLOADED_AND_VERIFIED", flush=True)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=("preflight", "upload"),
                        default="preflight")
    args = parser.parse_args()
    try:
        if args.action == "preflight":
            print("KIDS_UPLOAD_PREFLIGHT_THREE_IDS_" + ",".join(e["id"] for e in check_manifest()))
        else:
            upload()
        return 0
    except Exception as exc:
        msg = str(exc) if isinstance(exc, (KidsUploadBlocked, KidsBlocked)) else type(exc).__name__
        print("KIDS_PRIVATE_UPLOAD_BLOCKED_" + msg, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
