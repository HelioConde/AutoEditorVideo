#!/usr/bin/env python3
"""Stage an explicitly supplied GitHub Environment Secret in ephemeral storage.

Do not import browser cookies, collect credentials, or persist a refreshed
OAuth state. This module never prints token values, account IDs, or emails.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

# Below GitHub's 48 KiB single-secret limit, leaving some headroom.
MAX_SECRET_BYTES = 45 * 1024


class InvalidPrivateState(Exception):
    pass


def validate_state(raw: str) -> int:
    if not raw.strip():
        raise InvalidPrivateState("MISSING_SECRET")
    raw_bytes = raw.encode("utf-8")
    if len(raw_bytes) > MAX_SECRET_BYTES:
        raise InvalidPrivateState("SECRET_TOO_LARGE")
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        raise InvalidPrivateState("INVALID_JSON") from None
    if not isinstance(obj, dict):
        raise InvalidPrivateState("INVALID_STATE")
    rows = obj.get("records")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 20:
        raise InvalidPrivateState("RECORDS_NOT_FOUND")
    for record in rows:
        if not isinstance(record, dict) or not isinstance(record.get("token"), dict):
            raise InvalidPrivateState("INVALID_RECORD")
        token = record["token"]
        if not all(isinstance(token.get(key), str) and token[key].strip()
                   for key in ("access_token", "refresh_token")):
            raise InvalidPrivateState("TOKEN_FIELDS_MISSING")
    return len(rows)


def stage_private_state(raw: str, data_dir: Path) -> int:
    count = validate_state(raw)
    if data_dir.exists() and data_dir.is_symlink():
        raise InvalidPrivateState("DATA_DIR_SYMLINK")
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    data_dir.chmod(0o700)
    dest = data_dir / "accounts.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(dest, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            writer.write(raw)
        dest.chmod(0o600)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    return count


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Safely restore temporary private state")
    p.add_argument("data_dir", type=Path)
    args = p.parse_args(argv)
    try:
        n = stage_private_state(os.environ.get("PROXY_ACCOUNTS_JSON", ""), args.data_dir)
    except InvalidPrivateState as exc:
        # Always a fixed error code; never include secret data in errors.
        print("[PROXY_SESSION] " + str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError):
        print("[PROXY_SESSION] STAGING_FAILED", file=sys.stderr)
        return 1
    print("[PROXY_SESSION] TEMPORARY_STATE_READY")
    print("[PROXY_SESSION] ACCOUNT_COUNT_PRESENT: " + str(n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
