#!/usr/bin/env python3
"""Nov 9 independent 15-video AutoEditorVideo batch. Private upload after technical QA.

No rerender or overwrite of any older batch; all five channels use distinct exact
OAuth credentials. Anime editorial narratives avoid naming character designs that
would require reference-anchor edits unavailable in this still-art engine.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import five_channel_fifteen_20261108 as batch
import five_channel_fifteen_upload_20261108 as uploader
from youtube_channel_registry import KNOWN_IDS

WORKFLOW = "AutoEditorVideo - 15 fresh Shorts five channels Nov 09 private"
OWNER = "lote15_novos_20261109"
MANIFEST = ROOT / "conteudos" / "lote-15-canais-20261109.json"
LAUNCH = ROOT / "conteudos" / "lote-15-canais-20261109-launch.json"
OUTPUT_ROOT = ROOT / "cloud-lote-15-canais-20261109"
EXPECTED = {
    "br": ("5022-vinland-saga-vinganca", "5023-frieren-memorias", "5024-pluto-humanidade"),
    "en": ("7021-dandadan-misterios", "7022-made-in-abyss-descida", "7023-spy-family-segredos"),
    "games": ("game-110-factorio-gargalos", "game-111-dead-cells-escolhas", "game-112-slime-rancher-equilibrio"),
    "kids": ("kids-110-coruja-sons", "kids-111-caracol-arcoiris", "kids-112-nuvem-vento"),
    "alchemy": ("alchemy-111-prompt-exemplos", "alchemy-112-rag-documentos", "alchemy-113-legenda-sincronizada"),
}

class LaunchBlocked(ValueError):
    pass

def initialize() -> None:
    batch.MANIFEST = MANIFEST
    batch.OUTPUT_ROOT = OUTPUT_ROOT
    batch.OWNER = OWNER
    batch.WORKFLOW = WORKFLOW
    batch.EXPECTED = EXPECTED
    batch.engine.OUTPUT_ROOT = OUTPUT_ROOT
    uploader.OWNER = OWNER
    uploader.EXPECTED = EXPECTED
    uploader.WORKFLOW = WORKFLOW
    uploader.output = batch.output
    uploader.validate = batch.validate
    batch.guard = render_guard

def verify_manifest() -> dict:
    launch = json.loads(LAUNCH.read_text(encoding="utf-8"))
    if launch != {
        "schema": "autoeditorvideo/new-15-private-launch-20261109/v1",
        "date": "2026-11-09",
        "creator_requested": "generate three new videos for each of five YouTube channels via GitHub",
        "owner": OWNER,
        "private_first": True,
        "allow_public_publishing": False,
        "require_exact_channel_oauth": True,
        "require_no_duplicate_insert": True,
        "allow_reuse_of_old_videos": False,
    }:
        raise LaunchBlocked("LAUNCH_CONTENT_NOT_APPROVED")
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d.get("schema") != "autoeditorvideo/new-15-five-channels-editorial-v1"
            or d.get("production_owner") != OWNER
            or d.get("date") != "2026-11-09"
            or d.get("default_visibility") != "private"
            or d.get("status") != "new_original_narrations_pending_render"):
        raise LaunchBlocked("MANIFEST_OR_PRIVATE_POLICY_MISMATCH")
    rows = d.get("episodes", [])
    pairs = [(x.get("channel"), x.get("id")) for x in rows]
    if len(pairs) != 15 or len(set(pairs)) != 15:
        raise LaunchBlocked("FIFTEEN_DISTINCT_CHANNEL_EPISODES_REQUIRED")
    for channel, expected in EXPECTED.items():
        selected = [x for x in rows if x.get("channel") == channel]
        if tuple(x.get("id") for x in selected) != expected:
            raise LaunchBlocked("EPISODE_IDS_CHANGED")
        if any(x.get("channel_id") != KNOWN_IDS[channel] for x in selected):
            raise LaunchBlocked("YOUTUBE_CHANNEL_ID_CHANGED")
    for path in (
        ROOT / "conteudos" / "lote-15-canais-20261108.json",
        ROOT / "conteudos" / "lote-15-janela21-20261108.json",
    ):
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
            previous_pairs = {(x.get("channel"), x.get("id")) for x in previous.get("episodes", [])}
            if set(pairs).intersection(previous_pairs):
                raise LaunchBlocked("PREVIOUS_BATCH_EPISODE_REUSED")
    return d

def render_guard(channel: str) -> None:
    env = os.environ
    if not (
        channel in EXPECTED
        and env.get("GITHUB_REPOSITORY") == "HelioConde/AutoEditorVideo"
        and env.get("GITHUB_EVENT_NAME") == "push"
        and env.get("GITHUB_REF") == "refs/heads/main"
        and env.get("GITHUB_RUN_ATTEMPT") == "1"
        and env.get("GITHUB_WORKFLOW") == WORKFLOW
        and env.get("BATCH15_CHANNEL") == channel
        and env.get("BATCH15_RENDER_AUTHORIZED") == "yes"
        and env.get("IMAGE_MODEL") == "gpt-image-2"
    ):
        raise LaunchBlocked("MAIN_FIRST_PUSH_RENDER_AUTHORIZATION_REQUIRED")
    if any(env.get(x) for x in (
        "YOUTUBE_CLIENT_JSON", "YOUTUBE_CHANNEL_TOKEN_JSON",
        "YOUTUBE_BR_TOKEN_JSON", "YOUTUBE_EN_TOKEN_JSON",
        "YOUTUBE_GAMES_TOKEN_JSON", "YOUTUBE_KIDS_TOKEN_JSON",
        "YOUTUBE_ALCHEMY_TOKEN_JSON",
    )):
        raise LaunchBlocked("YOUTUBE_OAUTH_SECRETS_IN_RENDER_FORBIDDEN")
    # No editorial MAX_IMAGE_CALLS check; provider quotas, authentication and QA remain enforced.

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", required=True, choices=tuple(EXPECTED))
    parser.add_argument("--action", required=True, choices=("validate", "render", "upload"))
    args = parser.parse_args()
    try:
        initialize()
        verify_manifest()
        if args.action == "validate":
            batch.validate(args.channel)
            print("NOV09_THREE_VALIDATED_" + args.channel, flush=True)
        elif args.action == "render":
            batch.produce(args.channel)
            print("NOV09_THREE_RENDERED_" + args.channel, flush=True)
        else:
            uploader.upload(args.channel)
            print("NOV09_THREE_PRIVATE_UPLOADS_VERIFIED_" + args.channel, flush=True)
        return 0
    except Exception as error:
        if isinstance(error, LaunchBlocked):
            reason = str(error)
        else:
            reason = type(error).__name__
        print("NOV09_BATCH_BLOCKED_" + reason, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
