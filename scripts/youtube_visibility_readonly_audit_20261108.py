#!/usr/bin/env python3
"""Read-only owner-authenticated verification of YouTube visibility for 10 known IDs.

No uploads, updates, deletes, OAuth values, tokens or video contents are logged.
Safely compare public/private, upload processing and audience against originals.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
from youtube_channel_registry import KNOWN_IDS
from youtube_new_channels_oauth import validate_token_fields
from kids_static_90s_upload_20261107 import configure_resumable_transport

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports"
REFERENCE={
 "games":{
  "game-104-terraria-primeira-noite":"HW6fvYkYKlc",
  "game-105-stardew-estacoes":"mHW5MiWY71A",
  "game-106-celeste-dificuldade":"8yrTR6qQVg4"},
 "kids":{
  "kids-104-abelhinha-e-as-cores":"qJXNIUjkVrI",
  "kids-105-tartaruguinha-e-a-chuva":"bHpcB2z6nUc",
  "kids-106-estrelinhas-contam":"42Woqr9-ONw"},
 "alchemy":{
  "alchemy-104-automacao-gatilhos":"Nn8sOSw-_V8",
  "alchemy-105-agentes-supervisao":"Wu7RBUWDOb8",
  "alchemy-106-ia-checagem-fontes":"HHoIpKGTb-0",
  "alchemy-107-automacao-publicou-duplicado":"i-lzZrX_15w"}
}

def main()->int:
    channel=os.environ.get("AUDIT_CHANNEL")
    if (channel not in REFERENCE
        or os.environ.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
        or os.environ.get("GITHUB_REF")!="refs/heads/main"
        or os.environ.get("GITHUB_RUN_ATTEMPT")!="1"
        or os.environ.get("GITHUB_EVENT_NAME")!="push"
        or os.environ.get("GITHUB_WORKFLOW")!="AutoEditorVideo - read-only public status audit 20261108"):
        print("YOUTUBE_VISIBILITY_AUDIT_BLOCKED_ENVIRONMENT")
        return 2
    if not os.environ.get("YOUTUBE_CLIENT_JSON") or not os.environ.get("YOUTUBE_CHANNEL_TOKEN_JSON"):
        print("YOUTUBE_VISIBILITY_AUDIT_BLOCKED_MISSING_AUTHORIZATION")
        return 2

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    client=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
    token=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
    validate_token_fields(client,token)
    scopes=["https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload"]
    credentials=Credentials.from_authorized_user_info(token,scopes=scopes)
    if not credentials.valid:
        credentials.refresh(Request())
    transport=configure_resumable_transport(httplib2.Http(timeout=180))
    api=build("youtube","v3",http=AuthorizedHttp(credentials,http=transport),cache_discovery=False)
    owner=api.channels().list(part="id",mine=True).execute().get("items",[])
    if len(owner)!=1 or owner[0].get("id")!=KNOWN_IDS[channel]:
        print("YOUTUBE_VISIBILITY_AUDIT_BLOCKED_OWNER_MISMATCH")
        return 2

    manifest=json.loads((ROOT/"conteudos/lote-15-canais-20261108.json").read_text(encoding="utf-8"))
    originals={e["id"]:e for e in manifest["episodes"] if e["channel"]==channel}
    if channel=="alchemy":
        pilot=json.loads((ROOT/"conteudos/alchemy-publico-direto-20261108.json").read_text(encoding="utf-8"))
        originals.update({e["id"]:e for e in pilot["episodes"]})
    known=REFERENCE[channel]
    response=api.videos().list(part="snippet,status,processingDetails",id=",".join(known.values())).execute()
    byid={x["id"]:x for x in response.get("items",[])}
    rows=[]
    for episode_id,video_id in known.items():
        doc=byid.get(video_id)
        if not doc:
            row={"episode_id":episode_id,"youtube_id":video_id,"found":False,
                "visibility":"unknown","public_verified":False}
        else:
            snippet=doc.get("snippet",{})
            status=doc.get("status",{})
            expected=originals[episode_id]
            row={
                "episode_id":episode_id,"youtube_id":video_id,"found":True,
                "exact_owner":snippet.get("channelId")==KNOWN_IDS[channel],
                "title_exact":snippet.get("title")==expected["title"],
                "description_exact":snippet.get("description")==expected["description"],
                "visibility":status.get("privacyStatus"),
                "public_verified":status.get("privacyStatus")=="public" and snippet.get("channelId")==KNOWN_IDS[channel],
                "upload_status":status.get("uploadStatus"),
                "made_for_kids":status.get("madeForKids","field_absent"),
                "self_declared_made_for_kids":status.get("selfDeclaredMadeForKids","field_absent"),
                "processing":doc.get("processingDetails",{}).get("processingStatus","field_absent")
            }
        rows.append(row)
        print("YOUTUBE_VERIFIED_VIDEO_STATUS_"+channel+"_"+episode_id+"_"+row["visibility"]+
            ("_PUBLIC" if row.get("public_verified") else "_NOT_PUBLIC"),flush=True)
    result={"schema":"autoeditorvideo/read-only-visibility-20261108/v1",
            "channel":channel,"channel_id":KNOWN_IDS[channel],
            "video_count":len(rows),
            "verified_public_count":sum(x.get("public_verified",False) for x in rows),
            "read_only":True,"items":rows}
    OUT.mkdir(exist_ok=True)
    (OUT/("visibility-audit-20261108-"+channel+".json")).write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("YOUTUBE_VISIBILITY_AUDIT_COMPLETE_"+channel+"_"+str(result["verified_public_count"])+"_PUBLIC",flush=True)
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("YOUTUBE_VISIBILITY_AUDIT_BLOCKED_"+type(exc).__name__,file=sys.stderr)
        raise SystemExit(2)
