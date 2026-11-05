#!/usr/bin/env python3
"""Resume ONLY the missing Gamer Shorts after a proven partial private upload.

Original run 42044136670 created six MP4s.
Original upload run 42048524469 confirmed game-001 (and all three Alchemy).
The game-002 upload may have timed out AFTER YouTube accepted it, so this
runner checks the owning channel's uploads playlist and recent private videos
before inserting anything. It never reuploads a known video.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from games_alchemy_ai_upload import (
    OUTPUT, OWNER, CHANNEL_EPISODES, UploadBlocked, check_artifact,
    get_youtube, publish_private, confirm_private, set_thumbnail, _sha
)
from youtube_channel_registry import KNOWN_IDS
from youtube_new_channels_oauth import verify_channel_identity

EXPECTED_RUN = "42044136670"
EXPECTED_SHA = "a414b9aea8d778f27c765cfb3d45e94612d0ee05"
EXPECTED_PREVIOUS_UPLOAD_RUN = "42048524469"
FIRST_ID = "61bCmdk2dV8"
FIRST_EP = "game-001-gta4-gta5"
RECEIPTS = ROOT / "gamer-existing-receipts" / "games-youtube-private-receipts.json"
OUT_RECEIPTS = OUTPUT / "games-youtube-resume-private-receipts.json"

def preflight() -> None:
    env = os.environ
    if env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise UploadBlocked("WRONG_REPOSITORY")
    if env.get("GITHUB_REF") != "refs/heads/main" or env.get("GITHUB_EVENT_NAME") != "push":
        raise UploadBlocked("ONLY_ONE_APPROVED_MAIN_PUSH")
    if env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise UploadBlocked("RERUN_BLOCKED_DUPLICATE_RISK")
    if env.get("GITHUB_WORKFLOW") != "Gamer - resume only missing two AI Shorts":
        raise UploadBlocked("UNEXPECTED_RECOVERY_WORKFLOW")
    if (env.get("AI_SIX_PILOT_ORIGINAL_RUN_ID") != EXPECTED_RUN or
        env.get("AI_SIX_PILOT_ORIGINAL_SHA") != EXPECTED_SHA or
        env.get("PREVIOUS_UPLOAD_RUN_ID") != EXPECTED_PREVIOUS_UPLOAD_RUN):
        raise UploadBlocked("ORIGINAL_RUN_OR_UPLOAD_RUN_NOT_PINNED")
    if env.get("GAMER_RESUME_APPROVED") != "true":
        raise UploadBlocked("EXPLICIT_CREATOR_APPROVAL_REQUIRED")
    if not env.get("YOUTUBE_CLIENT_JSON") or not env.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise UploadBlocked("MISSING_SEPARATE_GAMER_OAUTH")
    if not RECEIPTS.is_file():
        raise UploadBlocked("PREVIOUS_RECEIPT_ARTIFACT_MISSING")
    if OUT_RECEIPTS.exists():
        raise UploadBlocked("RECOVERY_ALREADY_ATTEMPTED")

def check_first_receipt(items: list[dict]) -> dict:
    old = json.loads(RECEIPTS.read_text(encoding="utf-8"))
    if (not isinstance(old,list) or len(old)!=1 or
        old[0].get("channel")!="games" or
        old[0].get("episode_id")!=FIRST_EP or
        old[0].get("youtube_video_id")!=FIRST_ID or
        old[0].get("visibility")!="private" or
        old[0].get("confirmed_private") is not True):
        raise UploadBlocked("KNOWN_FIRST_UPLOAD_RECEIPT_INVALID")
    if old[0].get("source_sha256") != _sha(items[0]["video"]):
        raise UploadBlocked("FIRST_MP4_HASH_DIFFERS_FROM_UPLOADED")
    return old[0]

def _all_owned_uploads(youtube) -> dict[str,dict]:
    """Returns recently uploaded owned videos, including private owner uploads."""
    data = youtube.channels().list(part="contentDetails",mine=True).execute()
    listed = data.get("items") or []
    if len(listed)!=1 or listed[0].get("id") != KNOWN_IDS["games"]:
        raise UploadBlocked("RECOVERY_CHANNEL_ID_MISMATCH")
    playlist_id = (listed[0].get("contentDetails",{}).get("relatedPlaylists",{})
                   .get("uploads"))
    if not playlist_id:
        raise UploadBlocked("OWN_UPLOADS_PLAYLIST_MISSING")
    ids = []
    token = None
    for _ in range(5):
        kwargs = {"part":"snippet,contentDetails","playlistId":playlist_id,"maxResults":50}
        if token:
            kwargs["pageToken"]=token
        response = youtube.playlistItems().list(**kwargs).execute()
        for row in response.get("items",[]):
            video_id = row.get("contentDetails",{}).get("videoId")
            if video_id:
                ids.append(video_id)
        token = response.get("nextPageToken")
        if not token:
            break
    result = {}
    for i in range(0,len(ids),50):
        response = youtube.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute()
        for row in response.get("items",[]):
            if row.get("snippet",{}).get("channelId") == KNOWN_IDS["games"]:
                result[row["id"]] = row
    return result

def _find_uploaded(youtube, title: str) -> list[str]:
    candidates = _all_owned_uploads(youtube)
    recent = []
    for vid, item in candidates.items():
        snippet = item.get("snippet",{})
        if (snippet.get("title","").strip() == title.strip() and
            item.get("status",{}).get("privacyStatus") == "private"):
            # Avoid matching older videos with an identical title.
            stamp = snippet.get("publishedAt","")
            if stamp >= "2026-11-05T14:20":
                recent.append(vid)
    return recent

def _receipt(item: dict, video_id: str, source: str, youtube=None) -> dict:
    record = {"channel":"games","episode_id":item["id"],
              "youtube_video_id":video_id,"visibility":"private",
              "source_sha256":_sha(item["video"]),
              "recovered_from":source,
              "confirmed_private":True,
              "thumbnail_acknowledged":None}
    if youtube is not None and source == "newly_uploaded":
        record["thumbnail_acknowledged"]=set_thumbnail(youtube,video_id,item["cover"])
        record["confirmed_private"]=confirm_private(youtube,video_id,KNOWN_IDS["games"])
    return record

def _save(rows: list[dict]) -> None:
    OUT_RECEIPTS.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n",
                            encoding="utf-8")

def resume() -> None:
    preflight()
    items = check_artifact("games")
    first = check_first_receipt(items)
    youtube = get_youtube("games",dict(os.environ))
    verify_channel_identity(youtube,"games")
    if not confirm_private(youtube,FIRST_ID,KNOWN_IDS["games"]):
        raise UploadBlocked("KNOWN_FIRST_PRIVATE_UPLOAD_NOT_CONFIRMED")
    receipts = [_receipt(items[0],FIRST_ID,"first_upload_verified_again")]
    receipts[0]["thumbnail_acknowledged"]=first.get("thumbnail_acknowledged")
    _save(receipts)
    # Game-002 had a TimeoutError; it might have been created at Google.
    for item in items[1:]:
        found = _find_uploaded(youtube,item["metadata"]["title"])
        if not found:
            time.sleep(15)
            found = _find_uploaded(youtube,item["metadata"]["title"])
        if len(found)>1:
            raise UploadBlocked("AMBIGUOUS_EXISTING_UPLOAD_TITLE_" + item["id"])
        if found:
            vid=found[0]
            record=_receipt(item,vid,"found_existing_private_upload")
            receipts.append(record)
            _save(receipts)
            print("EXISTING_PRIVATE_GAMER_"+item["id"]+"_"+vid,flush=True)
            continue
        try:
            vid=publish_private(youtube,item)
        except Exception:
            # Never retry a timed-out videos.insert; check once for an accepted
            # upload before exiting. A missing result is still ambiguous.
            time.sleep(20)
            found=_find_uploaded(youtube,item["metadata"]["title"])
            if len(found)!=1:
                raise UploadBlocked("AMBIGUOUS_INSERT_NO_REUPLOAD_"+item["id"]) from None
            vid=found[0]
            record=_receipt(item,vid,"found_after_ambiguous_insert")
        else:
            record=_receipt(item,vid,"newly_uploaded",youtube=youtube)
        receipts.append(record)
        _save(receipts)
        print("CONFIRMED_PRIVATE_GAMER_"+item["id"]+"_"+vid,flush=True)
        if record["confirmed_private"] is not True:
            raise UploadBlocked("PRIVATE_CONFIRMATION_FAILED_NO_RETRY_"+item["id"])
    if len(receipts)!=3 or len({x["youtube_video_id"] for x in receipts})!=3:
        raise UploadBlocked("THREE_UNIQUE_PRIVATE_UPLOADS_NOT_CONFIRMED")
    print("ALL_THREE_GAMER_SHORTS_CONFIRMED_PRIVATE",flush=True)

def main() -> int:
    try:
        resume()
        return 0
    except Exception as exc:
        err = str(exc) if isinstance(exc,UploadBlocked) else type(exc).__name__
        print("GAMER_PRIVATE_RESUME_BLOCKED_"+err,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
