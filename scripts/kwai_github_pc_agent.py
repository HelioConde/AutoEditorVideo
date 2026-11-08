#!/usr/bin/env python3
"""Read-only GitHub queue -> paired Samsung over ADB, without self-hosted runner.

Runs ONLY on Windows under the same user that paired ADB Wi-Fi. GitHub remains
the source of approved MP4 artifacts; this local watcher performs *data
transfer*, never login or automated Kwai publication. No external server,
webhook port, GitHub Actions runner or third-party service is needed.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from kwai_adb_local_bridge import (
    BridgeBlocked, adb_exe, device_serial, check_phone, safe_video, stage
)
from kwai_adb_artifact_gate import (
    NAME, REPO, require_source_run, require_artifact, require_stage_inputs
)

QUEUE_PATH="config/kwai-adb-stage-queue.json"
ALLOWED_CHANNELS=frozenset(("br","en","games","kids","alchemy"))
QUEUE_ID=re.compile(r"[A-Za-z0-9_-]{5,130}\Z")
SHA=re.compile(r"[a-f0-9]{64}\Z")
MAX_ITEMS=3

class AgentBlocked(ValueError):
    pass

def gh(*args:str,timeout:int=90)->str:
    executable=shutil.which("gh")
    if not executable:
        raise AgentBlocked("GITHUB_CLI_NOT_INSTALLED_OR_NOT_ON_PATH")
    try:
        result=subprocess.run([executable,*args],timeout=timeout,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,encoding="utf-8",errors="replace")
    except (OSError,subprocess.TimeoutExpired):
        raise AgentBlocked("GITHUB_CLI_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode:
        raise AgentBlocked("GITHUB_API_ACTION_FAILED")
    return result.stdout

def gh_json(endpoint:str)->dict:
    if not endpoint.startswith("repos/"+REPO+"/"):
        raise AgentBlocked("ONLY_OWN_GITHUB_SOURCE_ALLOWED")
    return json.loads(gh("api",endpoint,timeout=45))

def queue()->list[dict]:
    endpoint="repos/"+REPO+"/contents/"+QUEUE_PATH+"?ref=main"
    raw=gh("api","-H","Accept: application/vnd.github.raw+json",endpoint,timeout=45)
    try:
        value=json.loads(raw)
        if isinstance(value,dict) and "content" in value and value.get("encoding")=="base64":
            value=json.loads(base64.b64decode(value["content"]).decode("utf-8"))
    except (ValueError,KeyError,UnicodeError):
        raise AgentBlocked("GITHUB_QUEUE_JSON_NOT_READABLE") from None
    expected={
        "schema":"autoeditorvideo/kwai-local-adb-stage-queue/v1",
        "platform":"kwai_brazil",
        "source_repository":REPO,
        "stage_only_no_publish":True,
        "requires_approved_video":True,
        "requires_successful_main_run":True,
        "allow_unapproved_artifacts":False,
        "automatic_stage_queue_enabled":True,
    }
    if not isinstance(value,dict) or {k:value.get(k) for k in expected}!=expected:
        raise AgentBlocked("GITHUB_QUEUE_POLICY_CHANGED")
    items=value.get("items")
    if not isinstance(items,list) or len(items)>200:
        raise AgentBlocked("GITHUB_QUEUE_INVALID_OR_TOO_LARGE")
    seen=set()
    for item in items:
        validate_item(item)
        if item["queue_id"] in seen:
            raise AgentBlocked("GITHUB_QUEUE_DUPLICATE_ENTRY")
        seen.add(item["queue_id"])
    return items

def validate_item(item:dict)->None:
    if not isinstance(item,dict):
        raise AgentBlocked("INVALID_QUEUE_ITEM")
    keys={"queue_id","channel","run_id","artifact_name","relative_video",
          "sha256","approved_for_local_stage","status"}
    if set(item)!=keys:
        raise AgentBlocked("UNEXPECTED_QUEUE_ITEM_KEYS")
    qid=item.get("queue_id")
    channel=item.get("channel")
    run_id=item.get("run_id")
    name=item.get("artifact_name")
    video=item.get("relative_video")
    digest=item.get("sha256")
    if not isinstance(qid,str) or not QUEUE_ID.fullmatch(qid):
        raise AgentBlocked("INVALID_QUEUE_ID")
    if channel not in ALLOWED_CHANNELS:
        raise AgentBlocked("UNKNOWN_SOURCE_CHANNEL")
    if type(run_id) is not int or run_id<=0 or len(str(run_id))>20:
        raise AgentBlocked("INVALID_SOURCE_RUN_ID")
    if not isinstance(name,str) or not NAME.fullmatch(name):
        raise AgentBlocked("INVALID_SOURCE_ARTIFACT_NAME")
    if not isinstance(video,str) or len(video)>260:
        raise AgentBlocked("INVALID_VIDEO_RELATIVE_PATH")
    if not isinstance(digest,str) or not SHA.fullmatch(digest):
        raise AgentBlocked("INVALID_EXPECTED_SHA256")
    if item.get("status") not in ("approved","held","completed"):
        raise AgentBlocked("UNKNOWN_QUEUE_STATUS")
    if item.get("approved_for_local_stage") is not (item["status"]=="approved"):
        raise AgentBlocked("QUEUE_ITEM_APPROVAL_STATUS_INCONSISTENT")
    # Strict source artifact gate, additionally check GitHub metadata later.
    if item["status"]=="approved":
        require_stage_inputs("stage",str(run_id),name,"true")

def app_data_path()->Path:
    root=os.environ.get("LOCALAPPDATA")
    if not root:
        raise AgentBlocked("WINDOWS_LOCALAPPDATA_REQUIRED")
    return Path(root)/"AutoEditorVideo"/"Kwai"/"staged-receipts.json"

def receipts(path:Path)->dict:
    if not path.exists():
        return {}
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict) or len(value)>10000:
        raise AgentBlocked("LOCAL_STAGE_RECEIPT_INVALID")
    return value

def save_receipts(path:Path,seen:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+"."+str(os.getpid())+".tmp")
    with temp.open("w",encoding="utf-8") as stream:
        json.dump(seen,stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    os.replace(temp,path)

def verified_artifact(item:dict)->None:
    run_id=str(item["run_id"])
    run=gh_json("repos/"+REPO+"/actions/runs/"+run_id)
    require_source_run(run,run_id)
    data=gh_json("repos/"+REPO+"/actions/runs/"+run_id+"/artifacts?per_page=100")
    if data.get("total_count",0)>100:
        raise AgentBlocked("TOO_MANY_SOURCE_ARTIFACTS")
    require_artifact(data.get("artifacts",[]),item["artifact_name"])

def process_once(*,dry_run:bool=False)->dict:
    items=queue()
    approved=[x for x in items if x["status"]=="approved"]
    if dry_run:
        return {"approved_count":len(approved),"mode":"dry_run_no_download"}
    if not approved:
        return {"mode":"no_pending_approved_videos","newly_staged":0}
    path=app_data_path()
    done=receipts(path)
    pending=[x for x in approved
             if done.get(x["queue_id"],{}).get("sha256")!=x["sha256"]]
    if not pending:
        return {"mode":"no_pending_approved_videos","newly_staged":0}
    adb=adb_exe()
    serial=device_serial(adb)
    info=check_phone(adb,serial)
    if not info["kwai_official_app_installed"]:
        raise AgentBlocked("KWAI_APP_MUST_BE_INSTALLED_ON_PAIRED_SAMSUNG")
    staged=0
    for item in pending[:MAX_ITEMS]:
        verified_artifact(item)
        with tempfile.TemporaryDirectory(prefix="kwai-approved-artifact-") as temp:
            target=Path(temp)
            gh("run","download",str(item["run_id"]),
               "--repo",REPO,"-n",item["artifact_name"],"-D",str(target),
               timeout=900)
            video,actual=safe_video(target,item["relative_video"])
            if actual!=item["sha256"]:
                raise AgentBlocked("SOURCE_VIDEO_SHA256_DOES_NOT_MATCH_APPROVED_QUEUE")
            result=stage(adb,serial,video,actual)
            if not result["integrity_verified"]:
                raise AgentBlocked("ANDROID_HASH_NOT_VERIFIED")
        done[item["queue_id"]]={
            "sha256":actual,"staged_at_utc":datetime.now(timezone.utc).isoformat(),
            "published":False,
            "mode":result["stage_result"]
        }
        save_receipts(path,done)
        staged+=1
    return {"mode":"copied_to_samsung_not_published","newly_staged":staged}

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--action",choices=("once","watch","dry-run"),default="dry-run")
    parser.add_argument("--interval-seconds",type=int,default=180)
    args=parser.parse_args()
    if args.action=="watch" and not 120<=args.interval_seconds<=3600:
        print("[KWAI] WATCH_INTERVAL_MUST_BE_120_TO_3600_SECONDS",file=sys.stderr)
        return 2
    print("[KWAI] GitHub approved queue -> ADB Wi-Fi; NO AUTOMATIC KWAI PUBLICATION")
    if os.name!="nt" and args.action!="dry-run":
        print("[KWAI] WINDOWS_LOCAL_PC_REQUIRED",file=sys.stderr)
        return 2
    while True:
        try:
            result=process_once(dry_run=args.action=="dry-run")
            print(json.dumps(result,ensure_ascii=False),flush=True)
        except (AgentBlocked,BridgeBlocked,ValueError,OSError) as exc:
            why=str(exc) if isinstance(exc,(AgentBlocked,BridgeBlocked)) else type(exc).__name__
            print("[KWAI PAUSED] "+why,file=sys.stderr,flush=True)
            if args.action!="watch":
                return 2
        if args.action!="watch":
            return 0
        try:
            time.sleep(args.interval_seconds)
        except KeyboardInterrupt:
            print("[KWAI] Monitoramento encerrado pelo usuario.")
            return 0

if __name__=="__main__":
    raise SystemExit(main())
