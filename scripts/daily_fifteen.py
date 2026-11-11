#!/usr/bin/env python3
"""Run a separately reserved, freshly authored 15-video daily batch.

Only a creator-authorized GitHub main push of exactly one dated manifest may
spend image requests or insert YouTube videos. Never recycle an older batch.
The existing verified AutoEditorVideo renderer/uploader remain responsible for
technical QA, exact OAuth channel ID and private, idempotent uploads.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import five_channel_fifteen_20261108 as batch
import five_channel_fifteen_upload_20261108 as uploader
from youtube_channel_registry import KNOWN_IDS
from production_reservations import assert_reserved

WORKFLOW = "AutoEditorVideo - lote diario 15 Shorts privados"
CHANNELS = ("br", "en", "games", "kids", "alchemy")
MANIFEST_DIR = ROOT / "conteudos" / "lotes-diarios"


class DailyBlocked(ValueError):
    pass


def selected_day(day: str) -> str:
    if not re.fullmatch(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]", day):
        raise DailyBlocked("INVALID_ISO_DATE")
    try:
        datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        raise DailyBlocked("INVALID_CALENDAR_DATE") from None
    return day


def manifest_path(day: str) -> Path:
    return MANIFEST_DIR / (selected_day(day) + ".json")


def verify_daily(day: str) -> dict:
    path = manifest_path(day)
    if not path.is_file():
        raise DailyBlocked("NEW_APPROVED_DAILY_MANIFEST_REQUIRED")
    d = json.loads(path.read_text(encoding="utf-8"))
    owner = "lote15_diario_" + day.replace("-", "")
    if (d.get("schema") != "autoeditorvideo/new-15-five-channels-editorial-v1"
            or d.get("date") != day or d.get("production_owner") != owner
            or d.get("requested_total") != 15 or d.get("per_channel") != 3
            or d.get("channels") != list(CHANNELS)
            or d.get("default_visibility") != "private"
            or d.get("status") != "new_original_narrations_pending_render"):
        raise DailyBlocked("DAILY_MANIFEST_CONTRACT_INVALID")
    approval = d.get("approval", {})
    if (approval.get("creator_requested_generation") is not True
            or approval.get("upload_only_after_render_qa_and_exact_youtube_id_check") is not True
            or approval.get("publication_to_public_not_approved_by_this_manifest") is not True):
        raise DailyBlocked("NEW_PRIVATE_BATCH_NOT_APPROVED")
    episodes = d.get("episodes", [])
    if len(episodes) != 15:
        raise DailyBlocked("EXACTLY_FIFTEEN_REQUIRED")
    keys, titles = set(), set()
    for channel in CHANNELS:
        rows = [x for x in episodes if x.get("channel") == channel]
        if len(rows) != 3:
            raise DailyBlocked("THREE_PER_CHANNEL_REQUIRED")
        for row in rows:
            key = (channel, row.get("id"))
            title = str(row.get("title", "")).strip().casefold()
            if key in keys or not title or title in titles:
                raise DailyBlocked("DUPLICATE_TITLE_OR_EPISODE")
            keys.add(key)
            titles.add(title)
            if row.get("channel_id") != KNOWN_IDS[channel]:
                raise DailyBlocked("TARGET_CHANNEL_ID_MISMATCH")
            if channel == "br" and ("death note" in title or "death-note" in str(row.get("id", ""))):
                raise DailyBlocked("BR_DEATH_NOTE_PAUSED")
            if row.get("production_state", {}).get("youtube_id") is not None:
                raise DailyBlocked("OLD_YOUTUBE_ID_IN_NEW_BATCH")
            assert_reserved(channel, row["id"], owner)
    # Distinct IDs and titles against *all* previous dated manifests and legacy
    # one-shot batches. Prevent reusing an old narrative as a new daily video.
    old_files = [
        ROOT / "conteudos" / "lote-15-canais-20261108.json",
        ROOT / "conteudos" / "lote-15-canais-20261109.json",
        ROOT / "conteudos" / "lote-15-janela21-20261108.json",
    ]
    old_files += [p for p in MANIFEST_DIR.glob("*.json") if p != path]
    for old in old_files:
        if not old.is_file():
            continue
        previous = json.loads(old.read_text(encoding="utf-8"))
        for item in previous.get("episodes", []):
            if (item.get("channel"), item.get("id")) in keys:
                raise DailyBlocked("PREVIOUS_BATCH_ID_REUSED")
            if str(item.get("title", "")).strip().casefold() in titles:
                raise DailyBlocked("PREVIOUS_BATCH_TITLE_REUSED")
    return d


def initialize(day: str) -> dict:
    d = verify_daily(day)
    owner = d["production_owner"]
    expected = {
        c: tuple(x["id"] for x in d["episodes"] if x["channel"] == c)
        for c in CHANNELS
    }
    output_root = ROOT / ("cloud-lote-15-diario-" + day)
    batch.MANIFEST = manifest_path(day)
    batch.OWNER = owner
    batch.WORKFLOW = WORKFLOW
    batch.EXPECTED = expected
    batch.OUTPUT_ROOT = output_root
    batch.engine.OUTPUT_ROOT = output_root
    uploader.OWNER = owner
    uploader.WORKFLOW = WORKFLOW
    uploader.EXPECTED = expected
    uploader.output = batch.output
    uploader.validate = batch.validate
    batch.guard = render_guard
    return d


def render_guard(channel: str) -> None:
    e = os.environ
    if not (channel in CHANNELS
            and e.get("GITHUB_REPOSITORY") == "HelioConde/AutoEditorVideo"
            and e.get("GITHUB_EVENT_NAME") == "push"
            and e.get("GITHUB_REF") == "refs/heads/main"
            and e.get("GITHUB_RUN_ATTEMPT") == "1"
            and e.get("GITHUB_WORKFLOW") == WORKFLOW
            and e.get("BATCH15_CHANNEL") == channel
            and e.get("BATCH15_RENDER_AUTHORIZED") == "yes"
            and e.get("IMAGE_MODEL") == "gpt-image-2"):
        raise DailyBlocked("UNAUTHORIZED_DAILY_RENDER")
    if any(e.get(k) for k in (
            "YOUTUBE_CLIENT_JSON", "YOUTUBE_CHANNEL_TOKEN_JSON",
            "YOUTUBE_BR_TOKEN_JSON", "YOUTUBE_EN_TOKEN_JSON",
            "YOUTUBE_GAMES_TOKEN_JSON", "YOUTUBE_KIDS_TOKEN_JSON",
            "YOUTUBE_ALCHEMY_TOKEN_JSON")):
        raise DailyBlocked("YOUTUBE_OAUTH_EXPOSED_IN_RENDER")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--channel", required=True, choices=CHANNELS)
    parser.add_argument("--action", required=True, choices=("validate", "render", "upload"))
    args = parser.parse_args()
    try:
        initialize(args.date)
        if args.action == "validate":
            rows = batch.validate(args.channel)
            print("DAILY_PREFLIGHT_" + args.channel + "_" + ",".join(x["id"] for x in rows))
        elif args.action == "render":
            batch.produce(args.channel)
            print("DAILY_THREE_RENDERED_" + args.channel, flush=True)
        else:
            uploader.upload(args.channel)
            print("DAILY_THREE_PRIVATE_UPLOADS_VERIFIED_" + args.channel, flush=True)
        return 0
    except Exception as exc:
        label = str(exc) if isinstance(exc, (DailyBlocked, batch.BatchBlocked, uploader.RemainingUploadBlocked)) else type(exc).__name__
        print("DAILY_BATCH_BLOCKED_" + label, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
