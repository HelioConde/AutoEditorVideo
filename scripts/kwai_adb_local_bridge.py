#!/usr/bin/env python3
"""Kwai Android bridge for a self-hosted Windows GitHub Actions runner.

No login, UI automation, video publishing, webhooks, platform APIs or ADB
credential extraction. It can inspect a locally paired Samsung and stage a
reviewed MP4 from an authorized GitHub Actions artifact into Android Movies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

EXPECTED_MODEL="SM-M236B"
KWAI_PACKAGE="com.kwai.video"
OUTPUT_DIR=Path("kwai-bridge-report")
MAX_VIDEO_BYTES=750*1024*1024
DEVICE_MEDIA_DIR="/sdcard/Movies/AutoEditorVideo"

class BridgeBlocked(RuntimeError):
    pass

def adb_exe()->str:
    found=shutil.which("adb")
    if found:
        return found
    fallbacks=[
        Path("C:/platform-tools/adb.exe"),
        Path(os.environ.get("LOCALAPPDATA","C:/Users/Public"))/"Android/Sdk/platform-tools/adb.exe",
    ]
    for path in fallbacks:
        if path.is_file():
            return str(path)
    raise BridgeBlocked("ADB_NOT_INSTALLED_ON_LOCAL_WINDOWS_RUNNER")

def exec_adb(executable:str,*args:str, timeout:int=90, strict:bool=True)->str:
    try:
        result=subprocess.run([executable,*args],check=False,timeout=timeout,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              text=True,encoding="utf-8",errors="replace")
    except (OSError,subprocess.TimeoutExpired):
        raise BridgeBlocked("LOCAL_ADB_UNAVAILABLE_OR_TIMEOUT") from None
    if strict and result.returncode!=0:
        # Android may include device serials and arbitrary strings in stderr.
        raise BridgeBlocked("LOCAL_ADB_COMMAND_FAILED")
    return result.stdout.strip()

def device_serial(adb:str)->str:
    listing=exec_adb(adb,"devices")
    parsed=[]
    for line in listing.splitlines():
        line=line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        fields=line.split()
        if len(fields)>=2:
            parsed.append((fields[0],fields[1]))
    if len(parsed)!=1 or parsed[0][1]!="device":
        raise BridgeBlocked("EXACTLY_ONE_AUTHORIZED_ADB_DEVICE_REQUIRED")
    serial=parsed[0][0]
    if (serial.startswith("emulator-") or not re.fullmatch(r"[A-Za-z0-9_.:-]{5,140}",serial)):
        raise BridgeBlocked("UNEXPECTED_OR_EMULATED_DEVICE")
    return serial

def check_phone(adb:str,serial:str)->dict:
    manufacturer=exec_adb(adb,"-s",serial,"shell","getprop","ro.product.manufacturer")
    model=exec_adb(adb,"-s",serial,"shell","getprop","ro.product.model")
    api=exec_adb(adb,"-s",serial,"shell","getprop","ro.build.version.sdk")
    if manufacturer.lower()!="samsung" or model!=EXPECTED_MODEL:
        raise BridgeBlocked("CONNECTED_ANDROID_IS_NOT_APPROVED_SAMSUNG_SM_M236B")
    try:
        sdk=int(api)
    except ValueError:
        raise BridgeBlocked("ANDROID_SDK_VERSION_INVALID") from None
    if sdk<34:
        raise BridgeBlocked("ANDROID_VERSION_14_OR_NEWER_REQUIRED")
    package=exec_adb(adb,"-s",serial,"shell","pm","path",KWAI_PACKAGE,
                     strict=False,timeout=45)
    return {
        "device_model":EXPECTED_MODEL,
        "android_api":sdk,
        "adb_authorized":True,
        "kwai_official_app_installed":package.startswith("package:"),
        "kwai_account_authenticated":"NOT_VERIFIED",
        "kwai_posting_automated":False,
    }

def safe_video(directory:Path, relative:str="")->tuple[Path,str]:
    base=directory.resolve(strict=True)
    if not base.is_dir():
        raise BridgeBlocked("SOURCE_ARTIFACT_DIRECTORY_MISSING")
    if relative:
        if "\\" in relative or ":" in relative or relative.startswith("/"):
            raise BridgeBlocked("VIDEO_RELATIVE_PATH_UNSAFE")
        components=relative.split("/")
        if any(p in ("",".","..") for p in components):
            raise BridgeBlocked("VIDEO_RELATIVE_PATH_TRAVERSAL")
        candidates=[base.joinpath(*components)]
    else:
        candidates=list(base.rglob("*.mp4"))
    if len(candidates)!=1:
        raise BridgeBlocked("EXACTLY_ONE_MP4_REQUIRED_OR_SELECT_RELATIVE_PATH")
    target=candidates[0]
    if target.is_symlink() or not target.is_file() or target.suffix.lower()!=".mp4":
        raise BridgeBlocked("SOURCE_IS_NOT_REGULAR_MP4")
    resolved=target.resolve(strict=True)
    if not resolved.is_relative_to(base):
        raise BridgeBlocked("VIDEO_ESCAPES_ARTIFACT_DIRECTORY")
    n=resolved.stat().st_size
    if not (10_000<=n<=MAX_VIDEO_BYTES):
        raise BridgeBlocked("MP4_INVALID_OR_TOO_LARGE")
    with resolved.open("rb") as stream:
        header=stream.read(32)
    if b"ftyp" not in header:
        raise BridgeBlocked("MP4_CONTAINER_HEADER_MISSING")
    sha=hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            sha.update(block)
    return resolved,sha.hexdigest()

def android_sha(adb:str,serial:str,remote:str)->str|None:
    raw=exec_adb(adb,"-s",serial,"shell","sha256sum",remote,
                 strict=False,timeout=65)
    match=re.match(r"^([a-fA-F0-9]{64})(?:\s|$)",raw)
    return match.group(1).lower() if match else None

def stage(adb:str,serial:str,file:Path,sha:str)->dict:
    remote=DEVICE_MEDIA_DIR+"/ae_"+sha[:32]+".mp4"
    existing=android_sha(adb,serial,remote)
    if existing==sha:
        action="already_staged_same_hash"
    else:
        if existing is not None:
            raise BridgeBlocked("REMOTE_VIDEO_EXISTS_WITH_DIFFERENT_CONTENT")
        exec_adb(adb,"-s",serial,"shell","mkdir","-p",DEVICE_MEDIA_DIR)
        exec_adb(adb,"-s",serial,"push",str(file),remote,timeout=900)
        final=android_sha(adb,serial,remote)
        if final!=sha:
            raise BridgeBlocked("ADB_MP4_INTEGRITY_VERIFICATION_FAILED")
        action="staged_new_video"
    exec_adb(adb,"-s",serial,"shell","am","broadcast","-a",
             "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
             "-d","file://"+remote,timeout=65)
    return {"stage_result":action,"remote_media_path":remote,
            "sha256":sha,"integrity_verified":True,
            "kwai_publish_attempted":False,
            "kwai_publish_success":False}

def write_report(report:dict)->None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR/"result.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("diagnose","stage"),required=True)
    p.add_argument("--artifact-directory",default="kwai-downloaded-artifact")
    p.add_argument("--relative-video",default="")
    args=p.parse_args(argv)
    report={"schema":"autoeditorvideo/kwai-adb-local-bridge/v1",
            "mode":args.action,"published":False,"status":"starting"}
    try:
        # The bridge never uses network login; GitHub Actions must gate source
        # artifact trust, workflow actor, QA consent and repository beforehand.
        if os.environ.get("GITHUB_ACTIONS")=="true":
            if (os.environ.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
                or os.environ.get("GITHUB_EVENT_NAME")!="workflow_dispatch"
                or os.environ.get("GITHUB_REF")!="refs/heads/main"
                or os.environ.get("GITHUB_ACTOR")!="HelioConde"):
                raise BridgeBlocked("UNEXPECTED_GITHUB_RUN_CONTEXT")
        if os.name!="nt" and os.environ.get("GITHUB_ACTIONS")=="true":
            raise BridgeBlocked("WINDOWS_SELF_HOSTED_RUNNER_REQUIRED")
        adb=adb_exe()
        serial=device_serial(adb)
        info=check_phone(adb,serial)
        report.update(info)
        if args.action=="stage":
            if not info["kwai_official_app_installed"]:
                raise BridgeBlocked("KWAI_OFFICIAL_APP_NOT_INSTALLED_ON_PHONE")
            video,sha=safe_video(Path(args.artifact_directory),args.relative_video)
            report.update(stage(adb,serial,video,sha))
            report["status"]="staged_to_android_not_published"
        else:
            report["status"]="phone_connected_awaiting_review"
        write_report(report)
        print("KWAI_LOCAL_BRIDGE_OK_"+report["status"].upper())
        print("NO_KWAI_LOGIN_NO_AUTOMATED_POST_NO_ACCOUNT_SECRETS")
        return 0
    except (BridgeBlocked,OSError,ValueError) as exc:
        report["status"]="blocked"
        report["reason"]=str(exc) if isinstance(exc,BridgeBlocked) else type(exc).__name__
        write_report(report)
        print("[KWAI BRIDGE] "+report["reason"],file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
