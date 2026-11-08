#!/usr/bin/env python3
"""ONE VIDEO ONLY: delete obsolete BR Solo Leveling via official YouTube API.

Execute once from a protected main-branch, explicitly authorized workflow,
with a dedicated user-consented OAuth token (youtube.force-ssl + readonly).
No upload, no change to any other video, and no blind deletion/retry.
Three replacement Shorts must be confirmed still public & processed, using
their original exact GitHub upload receipts and authenticated ownership.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_br_character_v2_20261108 import IDS,MANIFEST,ORIGINAL,CHANNEL_ID
from otaku_character_identity_policy import load_policy

WORKFLOW="Otaku Multicena BR - delete only verified obsolete Solo Leveling original"
OLD_ID="alHbSHUN0dA"
NEW_IDS=("K2kvO4wF7J8","yHxw_kTC6vA","OPsWY1QuinE")
SOURCE_PUBLISH_RUN=42446568286
SOURCE_RECEIPT_ARTIFACT="otaku-br-three-canonical-v2-public-youtube-receipts-20261108"
RECEIPT_PATH=ROOT/"br-original-v2-publish-receipts"/"br-three-character-v2-youtube-receipts.json"
RESULT=ROOT/"otaku-br-original-cleanup-result-20261108.json"
SCOPE="https://www.googleapis.com/auth/youtube.force-ssl"
READONLY="https://www.googleapis.com/auth/youtube.readonly"
DESCRIPTION_SUFFIX="\n\nNesta edição, as ilustrações foram refeitas para manter a aparência dos personagens consistente com a história."

class DeleteBlocked(ValueError):
    pass

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="workflow_dispatch"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("OTAKU_BR_DELETE_EXACT_OBSOLETE_ID_AUTHORIZED")!="yes"
            or e.get("OTAKU_BR_DELETE_EXPECTED_ID")!=OLD_ID
            or not e.get("YOUTUBE_BR_DELETE_TOKEN_JSON")
            or not e.get("YOUTUBE_CLIENT_JSON")):
        raise DeleteBlocked("EXPLICIT_GITHUB_MAIN_OWNER_DELETE_AUTH_REQUIRED")
    if any(e.get(k) for k in (
            "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
            "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
            "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
            "PROXY_ACCOUNTS_JSON","PROXY_API_KEY")):
        raise DeleteBlocked("ONLY_DEDICATED_BR_DELETION_OAUTH_ALLOWED")
    load_policy()
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (manifest.get("channel_id")!=CHANNEL_ID
            or manifest.get("allowed_old_video_ids_by_episode")!={
                IDS[0]:[OLD_ID],IDS[1]:[],IDS[2]:[]
            }
            or [v.get("id") for v in manifest.get("episodes",[])]!=list(IDS)):
        raise DeleteBlocked("CREATOR_ALLOWLIST_OR_EXACT_THREE_IDS_CHANGED")
    return manifest

def receipts_check()->list[dict]:
    if not RECEIPT_PATH.is_file() or RECEIPT_PATH.is_symlink():
        raise DeleteBlocked("SOURCE_GITHUB_PUBLIC_RECEIPTS_NOT_AVAILABLE")
    receipts=json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    if (not isinstance(receipts,list) or len(receipts)!=3
            or [x.get("episode_id") for x in receipts]!=list(IDS)
            or [x.get("new_youtube_id") for x in receipts]!=list(NEW_IDS)):
        raise DeleteBlocked("SOURCE_GITHUB_PUBLIC_VIDEO_IDS_CHANGED")
    for r in receipts:
        if (r.get("channel_id")!=CHANNEL_ID
                or r.get("new_public_processed") is not True
                or r.get("thumbnail_acknowledged") is not True
                or r.get("status")!="new_public_processed_cover_acknowledged"
                or r.get("old_id_allowlist")!=[]
                or not isinstance(r.get("mp4_sha256"),str)
                or len(r["mp4_sha256"])!=64):
            raise DeleteBlocked("REPLACEMENT_MP4_PUBLIC_OR_THUMB_NOT_CONFIRMED")
    if receipts[0].get("original_delete_status")!="pending_youtube_force_ssl_or_youtube_scope":
        raise DeleteBlocked("SOURCE_OLD_VIDEO_DELETE_STATUS_CHANGED")
    return receipts

def auth():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        client=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        token=json.loads(os.environ["YOUTUBE_BR_DELETE_TOKEN_JSON"])
        provider=client.get("installed") or client.get("web") or {}
        scopes=token.get("scopes",[])
        scopes=set(scopes.split()) if isinstance(scopes,str) else set(scopes)
        if (not provider.get("client_id")
                or token.get("client_id")!=provider["client_id"]
                or not token.get("refresh_token")
                or not {SCOPE,READONLY}.issubset(scopes)):
            raise DeleteBlocked("DEDICATED_OAUTH_CLIENT_OR_FORCE_SSL_SCOPE_MISMATCH")
        credentials=Credentials.from_authorized_user_info(token,scopes=[SCOPE,READONLY])
        if not credentials.valid:credentials.refresh(Request())
        api=build("youtube","v3",
                  http=AuthorizedHttp(credentials,http=httplib2.Http(timeout=90)),
                  cache_discovery=False)
        ch=api.channels().list(part="id",mine=True).execute().get("items",[])
        if len(ch)!=1 or ch[0].get("id")!=CHANNEL_ID:
            raise DeleteBlocked("OAUTH_NOT_OWNER_OF_OTAKU_MULTICENA_BR")
        print("OTAKU_BR_SAFE_DELETE_CHANNEL_OWNER_VERIFIED_"+CHANNEL_ID,flush=True)
        return api
    except DeleteBlocked:
        raise
    except Exception:
        raise DeleteBlocked("GOOGLE_DELETE_OAUTH_NOT_AUTHORIZED_OR_REFRESH_FAILED") from None

def video(api,id:str):
    r=api.videos().list(part="snippet,status,processingDetails,contentDetails",
                        id=id).execute().get("items",[])
    if len(r)>1:raise DeleteBlocked("YOUTUBE_DUPLICATE_ID_IN_API_RESPONSE")
    return r[0] if r else None

def assert_replacements(api,manifest,receipts):
    rows=manifest["episodes"]
    for row,receipt,id in zip(rows,receipts,NEW_IDS):
        v=video(api,id)
        if v is None:
            raise DeleteBlocked("REPLACEMENT_YOUTUBE_VIDEO_MISSING_"+id)
        sn=v.get("snippet",{})
        status=v.get("status",{})
        processing=v.get("processingDetails",{})
        if (sn.get("channelId")!=CHANNEL_ID
                or sn.get("title")!=row["title"]
                or sn.get("description")!=row["description"]+DESCRIPTION_SUFFIX
                or status.get("privacyStatus")!="public"
                or status.get("uploadStatus")!="processed"
                or status.get("madeForKids") is True
                or processing.get("processingStatus")!="succeeded"
                or v.get("contentDetails",{}).get("duration") in ("",None,"P0D","PT0S")):
            raise DeleteBlocked("REPLACEMENT_PUBLIC_PROCESSING_OR_OWNERSHIP_NOT_CONFIRMED_"+id)
        if receipt["new_youtube_id"]!=id:
            raise DeleteBlocked("NEW_ID_RECEIPT_CHANGED")
        print("OTAKU_BR_REPLACEMENT_PUBLIC_PROCESSED_"+id,flush=True)

def persist(result:dict):
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",
                      encoding="utf-8")

def cleanup():
    manifest=guard()
    receipts=receipts_check()
    api=auth()
    assert_replacements(api,manifest,receipts)
    prior=json.loads(ORIGINAL.read_text(encoding="utf-8"))
    expected_title=prior["episodes"][0]["title"]
    expected_description=prior["episodes"][0]["description"]
    if (prior["episodes"][0]["id"]!="5012-solo-leveling-igris"
            or manifest["episodes"][0]["original_episode_id"]!="5012-solo-leveling-igris"):
        raise DeleteBlocked("SOURCE_OLD_SOLO_LEVELING_ORIGIN_CHANGED")
    old=video(api,OLD_ID)
    state={
        "schema":"autoeditorvideo/otaku-br-obsolete-video-delete-one/v1",
        "br_channel_id":CHANNEL_ID,
        "old_video_id":OLD_ID,
        "source_publication_run":SOURCE_PUBLISH_RUN,
        "new_replacement_ids":list(NEW_IDS),
        "all_new_public_processed_and_cover_acknowledged":True,
        "old_video_delete_attempted":False,
        "old_video_delete_confirmed":False,
        "other_videos_touched":0,
        "status":"old_video_not_yet_checked"
    }
    if old is None:
        state["status"]="old_video_already_absent"
        state["old_video_delete_confirmed"]=True
        persist(state)
        print("OTAKU_BR_SAFE_DELETE_ORIGINAL_ALREADY_ABSENT_"+OLD_ID,flush=True)
        return
    snippet=old.get("snippet",{})
    if (old.get("id")!=OLD_ID
            or snippet.get("channelId")!=CHANNEL_ID
            or snippet.get("title")!=expected_title
            or snippet.get("description")!=expected_description):
        state["status"]="original_owner_title_description_mismatch_stop"
        persist(state)
        raise DeleteBlocked("ORIGINAL_VIDEO_NOT_EXACT_OWNED_SOLO_LEVELING_OLD_VERSION")
    state["status"]="verified_old_exact_owner_and_metadata_delete_started"
    state["old_video_delete_attempted"]=True
    persist(state)
    # DESTRUCTIVE operation: exactly ONE allowlisted ID, exactly ONE call, no retries.
    try:
        api.videos().delete(id=OLD_ID).execute(num_retries=0)
    except Exception:
        state["status"]="delete_api_response_uncertain_do_not_retry"
        persist(state)
        raise DeleteBlocked("DELETE_API_UNCERTAIN_DO_NOT_RETRY_CALL") from None
    state["status"]="delete_api_success_verification_pending"
    persist(state)
    for delay in (2,6,10):
        time.sleep(delay)
        if video(api,OLD_ID) is None:
            state["status"]="deleted_and_verified_absent"
            state["old_video_delete_confirmed"]=True
            persist(state)
            print("OTAKU_BR_SAFE_DELETE_CONFIRMED_ONLY_"+OLD_ID,flush=True)
            return
    state["status"]="delete_api_success_but_youtube_list_still_returns_old"
    persist(state)
    print("OTAKU_BR_DELETE_SUCCESS_UNCONFIRMED_EVENTUAL_CONSISTENCY_NO_RETRY_"+OLD_ID,flush=True)

def main():
    try:
        cleanup()
        return 0
    except DeleteBlocked as e:
        print("OTAKU_BR_SAFE_DELETE_BLOCKED_"+str(e),file=sys.stderr)
        return 2
    except Exception as e:
        print("OTAKU_BR_SAFE_DELETE_BLOCKED_"+type(e).__name__,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
