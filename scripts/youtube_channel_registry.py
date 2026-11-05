#!/usr/bin/env python3
"""Authoritative, fail-closed YouTube channel identity registry.

REGISTERED != AUTHORIZED. No network, OAuth, generation, or upload.
New Gamer/Kids/Alchemy channels cannot be published using the Otaku tokens.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "config" / "youtube-channel-registry.json"
KNOWN_IDS = {
    "br": "UCXGYTuBYn-0Ziqin5ajKhOw",
    "en": "UCBoNbQjaMYdpJqPLRZAFkvQ",
    "games": "UCg77gYc1_wkHuL07XPtKcow",
    "kids": "UCxEzVW2Uy44OUVurTQSg_Eg",
    "alchemy": "UCCTYFE5Cmz2aYZ37cJQ-wcg",
}
NEW_CHANNELS = ("games", "kids", "alchemy")
BLOCKED_STATE = {
    "blocked_until_separate_oauth_and_verified_uploader",
    "blocked_until_separate_oauth_and_kids_compliance_review",
}

class ChannelRegistryError(ValueError):
    pass

def load_registry(path: Path = REGISTRY) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "autoeditorvideo/youtube-channel-registry/v1":
        raise ChannelRegistryError("YOUTUBE_CHANNEL_REGISTRY_SCHEMA_UNRECOGNIZED")
    items = raw.get("channels")
    if not isinstance(items, dict) or set(items) != set(KNOWN_IDS):
        raise ChannelRegistryError("YOUTUBE_CHANNEL_REGISTRY_MISSING_OR_EXTRA_CHANNEL")
    ids, secrets, envs = set(), set(), set()
    for slug, expected in KNOWN_IDS.items():
        record = items[slug]
        if not isinstance(record, dict):
            raise ChannelRegistryError("CHANNEL_CONFIG_NOT_AN_OBJECT")
        actual = record.get("youtube_channel_id")
        if (not isinstance(actual, str)
                or not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", actual)
                or actual != expected):
            raise ChannelRegistryError("CHANNEL_ID_MISMATCH_" + slug.upper())
        if actual in ids:
            raise ChannelRegistryError("CHANNEL_ID_DUPLICATE")
        ids.add(actual)
        language = record.get("language")
        if language != ("en-US" if slug == "en" else "pt-BR"):
            raise ChannelRegistryError("CHANNEL_LANGUAGE_MISMATCH_" + slug.upper())
        if record.get("visibility_default") != "private":
            raise ChannelRegistryError("CHANNEL_MUST_DEFAULT_TO_PRIVATE_" + slug.upper())
        if record.get("made_for_kids_default") is not (slug == "kids"):
            raise ChannelRegistryError("KIDS_AUDIENCE_FLAG_MISMATCH_" + slug.upper())
        secret = record.get("oauth_token_secret_name")
        if not isinstance(secret, str) or not re.fullmatch(r"YOUTUBE_[A-Z]+_TOKEN_JSON", secret):
            raise ChannelRegistryError("CHANNEL_OAUTH_SECRET_NAME_INVALID")
        if secret in secrets:
            raise ChannelRegistryError("CHANNEL_OAUTH_SECRET_NAME_SHARED")
        secrets.add(secret)
        environment = record.get("youtube_environment")
        if not isinstance(environment, str) or not environment:
            raise ChannelRegistryError("CHANNEL_ENVIRONMENT_MISSING")
        if slug in NEW_CHANNELS:
            if record.get("cloud_upload_state") not in BLOCKED_STATE:
                raise ChannelRegistryError("NEW_CHANNEL_MUST_NOT_AUTO_PUBLISH_" + slug.upper())
            if environment in envs or environment == "youtube-private-upload":
                raise ChannelRegistryError("NEW_CHANNEL_MUST_HAVE_SEPARATE_OAUTH_ENVIRONMENT")
            if record.get("brand_status") == "active" and (
                record.get("name") != record.get("observed_youtube_title")
            ):
                raise ChannelRegistryError("BRAND_RENAME_NOT_VERIFIED")
        else:
            if record.get("cloud_upload_state") != "existing_explicit_workflow":
                raise ChannelRegistryError("OTAKU_CLOUD_CONFIG_CHANGED_UNEXPECTEDLY")
        envs.add(environment)
    if items["kids"].get("series") != "Fofinhos" or items["kids"].get("audience") != "children":
        raise ChannelRegistryError("FOFINHOS_CHILD_SAFETY_MISSING")
    if raw.get("policy", {}).get("no_automatic_publication_from_registration") is not True:
        raise ChannelRegistryError("REGISTRATION_CANNOT_TRIGGER_UPLOADS")
    return raw

def get_channel(slug: str, *, registry: dict | None = None) -> dict:
    data = registry if registry is not None else load_registry()
    if slug not in KNOWN_IDS:
        raise ChannelRegistryError("UNKNOWN_CHANNEL")
    return data["channels"][slug]

def assert_upload_authorized(slug: str, *, registry: dict | None = None) -> dict:
    """Fail closed for all new channels until a separate verified uploader exists."""
    row = get_channel(slug, registry=registry)
    if slug in NEW_CHANNELS or row.get("cloud_upload_state") != "existing_explicit_workflow":
        raise ChannelRegistryError("CHANNEL_REGISTERED_BUT_YOUTUBE_UPLOAD_NOT_AUTHORIZED")
    return row

def assert_correct_destination(slug: str, supplied_youtube_id: str,
                               *, registry: dict | None = None) -> dict:
    row = get_channel(slug, registry=registry)
    if supplied_youtube_id != row["youtube_channel_id"]:
        raise ChannelRegistryError("WRONG_DESTINATION_CHANNEL_ID")
    return row

def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect registered YouTube channels without OAuth.")
    parser.add_argument("--action", choices=["list", "verify", "check-upload"], default="list")
    parser.add_argument("--channel", choices=tuple(KNOWN_IDS), default="games")
    args = parser.parse_args()
    data = load_registry()
    if args.action == "list":
        for slug, row in data["channels"].items():
            print(f"{slug}: {row['name']} | {row['youtube_channel_id']} "
                  f"| {row['cloud_upload_state']} | {row['visibility_default']}")
    elif args.action == "verify":
        row = get_channel(args.channel, registry=data)
        print(f"[REGISTERED] {args.channel}: {row['youtube_channel_id']} (upload not implied)")
    else:
        assert_upload_authorized(args.channel, registry=data)
        print(f"[EXISTING EXPLICIT ROUTE] {args.channel}: OAuth and video approval still required")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
