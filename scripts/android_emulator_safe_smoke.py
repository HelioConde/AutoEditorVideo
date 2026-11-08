#!/usr/bin/env python3
"""Safe Android 14 emulator smoke test: boot, ADB, synthetic MP4, screenshot.

This script does not install TikTok/Kwai APKs, log into social accounts, call
platform APIs, upload real videos or publish anything. GitHub artifact is
a generated fixture and test report, never a recording of real user content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

WORKFLOW="AutoEditorVideo - Android 14 emulator safe smoke test"
OUT=Path("android-emulator-smoke-results")
DEVICE_VIDEO="/sdcard/Movies/autoeditorvideo-ci-test-only.mp4"
DEVICE_SHOT="/sdcard/Pictures/autoeditorvideo-ci-screenshot.png"
PNG_HEADER=b"\x89PNG\r\n\x1a\n"

class SmokeBlocked(RuntimeError):
    pass

def cmd(*argv:str,timeout:int=120)->str:
    r=subprocess.run(argv,check=True,capture_output=True,text=True,timeout=timeout)
    return r.stdout.strip()

def digest(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def parse_android_sha256(output:str)->str:
    first=output.strip().split()
    if not first or not re.fullmatch(r"[0-9a-fA-F]{64}",first[0]):
        raise SmokeBlocked("ANDROID_SHA256_COMMAND_UNEXPECTED_OUTPUT")
    return first[0].lower()

def policy()->dict:
    return json.loads(
        Path("config/android-ci-publication-feasibility.json").read_text(encoding="utf-8")
    )

def validate_policy()->None:
    d=policy()
    expected={
        "schema":"autoeditorvideo/android-emulator-safe-test/v1",
        "authorized_at":"2026-11-08",
        "android_api":34,
        "architecture":"x86_64",
        "test_mode":"safe_no_login_no_publishing",
        "sample_media":"synthetic_only_2s_360x640",
        "test_adb_video_push":True,
        "test_android_sha256":True,
        "test_home_screenshot":True,
        "install_third_party_apks":False,
        "login_to_tiktok_or_kwai":False,
        "upload_real_video":False,
        "post_any_content":False,
        "save_social_credentials":False,
        "require_creator_approval_before_live_upload":True
    }
    if d!=expected:
        raise SmokeBlocked("SAFE_ANDROID_TEST_POLICY_CHANGED")

def guard()->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("ANDROID_SMOKE_NO_PUBLICATION")!="yes"
            or e.get("ANDROID_EMULATOR_TEST_ONLY")!="true"):
        raise SmokeBlocked("ANDROID_TEST_NOT_EXACT_AUTHORIZED_GITHUB_ONE_SHOT")
    forbidden=("TIKTOK_ACCESS_TOKEN","KWAI_ACCESS_TOKEN","TIKTOK_REFRESH_TOKEN",
               "KWAI_REFRESH_TOKEN","YOUTUBE_CLIENT_JSON",
               "YOUTUBE_CHANNEL_TOKEN_JSON","PROXY_ACCOUNTS_JSON",
               "PROXY_API_KEY","ANDROID_APP_PASSWORD","ANDROID_APK_URL")
    if any(e.get(name) for name in forbidden):
        raise SmokeBlocked("PLATFORM_OR_PROVIDER_SECRETS_NOT_PERMITTED_IN_EMULATOR")
    validate_policy()

def make_fixture(path:Path)->None:
    cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-f","lavfi","-i","color=c=0x17335a:s=360x640:r=15",
        "-f","lavfi","-i","sine=frequency=440:sample_rate=44100",
        "-t","2","-c:v","libx264","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","64k","-shortest",
        "-movflags","+faststart",str(path),timeout=90)
    if not path.is_file() or path.stat().st_size<6000:
        raise SmokeBlocked("SYNTHETIC_MP4_NOT_CREATED")
    if b"ftyp" not in path.read_bytes()[:16]:
        raise SmokeBlocked("SYNTHETIC_MP4_NOT_ISO_BMFF")

def run()->None:
    guard()
    OUT.mkdir(exist_ok=True)
    report={
        "schema":"autoeditorvideo/android-emulator-safe-smoke-result/v1",
        "android_booted":False,"adb_connected":False,
        "synthetic_mp4_uploaded_to_emulator":False,"sha256_verified":False,
        "screenshot_captured":False,"platforms_logged_in":False,
        "third_party_apps_installed":False,"real_video_uploaded":False,
        "real_publication_attempted":False,
        "supports_tiktok_or_kwai_publishing":"NOT_TESTED",
        "status":"started"
    }
    target=OUT/"android-status.json"
    def save():
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                          encoding="utf-8")
    save()
    try:
        cmd("adb","wait-for-device",timeout=150)
        devices=cmd("adb","devices")
        if "emulator-" not in devices or "\tdevice" not in devices:
            raise SmokeBlocked("ANDROID_ADB_NOT_READY")
        report["adb_connected"]=True
        api=cmd("adb","shell","getprop","ro.build.version.sdk")
        booted=cmd("adb","shell","getprop","sys.boot_completed")
        if api!="34" or booted!="1":
            raise SmokeBlocked("ANDROID_14_DID_NOT_BOOT_"+api)
        report["android_booted"]=True
        report["android_api"]=int(api)
        report["android_release"]=cmd("adb","shell","getprop","ro.build.version.release")
        report["architecture"]=cmd("adb","shell","getprop","ro.product.cpu.abi")
        save()
        local=OUT/"autoeditorvideo-ci-test-only.mp4"
        make_fixture(local)
        cmd("adb","shell","mkdir","-p","/sdcard/Movies")
        cmd("adb","push",str(local),DEVICE_VIDEO,timeout=120)
        report["synthetic_mp4_uploaded_to_emulator"]=True
        expected=digest(local.read_bytes())
        actual=parse_android_sha256(cmd("adb","shell","sha256sum",DEVICE_VIDEO))
        if actual!=expected:
            raise SmokeBlocked("ANDROID_MEDIA_SHA256_MISMATCH")
        report["sha256_verified"]=True
        report["synthetic_mp4_sha256"]=expected
        save()
        cmd("adb","shell","input","keyevent","KEYCODE_HOME")
        cmd("adb","shell","mkdir","-p","/sdcard/Pictures")
        cmd("adb","shell","screencap","-p",DEVICE_SHOT)
        screenshot=OUT/"android-home.png"
        cmd("adb","pull",DEVICE_SHOT,str(screenshot))
        if not screenshot.is_file() or screenshot.stat().st_size<4000:
            raise SmokeBlocked("ANDROID_SCREENSHOT_EMPTY")
        if not screenshot.read_bytes().startswith(PNG_HEADER):
            raise SmokeBlocked("ANDROID_SCREENSHOT_INVALID_PNG")
        report["screenshot_captured"]=True
        report["screenshot_file"]="android-home.png"
        report["synthetic_video_file"]="autoeditorvideo-ci-test-only.mp4"
        report["status"]="passed"
        save()
        print("ANDROID_SAFE_SMOKE_PASSED_API_34_ADB_MP4_SHA256_SCREENSHOT",flush=True)
        print("ANDROID_NO_TIKTOK_OR_KWAI_LOGIN_NO_PUBLICATION",flush=True)
    except Exception as exc:
        report["status"]="failed"
        report["failure_type"]=type(exc).__name__
        report["failure_reason"]=(str(exc) if isinstance(exc,SmokeBlocked)
                                  else "COMMAND_OR_EMULATOR_FAILURE")
        save()
        raise

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--action",choices=("preflight","run"),default="preflight")
    args=parser.parse_args()
    validate_policy()
    if args.action=="preflight":
        print("ANDROID_SAFE_SMOKE_OFFLINE_PREFLIGHT_OK")
    else:
        run()

if __name__=="__main__":
    main()
