#!/usr/bin/env python3
"""Channel-scoped uploader for the six AI-illustrated AutoEditorVideo Shorts.

Consumes validated MP4+JPG artifacts. YouTube credential and channel ID are
verified per invocation. Only the explicitly reserved Gamer or Alchemy trio
is eligible. No upload is public by default, no secrets are written to disk,
and a failed/ambiguous upload is NEVER retried automatically.
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
from production_reservations import assert_reserved
from youtube_channel_registry import get_channel, KNOWN_IDS
from youtube_new_channels_oauth import validate_token_fields, verify_channel_identity
from youtube_public_tags import public_tags

OUTPUT = ROOT / "cloud-games-alchemy-ai-six"
OWNER = "games_alchemy_six_shorts_20261105"
CHANNEL_EPISODES = {
    "games": ["game-001-gta4-gta5", "game-002-primeira-noite-minecraft",
              "game-003-minecraft-sem-amarelo"],
    "alchemy": ["alchemy-001-chatgpt-gifs",
                "alchemy-002-images-26-consistencia",
                "alchemy-003-gif-animado-tutorial"]
}

class UploadBlocked(ValueError):
    pass

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preflight(channel: str, env: dict) -> dict:
    if channel not in CHANNEL_EPISODES:
        raise UploadBlocked("UNSUPPORTED_CHANNEL")
    if env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise UploadBlocked("WRONG_REPOSITORY")
    if env.get("GITHUB_REF") != "refs/heads/main":
        raise UploadBlocked("MAIN_ONLY")
    if env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise UploadBlocked("NEVER_RERUN_AMBIGUOUS_UPLOAD")
    if env.get("GITHUB_EVENT_NAME") != "push":
        raise UploadBlocked("ONE_SHOT_PUSH_ONLY")
    if env.get("GITHUB_WORKFLOW") != "Gamer + Alchemy - private upload from completed AI render":
        raise UploadBlocked("UNEXPECTED_UPLOAD_WORKFLOW")
    # This workflow may ONLY use the already completed, uniquely pinned render.
    if (env.get("AI_SIX_PILOT_ORIGINAL_RUN_ID") != "42044136670" or
        env.get("AI_SIX_PILOT_ORIGINAL_SHA") != "a414b9aea8d778f27c765cfb3d45e94612d0ee05"):
        raise UploadBlocked("UNAUTHORIZED_ORIGINAL_RENDER")
    if env.get("AI_SIX_PILOT_USER_APPROVED") != "true":
        raise UploadBlocked("EXPLICIT_PILOT_APPROVAL_REQUIRED")
    cfg = get_channel(channel)
    if cfg["youtube_channel_id"] != KNOWN_IDS[channel]:
        raise UploadBlocked("CHANNEL_REGISTRY_MISMATCH")
    if cfg.get("oauth_token_secret_name") != (
            "YOUTUBE_GAMES_TOKEN_JSON" if channel == "games"
            else "YOUTUBE_ALCHEMY_TOKEN_JSON"):
        raise UploadBlocked("UNEXPECTED_TOKEN_SECRET_ROUTE")
    if cfg.get("youtube_environment") != "youtube-private-upload":
        raise UploadBlocked("WRONG_ENVIRONMENT")
    if cfg.get("visibility_default") != "private":
        raise UploadBlocked("PRIVATE_UPLOAD_POLICY_CHANGED")
    if not env.get("YOUTUBE_CLIENT_JSON") or not env.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise UploadBlocked("GITHUB_YOUTUBE_SECRETS_NOT_CONFIGURED")
    if not OUTPUT.is_dir():
        raise UploadBlocked("RENDER_ARTIFACT_MISSING")
    return cfg

def check_artifact(channel: str) -> list[dict]:
    root = OUTPUT.resolve()
    summary_file = root / "summary.json"
    if not summary_file.is_file():
        raise UploadBlocked("MISSING_BATCH_SUMMARY")
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    if summary.get("schema") != "autoeditorvideo/six-ai-illustrated-review/v1":
        raise UploadBlocked("WRONG_RENDER_ARTIFACT")
    if summary.get("publication") != "not_performed" or summary.get("count") != 6:
        raise UploadBlocked("NOT_A_NEW_SIX_VIDEO_ARTIFACT")
    if summary.get("production_owner") != OWNER or len(summary.get("videos", [])) != 6:
        raise UploadBlocked("WRONG_ARTIFACT_OWNER")
    selected = [x for x in summary["videos"] if x["channel"] == channel]
    if [x["id"] for x in selected] != CHANNEL_EPISODES[channel]:
        raise UploadBlocked("CHANNEL_ARTIFACT_SET_MISMATCH")
    found = []
    for v in selected:
        episode = v["id"]
        assert_reserved(channel, episode, OWNER)
        folder = (root / episode).resolve()
        if folder.parent != root:
            raise UploadBlocked("ARTIFACT_PATH_ESCAPE")
        mp4, cover, qa_file, metadata = (
            folder / "final.mp4", folder / "thumb.jpg",
            folder / "qa.json", folder / "metadata.json")
        if any(not p.is_file() for p in (mp4, cover, qa_file, metadata)):
            raise UploadBlocked("MISSING_RENDERED_OUTPUT")
        qa = json.loads(qa_file.read_text(encoding="utf-8"))
        meta = json.loads(metadata.read_text(encoding="utf-8"))
        if qa.get("structural_qa") != "passed":
            raise UploadBlocked("RENDER_QA_FAILED")
        if qa.get("mp4_sha256") != v.get("sha256") or _sha(mp4) != v.get("sha256"):
            raise UploadBlocked("MP4_HASH_MISMATCH")
        if qa.get("cover_sha256") != _sha(cover) or qa.get("manual_visual_qc") != "not_performed":
            raise UploadBlocked("INVALID_COVER_OR_QA_RECORD")
        if meta.get("id") != episode or meta.get("channel") != channel:
            raise UploadBlocked("CROSS_CHANNEL_METADATA")
        if meta.get("channel_id") != KNOWN_IDS[channel] or meta.get("render_sha256") != v.get("sha256"):
            raise UploadBlocked("CHANNEL_ID_OR_SHA_MISMATCH")
        if meta.get("ai_visuals_only") is not True or meta.get("containsSyntheticMedia") is not True:
            raise UploadBlocked("SYNTHETIC_MEDIA_DISCLOSURE_REQUIRED")
        if meta.get("categoryId") != ("20" if channel == "games" else "28"):
            raise UploadBlocked("WRONG_YOUTUBE_CATEGORY")
        if not 20 <= qa.get("duration_seconds", -1) <= 180:
            raise UploadBlocked("INVALID_SHORT_DURATION")
        if not isinstance(meta.get("tags"), list) or not meta["tags"]:
            raise UploadBlocked("TAGS_MISSING")
        if len(meta.get("title", "")) > 100 or not meta.get("description"):
            raise UploadBlocked("BAD_METADATA")
        if ("Visuais ilustrativos" not in meta["description"]
            and "Ilustrações geradas por IA" not in meta["description"]):
            raise UploadBlocked("AI_DISCLOSURE_NOT_IN_DESCRIPTION")
        if mp4.stat().st_size < 250000 or cover.stat().st_size < 25000:
            raise UploadBlocked("RENDER_OUTPUT_TOO_SMALL")
        found.append({"video": mp4, "cover": cover, "metadata": meta, "id": episode})
    return found

def get_youtube(channel: str, env: dict):
    # Import only after artifact, permission and identity preflight.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        client = json.loads(env["YOUTUBE_CLIENT_JSON"])
        token = json.loads(env["YOUTUBE_CHANNEL_TOKEN_JSON"])
        validate_token_fields(client, token)
        credential = Credentials.from_authorized_user_info(
            token, scopes=["https://www.googleapis.com/auth/youtube.upload",
                           "https://www.googleapis.com/auth/youtube.readonly"])
        if not credential.valid:
            credential.refresh(Request())
        # Private upload can take longer than googleapiclient's default socket
        # timeout; set a bounded 180-second HTTP timeout without extra retries.
        api_http = AuthorizedHttp(credential, http=httplib2.Http(timeout=180))
        api = build("youtube", "v3", http=api_http, cache_discovery=False)
        verify_channel_identity(api, channel)
        return api
    except Exception:
        raise UploadBlocked("OAUTH_INVALID_OR_WRONG_CHANNEL") from None

def publish_private(youtube, item: dict) -> str:
    from googleapiclient.http import MediaFileUpload
    meta = item["metadata"]
    # We intentionally upload PRIVATE: user can review in Studio.
    # No public status change is attempted without a separate explicit approval.
    insert_body = {
        "snippet": {"title": meta["title"], "description": meta["description"],
                    "tags": public_tags(meta["tags"]), "categoryId": meta["categoryId"],
                    "defaultLanguage": "pt-BR"},
        "status": {"privacyStatus": "private",
                   "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True}
    }
    upload = youtube.videos().insert(
        part="snippet,status",
        body=insert_body,
        media_body=MediaFileUpload(str(item["video"]),
                                   mimetype="video/mp4", resumable=True,
                                   chunksize=8*1024*1024),
        notifySubscribers=False)
    response = None
    # Network ambiguity is never automatically retried: a repeat might duplicate a Short.
    while response is None:
        _, response = upload.next_chunk(num_retries=0)
    video_id = response.get("id")
    if not video_id or not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
        raise UploadBlocked("YOUTUBE_UPLOAD_ID_UNCONFIRMED")
    return video_id

def set_thumbnail(youtube, video_id: str, cover: Path) -> bool:
    from googleapiclient.http import MediaFileUpload
    try:
        response = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(cover), mimetype="image/jpeg")).execute()
        return bool(response.get("items"))
    except Exception:
        return False

def confirm_private(youtube, video_id: str, expected_channel: str) -> bool:
    try:
        response = youtube.videos().list(part="snippet,status", id=video_id).execute()
        items = response.get("items", [])
        return (len(items) == 1
                and items[0]["snippet"]["channelId"] == expected_channel
                and items[0]["status"]["privacyStatus"] == "private")
    except Exception:
        return False

def upload_trio(channel: str) -> None:
    env = dict(os.environ)
    preflight(channel, env)
    videos = check_artifact(channel)
    youtube = get_youtube(channel, env)
    # Validate identity before first video, never use a token from another channel.
    receipts = []
    path = OUTPUT / f"{channel}-youtube-private-receipts.json"
    if path.exists():
        raise UploadBlocked("UPLOAD_RECEIPTS_ALREADY_EXIST_NO_RETRY")
    for item in videos:
        video_id = publish_private(youtube, item)
        # Write receipt immediately: even thumbnail errors should not cause reupload.
        receipt = {"channel": channel, "episode_id": item["id"],
                   "youtube_video_id": video_id, "visibility": "private",
                   "thumbnail_acknowledged": False,
                   "source_sha256": _sha(item["video"])}
        receipts.append(receipt)
        path.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
        # Shorts may not be ready for a custom cover immediately after upload.
        # Persist the confirmed video ID FIRST, then wait before thumbnails.set.
        receipt["thumbnail_wait_after_upload_seconds"] = 75
        time.sleep(75)
        receipt["thumbnail_acknowledged"] = set_thumbnail(youtube, video_id, item["cover"])
        receipt["confirmed_private"] = confirm_private(
            youtube, video_id, KNOWN_IDS[channel])
        path.write_text(json.dumps(receipts, indent=2), encoding="utf-8")
        print("UPLOADED_PRIVATE_" + channel + "_" + item["id"] + "_" + video_id, flush=True)
        if not receipt["confirmed_private"]:
            raise UploadBlocked("YOUTUBE_PRIVATE_IDENTITY_UNCONFIRMED_DO_NOT_RETRY")
        if receipt["thumbnail_acknowledged"] is not True:
            # The video itself may already be on YouTube. Never call
            # videos.insert again to repair a cover: use thumbnail-only recovery.
            raise UploadBlocked("THUMBNAIL_NOT_ACKNOWLEDGED_RECOVER_WITHOUT_VIDEO_REUPLOAD")
    print("THREE_PRIVATE_UPLOADS_VERIFIED_" + channel, flush=True)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--channel", choices=["games","alchemy"], required=True)
    args = p.parse_args()
    try:
        upload_trio(args.channel)
        return 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, UploadBlocked) else type(exc).__name__
        print("SIX_AI_YOUTUBE_BLOCKED_" + message, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
