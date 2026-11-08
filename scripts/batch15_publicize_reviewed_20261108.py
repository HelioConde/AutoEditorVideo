#!/usr/bin/env python3
"""Publicize only already uploaded, inspected batch15 Shorts by real YouTube ID.

NEVER uploads/reuploads video, creates drafts, deletes media, changes another video
or assumes a successful API write without read-only re-verification.
A missing edit scope means reauthorization is needed; NEVER treat youtube.upload
as permission for videos.update. Kept to three channel-specific video IDs.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_httplib2 import AuthorizedHttp
import httplib2
from youtube_new_channels_oauth import validate_token_fields
from youtube_channel_registry import KNOWN_IDS

ROOT=Path(__file__).resolve().parents[1]
APPROVAL=ROOT/"conteudos"/"lote-15-public-approval-20261108.json"
MANIFEST=ROOT/"conteudos"/"lote-15-canais-20261108.json"
SRC_RUN=42481839933
SRC_SHA="49bdeaf75201ce2bc363836b4ac9ee4dbc19f0b6"
WORKFLOW="AutoEditorVideo - publish batch15 reviewed videos publicly"
EDIT_SCOPES={
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtubepartner"
}
CHANNELS=("games","kids","alchemy")
IDS={
 "games":("game-104-terraria-primeira-noite","game-105-stardew-estacoes","game-106-celeste-dificuldade"),
 "kids":("kids-104-abelhinha-e-as-cores","kids-105-tartaruguinha-e-a-chuva","kids-106-estrelinhas-contam"),
 "alchemy":("alchemy-104-automacao-gatilhos","alchemy-105-agentes-supervisao","alchemy-106-ia-checagem-fontes"),
}

class PublishBlocked(ValueError):
    pass

def read_json(p:Path)->dict|list:
    return json.loads(p.read_text(encoding="utf-8"))

def guard(channel:str)->tuple[list[dict],Path]:
    if channel not in CHANNELS:
        raise PublishBlocked("CHANNEL_NOT_VISUALLY_REVIEWED_OR_NO_COMPLETE_3_VIDEO_ARTIFACT")
    a=read_json(APPROVAL)
    if (a.get("schema")!="autoeditorvideo/batch15-reviewed-public-20261108/v1"
        or a.get("source_run_id")!=SRC_RUN
        or a.get("source_sha")!=SRC_SHA
        or a.get("creator_publication_authorized") is not True
        or a.get("reviewed_channels")!=list(CHANNELS)
        or a.get("original_videos_untouched") is not True
        or a.get("no_blind_reupload") is not True
        or a.get("review_scope")!="24 original static storyboard scenes visually checked per channel"
        or a.get("kids_made_for_kids") is not True):
        raise PublishBlocked("PUBLIC_APPROVAL_OR_VISUAL_REVIEW_MISSING")
    d=read_json(MANIFEST)
    if d.get("production_owner")!="lote15_novos_20261108":
        raise PublishBlocked("MANIFEST_OWNER_MISMATCH")
    rows=[e for e in d["episodes"] if e.get("channel")==channel]
    if tuple(e["id"] for e in rows)!=IDS[channel]:
        raise PublishBlocked("APPROVED_EPISODE_IDS_CHANGED")
    if any(e.get("channel_id")!=KNOWN_IDS[channel] for e in rows):
        raise PublishBlocked("CHANNEL_ID_MISMATCH")
    receipt=ROOT/"cloud-lote-15-canais-20261108"/channel/"youtube-private-receipts.json"
    if not receipt.is_file():
        raise PublishBlocked("NO_PRIVATE_UPLOAD_RECEIPTS_DO_NOT_INSERT_NEW_VIDEOS")
    records=read_json(receipt)
    if not isinstance(records,list) or len(records)!=3:
        raise PublishBlocked("THREE_PRIVATE_RECEIPTS_REQUIRED")
    for e,r in zip(rows,records):
        if (r.get("episode_id")!=e["id"] or r.get("channel")!=channel
            or r.get("channel_id")!=KNOWN_IDS[channel]
            or r.get("made_for_kids") is not (channel=="kids")
            or not isinstance(r.get("video_sha256"),str)
            or not re.fullmatch("[a-f0-9]{64}",r["video_sha256"])
            or r.get("confirmed_private") is not True
            or r.get("upload_state")!="private_verified"
            or not re.fullmatch(r"[A-Za-z0-9_-]{11}",r.get("youtube_id") or "")):
            raise PublishBlocked("UNCERTAIN_OR_WRONG_PRIVATE_UPLOAD_RECEIPT_"+e["id"])
    if len({x["youtube_id"] for x in records})!=3:
        raise PublishBlocked("DUPLICATE_YOUTUBE_IDS")
    return rows,receipt

def github_guard(channel:str)->None:
    v=os.environ
    if (v.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or v.get("GITHUB_REF")!="refs/heads/main"
        or v.get("GITHUB_RUN_ATTEMPT")!="1"
        or v.get("BATCH15_PUBLIC_CHANNEL")!=channel
        or v.get("BATCH15_PUBLIC_AUTHORIZED")!="yes"):
        raise PublishBlocked("WRONG_GITHUB_ONE_SHOT_PUBLIC_WORKFLOW")
    event=read_json(Path(v["GITHUB_EVENT_PATH"]))
    if v.get("GITHUB_EVENT_NAME")=="workflow_dispatch":
        if (v.get("GITHUB_WORKFLOW")!="AutoEditorVideo - publish nine existing Shorts after new OAuth"
            or v.get("BATCH15_MANUAL_PUBLIC_CONFIRM")!="PUBLICAR-9-SEM-DUPLICAR"
            or event.get("inputs",{}).get("confirmar")!="PUBLICAR-9-SEM-DUPLICAR"):
            raise PublishBlocked("MANUAL_DISPATCH_CONFIRMATION_MISSING")
        return
    if v.get("GITHUB_EVENT_NAME")!="workflow_run" or v.get("GITHUB_WORKFLOW")!=WORKFLOW:
        raise PublishBlocked("WRONG_SOURCE_WORKFLOW")
    src=event.get("workflow_run",{})
    if (src.get("id")!=SRC_RUN or src.get("head_sha")!=SRC_SHA
        or src.get("head_branch")!="main"
        or src.get("name")!="AutoEditorVideo - 15 new Shorts BR EN Gamer Kids Alchemy private-first"
        or src.get("status")!="completed"
        or src.get("conclusion") not in ("success","failure")):
        raise PublishBlocked("UNRELATED_SOURCE_RUN_BLOCKED")

def api_for(channel:str):
    raw_client=os.environ.get("YOUTUBE_CLIENT_JSON")
    raw_token=os.environ.get("YOUTUBE_CHANNEL_TOKEN_JSON")
    if not raw_client or not raw_token:
        raise PublishBlocked("MISSING_CHANNEL_OAUTH_SECRET")
    client=json.loads(raw_client)
    token=json.loads(raw_token)
    validate_token_fields(client,token)
    scopes=token.get("scopes",[])
    if isinstance(scopes,str):
        scopes=set(scopes.split())
    else:
        scopes=set(scopes)
    # Authorizing YouTube uploads does not permit privacy updates.
    if not (scopes & EDIT_SCOPES):
        raise PublishBlocked("OAUTH_MISSING_YOUTUBE_EDIT_SCOPE_REAUTHORIZE_CHANNEL_NO_REUPLOAD")
    creds=Credentials.from_authorized_user_info(token,scopes=sorted(scopes))
    if not creds.valid:
        creds.refresh(Request())
    granted=getattr(creds,"granted_scopes",None)
    if granted is not None and not (set(granted)&EDIT_SCOPES):
        raise PublishBlocked("GOOGLE_DID_NOT_GRANT_YOUTUBE_EDIT_SCOPE")
    api=build("youtube","v3",http=AuthorizedHttp(creds,http=httplib2.Http(timeout=180)),cache_discovery=False)
    accounts=api.channels().list(part="id",mine=True).execute().get("items",[])
    if len(accounts)!=1 or accounts[0].get("id")!=KNOWN_IDS[channel]:
        raise PublishBlocked("OAUTH_LOGGED_IN_TO_WRONG_CHANNEL")
    return api

def inspect(api,video_id:str,e:dict,channel:str):
    data=api.videos().list(part="snippet,status,processingDetails,contentDetails",id=video_id).execute()
    vids=data.get("items",[])
    if len(vids)!=1:
        raise PublishBlocked("VIDEO_ID_NOT_FOUND_"+video_id)
    v=vids[0]
    snippet=v.get("snippet",{})
    st=v.get("status",{})
    if (snippet.get("channelId")!=KNOWN_IDS[channel]
        or snippet.get("title")!=e.get("title")
        or snippet.get("description")!=e.get("description")
        or st.get("madeForKids") is not (channel=="kids")
        or st.get("selfDeclaredMadeForKids") is not (channel=="kids")):
        raise PublishBlocked("WRONG_OWNER_TITLE_DESCRIPTION_OR_AUDIENCE_"+video_id)
    if st.get("privacyStatus") not in ("private","public"):
        raise PublishBlocked("UNEXPECTED_VIDEO_VISIBILITY_"+video_id)
    if st.get("uploadStatus")!="processed":
        raise PublishBlocked("YOUTUBE_VIDEO_NOT_PROCESSED_"+video_id)
    p=v.get("processingDetails",{}).get("processingStatus")
    if p not in (None,"succeeded"):
        raise PublishBlocked("YOUTUBE_PROCESSING_NOT_DONE_"+video_id)
    return v

def status_body(v:dict,channel:str)->dict:
    s=v["status"]
    body={
        "privacyStatus":"public",
        "selfDeclaredMadeForKids":channel=="kids",
        "containsSyntheticMedia":True
    }
    # videos.update(part=status) replaces mutable status properties.
    for key in ("embeddable","license","publicStatsViewable"):
        if key in s:
            body[key]=s[key]
    if s.get("publishAt"):
        raise PublishBlocked("SCHEDULED_VIDEO_DO_NOT_OVERRIDE")
    return body

def save(p:Path,records:list)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def publish(channel:str)->None:
    rows,p=guard(channel)
    github_guard(channel)
    receipts=read_json(p)
    api=api_for(channel)
    output=p.parent/"public-transition-receipts.json"
    records=[]
    for ep,rec in zip(rows,receipts):
        vid=rec["youtube_id"]
        try:
            original=inspect(api,vid,ep,channel)
        except PublishBlocked as err:
            # Some Shorts can remain in YouTube's processing queue even after
            # their uploads have succeeded. Record the pending state and keep
            # handling the other verified episodes. Never modify pending media.
            if str(err).startswith(("YOUTUBE_VIDEO_NOT_PROCESSED_",
                                    "YOUTUBE_PROCESSING_NOT_DONE_")):
                records.append({"channel":channel,"episode_id":ep["id"],
                    "youtube_id":vid,"channel_id":KNOWN_IDS[channel],
                    "expected_made_for_kids":channel=="kids",
                    "privacy_before":"not_checked_until_processing_done",
                    "public_verified":False,
                    "transition_state":"youtube_processing_pending_no_mutation"})
                save(output,records)
                print("BATCH15_PROCESSING_PENDING_"+channel+"_"+ep["id"],flush=True)
                continue
            raise
        stat=original["status"]
        item={"channel":channel,"episode_id":ep["id"],"youtube_id":vid,
              "channel_id":KNOWN_IDS[channel],"expected_made_for_kids":channel=="kids",
              "privacy_before":stat["privacyStatus"],"public_verified":False,
              "transition_state":"checking"}
        records.append(item)
        save(output,records)
        if stat["privacyStatus"]=="private":
            try:
                api.videos().update(part="status",
                    body={"id":vid,"status":status_body(original,channel)}).execute()
            except Exception:
                # A failed connection may mean update succeeded; inspect only,
                # never retry the mutation until source video status is verified.
                after=inspect(api,vid,ep,channel)
                if after["status"]["privacyStatus"]!="public":
                    item["transition_state"]="update_failed_manual_review_no_retry"
                    save(output,records)
                    raise PublishBlocked("PUBLIC_UPDATE_FAILED_NO_RETRY_"+vid) from None
        result=inspect(api,vid,ep,channel)
        if result["status"]["privacyStatus"]!="public":
            raise PublishBlocked("YOUTUBE_DID_NOT_CONFIRM_PUBLIC_"+vid)
        item["public_verified"]=True
        item["transition_state"]="public_verified"
        save(output,records)
        print("BATCH15_PUBLIC_CONFIRMED_"+channel+"_"+ep["id"]+"_"+vid,flush=True)
    if len(records)!=3 or not all(x["public_verified"] for x in records):
        raise PublishBlocked("CHANNEL_NOT_ALL_PUBLIC")
    print("BATCH15_PUBLIC_THREE_VERIFIED_"+channel,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=CHANNELS,required=True)
    p.add_argument("--action",choices=("preflight","publish"),default="preflight")
    args=p.parse_args()
    try:
        if args.action=="preflight":
            # The upload results do not exist until source run completes.
            a=read_json(APPROVAL)
            assert a["source_run_id"]==SRC_RUN
            print("BATCH15_PUBLIC_PREFLIGHT_OK_"+args.channel)
        else:
            publish(args.channel)
        return 0
    except Exception as ex:
        msg=str(ex) if isinstance(ex,PublishBlocked) else type(ex).__name__
        print("BATCH15_PUBLIC_BLOCKED_"+msg,file=sys.stderr)
        return 2
if __name__=="__main__":
    raise SystemExit(main())
