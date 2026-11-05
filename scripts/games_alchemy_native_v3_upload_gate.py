#!/usr/bin/env python3
"""Read-only gate for exactly six V3 native-media private YouTube uploads.

Refuse public uploads, unsupported channels, unverified original renderer,
any unprotected branch or unauthorized rerun. Never reads YouTube secrets.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
from urllib import request

from youtube_new_channels_env_guard import fetch_protected_policy,policy_is_main_only
from games_alchemy_native_v3 import validate_plan

REPO="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - private upload native V3 master style"
COMMIT="feat(games-alchemy): upload six native Remotion Shorts privately with program covers"
ORIGIN_RUN=42058545056
ARTIFACT="gamer-alchemy-six-native-v3"
MARKER=Path(__file__).resolve().parents[1]/"conteudos"/"games-alchemy-native-v3-upload-20261105.json"

class NativeGateError(ValueError):pass

def check_launch(e:dict)->dict:
    if (e.get("GITHUB_REPOSITORY")!=REPO or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise NativeGateError("SINGLE_APPROVED_MAIN_PUSH_ONLY")
    event=Path(e.get("GITHUB_EVENT_PATH",""))
    if not event.is_file():
        raise NativeGateError("NO_GITHUB_EVENT")
    d=json.loads(event.read_text(encoding="utf-8"))
    commit=d.get("head_commit") or {}
    if (d.get("ref")!="refs/heads/main" or
        commit.get("message")!=COMMIT or
        commit.get("id")!=e.get("GITHUB_SHA")):
        raise NativeGateError("UNAUTHORIZED_COMMIT")
    if not MARKER.is_file():raise NativeGateError("NO_APPROVED_V3_MARKER")
    m=json.loads(MARKER.read_text(encoding="utf-8"))
    if (m.get("approved_by_creator") is not True or
        m.get("source_run")!=ORIGIN_RUN or
        m.get("source_artifact")!=ARTIFACT or
        m.get("visibility")!="private" or
        m.get("keep_older_private_uploads") is not True or
        m.get("channel_counts")!={"games":3,"alchemy":3} or
        m.get("official_cover_and_caption_only") is not True or
        m.get("thumbnail_delay_s")!=75):
        raise NativeGateError("UNEXPECTED_APPROVED_MARKER")
    if not e.get("GH_TOKEN"):
        raise NativeGateError("NO_GITHUB_READ_TOKEN")
    return m

def get_github(token:str,endpoint:str)->dict:
    if not endpoint.startswith(f"https://api.github.com/repos/{REPO}/actions/runs/{ORIGIN_RUN}/"):
        raise NativeGateError("UNSUPPORTED_GITHUB_ENDPOINT")
    headers={"Authorization":"Bearer "+token,
             "Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"AutoEditorVideo-V3-Upload-Guard"}
    try:
        with request.urlopen(request.Request(endpoint,headers=headers),timeout=25) as response:
            return json.loads(response.read(2_000_000))
    except Exception:
        raise NativeGateError("GITHUB_READ_FAILED") from None

def check_renderer_success(token:str)->None:
    jobs=get_github(token,f"https://api.github.com/repos/{REPO}/actions/runs/{ORIGIN_RUN}/jobs?per_page=100")
    results={i.get("name"):i.get("conclusion") for i in jobs.get("jobs",[])}
    if (results.get("validate-original-program")!="success" or
        results.get("render-with-native-remotion")!="success"):
        raise NativeGateError("ORIGINAL_RENDER_JOB_FAILED_OR_RUNNING")
    artifacts=get_github(token,f"https://api.github.com/repos/{REPO}/actions/runs/{ORIGIN_RUN}/artifacts?per_page=100")
    matched=[a for a in artifacts.get("artifacts",[])
             if a.get("name")==ARTIFACT and not a.get("expired")]
    if len(matched)!=1:
        raise NativeGateError("NATIVE_RENDER_ARTIFACT_NOT_AVAILABLE")

def main()->int:
    try:
        e=dict(os.environ)
        check_launch(e)
        validate_plan()
        check_renderer_success(e["GH_TOKEN"])
        for ch in ("games","alchemy"):
            cfg,policies=fetch_protected_policy(ch,e["GH_TOKEN"])
            policy_is_main_only(ch,cfg,policies)
        print("NATIVE_V3_PRIVATE_GATE_SUCCESS_OFFICIAL_REMOTION_COVER_AND_CAPTIONS",flush=True)
        return 0
    except Exception as exc:
        reason=str(exc) if isinstance(exc,NativeGateError) else type(exc).__name__
        print("NATIVE_V3_GATE_BLOCKED_"+reason,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
