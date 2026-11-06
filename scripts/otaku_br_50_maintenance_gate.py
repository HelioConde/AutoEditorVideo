#!/usr/bin/env python3
"""Fail-closed creator-maintenance gate for Otaku Multicena BR.

Read authorization from CURRENT GitHub main, not the potentially stale
checkout of a running workflow. Does not access image or YouTube secrets.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib import request

REPO = "HelioConde/AutoEditorVideo"
CONTROL = "conteudos/otaku-br-50-serial-launch-20261106.json"
CHANNEL = "UCXGYTuBYn-0Ziqin5ajKhOw"
SCHEMA = "autoeditorvideo/otaku-br-50-serial-launch/v1"

class MaintenanceBlocked(ValueError):
    pass

def check_authorization(data: dict) -> bool:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("channel_id") != CHANNEL:
        raise MaintenanceBlocked("INVALID_MAINTENANCE_CONTROL")
    if data.get("pause_requested") is not False:
        raise MaintenanceBlocked("CREATOR_PAUSED_AUTOMATION")
    if data.get("authorized_public") is not True:
        raise MaintenanceBlocked("PUBLICATION_NOT_AUTHORIZED")
    if data.get("maintenance_complete") is not True:
        raise MaintenanceBlocked("EDITOR_MAINTENANCE_NOT_COMPLETED")
    if data.get("resume_authorized_after_maintenance") is not True:
        raise MaintenanceBlocked("CREATOR_HAS_NOT_AUTHORIZED_RESUMPTION")
    return True

def current_control(token: str | None = None) -> dict:
    credential = token if token is not None else os.environ.get("GH_TOKEN", "")
    if not credential:
        raise MaintenanceBlocked("GITHUB_READ_TOKEN_REQUIRED")
    url = f"https://api.github.com/repos/{REPO}/contents/{CONTROL}?ref=main"
    req = request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + credential,
        "X-GitHub-Api-Version": "2022-11-28",
        "Cache-Control": "no-cache",
    })
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or payload.get("encoding") != "base64":
            raise MaintenanceBlocked("CONTROL_FILE_FORMAT_INVALID")
        raw = base64.b64decode(payload["content"], validate=False)
        return json.loads(raw.decode("utf-8"))
    except MaintenanceBlocked:
        raise
    except Exception:
        raise MaintenanceBlocked("CURRENT_MAINTENANCE_STATE_UNAVAILABLE") from None

def ensure_unpaused_live() -> bool:
    return check_authorization(current_control())

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, help="Offline validation only; not an authorization for CI or uploads")
    args = parser.parse_args()
    control = json.loads(args.file.read_text(encoding="utf-8")) if args.file else current_control()
    try:
        check_authorization(control)
    except MaintenanceBlocked as exc:
        print("[OTAKU BR PAUSED] " + str(exc))
        return 1
    print("[OTAKU BR] CREATOR_AUTHORIZATION_VERIFIED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
