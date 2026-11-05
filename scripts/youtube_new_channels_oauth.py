#!/usr/bin/env python3
"""Isolated, read-only YouTube OAuth onboarding for Games, Kids, Alchemy.

'connect': runs only on user's own computer, stores an ignored token under
.secrets ONLY after channels.list(mine=true) matches the registered channel.
'verify': runs only in protected GitHub Environment on main with already
installed secrets; authenticates and reads the channel; NEVER uploads.
No Google OAuth token, response body, or client secret is logged.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from youtube_channel_registry import NEW_CHANNELS, get_channel

ROOT = Path(__file__).resolve().parents[1]
SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)
CLIENT_FILE = ROOT / ".secrets" / "youtube-oauth-client.json"


class NewChannelOAuthBlocked(ValueError):
    pass


def local_token_path(channel: str) -> Path:
    if channel not in NEW_CHANNELS:
        raise NewChannelOAuthBlocked("CHANNEL_NOT_NEW_OR_UNAPPROVED")
    return ROOT / ".secrets" / f"youtube-{channel}-cloud-token.json"


def validate_token_fields(client_data: dict, token_data: dict) -> None:
    if not isinstance(client_data, dict) or not isinstance(token_data, dict):
        raise NewChannelOAuthBlocked("OAUTH_JSON_NOT_AN_OBJECT")
    client = client_data.get("installed") or client_data.get("web")
    if not isinstance(client, dict) or not client.get("client_id") or not client.get("client_secret"):
        raise NewChannelOAuthBlocked("GOOGLE_OAUTH_CLIENT_FIELDS_MISSING")
    if token_data.get("client_id") != client["client_id"]:
        raise NewChannelOAuthBlocked("TOKEN_BELONGS_TO_ANOTHER_OAUTH_CLIENT")
    if not isinstance(token_data.get("refresh_token"), str) or not token_data["refresh_token"]:
        raise NewChannelOAuthBlocked("OFFLINE_REFRESH_TOKEN_MISSING")
    scopes = token_data.get("scopes")
    if not isinstance(scopes, (str, list, tuple)):
        raise NewChannelOAuthBlocked("OAUTH_SCOPES_NOT_RECORDED")
    recorded = set(scopes.split()) if isinstance(scopes, str) else set(scopes)
    if not set(SCOPES).issubset(recorded):
        raise NewChannelOAuthBlocked("YOUTUBE_UPLOAD_AND_READONLY_SCOPES_REQUIRED")


def verify_channel_identity(youtube, channel: str) -> str:
    """Only Google channels.list, and no videos.insert or thumbnails.set."""
    expected = get_channel(channel)["youtube_channel_id"]
    try:
        data = youtube.channels().list(part="id", mine=True).execute()
        items = data.get("items") or []
    except Exception:
        raise NewChannelOAuthBlocked("GOOGLE_CHANNEL_ID_LOOKUP_FAILED") from None
    if len(items) != 1 or items[0].get("id") != expected:
        raise NewChannelOAuthBlocked("AUTHENTICATED_YOUTUBE_CHANNEL_ID_MISMATCH")
    return expected


def authorize_locally(channel: str, *, replace_token: bool = False,
                      client_file: Path = CLIENT_FILE) -> Path:
    if channel not in NEW_CHANNELS:
        raise NewChannelOAuthBlocked("CHANNEL_NOT_NEW_OR_UNAPPROVED")
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise NewChannelOAuthBlocked("INTERACTIVE_LOGIN_FORBIDDEN_IN_GITHUB")
    if client_file != CLIENT_FILE or not client_file.is_file():
        raise NewChannelOAuthBlocked("LOCAL_OAUTH_CLIENT_FILE_REQUIRED")
    dest = local_token_path(channel)
    if dest.exists() and not replace_token:
        raise NewChannelOAuthBlocked("LOCAL_TOKEN_ALREADY_EXISTS_USE_REPLACE_TOKEN")
    # Imports lazy: offline registry checks do not need Google dependencies.
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), list(SCOPES))
        credentials = flow.run_local_server(port=0, prompt="consent", access_type="offline")
        token = json.loads(credentials.to_json())
        client = json.loads(client_file.read_text(encoding="utf-8"))
        validate_token_fields(client, token)
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        verified = verify_channel_identity(youtube, channel)
    except NewChannelOAuthBlocked:
        raise
    except Exception:
        raise NewChannelOAuthBlocked("OAUTH_INTERACTIVE_AUTHORIZATION_FAILED") from None

    dest.parent.mkdir(parents=True, exist_ok=True)
    # Write only after exact channel verification and granted scopes; refuse
    # to leak refresh tokens through Git, stdout, artifact or temp file.
    temporary = None
    try:
        fd, name = tempfile.mkstemp(dir=str(dest.parent), prefix=".oauth-private-", suffix=".tmp")
        temporary = Path(name)
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(token, fp, ensure_ascii=False)
            fp.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, dest)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    print(f"[OAUTH {channel.upper()}] CHANNEL_ID_CONFIRMED_{verified}")
    print("[OAUTH] LOCAL_PRIVATE_TOKEN_SAVED_NOT_UPLOADED_TO_GITHUB")
    return dest


def verify_on_github(channel: str, env: dict[str, str] | None = None) -> str:
    env = dict(os.environ if env is None else env)
    if channel not in NEW_CHANNELS:
        raise NewChannelOAuthBlocked("CHANNEL_NOT_NEW_OR_UNAPPROVED")
    if env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise NewChannelOAuthBlocked("WRONG_REPOSITORY")
    if env.get("GITHUB_REF") != "refs/heads/main":
        raise NewChannelOAuthBlocked("MAIN_ONLY")
    if env.get("GITHUB_EVENT_NAME") != "workflow_dispatch" or env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise NewChannelOAuthBlocked("ONE_SHOT_MANUAL_DIAGNOSTIC_ONLY")
    if env.get("EXPECTED_CHANNEL_SLUG") != channel:
        raise NewChannelOAuthBlocked("CROSS_CHANNEL_WORKFLOW_INPUT")
    if env.get("GITHUB_ACTIONS", "").lower() != "true":
        raise NewChannelOAuthBlocked("GITHUB_RUNNER_REQUIRED")
    client_string = env.get("YOUTUBE_CLIENT_JSON")
    token_string = env.get("YOUTUBE_CHANNEL_TOKEN_JSON")
    if not client_string or not token_string:
        raise NewChannelOAuthBlocked("CHANNEL_SPECIFIC_OAUTH_SECRETS_MISSING")
    try:
        client = json.loads(client_string)
        token = json.loads(token_string)
    except (ValueError, TypeError):
        raise NewChannelOAuthBlocked("INVALID_OAUTH_SECRET_JSON") from None
    validate_token_fields(client, token)

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    try:
        credentials = Credentials.from_authorized_user_info(token, scopes=list(SCOPES))
        if not credentials.valid:
            credentials.refresh(Request())
        granted = getattr(credentials, "granted_scopes", None)
        if granted is not None and not set(SCOPES).issubset(set(granted)):
            raise NewChannelOAuthBlocked("OAUTH_GRANTED_SCOPES_INCOMPLETE")
        youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    except NewChannelOAuthBlocked:
        raise
    except Exception:
        raise NewChannelOAuthBlocked("GOOGLE_OAUTH_TOKEN_REFRESH_FAILED") from None
    verified = verify_channel_identity(youtube, channel)
    print(f"[GITHUB OAUTH] VERIFIED_{channel.upper()}_{verified}")
    print("[SAFETY] READ_ONLY_ZERO_VIDEOS_UPLOADED_ZERO_TOKENS_LOGGED")
    return verified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Onboard one YouTube channel safely.")
    parser.add_argument("--action", required=True, choices=("inspect", "connect", "verify"))
    parser.add_argument("--channel", required=True, choices=NEW_CHANNELS)
    parser.add_argument("--replace-token", action="store_true")
    args = parser.parse_args(argv)
    try:
        row = get_channel(args.channel)
        if args.action == "inspect":
            print(f"[CHANNEL] {args.channel}: {row['youtube_channel_id']}")
            print(f"[GITHUB] Expected protected environment: {row['youtube_environment']}")
            print(f"[GITHUB] Expected token Secret name: {row['oauth_token_secret_name']}")
            print("[SAFETY] INSPECT_ONLY_NO_LOGIN_NO_UPLOAD")
        elif args.action == "connect":
            authorize_locally(args.channel, replace_token=args.replace_token)
        else:
            verify_on_github(args.channel)
        return 0
    except NewChannelOAuthBlocked as exc:
        print("[YOUTUBE OAUTH BLOCKED] " + str(exc), file=sys.stderr)
        return 1
    except Exception:
        print("[YOUTUBE OAUTH BLOCKED] UNCLASSIFIED_ERROR_NO_PROVIDER_DETAILS", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
