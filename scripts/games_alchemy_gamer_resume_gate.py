#!/usr/bin/env python3
"""Read-only single-use recovery guard for the incomplete Gamer YouTube upload.

Validates the precise approved push, original six-video render, prior partial
upload and main-only protected YouTube environment. No secrets or uploads.
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
PREVIOUS_UPLOAD_RUN=42048524469
RENDER_RUN=42044136670
RENDER_SHA="a414b9aea8d778f27c765cfb3d45e94612d0ee05"
MESSAGE="feat(gamer): resume only missing AI Shorts after checking YouTube"
WORKFLOW="Gamer - resume only missing two AI Shorts"
MARKER=Path(__file__).resolve().parents[1]/"conteudos"/"games-alchemy-gamer-resume-20261105.json"

class ResumeBlocked(ValueError):
    pass

def guard_event(env:dict)->None:
    if env.get("GITHUB_REPOSITORY")!=REPO or env.get("GITHUB_REF")!="refs/heads/main":
        raise ResumeBlocked("WRONG_REPO_OR_BRANCH")
    if env.get("GITHUB_EVENT_NAME")!="push" or env.get("GITHUB_RUN_ATTEMPT")!="1":
        raise ResumeBlocked("ONE_SHOT_PUSH_ONLY")
    if env.get("GITHUB_WORKFLOW")!=WORKFLOW:
        raise ResumeBlocked("WRONG_WORKFLOW")
    event_path=Path(env.get("GITHUB_EVENT_PATH",""))
    if not event_path.is_file():
        raise ResumeBlocked("EVENT_NOT_FOUND")
    obj=json.loads(event_path.read_text(encoding="utf-8"))
    commit=obj.get("head_commit") or {}
    if (commit.get("id")!=env.get("GITHUB_SHA") or
        commit.get("message")!=MESSAGE or obj.get("ref")!="refs/heads/main"):
        raise ResumeBlocked("INVALID_LAUNCH_COMMIT")
    if not MARKER.is_file():
        raise ResumeBlocked("MARKER_NOT_PRESENT")
    marker=json.loads(MARKER.read_text(encoding="utf-8"))
    if (marker.get("approved_by_creator") is not True or
        marker.get("original_render_run_id")!=RENDER_RUN or
        marker.get("original_render_sha")!=RENDER_SHA or
        marker.get("previous_upload_run_id")!=PREVIOUS_UPLOAD_RUN or
        marker.get("already_confirmed_video_id")!="61bCmdk2dV8" or
        marker.get("channel_id")!="UCg77gYc1_wkHuL07XPtKcow" or
        marker.get("missing")!=["game-002-primeira-noite-minecraft","game-003-minecraft-sem-amarelo"] or
        marker.get("upload_visibility")!="private"):
        raise ResumeBlocked("RECOVERY_MARKER_MISMATCH")
    if not env.get("GH_TOKEN"):
        raise ResumeBlocked("GITHUB_READ_TOKEN_MISSING")

def github_json(url:str,token:str)->dict:
    if not url.startswith(f"https://api.github.com/repos/{REPO}/actions/runs/"):
        raise ResumeBlocked("UNEXPECTED_API_RESOURCE")
    headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"AutoEditorVideo-Private-Recovery-Gate"}
    try:
        with request.urlopen(request.Request(url,headers=headers),timeout=20) as r:
            return json.loads(r.read(2_000_000))
    except Exception:
        raise ResumeBlocked("GITHUB_API_UNAVAILABLE") from None

def verify_prior_upload(token:str)->None:
    jobs=github_json(f"https://api.github.com/repos/{REPO}/actions/runs/{PREVIOUS_UPLOAD_RUN}/jobs?per_page=100",token)
    status={x.get("name"):x.get("conclusion") for x in jobs.get("jobs",[])}
    if status.get("upload-alchemy")!="success" or status.get("upload-gamer")!="failure":
        raise ResumeBlocked("PRIOR_UPLOAD_EXPECTATIONS_NOT_MET")
    checks=[
        (PREVIOUS_UPLOAD_RUN,"six-ai-gamer-private-receipts"),
        (RENDER_RUN,"games-alchemy-six-ai-render")
    ]
    for rid,name in checks:
        data=github_json(f"https://api.github.com/repos/{REPO}/actions/runs/{rid}/artifacts?per_page=100",token)
        matching=[x for x in data.get("artifacts",[]) if x.get("name")==name and not x.get("expired")]
        if len(matching)!=1:
            raise ResumeBlocked("REQUIRED_ARTIFACT_MISSING_"+name)

def main()->int:
    try:
        env=dict(os.environ)
        guard_event(env)
        verify_original_render_job(env["GH_TOKEN"])
        verify_prior_upload(env["GH_TOKEN"])
        state,policies=fetch_protected_policy("games",env["GH_TOKEN"])
        policy_is_main_only("games",state,policies)
        print("GAMER_RECOVERY_SAFE_ORIGINAL_ARTIFACTS_AND_ENVIRONMENT_VERIFIED")
        print("ONLY_MISSING_GAME_EPISODES_ALLOWED_NO_SECRETS_ACCESSED")
        return 0
    except Exception as e:
        reason=str(e) if isinstance(e,ResumeBlocked) else type(e).__name__
        print("GAMER_RECOVERY_GUARD_BLOCKED_"+reason,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
