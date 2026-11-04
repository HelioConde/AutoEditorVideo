"""Safe read-only OAuth smoke probe for GitHub Actions on trusted main only.

Never writes tokens, generates images, or uploads to YouTube. Logs only
fixed status labels. All credential-bearing exceptions are suppressed.
"""
from __future__ import annotations

import json
import os
import sys

READ_SCOPES = frozenset({
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtubepartner",
})
TOKENS = {
    "BR": "YOUTUBE_BR_TOKEN_JSON",
    "EN": "YOUTUBE_EN_TOKEN_JSON",
}
# The verified English channel ID is recorded in AGENTS.md.
EXPECTED_EN_CHANNEL = "UCBoNbQjaMYdpJqPLRZAFkvQ"


def parse_secret(label: str, raw: str) -> dict:
    if not raw.strip():
        raise ValueError(f"{label}:MISSING")
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label}:INVALID_JSON") from None
    if not isinstance(obj, dict):
        raise ValueError(f"{label}:INVALID_JSON")
    return obj


def verify_client_match(client: dict, token: dict) -> None:
    installed = client.get("installed", {})
    if not isinstance(installed, dict) or not installed.get("client_id"):
        raise ValueError("CLIENT:INVALID")
    if (installed.get("client_id") != token.get("client_id")
            or installed.get("client_secret") != token.get("client_secret")):
        raise ValueError("CLIENT:TOKEN_MISMATCH")
    if not token.get("refresh_token"):
        raise ValueError("TOKEN:NO_REFRESH")


def has_read_scope(token: dict) -> bool:
    scopes = token.get("scopes", [])
    if not isinstance(scopes, list):
        return False
    return bool(READ_SCOPES.intersection(scopes))


def check_channel_id(items: list[dict], expected: str) -> bool:
    return len(items) == 1 and items[0].get("id") == expected


def run() -> int:
    # These secret values only exist on the GitHub Actions trusted main job.
    # Do not handle secrets on pull_request events or upload workflow artifacts.
    try:
        client = parse_secret("CLIENT", os.environ.get("YOUTUBE_OAUTH_CLIENT_JSON", ""))
    except ValueError as exc:
        print(f"[AUTH] {exc}")
        return 1

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        import requests
    except ImportError:
        print("[AUTH] DEPENDENCIES_MISSING")
        return 1

    errors = 0
    for label, env_name in TOKENS.items():
        try:
            token = parse_secret(label, os.environ.get(env_name, ""))
            verify_client_match(client, token)
            creds = Credentials.from_authorized_user_info(token)
            # Explicitly exercises the refresh token, not just a cached access token.
            creds.refresh(Request())
            print(f"[YOUTUBE_{label}] OAUTH_REFRESH_OK")
        except ValueError as exc:
            print(f"[YOUTUBE_{label}] {exc}")
            errors += 1
            continue
        except Exception:
            print(f"[YOUTUBE_{label}] OAUTH_REFRESH_FAILED")
            errors += 1
            continue

        if not has_read_scope(token):
            print(f"[YOUTUBE_{label}] CHANNEL_NOT_VERIFIED_NO_READ_SCOPE")
            continue

        try:
            response = requests.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "id", "mine": "true"},
                headers={"Authorization": "Bearer " + creds.token},
                timeout=(5, 20),
            )
            if response.status_code != 200:
                print(f"[YOUTUBE_{label}] CHANNEL_READ_HTTP_{response.status_code}")
                errors += 1
                continue
            items = response.json().get("items", [])
            if not isinstance(items, list):
                raise ValueError("Invalid channel response")
            if label == "EN" and not check_channel_id(items, EXPECTED_EN_CHANNEL):
                print("[YOUTUBE_EN] WRONG_CHANNEL")
                errors += 1
            elif len(items) != 1:
                print(f"[YOUTUBE_{label}] CHANNEL_COUNT_UNEXPECTED")
                errors += 1
            else:
                print(f"[YOUTUBE_{label}] CHANNEL_READ_OK")
        except Exception:
            print(f"[YOUTUBE_{label}] CHANNEL_READ_FAILED")
            errors += 1

    # A local proxy server at 127.0.0.1:8080 on Windows is NOT present on Actions.
    # Never leak PROXY_API_KEY or pretend a live image generation test happened.
    if os.environ.get("PROXY_API_KEY", "").strip():
        print("[IMAGE_PROXY] KEY_PRESENT_SERVER_NOT_CONFIGURED_ON_RUNNER")
    else:
        print("[IMAGE_PROXY] KEY_MISSING")
        errors += 1
    print("[SAFETY] NO_UPLOAD_NO_IMAGE_GENERATION_NO_TOKEN_LOGGING")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(run())
