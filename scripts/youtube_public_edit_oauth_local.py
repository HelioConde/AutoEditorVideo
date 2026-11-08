#!/usr/bin/env python3
"""One-time LOCAL Google consent for video privacy updates; never run in Actions.

Produces an ignored private local token with youtube.force-ssl, youtube.upload
and youtube.readonly after matching the exact intended YouTube channel ID.
Does not send tokens to ChatGPT, GitHub or stdout. User separately uploads
it to their protected GitHub Environment after reviewing the permissions.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

from youtube_channel_registry import KNOWN_IDS, get_channel
from youtube_new_channels_oauth import (
    CLIENT_FILE, validate_token_fields, verify_channel_identity
)

ROOT=Path(__file__).resolve().parents[1]
SCOPES=(
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl"
)

class LocalAuthorizationBlocked(ValueError):
    pass

def token_path(channel:str)->Path:
    if channel not in KNOWN_IDS:
        raise LocalAuthorizationBlocked("CHANNEL_NOT_IN_VERIFIED_REGISTRY")
    return ROOT/".secrets"/f"youtube-{channel}-public-edit-token.json"

def connect(channel:str)->None:
    if os.environ.get("GITHUB_ACTIONS","").lower()=="true":
        raise LocalAuthorizationBlocked("INTERACTIVE_OAUTH_FORBIDDEN_IN_GITHUB_ACTIONS")
    if not CLIENT_FILE.is_file() or CLIENT_FILE.resolve().parent!=(ROOT/".secrets").resolve():
        raise LocalAuthorizationBlocked("LOCAL_IGNORED_YOUTUBE_OAUTH_CLIENT_MISSING")
    registry=get_channel(channel)
    if (registry["youtube_channel_id"]!=KNOWN_IDS[channel]
        or registry["youtube_environment"]!="youtube-private-upload"):
        raise LocalAuthorizationBlocked("UNVERIFIED_CHANNEL_OR_ENVIRONMENT")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    try:
        flow=InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE),list(SCOPES))
        creds=flow.run_local_server(port=0,prompt="consent",access_type="offline")
        new_token=json.loads(creds.to_json())
        client=json.loads(CLIENT_FILE.read_text(encoding="utf-8"))
        validate_token_fields(client,new_token)
        saved=set(new_token.get("scopes",[]))
        if not set(SCOPES).issubset(saved):
            raise LocalAuthorizationBlocked("GOOGLE_MISSING_PRIVACY_EDIT_PERMISSION")
        yt=build("youtube","v3",credentials=creds,cache_discovery=False)
        verified=verify_channel_identity(yt,channel)
    except LocalAuthorizationBlocked:
        raise
    except Exception:
        raise LocalAuthorizationBlocked("GOOGLE_OAUTH_OR_CHANNEL_VERIFICATION_FAILED") from None
    dest=token_path(channel)
    dest.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".youtube-oauth-private-",suffix=".tmp",dir=dest.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as fp:
            json.dump(new_token,fp,ensure_ascii=False)
            fp.write("\n")
        os.chmod(temp,0o600)
        temp.replace(dest)
    finally:
        temp.unlink(missing_ok=True)
    print("YOUTUBE_PUBLIC_EDIT_SCOPE_AUTHORIZED_"+channel+"_"+verified)
    print("LOCAL_PRIVATE_TOKEN_SAVED_NOT_SENT_TO_GITHUB")

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",choices=list(KNOWN_IDS),required=True)
    args=ap.parse_args()
    try:
        connect(args.channel)
        return 0
    except LocalAuthorizationBlocked as exc:
        print("YOUTUBE_PUBLIC_EDIT_LOCAL_BLOCKED_"+str(exc),file=sys.stderr)
        return 2
    except Exception:
        print("YOUTUBE_PUBLIC_EDIT_LOCAL_BLOCKED_UNCLASSIFIED_NO_SECRETS",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
