#!/usr/bin/env python3
"""Authorize a standalone BR-only OAuth token for deleting one obsolete YouTube video.

Runs only on the creator's computer (localhost OAuth in browser). Saves a NEW
separate secret .secrets/youtube-br-delete-token.json, preserving the existing
YouTube upload/readonly token and all other channel credentials. Does NOT
delete, upload, change visibility or execute external webhooks itself.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from autorizar_youtube_canais import validate_client,validate_channel,save_token

ROOT=Path(__file__).resolve().parents[1]
CLIENT=ROOT/".secrets"/"youtube-oauth-client.json"
TARGET=ROOT/".secrets"/"youtube-br-delete-token.json"
CHANNEL_ID="UCXGYTuBYn-0Ziqin5ajKhOw"
SCOPES=("https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/youtube.readonly")


def authorize(*,replace:bool=False):
    validate_client(CLIENT)
    if TARGET.is_file() and not replace:
        raise FileExistsError("BR_DELETE_TOKEN_ALREADY_EXISTS_USE_RENOVAR")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    flow=InstalledAppFlow.from_client_secrets_file(str(CLIENT),list(SCOPES))
    creds=flow.run_local_server(host="localhost",port=0,open_browser=True,
                                access_type="offline",prompt="consent")
    if not creds.refresh_token:
        raise RuntimeError("DELETE_OAUTH_NO_REFRESH_TOKEN")
    granted=set(creds.granted_scopes or creds.scopes or [])
    if not set(SCOPES).issubset(granted):
        raise RuntimeError("GOOGLE_DID_NOT_GRANT_FORCE_SSL_AND_READONLY")
    yt=build("youtube","v3",credentials=creds,cache_discovery=False)
    actual=yt.channels().list(part="id,snippet",mine=True).execute().get("items",[])
    title=validate_channel(actual,CHANNEL_ID)
    payload=json.loads(creds.to_json())
    payload["scopes"]=list(SCOPES)
    save_token(TARGET,json.dumps(payload,ensure_ascii=False)+"\n",replace=replace)
    print("[OK] OAuth de exclusao do canal BR autenticado: "+title+
          " ("+CHANNEL_ID+").")
    print("[OK] Token de exclusao isolado salvo localmente; videos existentes NAO alterados.")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--renovar",action="store_true")
    args=p.parse_args()
    try:
        authorize(replace=args.renovar)
        return 0
    except (ImportError,OSError,ValueError,RuntimeError,FileExistsError) as exc:
        print("[BLOQUEADO] OAuth BR de exclusao: "+str(exc).splitlines()[0][:120],file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
