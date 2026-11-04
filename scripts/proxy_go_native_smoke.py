#!/usr/bin/env python3
"""Smoke-test the upstream Go proxy running natively, without Docker.

Safety: deliberately uses a fake API key, an empty temp data directory,
no OAuth accounts, no image requests, and no external API calls.
"""
from __future__ import annotations

import json
import os
import time
from urllib import error, request

ROOT = "http://127.0.0.1:8080"


def get(path: str, key: str | None = None) -> tuple[int, bytes]:
    headers = {"Authorization": "Bearer " + key} if key else {}
    try:
        with request.urlopen(
            request.Request(ROOT + path, headers=headers), timeout=3
        ) as response:
            return response.status, response.read(64 * 1024)
    except error.HTTPError as exc:
        # Never display credential-bearing response bodies in GitHub logs.
        return exc.code, b""


def check() -> None:
    secret = os.environ.get("PROXY_API_KEY", "")
    if len(secret) < 20:
        raise RuntimeError("Missing long synthetic test key")
    # Go compilation and process startup can require several seconds.
    for _ in range(80):
        try:
            code, body = get("/health/live")
            if code == 200 and json.loads(body).get("status") == "ok":
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.3)
    else:
        raise RuntimeError("Native Go server did not answer on loopback")

    if get("/admin/accounts")[0] != 401:
        raise RuntimeError("Admin route accepted missing auth")
    if get("/admin/accounts", "invalid-test-key")[0] != 401:
        raise RuntimeError("Admin route accepted incorrect auth")
    code, payload = get("/admin/accounts", secret)
    if code != 200:
        raise RuntimeError("Admin route rejected valid synthetic key")
    accounts = json.loads(payload).get("accounts")
    if accounts != []:
        raise RuntimeError("Expected empty test account state")
    code, body = get("/health", secret)
    if code != 200 or json.loads(body).get("status") != "ok":
        raise RuntimeError("Protected health check failed")
    print("[PASS] GO_NATIVE_NO_DOCKER_HEALTH")
    print("[PASS] GO_NATIVE_API_KEY_REQUIRED")
    print("[PASS] GO_NATIVE_EMPTY_ACCOUNT_STORE")
    print("[SAFETY] ZERO_IMAGE_REQUESTS_ZERO_YOUTUBE_UPLOADS_ZERO_REAL_SECRETS")


if __name__ == "__main__":
    try:
        check()
    except Exception as exc:
        print("[FAIL] " + type(exc).__name__ + ": " + str(exc))
        raise SystemExit(1)
