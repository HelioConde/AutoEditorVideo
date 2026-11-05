#!/usr/bin/env python3
"""One-shot no-secrets verifier for uploading six revised Shorts as PRIVATE."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
from urllib import request
from youtube_new_channels_env_guard import fetch_protected_policy,policy_is_main_only
from games_alchemy_six_recut_v2 import validate_manifest

REPO="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - private upload six corrected v2 Shorts"
COMMIT="feat(recut): upload approved six revised Shorts privately"
MARKER=Path(__file__).resolve().parents[1]/"conteudos"/"games-alchemy-six-recut-v2-upload-20261105.json"
RUN=42055957229
ARTIFACT=13429072215

class V2GateError(ValueError): pass

def check_launch(env:dict)->None:
    if (env.get("GITHUB_REPOSITORY")!=REPO or
        env.get("GITHUB_REF")!="refs/heads/main" or
        env.get("GITHUB_EVENT_NAME")!="push" or
        env.get("GITHUB_RUN_ATTEMPT")!="1" or
        env.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise V2GateError("REPO_MAIN_ONE_SHOT_WORKFLOW_REQUIRED")
    p=Path(env.get("GITHUB_EVENT_PATH",""))
    if not p.is_file(): raise V2GateError("NO_EVENT_PAYLOAD")
    event=json.loads(p.read_text(encoding="utf-8"))
    if (event.get("ref")!="refs/heads/main" or
        (event.get("head_commit") or {}).get("id")!=env.get("GITHUB_SHA") or
        (event.get("head_commit") or {}).get("message")!=COMMIT):
        raise V2GateError("NOT_CREATOR_APPROVED_TRIGGER")
    if not MARKER.is_file():raise V2GateError("NO_MARKER")
    m=json.loads(MARKER.read_text(encoding="utf-8"))
    if (m.get("approved_by_creator") is not True or
        m.get("revision")!="v2" or
        m.get("source_recut_run")!=RUN or
        m.get("source_artifact_id")!=ARTIFACT or
        m.get("visibility")!="private" or
        m.get("keep_old_private_videos") is not True or
        m.get("thumbnail_upload_delay_s")!=75 or
        m.get("channel_counts")!={"games":3,"alchemy":3}):
        raise V2GateError("REVIEWED_REVISION_TRIGGER_MISMATCH")
    if not env.get("GH_TOKEN"):raise V2GateError("NO_READ_TOKEN")

def get(token:str,url:str)->dict:
    prefix=f"https://api.github.com/repos/{REPO}/actions/runs/{RUN}/"
    if not url.startswith(prefix):raise V2GateError("UNEXPECTED_API_PATH")
    headers={"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"AutoEditorVideo-V2-Private-Upload-Guard"}
    try:
        with request.urlopen(request.Request(url,headers=headers),timeout=20) as r:
            return json.loads(r.read(2_000_000))
    except Exception:
        raise V2GateError("GH_API_READ_FAILED") from None

def verify_recut_artifact(token:str)->None:
    jobs=get(token,f"https://api.github.com/repos/{REPO}/actions/runs/{RUN}/jobs?per_page=100")
    by={j.get("name"):j.get("conclusion") for j in jobs.get("jobs",[])}
    if by.get("validate-v2-editorial")!="success" or by.get("recut-existing-ai-footage")!="success":
        raise V2GateError("V2_RENDER_NOT_CONFIRMED_SUCCESS")
    a=get(token,f"https://api.github.com/repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100")
    files=[x for x in a.get("artifacts",[])
           if x.get("id")==ARTIFACT and x.get("name")=="games-alchemy-six-recut-v2-preview" and not x.get("expired")]
    if len(files)!=1:raise V2GateError("PINNED_V2_ARTIFACT_NOT_FOUND")

def main()->int:
    try:
        env=dict(os.environ); check_launch(env)
        validate_manifest()
        verify_recut_artifact(env["GH_TOKEN"])
        for slug in ("games","alchemy"):
            e,p=fetch_protected_policy(slug,env["GH_TOKEN"])
            policy_is_main_only(slug,e,p)
        print("SIX_RECUT_V2_PRIVATE_UPLOAD_GATE_PASSED_NO_SECRETS",flush=True)
        return 0
    except Exception as exc:
        print("V2_UPLOAD_GATE_BLOCKED_"+(str(exc) if isinstance(exc,V2GateError) else type(exc).__name__),file=sys.stderr)
        return 2
if __name__=="__main__":raise SystemExit(main())
