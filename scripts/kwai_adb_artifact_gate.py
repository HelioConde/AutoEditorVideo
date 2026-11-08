#!/usr/bin/env python3
"""Fail-closed source provenance gate for GitHub -> local Samsung ADB.

Runs only on GitHub-hosted Linux; the local Windows runner receives no
repository writes and only the name/ID of an approved artifact from main.
No publishing, login or remote commands.
"""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.request import Request,urlopen
from urllib.error import URLError,HTTPError

REPO="HelioConde/AutoEditorVideo"
BASE="https://api.github.com/repos/"+REPO
ALLOWED_EVENTS=("push","workflow_dispatch")
NAME=re.compile(r"[A-Za-z0-9_.-]{5,140}\Z")

class ProvenanceBlocked(ValueError):
    pass

def require_stage_inputs(operation:str,run_id:str,artifact:str,confirmed:str)->None:
    if operation not in ("diagnose","stage"):
        raise ProvenanceBlocked("OPERATION_UNSUPPORTED")
    if operation=="diagnose":
        return
    if (not run_id.isdecimal() or not 1<=len(run_id)<=20
        or not NAME.fullmatch(artifact)
        or confirmed!="true"):
        raise ProvenanceBlocked("EXACT_SOURCE_RUN_ARTIFACT_AND_QA_CONFIRMATION_REQUIRED")

def require_source_run(row:dict,run_id:str)->None:
    if not isinstance(row,dict) or str(row.get("id"))!=run_id:
        raise ProvenanceBlocked("SOURCE_RUN_ID_MISMATCH")
    if (row.get("status")!="completed" or row.get("conclusion")!="success"
        or row.get("head_branch")!="main"
        or row.get("event") not in ALLOWED_EVENTS
        or (row.get("repository") or {}).get("full_name")!=REPO
        or (row.get("head_repository") or {}).get("full_name")!=REPO):
        raise ProvenanceBlocked("SOURCE_MUST_BE_SUCCESSFUL_SAME_REPO_MAIN_RUN")

def require_artifact(items:list,name:str)->None:
    matches=[r for r in items if r.get("name")==name and not r.get("expired")]
    if len(matches)!=1 or not 0<int(matches[0].get("size_in_bytes") or 0)<=1024**3:
        raise ProvenanceBlocked("SOURCE_ARTIFACT_NOT_FOUND_OR_UNSAFE_SIZE")

def api_get(url:str,token:str)->dict:
    if not url.startswith(BASE+"/actions/runs/"):
        raise ProvenanceBlocked("UNEXPECTED_GITHUB_API_ENDPOINT")
    request=Request(url,headers={
        "Accept":"application/vnd.github+json",
        "Authorization":"Bearer "+token,
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"AutoEditorVideo-Kwai-Local-Staging-Guard",
    })
    try:
        with urlopen(request,timeout=15) as response:
            return json.loads(response.read(1_000_000))
    except (ValueError,HTTPError,URLError,OSError):
        raise ProvenanceBlocked("CANNOT_VERIFY_GITHUB_SOURCE") from None

def main()->int:
    env=os.environ
    op=env.get("KWAI_OPERATION","")
    run_id=env.get("KWAI_SOURCE_RUN_ID","")
    artifact=env.get("KWAI_SOURCE_ARTIFACT","")
    confirm=env.get("KWAI_QA_CONFIRMED","")
    try:
        if (env.get("GITHUB_ACTIONS")!="true"
            or env.get("GITHUB_REPOSITORY")!=REPO
            or env.get("GITHUB_ACTOR")!="HelioConde"
            or env.get("GITHUB_EVENT_NAME")!="workflow_dispatch"
            or env.get("GITHUB_REF")!="refs/heads/main"):
            raise ProvenanceBlocked("ONLY_REPO_OWNER_MANUAL_MAIN_WORKFLOW_ALLOWED")
        require_stage_inputs(op,run_id,artifact,confirm)
        if op=="stage":
            token=env.get("GITHUB_TOKEN","")
            if not token:
                raise ProvenanceBlocked("GITHUB_ACTIONS_READ_TOKEN_REQUIRED")
            record=api_get(BASE+"/actions/runs/"+run_id,token)
            require_source_run(record,run_id)
            artifacts=api_get(BASE+"/actions/runs/"+run_id+"/artifacts?per_page=100",token)
            if artifacts.get("total_count",0)>100:
                raise ProvenanceBlocked("SOURCE_ARTIFACTS_PAGINATION_NOT_VERIFIED")
            require_artifact(artifacts.get("artifacts",[]),artifact)
            print("KWAI_SOURCE_SUCCESSFUL_MAIN_RUN_ARTIFACT_QA_CONFIRMED")
        else:
            print("KWAI_BRIDGE_DIAGNOSTIC_NO_ARTIFACT_NO_MEDIA")
        print("KWAI_DEVICE_STAGE_ONLY_NO_KWAI_PUBLISH")
        return 0
    except (ValueError,TypeError) as exc:
        reason=str(exc) if isinstance(exc,ProvenanceBlocked) else type(exc).__name__
        print("[KWAI SOURCE BLOCKED] "+reason,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
