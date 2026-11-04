#!/usr/bin/env python3
"""Check a locally started Go proxy using only protected read-only endpoints.

Does not call image, account refresh, device-login, or YouTube endpoints.
"""
from __future__ import annotations

import json
import os
import sys
import time
from urllib import error, request


URL = "http://127.0.0.1:8080"


class ReadOnlyProbeError(Exception):
    pass


def fetch(path: str, token: str = "", opener=None):
    if path not in ("/health/live", "/admin/accounts"):
        raise ReadOnlyProbeError("FORBIDDEN_ENDPOINT")
    headers = {"Authorization": "Bearer " + token} if token else {}
    handler = opener or request.urlopen
    req = request.Request(URL + path, headers=headers)
    try:
        with handler(req, timeout=3) as res:
            if res.status != 200:
                raise ReadOnlyProbeError("BAD_HTTP_STATUS")
            return json.loads(res.read(128 * 1024))
    except (OSError, error.URLError, ValueError, TypeError):
        raise ReadOnlyProbeError("PROXY_READ_FAILED") from None


def check(key: str, opener=None) -> str:
    if len(key.strip()) < 15:
        raise ReadOnlyProbeError("PROXY_KEY_MISSING")
    for _ in range(50):
        try:
            if fetch("/health/live", opener=opener).get("status") == "ok":
                break
        except ReadOnlyProbeError:
            pass
        time.sleep(0.2)
    else:
        raise ReadOnlyProbeError("PROXY_NOT_STARTED")
    data = fetch("/admin/accounts", key, opener)
    records = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(records, list) or not records:
        raise ReadOnlyProbeError("NO_AUTHORIZED_ACCOUNTS_LOADED")
    # This is a cached eligibility flag; it does NOT prove upstream model access.
    eligible = any(isinstance(x, dict) and x.get("eligible_now") is True for x in records)
    if not eligible:
        return "ACCOUNT_RECORDS_LOADED_BUT_NOT_CACHED_ELIGIBLE"
    return "ACCOUNT_RECORDS_LOADED_CACHED_ELIGIBLE"


def main() -> int:
    try:
        result = check(os.environ.get("PROXY_API_KEY", ""))
    except ReadOnlyProbeError as exc:
        print("[IMAGE_SESSION] " + str(exc), file=sys.stderr)
        return 1
    print("[IMAGE_SESSION] " + result)
    print("[SAFETY] NO_IMAGE_CALLS_NO_UPLOAD_NO_UPSTREAM_AUTH_TEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
