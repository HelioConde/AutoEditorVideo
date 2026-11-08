#!/usr/bin/env python3
"""Kwai BR Android 14 Google Play feasibility probe, strictly NO login or posting."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, time
from pathlib import Path

WORKFLOW="AutoEditorVideo - Kwai Brazil Android Play Store feasibility"
POLICY=Path("config/kwai-android-playstore-policy-20261108.json")
OUT=Path("kwai-android-feasibility-results")
PACKAGE="com.kwai.video"
STORE="com.android.vending"
MARKET="market://details?id=com.kwai.video"
PNG=b"\x89PNG\r\n\x1a\n"
class KwaiProbeBlocked(ValueError):pass

def command(*args, timeout=120, strict=True):
    r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if strict and r.returncode:
        raise KwaiProbeBlocked("ADB_OR_LOCAL_EXIT_"+str(r.returncode))
    return r.stdout.strip()

def policy():
    d=json.loads(POLICY.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/kwai-android-playstore-no-login/v1"
        or d.get("platform")!="kwai_brazil_only" or d.get("android_api")!=34
        or d.get("system_image")!="google_apis_playstore"
        or d.get("cpu_arch")!="x86_64"
        or d.get("official_android_package")!=PACKAGE
        or d.get("scope")!="read_only_store_listing_and_synthetic_mp4"
        or not all(d.get(x) is True for x in (
            "check_android_and_adb","check_google_play_package",
            "open_official_market_listing","verify_synthetic_mp4_sha256",
            "save_screenshot_of_no_account_screen",
            "live_publication_requires_separate_creator_approval"))
        or any(d.get(x) is not False for x in (
            "install_kwai_apk","use_unauthorized_apk_mirrors","login_to_kwai",
            "circumvent_emulator_restrictions","upload_original_mp4",
            "publish_video","store_credentials","modify_existing_channels"))):
        raise KwaiProbeBlocked("KWAI_NO_LOGIN_POLICY_CHANGED")
    return d

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or e.get("GITHUB_REF")!="refs/heads/main"
        or e.get("GITHUB_EVENT_NAME") not in ("push","workflow_dispatch")
        or e.get("GITHUB_RUN_ATTEMPT")!="1"
        or e.get("GITHUB_WORKFLOW")!=WORKFLOW
        or e.get("KWAI_READ_ONLY_EMULATOR_TEST")!="yes"):
        raise KwaiProbeBlocked("MAIN_ONLY_ONE_SHOT_KWAI_PROBE_REQUIRED")
    if any(e.get(x) for x in (
        "KWAI_ACCESS_TOKEN","KWAI_REFRESH_TOKEN","KWAI_PASSWORD",
        "KWAI_SESSION","KWAI_COOKIE","TIKTOK_ACCESS_TOKEN",
        "YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
        "PROXY_API_KEY","PROXY_ACCOUNTS_JSON","ANDROID_APK_URL")):
        raise KwaiProbeBlocked("NO_EXTERNAL_ACCOUNT_OR_PROVIDER_SECRETS")
    policy()

def installed(package):
    if package not in (PACKAGE,STORE):
        raise KwaiProbeBlocked("UNEXPECTED_PACKAGE")
    return "package:" in command("adb","shell","pm","path",package,strict=False,timeout=45)

def synthetic_media_sha():
    local=OUT/"kwai-only-synthetic-2sec.mp4"
    command("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","lavfi","-i","color=c=navy:s=360x640:r=15",
            "-t","2","-c:v","libx264","-pix_fmt","yuv420p",
            "-movflags","+faststart",str(local),timeout=90)
    data=local.read_bytes()
    if len(data)<2000 or b"ftyp" not in data[:16]:
        raise KwaiProbeBlocked("SYNTHETIC_VIDEO_INVALID")
    h=hashlib.sha256(data).hexdigest()
    remote="/sdcard/Movies/kwai-synthetic-test-only.mp4"
    command("adb","shell","mkdir","-p","/sdcard/Movies")
    command("adb","push",str(local),remote,timeout=110)
    raw=command("adb","shell","sha256sum",remote)
    if not raw.split() or raw.split()[0].lower()!=h:
        raise KwaiProbeBlocked("SYNTHETIC_VIDEO_SHA256_MISMATCH")
    return h

def screenshot():
    r=subprocess.run(["adb","exec-out","screencap","-p"],
                     capture_output=True,timeout=45)
    if r.returncode or len(r.stdout)<4000 or not r.stdout.startswith(PNG):
        raise KwaiProbeBlocked("CLEAN_GOOGLE_PLAY_SCREENSHOT_FAILED")
    dest=OUT/"kwai-official-google-play-listing.png"
    dest.write_bytes(r.stdout)
    return dest.name

def probe():
    guard()
    OUT.mkdir(exist_ok=True)
    report={"schema":"autoeditorvideo/kwai-brazil-emulator-probe-result/v1",
       "official_package":PACKAGE,
       "official_play_url":"https://play.google.com/store/apps/details?id=com.kwai.video&gl=BR",
       "status":"started","android_booted":False,"adb_connected":False,
       "play_store_present":False,"official_market_intent_started":False,
       "kwai_app_installed":False,"kwai_app_installation_tested":False,
       "kwai_login_attempted":False,"real_upload_attempted":False,
       "real_publication_attempted":False,
       "kwai_app_publishing_compatibility":"NOT_TESTED",
       "real_publication_capability":"NOT_PROVEN"}
    report_path=OUT/"kwai-android-report.json"
    def save():
        report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",
                               encoding="utf-8")
    save()
    try:
        command("adb","wait-for-device",timeout=160)
        if "emulator-" not in command("adb","devices"):
            raise KwaiProbeBlocked("ADB_EMULATOR_NOT_AVAILABLE")
        report["adb_connected"]=True
        sdk=command("adb","shell","getprop","ro.build.version.sdk")
        boot=command("adb","shell","getprop","sys.boot_completed")
        abi=command("adb","shell","getprop","ro.product.cpu.abi")
        if sdk!="34" or boot!="1" or abi!="x86_64":
            raise KwaiProbeBlocked("ANDROID_14_OR_X86_64_NOT_READY")
        report["android_booted"]=True
        report["android_api"]=int(sdk)
        report["android_abi"]=abi
        report["play_store_present"]=installed(STORE)
        if installed(PACKAGE):
            raise KwaiProbeBlocked("KWAI_UNEXPECTEDLY_INSTALLED_IN_CLEAN_EMULATOR")
        report["synthetic_video_sha256"]=synthetic_media_sha()
        report["synthetic_video_integrity_verified"]=True
        save()
        if report["play_store_present"]:
            response=command("adb","shell","am","start","-W",
                             "-a","android.intent.action.VIEW",
                             "-d",MARKET,"-p",STORE,strict=False,timeout=60)
            report["official_market_intent_started"]=(
                "Error:" not in response and
                ("com.android.vending" in response or "Status: ok" in response))
            time.sleep(9)
        report["screenshot"]=screenshot()
        report["screenshot_saved"]=True
        if installed(PACKAGE):
            raise KwaiProbeBlocked("NO_APK_INSTALL_ALLOWED")
        report["status"]=("official_play_store_probe_completed"
                          if report["play_store_present"] else
                          "play_store_missing_inconclusive")
        save()
        print("KWAI_ANDROID_NO_ACCOUNT_PROBE_"+report["status"].upper(),flush=True)
        print("KWAI_APP_NOT_INSTALLED_NO_LOGIN_NO_VIDEO_PUBLICATION",flush=True)
    except Exception as e:
        report["status"]="failed"
        report["failure_type"]=type(e).__name__
        if isinstance(e,KwaiProbeBlocked):
            report["failure_reason"]=str(e)
        save()
        raise

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=("preflight","probe"),default="preflight")
    args=ap.parse_args()
    policy()
    if args.action=="preflight":print("KWAI_NO_LOGIN_AND_NO_PUBLICATION_PREFLIGHT_OK")
    else:probe()

if __name__=="__main__":
    main()
