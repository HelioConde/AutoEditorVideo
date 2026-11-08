#!/usr/bin/env python3
"""Reconcile exactly existing new Elefantinho ID; NEVER insert another video.

Owner-authenticated YouTube API; polls processing and made-for-kids audience;
then attaches original canonical thumbnail if needed. Original stuck ID and
every other Kids video are preserved unchanged. Records real status.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time

from kids_elefantinho_stuck_replacement_20261108 import (
    OLD_ID, CHANNEL_ID, EXPECTED_COVER_SHA, BASE,
    DESCRIPTION_SUFFIX, yt, KidsRecoverBlocked
)
from kids_static_90s_20261107 import digest

WORKFLOW="Emanuelly Kids - reconcile one already-uploaded Elefantinho ID"
NEW_ID="zl0Rw482XRw"
MANIFEST=Path("conteudos/kids-elefantinho-existing-id-reconcile-20261108.json")
RESULT=Path("kids-elefantinho-v2-only-reconcile-result.json")

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("KIDS_ELEFANTINHO_EXISTING_ID_READ_AND_COVER")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or any(e.get(k) for k in (
                "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
                "PROXY_API_KEY","PROXY_ACCOUNTS_JSON"))):
        raise KidsRecoverBlocked("RECONCILE_ONLY_EXACT_KIDS_OWNER_AUTH_REQUIRED")
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if d != {
        "schema":"autoeditorvideo/elefantinho-one-id-reconcile-only/v1",
        "original_id":OLD_ID,"new_uploaded_id":NEW_ID,
        "source_upload_run":42449321817,
        "new_original_transcoded_sha256":"8a8d81f30f5f255597db4af24d86195f2c233cb7efa8d5f8b7e76534ac0ded75",
        "channel_id":CHANNEL_ID,
        "reupload_another_video":False,
        "delete_video":False,
        "change_privacy":False,
        "modify_other_kids_videos":False,
        "require_made_for_kids":True,
        "confirm_processed":True,
        "may_attach_exact_original_thumbnail":True,
        "creator_authorized_at":"2026-11-08"
    }:
        raise KidsRecoverBlocked("EXACT_PREVIOUS_YOUTUBE_ID_RECONCILIATION_CONTRACT_CHANGED")

def persist(row):
    RESULT.write_text(json.dumps(row,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def execute():
    guard()
    api,_=yt()
    metadata=json.loads((BASE/"metadata.json").read_text(encoding="utf-8"))
    expected_desc=metadata["description"]+DESCRIPTION_SUFFIX
    if digest(BASE/"thumb.jpg")!=EXPECTED_COVER_SHA:
        raise KidsRecoverBlocked("ORIGINAL_THUMB_SHA256_CHANGED")
    status_record={"old_id":OLD_ID,"new_id":NEW_ID,
                   "new_public_processed":False,"thumbnail_acknowledged":False,
                   "old_video_deleted":False,"new_id_was_already_uploaded":True,
                   "status":"reconciliation_started"}
    for n in range(34):
        obj=api.videos().list(part="snippet,status,processingDetails,contentDetails",
                              id=NEW_ID).execute().get("items",[])
        if len(obj)!=1:raise KidsRecoverBlocked("NEW_VIDEO_ID_NOT_RETURNED_BY_KIDS_ACCOUNT")
        v=obj[0]
        sn=v.get("snippet",{})
        st=v.get("status",{})
        p=v.get("processingDetails",{})
        duration=v.get("contentDetails",{}).get("duration")
        status_record.update({
            "visibility":st.get("privacyStatus"),
            "made_for_kids":st.get("madeForKids"),
            "self_declared_made_for_kids":st.get("selfDeclaredMadeForKids"),
            "upload_status":st.get("uploadStatus"),
            "processing_status":p.get("processingStatus"),
            "duration":duration
        })
        persist(status_record)
        if (sn.get("channelId")!=CHANNEL_ID
                or sn.get("title")!=metadata["title"]
                or sn.get("description")!=expected_desc):
            raise KidsRecoverBlocked("NEW_KIDS_UPLOAD_OWNER_TITLE_OR_DESCRIPTION_MISMATCH")
        if (st.get("privacyStatus")!="public"
                or st.get("selfDeclaredMadeForKids") is not True):
            raise KidsRecoverBlocked("NEW_KIDS_VIDEO_NOT_PUBLIC_OR_NOT_MARKED_FOR_CHILDREN")
        if (st.get("uploadStatus") in ("rejected","failed","deleted")
                or p.get("processingStatus") in ("failed","terminated")):
            raise KidsRecoverBlocked("NEW_KIDS_VIDEO_PROCESSING_REJECTED")
        if (st.get("uploadStatus")=="processed"
                and p.get("processingStatus")=="succeeded"
                and duration not in (None,"","P0D","PT0S")):
            if st.get("madeForKids") is not True:
                raise KidsRecoverBlocked("NEW_VIDEO_PROCESSED_BUT_NOT_CLASSIFIED_MADE_FOR_KIDS")
            status_record["new_public_processed"]=True
            status_record["status"]="new_public_processed_made_for_kids_confirmed"
            persist(status_record)
            break
        if n<33:time.sleep(12)
    if not status_record["new_public_processed"]:
        status_record["status"]="new_youtube_processing_still_pending_no_new_upload"
        persist(status_record)
        raise KidsRecoverBlocked("NEW_REPLACEMENT_PROCESSING_STILL_PENDING")
    from googleapiclient.http import MediaFileUpload
    try:
        time.sleep(45)
        response=api.thumbnails().set(
            videoId=NEW_ID,
            media_body=MediaFileUpload(str(BASE/"thumb.jpg"),mimetype="image/jpeg")).execute()
        status_record["thumbnail_acknowledged"]=bool(response.get("items"))
    except Exception:
        status_record["thumbnail_review_required"]=True
    status_record["status"]=("public_processed_kids_thumbnail_verified"
                            if status_record["thumbnail_acknowledged"] else
                            "public_processed_kids_cover_manual_review_required")
    persist(status_record)
    print("KIDS_ELEFANTINHO_NEW_VIDEO_CONFIRMED_PUBLIC_PROCESSED_"+NEW_ID,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("preflight","reconcile"),default="preflight")
    x=p.parse_args()
    try:
        if x.action=="preflight":
            d=json.loads(MANIFEST.read_text(encoding="utf-8"))
            if d.get("new_uploaded_id")!=NEW_ID or d.get("reupload_another_video") is not False:
                raise KidsRecoverBlocked("NO_DUPLICATE_RECONCILIATION_GUARD")
            print("KIDS_ELEFANTINHO_EXISTING_ID_RECONCILE_ONLY_APPROVED")
        else:execute()
        return 0
    except Exception as e:
        name=str(e) if isinstance(e,KidsRecoverBlocked) else type(e).__name__
        print("KIDS_ELEFANTINHO_RECONCILE_BLOCKED_"+name,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
