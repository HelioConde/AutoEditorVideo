#!/usr/bin/env python3
"""Read-only security guard for a *thumbnail-only* one-time recovery.

This checks protected environment policy, exact original six-upload receipts,
original render and a single creator-approved push. It does not read OAuth.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import request

from games_alchemy_ai_recovery_gate import verify_original_render_job
from youtube_new_channels_env_guard import fetch_protected_policy,policy_is_main_only

REPO="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - delayed thumbnail retry for six private Shorts"
COMMIT_MESSAGE="feat(thumbnail): retry existing six private Shorts covers after delay"
MARKER=Path(__file__).resolve().parents[1]/"conteudos"/"games-alchemy-six-thumbnail-retry-20261105.json"
RENDER_RUN=42044136670
ARTIFACT_NAME="games-alchemy-six-ai-render"
PREVIOUS_UPLOAD=42048524469
GAMER_RECOVERY=42049521888

class UnsafeThumbnailRetry(ValueError):
    pass

def check_launch(env: dict) -> None:
    if env.get("GITHUB_REPOSITORY")!=REPO or env.get("GITHUB_REF")!="refs/heads/main":
        raise UnsafeThumbnailRetry("REPO_MAIN_ONLY")
    if env.get("GITHUB_EVENT_NAME")!="push" or env.get("GITHUB_RUN_ATTEMPT")!="1":
        raise UnsafeThumbnailRetry("ONE_SHOT_PUSH_ONLY")
    if env.get("GITHUB_WORKFLOW")!=WORKFLOW:
        raise UnsafeThumbnailRetry("UNEXPECTED_WORKFLOW")
    path=Path(env.get("GITHUB_EVENT_PATH",""))
    if not path.is_file():
        raise UnsafeThumbnailRetry("EVENT_MISSING")
    event=json.loads(path.read_text(encoding="utf-8"))
    commit=event.get("head_commit") or {}
    if (event.get("ref")!="refs/heads/main" or
        commit.get("id")!=env.get("GITHUB_SHA") or
        commit.get("message")!=COMMIT_MESSAGE):
        raise UnsafeThumbnailRetry("UNAUTHORIZED_COMMIT")
    if not MARKER.is_file():
        raise UnsafeThumbnailRetry("MISSING_APPROVED_MARKER")
    marker=json.loads(MARKER.read_text(encoding="utf-8"))
    if (marker.get("approved_by_creator") is not True or
        marker.get("scope")!="thumbnails_only_no_video_upload" or
        marker.get("render_run")!=RENDER_RUN or
        marker.get("original_upload_run")!=PREVIOUS_UPLOAD or
        marker.get("gamer_recovery_run")!=GAMER_RECOVERY or
        marker.get("initial_visibility")!="private" or
        marker.get("delay_after_upload_seconds")!=75 or
        marker.get("channels")!=["games","alchemy"] or
        marker.get("expected_shorts")!=6):
        raise UnsafeThumbnailRetry("MARKER_FIELDS_INVALID")
    if not env.get("GH_TOKEN"):
        raise UnsafeThumbnailRetry("GITHUB_READ_TOKEN_MISSING")

def fetch_json(token: str, url: str) -> dict:
    if not url.startswith(f"https://api.github.com/repos/{REPO}/actions/runs/"):
        raise UnsafeThumbnailRetry("UNEXPECTED_API_ENDPOINT")
    headers={"Accept":"application/vnd.github+json",
             "Authorization":"Bearer "+token,
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"AutoEditorVideo-ThumbOnly-Guard"}
    try:
        with request.urlopen(request.Request(url,headers=headers),timeout=15) as resp:
            return json.loads(resp.read(1500000))
    except Exception:
        raise UnsafeThumbnailRetry("GITHUB_RUN_LOOKUP_UNAVAILABLE") from None

def check_previous(token: str) -> None:
    for rid,expected in (
        (PREVIOUS_UPLOAD,{"upload-alchemy":"success","upload-gamer":"failure"}),
        (GAMER_RECOVERY,{"verify-original-and-prior-uploads":"success","resume-gamer-private":"success"})
    ):
        jobs=fetch_json(token,f"https://api.github.com/repos/{REPO}/actions/runs/{rid}/jobs?per_page=100")
        states={item.get("name"):item.get("conclusion") for item in jobs.get("jobs",[])}
        if any(states.get(k)!=v for k,v in expected.items()):
            raise UnsafeThumbnailRetry("PREVIOUS_UPLOAD_RUN_NOT_VERIFIED")
    artifacts=fetch_json(token,f"https://api.github.com/repos/{REPO}/actions/runs/{RENDER_RUN}/artifacts?per_page=100")
    matching=[v for v in artifacts.get("artifacts",[])
              if v.get("name")==ARTIFACT_NAME and not v.get("expired")]
    if len(matching)!=1 or matching[0].get("id")!=13425056457:
        raise UnsafeThumbnailRetry("PINNED_ORIGINAL_ARTIFACT_UNAVAILABLE")

def main() -> int:
    try:
        env=dict(os.environ)
        check_launch(env)
        verify_original_render_job(env["GH_TOKEN"])
        check_previous(env["GH_TOKEN"])
        for channel in ("games","alchemy"):
            e,p=fetch_protected_policy(channel,env["GH_TOKEN"])
            policy_is_main_only(channel,e,p)
        print("THUMB_ONLY_GUARD_MAIN_ENV_AND_SIX_PRIVATE_UPLOADS_VERIFIED",flush=True)
        print("NO_SECRETS_NO_VIDEO_INSERT_NO_IMAGE_GENERATION",flush=True)
        return 0
    except Exception as ex:
        print("THUMB_ONLY_GUARD_BLOCKED_"+(str(ex) if isinstance(ex,UnsafeThumbnailRetry) else type(ex).__name__),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
