#!/usr/bin/env python3
"""Verify approved V3 selective recovery is safe before any YouTube secret."""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
from urllib import request
from youtube_new_channels_env_guard import fetch_protected_policy, policy_is_main_only
from games_alchemy_native_v3 import validate_plan

REPO="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - selectively resume four missing native V3 private Shorts"
COMMIT="feat(games-alchemy): recover only missing native V3 Shorts after audit"
MARKER=Path(__file__).resolve().parents[1]/"conteudos"/"games-alchemy-native-v3-resume-20261105.json"
SOURCE_RUN=42058545056
INITIAL_UPLOAD=42063131990
AUDIT_RUN=42063706481

class GateError(ValueError): pass

def github_json(token:str,url:str)->dict:
    if not url.startswith(f"https://api.github.com/repos/{REPO}/actions/runs/"):
        raise GateError("UNEXPECTED_API_URL")
    headers={"Authorization":"Bearer "+token,
             "Accept":"application/vnd.github+json",
             "X-GitHub-Api-Version":"2022-11-28",
             "User-Agent":"AutoEditorVideo-V3-Safe-Recovery-Guard"}
    try:
        with request.urlopen(request.Request(url,headers=headers),timeout=20) as response:
            return json.loads(response.read(2_000_000))
    except Exception:
        raise GateError("GITHUB_API_UNAVAILABLE") from None

def check_launch(env:dict)->None:
    if (env.get("GITHUB_REPOSITORY")!=REPO or
        env.get("GITHUB_REF")!="refs/heads/main" or
        env.get("GITHUB_EVENT_NAME")!="push" or
        env.get("GITHUB_RUN_ATTEMPT")!="1" or
        env.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise GateError("ONLY_ONE_MAIN_PUSH_ALLOWED")
    ev=Path(env.get("GITHUB_EVENT_PATH",""))
    if not ev.is_file():raise GateError("GITHUB_EVENT_NOT_FOUND")
    event=json.loads(ev.read_text(encoding="utf-8"))
    head=event.get("head_commit") or {}
    if (head.get("id")!=env.get("GITHUB_SHA") or
        head.get("message")!=COMMIT or
        event.get("ref")!="refs/heads/main"):
        raise GateError("CREATOR_APPROVED_COMMIT_MISMATCH")
    if not MARKER.is_file():raise GateError("APPROVAL_MARKER_MISSING")
    mark=json.loads(MARKER.read_text(encoding="utf-8"))
    if (mark.get("creator_authorized") is not True or
        mark.get("source_render_run")!=SOURCE_RUN or
        mark.get("first_upload_run")!=INITIAL_UPLOAD or
        mark.get("read_only_audit_run")!=AUDIT_RUN or
        mark.get("expected_existing_v3")!={"games":1,"alchemy":1} or
        mark.get("desired_private_v3")!={"games":3,"alchemy":3} or
        mark.get("visibility")!="private" or
        mark.get("preserve_old_versions") is not True or
        mark.get("no_new_image_generation") is not True):
        raise GateError("APPROVED_RECOVERY_SCOPE_MISMATCH")
    if not env.get("GH_TOKEN"):
        raise GateError("READ_ONLY_GITHUB_TOKEN_MISSING")

def read_state(token:str)->None:
    checks=[
      (SOURCE_RUN,{"validate-original-program":"success","render-with-native-remotion":"success"}),
      (INITIAL_UPLOAD,{"verify-native-v3-render":"success","gamer-v3-private":"failure","alchemy-v3-private":"failure"})
    ]
    for run,required in checks:
        result=github_json(token,f"https://api.github.com/repos/{REPO}/actions/runs/{run}/jobs?per_page=100")
        statuses={x.get("name"):x.get("conclusion") for x in result.get("jobs",[])}
        if any(statuses.get(name)!=status for name,status in required.items()):
            raise GateError("PRIOR_SOURCE_OR_UPLOAD_RUN_STATE_MISMATCH")
    audit=github_json(token,f"https://api.github.com/repos/{REPO}/actions/runs/{AUDIT_RUN}/jobs?per_page=100")
    for name in ("audit (games, YOUTUBE_GAMES_TOKEN_JSON)","audit (alchemy, YOUTUBE_ALCHEMY_TOKEN_JSON)"):
        if not any(x.get("name")==name and x.get("conclusion")=="success" for x in audit.get("jobs",[])):
            raise GateError("READ_ONLY_RECONCILIATION_NOT_SUCCESSFUL")
    source=github_json(token,f"https://api.github.com/repos/{REPO}/actions/runs/{SOURCE_RUN}/artifacts?per_page=100")
    expected=[x for x in source.get("artifacts",[]) if x.get("name")=="gamer-alchemy-six-native-v3" and not x.get("expired")]
    if len(expected)!=1 or expected[0].get("id")!=13432425860:
        raise GateError("REVISED_SIX_VIDEO_ARTIFACT_NOT_ACCESSIBLE")

def main()->int:
    try:
        env=dict(os.environ)
        check_launch(env)
        validate_plan()
        read_state(env["GH_TOKEN"])
        for channel in ("games","alchemy"):
            protected,policies=fetch_protected_policy(channel,env["GH_TOKEN"])
            policy_is_main_only(channel,protected,policies)
        print("V3_SELECTIVE_RECOVERY_GATE_SUCCESS_FIRST_TWO_ACCEPTED",flush=True)
        print("NO_SECRETS_AND_NO_YOUTUBE_WRITES_IN_GATE",flush=True)
        return 0
    except Exception as e:
        reason=str(e) if isinstance(e,GateError) else type(e).__name__
        print("V3_SELECTIVE_RECOVERY_GATE_BLOCKED_"+reason,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
