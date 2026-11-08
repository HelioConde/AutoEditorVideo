#!/usr/bin/env python3
"""One-episode at a time recovery of exactly six failed BR/EN batch15 Shorts.

Only this new one-shot private-only workflow. Each media artifact has its own
QA, own strict YouTube reconciliation and receipt. No duplicate insert retries,
no public updates, no touching previous nine videos. Never print OAuth secrets.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time

import five_channel_fifteen_20261108 as batch
import five_channel_fifteen_upload_20261108 as uploader
from youtube_channel_registry import KNOWN_IDS, get_channel
from kids_static_90s_20261107 import digest, probe

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cloud-batch15-br-en-recovery-20261108"
WORKFLOW = "AutoEditorVideo - recover six BR EN batch15 originals private 20261108"
LAUNCH = ROOT / "conteudos" / "lote-15-br-en-private-recovery-launch-20261108.json"
SOURCE_RUN = 42481839933
SOURCE_SHA = "49bdeaf75201ce2bc363836b4ac9ee4dbc19f0b6"
EPISODES = {"br": batch.EXPECTED["br"], "en": batch.EXPECTED["en"]}

class RecoveryBlocked(ValueError):
    pass

def check(channel: str, episode: str):
    if channel not in EPISODES or episode not in EPISODES[channel]:
        raise RecoveryBlocked("ONLY_SIX_ORIGINAL_FAILED_BR_EN_EPISODES")
    launch = json.loads(LAUNCH.read_text(encoding="utf-8"))
    if (launch.get("schema") != "autoeditorvideo/batch15-br-en-private-recovery/v1"
        or launch.get("source_run_id") != SOURCE_RUN
        or launch.get("source_sha") != SOURCE_SHA
        or launch.get("requested_visibility") != "private"
        or launch.get("creator_authorized_retry") is not True
        or launch.get("excluded_channels") != ["games", "kids", "alchemy"]
        or launch.get("source_privates_must_remain_untouched") is not True
        or launch.get("render_each_video_separately") is not True
        or launch.get("target_ids") != {c: list(EPISODES[c]) for c in EPISODES}):
        raise RecoveryBlocked("LAUNCH_NOT_EXACT_OR_PRIVATE")
    row = next((x for x in batch.validate(channel) if x["id"] == episode), None)
    if row is None or row["channel_id"] != KNOWN_IDS[channel] or row["made_for_kids"] is not False:
        raise RecoveryBlocked("RESERVATION_OR_DESTINATION_WRONG")
    return row

def environment_guard(channel: str, episode: str, operation: str):
    e = os.environ
    if (e.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo"
        or e.get("GITHUB_REF") != "refs/heads/main"
        or e.get("GITHUB_EVENT_NAME") != "push"
        or e.get("GITHUB_RUN_ATTEMPT") != "1"
        or e.get("GITHUB_WORKFLOW") != WORKFLOW
        or e.get("RECOVERY_CHANNEL") != channel
        or e.get("RECOVERY_EPISODE") != episode):
        raise RecoveryBlocked("ONE_SHOT_MAIN_EXACT_CHANNEL_EPISODE_GUARD")
    if operation == "render":
        if (e.get("RECOVERY_RENDER_AUTHORIZED") != "yes"
            or e.get("IMAGE_MODEL") != "gpt-image-2"
            or e.get("MAX_IMAGE_CALLS") != "8"
            or any(e.get(x) for x in ("YOUTUBE_CLIENT_JSON",
                "YOUTUBE_CHANNEL_TOKEN_JSON", "YOUTUBE_BR_TOKEN_JSON",
                "YOUTUBE_EN_TOKEN_JSON"))):
            raise RecoveryBlocked("EIGHT_IMAGE_LIMIT_OR_RENDER_NO_YOUTUBE_AUTH")
    elif operation == "upload":
        if (e.get("RECOVERY_PRIVATE_UPLOAD_AUTHORIZED") != "yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or any(e.get(x) for x in ("PROXY_ACCOUNTS_JSON","PROXY_API_KEY",
                "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
                "YOUTUBE_GAMES_TOKEN_JSON"))
            or get_channel(channel)["oauth_token_secret_name"] != batch.TOKENS[channel]):
            raise RecoveryBlocked("CHANNEL_OAUTH_OR_IMAGE_SECRETS_NOT_ISOLATED")
    else:
        raise RecoveryBlocked("INVALID_OPERATION")

def folder_for(channel: str, episode: str) -> Path:
    return OUT / channel / episode

def render(channel: str, episode: str):
    row = check(channel, episode)
    environment_guard(channel, episode, "render")
    folder = folder_for(channel, episode)
    if folder.exists():
        raise RecoveryBlocked("EXISTING_MEDIA_REFUSE_SECOND_RENDER")
    folder.mkdir(parents=True, exist_ok=False)
    engine = batch.engine
    voice, seconds, words = engine.voice_takes(row, folder, channel)
    from gerar_video_codex import proxy_key, check_proxy_accounts
    key = proxy_key()
    check_proxy_accounts(key)
    pictures = engine.images(row, folder, key, channel)
    result = engine.render_one(row, folder, voice, seconds, words, pictures, channel)
    qa_file = folder / "qa.json"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    qa.update({
        "batch": "batch15-br-en-recovery-20261108",
        "source_run_id": SOURCE_RUN,
        "manual_visual_review": False,
        "visual_review_status": "pending",
        "publication_allowed": False,
        "original_artwork_only": True
    })
    qa_file.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    meta_file = folder / "metadata.json"
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    if metadata["privacyStatus"] != "private" or metadata["channel_id"] != KNOWN_IDS[channel]:
        raise RecoveryBlocked("WRONG_PRIVACY_OR_CHANNEL")
    summary = {
        "schema": "autoeditorvideo/batch15-br-en-single-recovery/v1",
        "channel": channel, "channel_id": KNOWN_IDS[channel],
        "episode_id": episode, "source_run_id": SOURCE_RUN,
        "visibility": "private", "video": result
    }
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for p in folder.glob("tts-*"):
        if p.is_dir(): shutil.rmtree(p)
    (folder/"props.json").unlink(missing_ok=True)
    print("BATCH15_RECOVERY_MP4_QA_PASSED_"+channel+"_"+episode, flush=True)

def media(channel: str, episode: str) -> dict:
    row = check(channel, episode)
    f = folder_for(channel, episode)
    summary,qa_file,meta_file = f/"summary.json",f/"qa.json",f/"metadata.json"
    video,cover = f/"final.mp4",f/"thumb.jpg"
    if not all(p.is_file() for p in (summary,qa_file,meta_file,video,cover)):
        raise RecoveryBlocked("ORIGINAL_APPROVED_MEDIA_FILES_MISSING")
    report = json.loads(summary.read_text(encoding="utf-8"))
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    md = json.loads(meta_file.read_text(encoding="utf-8"))
    if (report.get("schema") != "autoeditorvideo/batch15-br-en-single-recovery/v1"
        or report.get("channel") != channel or report.get("episode_id") != episode
        or report.get("source_run_id") != SOURCE_RUN or report.get("visibility") != "private"
        or report.get("channel_id") != KNOWN_IDS[channel]
        or report.get("video",{}).get("id") != episode
        or qa.get("schema") != "autoeditorvideo/remaining-static-original-90s-qa/v1"
        or qa.get("automated_technical_qa") != "passed"
        or qa.get("episode_id") != episode or qa.get("channel") != channel
        or qa.get("channel_id") != KNOWN_IDS[channel]
        or qa.get("word_boundaries_synced") is not True
        or qa.get("publication_allowed") is not False
        or qa.get("youtube_upload") != "not_performed"
        or md.get("id") != episode or md.get("channel") != channel
        or md.get("channel_id") != KNOWN_IDS[channel]
        or md.get("privacyStatus") != "private"
        or md.get("selfDeclaredMadeForKids") is not False
        or md.get("containsSyntheticMedia") is not True
        or md.get("title") != row["title"]
        or md.get("description") != row["description"]
        or md.get("tags") != row["tags"]
        or md.get("categoryId") != batch.CATEGORY[channel]
        or md.get("defaultLanguage") != row["language"]):
        raise RecoveryBlocked("QA_OR_EXACT_EPISODE_PROVENANCE_MISMATCH")
    mp4_hash = digest(video)
    cover_hash = digest(cover)
    if (any(x != mp4_hash for x in (qa["mp4_sha256"],md["mp4_sha256"],report["video"]["mp4_sha256"]))
        or any(x != cover_hash for x in (qa["cover_sha256"],md["cover_sha256"],report["video"]["cover_sha256"]))):
        raise RecoveryBlocked("MEDIA_HASH_INTEGRITY_FAIL")
    info = probe(video)
    duration = float(info["format"]["duration"])
    video_streams = [x for x in info["streams"] if x.get("codec_type")=="video"]
    audio_streams = [x for x in info["streams"] if x.get("codec_type")=="audio"]
    if (not 90 <= duration <= 121 or len(video_streams)!=1 or not audio_streams
        or video_streams[0].get("width") != 1080 or video_streams[0].get("height") != 1920
        or video.stat().st_size < 300000 or cover.stat().st_size < 25000):
        raise RecoveryBlocked("MP4_QUALITY_RESOLUTION_AUDIO_OR_DURATION_FAIL")
    return {"episode_id":episode,"metadata":md,"video":video,"cover":cover,"sha256":mp4_hash,"seconds":duration}

def write_receipt(path: Path, record: dict):
    path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def upload(channel: str, episode: str):
    check(channel,episode)
    environment_guard(channel,episode,"upload")
    item = media(channel,episode)
    receipt = folder_for(channel,episode)/"youtube-private-receipt.json"
    if receipt.exists():
        raise RecoveryBlocked("EXISTING_UPLOAD_RECEIPT_MANUAL_RECONCILIATION_REQUIRED")
    api,playlist = uploader.youtube(channel)
    matches = uploader.scan_existing(api,playlist,item,channel)
    if len(matches)>1:
        raise RecoveryBlocked("DUPLICATE_EXISTING_VIDEOS_STOP")
    recovered = bool(matches)
    record = {
        "episode_id":episode,"channel":channel,"channel_id":KNOWN_IDS[channel],
        "video_sha256":item["sha256"],"visibility":"private",
        "made_for_kids":False,"youtube_id":None,"confirmed_private":False,
        "upload_state":"existing_found" if recovered else "insert_started_result_uncertain",
        "source_run_id":SOURCE_RUN
    }
    write_receipt(receipt,record)
    if recovered:
        video_id=matches[0]
        print("BATCH15_RECOVERY_MATCHED_EXISTING_PRIVATE_"+channel+"_"+episode,flush=True)
    else:
        try:
            video_id=uploader.insert_private(api,item)
        except Exception:
            # Inconclusive network response is NOT permission to retry insert.
            recovered_id=None
            for delay in (12,24,35):
                time.sleep(delay)
                previous=uploader.scan_existing(api,playlist,item,channel)
                if previous:
                    recovered_id=previous[0]
                    break
            if not recovered_id:
                raise RecoveryBlocked("AMBIGUOUS_INSERT_DO_NOT_REUPLOAD_"+episode) from None
            video_id=recovered_id
            recovered=True
    record["youtube_id"]=video_id
    record["upload_state"]="youtube_id_received"
    record["reconciled_existing"]=recovered
    write_receipt(receipt,record)
    for delay in (0,12,24,35):
        if delay:time.sleep(delay)
        if uploader.verify_video(api,video_id,channel,item):
            record["confirmed_private"]=True
            record["upload_state"]="private_verified"
            write_receipt(receipt,record)
            break
    if not record["confirmed_private"]:
        raise RecoveryBlocked("YOUTUBE_OWNER_PRIVATE_ID_NOT_VERIFIED_"+episode)
    try:
        from googleapiclient.http import MediaFileUpload
        if not recovered: time.sleep(75)
        response=api.thumbnails().set(videoId=video_id,
            media_body=MediaFileUpload(str(item["cover"]),mimetype="image/jpeg")).execute()
        record["thumbnail_acknowledged"]=bool(response.get("items"))
    except Exception:
        record["thumbnail_review_required"]=True
    write_receipt(receipt,record)
    print("BATCH15_RECOVERY_PRIVATE_VERIFIED_"+channel+"_"+episode+"_"+video_id,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=tuple(EPISODES),required=True)
    p.add_argument("--episode",required=True)
    p.add_argument("--action",choices=("validate","render","upload"),default="validate")
    args=p.parse_args()
    try:
        if args.action=="validate":
            check(args.channel,args.episode)
            print("BATCH15_RECOVERY_PREFLIGHT_OK_"+args.channel+"_"+args.episode)
        elif args.action=="render":render(args.channel,args.episode)
        else:upload(args.channel,args.episode)
        return 0
    except Exception as ex:
        # Safe class + generic status, no provider token/API response dumps.
        message=str(ex) if isinstance(ex,RecoveryBlocked) else type(ex).__name__
        print("BATCH15_RECOVERY_BLOCKED_"+message,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
