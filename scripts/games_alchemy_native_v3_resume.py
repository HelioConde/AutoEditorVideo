#!/usr/bin/env python3
"""Recover only missing native V3 private Shorts after ambiguous insert responses.

The first V3 upload for each channel was ACCEPTED by YouTube, although the
caller lost its acknowledgement. Never re-upload existing V3 videos.
Only exact reserved V3 episodes, channel-scoped OAuth, pinned verified media.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time
from googleapiclient.errors import HttpError

from production_reservations import assert_reserved
from games_alchemy_ai_upload import get_youtube, confirm_private, set_thumbnail
from games_alchemy_native_v3_upload import (
    SOURCE, OWNER, RUN_ID, EXPECTED, verified_jobs, recent_private_v3,
    insert_private, sha
)
from youtube_channel_registry import KNOWN_IDS, get_channel

REPO="HelioConde/AutoEditorVideo"
WORKFLOW="Gamer + Alchemy - selectively resume four missing native V3 private Shorts"
ORIGINAL_UPLOAD_RUN="42063131990"
RECONCILIATION_RUN="42063706481"
ALLOWED=["games","alchemy"]
WAIT_THUMB_SECONDS=75

class ResumeBlocked(ValueError):
    pass

def preflight(channel:str)->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!=REPO or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW):
        raise ResumeBlocked("ONE_SHOT_MAIN_RECOVERY_ONLY")
    if (e.get("V3_RECOVERY_CREATOR_APPROVED")!="true" or
        e.get("SOURCE_NATIVE_RENDER_RUN_ID")!=RUN_ID or
        e.get("ORIGINAL_FAILED_UPLOAD_RUN")!=ORIGINAL_UPLOAD_RUN or
        e.get("READ_ONLY_AUDIT_RUN")!=RECONCILIATION_RUN):
        raise ResumeBlocked("PINNED_SOURCE_RUN_APPROVAL_REQUIRED")
    if not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        raise ResumeBlocked("OAUTH_SECRET_MISSING")
    cfg=get_channel(channel)
    if (cfg.get("youtube_channel_id")!=KNOWN_IDS[channel] or
        cfg.get("youtube_environment")!="youtube-private-upload" or
        cfg.get("oauth_token_secret_name")!=("YOUTUBE_GAMES_TOKEN_JSON" if channel=="games"
                                          else "YOUTUBE_ALCHEMY_TOKEN_JSON")):
        raise ResumeBlocked("CHANNEL_OR_ENVIRONMENT_MISMATCH")
    if not SOURCE.is_dir():
        raise ResumeBlocked("SOURCE_REVISED_V3_ARTIFACT_MISSING")
    if (SOURCE/(channel+"-v3-recovered-receipts.json")).exists():
        raise ResumeBlocked("RECOVERY_ALREADY_RUN_NO_REPLAY")

def original_audit(channel:str)->dict:
    path=Path("native-v3-readonly-audit")/(channel+".json")
    if not path.is_file():
        raise ResumeBlocked("READONLY_AUDIT_ARTIFACT_MISSING")
    audit=json.loads(path.read_text(encoding="utf-8"))
    if (audit.get("channel")!=channel or
        audit.get("channel_id")!=KNOWN_IDS[channel] or
        audit.get("no_video_insert_performed") is not True or
        audit.get("total_expected")!=3 or
        audit.get("found")!=1):
        raise ResumeBlocked("READONLY_AUDIT_INCONSISTENT")
    rows=audit.get("episodes",[])
    if [r.get("episode") for r in rows]!=EXPECTED[channel]:
        raise ResumeBlocked("UNEXPECTED_AUDIT_ORDER")
    if (len(rows[0].get("matching_v3_private_youtube_ids",[]))!=1 or
        any(r.get("matching_v3_private_youtube_ids") for r in rows[1:])):
        raise ResumeBlocked("PREVIOUS_UPLOADS_COUNT_CHANGED")
    return audit

def _write(path:Path,receipts:list[dict])->None:
    path.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def _find_twice(youtube,channel:str,title:str, *, pause:bool=True)->list[str]:
    ids=recent_private_v3(youtube,channel,title)
    if len(ids)>1:
        raise ResumeBlocked("MULTIPLE_MATCHING_REVISIONS_DUPLICATE_RISK")
    if ids or not pause:
        return ids
    # Detect eventual consistency of prior ambiguous uploads before adding new one.
    time.sleep(10)
    ids=recent_private_v3(youtube,channel,title)
    if len(ids)>1:
        raise ResumeBlocked("MULTIPLE_MATCHING_REVISIONS_DUPLICATE_RISK")
    return ids

def _reason(exc:Exception)->str:
    if isinstance(exc,HttpError):
        code=getattr(exc.resp,"status",0)
        kind="unknown"
        try:
            raw=json.loads(exc.content.decode("utf-8",errors="replace"))
            kind=str((raw.get("error",{}).get("errors") or [{}])[0].get("reason","unknown"))
        except Exception:
            pass
        kind="".join(x for x in kind if x.isalnum() or x in "-_")[:60]
        return f"YOUTUBE_HTTP_{code}_{kind}"
    return type(exc).__name__

def _confirm_and_set_cover(youtube,channel:str,job:dict,video_id:str,
                           receipts:list[dict],path:Path,*,new:bool)->None:
    if not confirm_private(youtube,video_id,KNOWN_IDS[channel]):
        raise ResumeBlocked("PRIVATE_DESTINATION_NOT_VERIFIED_"+job["id"])
    record={
      "id":job["id"],"channel":channel,
      "video_id":video_id,"visibility":"private",
      "confirmed_private":True,"reused_existing_private_v3":not new,
      "cover_sha256":sha(job["cover"]),
      "source_sha256":sha(job["video"]),
      "thumbnail_api_acknowledged":False,
      "thumbnail_studio_visible":"not_checked"
    }
    receipts.append(record)
    _write(path,receipts)
    if new:
        time.sleep(WAIT_THUMB_SECONDS)
    # Safe to repeat thumbnail.set on existing video: never videos.insert.
    record["thumbnail_api_acknowledged"]=set_thumbnail(youtube,video_id,job["cover"])
    record["thumbnail_after_new_upload_wait_seconds"]=WAIT_THUMB_SECONDS if new else 0
    _write(path,receipts)
    print("V3_RECOVERED_PRIVATE_"+job["id"]+"_"+video_id,flush=True)
    if not record["thumbnail_api_acknowledged"]:
        raise ResumeBlocked("THUMB_API_NOT_ACKNOWLEDGED_NO_VIDEO_REUPLOAD_"+job["id"])

def run(channel:str)->None:
    preflight(channel)
    audit=original_audit(channel)
    jobs=verified_jobs(channel)
    youtube=get_youtube(channel,dict(os.environ))
    saved=SOURCE/(channel+"-v3-recovered-receipts.json")
    receipts=[]
    # Source may have changed since the read-only audit. Never assume first ID.
    for i,job in enumerate(jobs):
        seen=_find_twice(youtube,channel,job["meta"]["title"])
        if i==0:
            expected=audit["episodes"][0]["matching_v3_private_youtube_ids"][0]
            if seen!=[expected]:
                raise ResumeBlocked("PREVIOUSLY_ACCEPTED_FIRST_VIDEO_NOT_FOUND_OR_CHANGED")
            _confirm_and_set_cover(youtube,channel,job,expected,receipts,saved,new=False)
            continue
        if seen:
            _confirm_and_set_cover(youtube,channel,job,seen[0],receipts,saved,new=False)
            continue
        try:
            video_id=insert_private(youtube,job)
        except Exception as exc:
            # An API transport failure can happen AFTER YouTube accepted the
            # video. Never resend without reconciling the owning channel.
            reason=_reason(exc)
            print("V3_UPLOAD_RESPONSE_UNCERTAIN_"+job["id"]+"_"+reason,flush=True)
            time.sleep(20)
            recovered=_find_twice(youtube,channel,job["meta"]["title"])
            if len(recovered)!=1:
                raise ResumeBlocked("AMBIGUOUS_UPLOAD_NO_RETRY_"+reason+"_"+job["id"]) from None
            video_id=recovered[0]
            _confirm_and_set_cover(youtube,channel,job,video_id,receipts,saved,new=False)
            continue
        _confirm_and_set_cover(youtube,channel,job,video_id,receipts,saved,new=True)
    if len(receipts)!=3 or len({r["video_id"] for r in receipts})!=3:
        raise ResumeBlocked("THREE_UNIQUE_PRIVATE_V3_VIDEOS_NOT_CONFIRMED")
    print("ALL_THREE_NATIVE_V3_PRIVATE_SHORTS_CONFIRMED_"+channel,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=ALLOWED,required=True)
    args=p.parse_args()
    try:
        run(args.channel)
        return 0
    except Exception as e:
        reason=str(e) if isinstance(e,ResumeBlocked) else type(e).__name__
        print("V3_SELECTIVE_RECOVERY_BLOCKED_"+reason,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
