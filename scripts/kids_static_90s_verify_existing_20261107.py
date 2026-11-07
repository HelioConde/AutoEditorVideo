#!/usr/bin/env python3
"""Verify 3 already-accepted Emanuelly Kids PRIVATE videos and repair third cover.

READ-ONLY for YouTube videos; allows only thumbnails.set for the known third ID.
No videos.insert, videos.update, videos.delete or new image/MP4 generation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

from kids_static_90s_upload_20261107 import (
    OUT, CHANNEL_ID, validate_artifacts, youtube_client, KidsUploadBlocked
)

EXPECTED = {
    "kids-101-elefantinho-agua-escondida": "d7hjFP6Ky6w",
    "kids-102-quiz-sombras-animais": "ax0ude5BUhE",
    "kids-103-dinos-segredos-incriveis": "It-7R1o9k7Q",
}
OUTPUT = OUT / "kids-existing-3-video-verification.json"

def guard() -> None:
    e = os.environ
    if (e.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF") != "refs/heads/main"
            or e.get("GITHUB_EVENT_NAME") != "push"
            or e.get("GITHUB_RUN_ATTEMPT") != "1"
            or e.get("GITHUB_WORKFLOW") !=
            "Emanuelly Kids - verify 3 existing private videos and recover cover"):
        raise KidsUploadBlocked("PRIVATE_VERIFY_FIRST_MAIN_PUSH_ONLY")
    if e.get("KIDS_EXISTING_ONLY_APPROVED") != "yes":
        raise KidsUploadBlocked("EXISTING_ONLY_APPROVAL_REQUIRED")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise KidsUploadBlocked("KIDS_OAUTH_UNAVAILABLE")
    if e.get("PROXY_API_KEY") or e.get("PROXY_ACCOUNTS_JSON"):
        raise KidsUploadBlocked("IMAGE_SECRETS_FORBIDDEN")

def confirm_all(api, artifacts: list[dict]) -> list[dict]:
    # Poll known video IDs; never create a fourth or second copy.
    found = []
    for attempt, delay in enumerate((0, 12, 24, 35)):
        if delay:
            time.sleep(delay)
        result = api.videos().list(
            part="snippet,status", id=",".join(EXPECTED.values())
        ).execute()
        found = result.get("items") or []
        data = {v.get("id"): v for v in found}
        if all(video_id in data for video_id in EXPECTED.values()):
            break
    data = {v.get("id"): v for v in found}
    report = []
    for entry in artifacts:
        ep = entry["episode_id"]
        video_id = EXPECTED.get(ep)
        if not video_id:
            raise KidsUploadBlocked("UNEXPECTED_EPISODE_IN_VERIFICATION")
        v = data.get(video_id)
        if not v:
            raise KidsUploadBlocked("EXISTING_VIDEO_NOT_YET_VISIBLE_STOP_WITHOUT_REUPLOAD")
        sn = v.get("snippet", {})
        st = v.get("status", {})
        metadata = entry["metadata"]
        if (sn.get("channelId") != CHANNEL_ID
                or sn.get("title") != metadata["title"]
                or sn.get("description") != metadata["description"]):
            raise KidsUploadBlocked("VERIFIED_VIDEO_METADATA_OR_CHANNEL_MISMATCH")
        if (st.get("privacyStatus") != "private"
                or st.get("madeForKids") is not True):
            raise KidsUploadBlocked("EXISTING_VIDEO_PRIVACY_OR_KIDS_NOT_CONFIRMED")
        report.append({"episode_id": ep, "youtube_id": video_id,
                       "channel_id": CHANNEL_ID, "visibility": "private",
                       "made_for_kids": True,
                       "verified_existing_id": True,
                       "video_sha256": entry["sha256"],
                       "thumbnail_confirmed_by_original_receipt": ep !=
                           "kids-103-dinos-segredos-incriveis",
                       "thumbnail_api_acknowledged": None})
    if len(report) != 3:
        raise KidsUploadBlocked("NEED_ALL_THREE_EXISTING_PRIVATE_VIDEOS")
    return report

def verify() -> None:
    guard()
    artifacts = validate_artifacts()
    if [x["episode_id"] for x in artifacts] != list(EXPECTED):
        raise KidsUploadBlocked("SOURCE_ORDER_MISMATCH")
    api = youtube_client()
    records = confirm_all(api, artifacts)
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("THREE_EXISTING_KIDS_PRIVATE_MADE_FOR_KIDS_VERIFIED", flush=True)
    # First two covers were acknowledged by YouTube previously; touch only
    # the THIRD known video. Never re-insert any video.
    third = artifacts[2]
    third_record = records[2]
    try:
        from googleapiclient.http import MediaFileUpload
        result = api.thumbnails().set(
            videoId=third_record["youtube_id"],
            media_body=MediaFileUpload(str(third["cover"]),
                                       mimetype="image/jpeg")
        ).execute()
        third_record["thumbnail_api_acknowledged"] = bool(result.get("items"))
    except Exception:
        third_record["thumbnail_api_acknowledged"] = False
        third_record["thumbnail_review_in_youtube_studio"] = True
    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("KIDS_3_EXISTING_PRIVATE_VERIFIED_NO_NEW_UPLOADS", flush=True)
    if not third_record["thumbnail_api_acknowledged"]:
        print("KIDS_THIRD_COVER_REQUIRES_YOUTUBE_STUDIO_REVIEW", flush=True)

if __name__ == "__main__":
    try:
        verify()
    except Exception as exc:
        message = str(exc) if isinstance(exc, KidsUploadBlocked) else type(exc).__name__
        print("KIDS_EXISTING_VERIFY_BLOCKED_" + message, file=sys.stderr)
        raise SystemExit(2)
