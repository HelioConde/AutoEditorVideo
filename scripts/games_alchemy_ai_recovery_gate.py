#!/usr/bin/env python3
"""One-shot, read-only YouTube environment guard for the exact six-video render.

Distinct from the OAuth onboarding guard (which intentionally allows only
workflow_dispatch). This guard reads the protected branch policy and the
completed original rendering workflow before any YouTube token is requested.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from urllib import request
import sys
from youtube_new_channels_env_guard import fetch_protected_policy, policy_is_main_only

EXPECTED_ID = 42044136670
EXPECTED_SHA = "a414b9aea8d778f27c765cfb3d45e94612d0ee05"
EXPECTED_WORKFLOW = "Gamer + Alchemy - six AI-illustrated Shorts one-shot"
REPO = "HelioConde/AutoEditorVideo"

class RecoveryBlocked(ValueError):
    pass

def guard_event(env: dict) -> None:
    if env.get("GITHUB_REPOSITORY") != REPO or env.get("GITHUB_REF") != "refs/heads/main":
        raise RecoveryBlocked("WRONG_REPOSITORY_OR_REF")
    if env.get("GITHUB_EVENT_NAME") != "workflow_run" or env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise RecoveryBlocked("ONE_SHOT_WORKFLOW_RUN_ONLY")
    event_file = Path(env.get("GITHUB_EVENT_PATH", ""))
    if not event_file.is_file():
        raise RecoveryBlocked("MISSING_ORIGINAL_EVENT")
    payload = json.loads(event_file.read_text(encoding="utf-8"))
    run = payload.get("workflow_run") or {}
    if (run.get("id") != EXPECTED_ID or
        run.get("name") != EXPECTED_WORKFLOW or
        run.get("head_sha") != EXPECTED_SHA or
        run.get("head_branch") != "main" or
        run.get("event") != "push" or
        run.get("run_attempt") != 1 or
        run.get("status") != "completed"):
        raise RecoveryBlocked("UNRECOGNIZED_SOURCE_WORKFLOW")
    if not env.get("GH_TOKEN"):
        raise RecoveryBlocked("NO_GITHUB_READ_TOKEN")

def verify_original_render_job(token: str) -> None:
    url = f"https://api.github.com/repos/{REPO}/actions/runs/{EXPECTED_ID}/jobs?per_page=100"
    headers = {"Accept": "application/vnd.github+json",
               "Authorization": "Bearer " + token,
               "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "AutoEditorVideo-SixVideo-Artifact-Guard"}
    try:
        with request.urlopen(request.Request(url, headers=headers), timeout=15) as response:
            payload = json.loads(response.read(1024 * 1024))
    except Exception:
        raise RecoveryBlocked("CANNOT_READ_ORIGINAL_RUN_JOBS") from None
    jobs = {item.get("name"): item.get("conclusion") for item in payload.get("jobs", [])}
    required = ("offline-contract", "check-image-environment", "generate-six-shorts")
    if not all(jobs.get(name) == "success" for name in required):
        raise RecoveryBlocked("ORIGINAL_RENDER_NOT_PROVEN_SUCCESSFUL")

def main() -> int:
    try:
        env = dict(os.environ)
        guard_event(env)
        verify_original_render_job(env["GH_TOKEN"])
        for channel in ("games", "alchemy"):
            original, policies = fetch_protected_policy(channel, env["GH_TOKEN"])
            policy_is_main_only(channel, original, policies)
        print("RECOVERY_GUARD_ORIGINAL_RENDER_SUCCESS_SHARED_ENV_MAIN_ONLY")
        print("NO_SECRETS_ACCESSED_NO_UPLOAD_PERFORMED_BY_GATE")
        return 0
    except Exception as e:
        tag = str(e) if isinstance(e, RecoveryBlocked) else type(e).__name__
        print("RECOVERY_GUARD_BLOCKED_" + tag, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
