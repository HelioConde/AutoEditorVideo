"""Read-only image proxy connectivity preflight. Zero image and login calls.

The GitHub runner has no local Docker proxy. A remote HTTPS URL has to be
configured separately as PROXY_BASE_URL in GitHub Actions Secrets.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib import request, error

from proxy_endpoint import proxy_api_url, proxy_base_url


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _open(req: request.Request, opener=None, timeout: int = 7):
    open_fn = opener or request.build_opener(NoRedirect()).open
    return open_fn(req, timeout=timeout)


def check(env: dict[str, str] | None = None, *, opener=None) -> str:
    env = os.environ if env is None else env
    if not env.get("PROXY_BASE_URL", "").strip():
        return "REMOTE_ENDPOINT_NOT_CONFIGURED"
    try:
        base = proxy_base_url(env)
    except ValueError:
        return "INVALID_REMOTE_URL"
    if env.get("GITHUB_ACTIONS", "").lower() == "true" and not base.startswith("https://"):
        return "CLOUD_REQUIRES_HTTPS_REMOTE"
    key = env.get("PROXY_API_KEY", "").strip()
    if len(key) < 15 or key.lower().startswith("change-me"):
        return "KEY_MISSING_OR_INVALID"
    try:
        with _open(request.Request(proxy_api_url("/health/live", env)), opener=opener, timeout=6) as reply:
            if reply.status != 200:
                return "HEALTH_CHECK_FAILED"
            reply.read(1024)
    except (OSError, error.URLError, ValueError):
        return "HEALTH_CHECK_FAILED"
    try:
        req = request.Request(
            proxy_api_url("/admin/accounts", env),
            headers={"Authorization": "Bearer " + key},
        )
        with _open(req, opener=opener, timeout=8) as reply:
            if reply.status != 200:
                return "AUTH_CHECK_FAILED"
            payload = reply.read(65536)
        data = json.loads(payload)
        if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
            return "ACCOUNT_STATUS_UNAVAILABLE"
        if not any(isinstance(a, dict) and a.get("eligible_now") is True
                   for a in data["accounts"]):
            return "NO_ELIGIBLE_ACCOUNT"
    except (OSError, error.URLError, ValueError, TypeError):
        return "AUTH_CHECK_FAILED"
    return "REMOTE_PROXY_READY"


def main() -> int:
    ap = argparse.ArgumentParser(description="Read-only proxy connectivity preflight")
    ap.add_argument("--strict", action="store_true", help="Fail when endpoint is not ready")
    args = ap.parse_args()
    result = check()
    print("[PROXY] " + result)
    print("[SAFETY] READ_ONLY_NO_IMAGE_GENERATION_NO_UPLOAD")
    if result == "REMOTE_ENDPOINT_NOT_CONFIGURED" and not args.strict:
        return 0
    return 0 if result == "REMOTE_PROXY_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
