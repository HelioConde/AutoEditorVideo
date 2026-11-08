#!/usr/bin/env python3
"""Recover ONE children-directed original whose YouTube processing stayed at P0D.

Reuse exactly previously rendered original 110s MP4, SHA256-validate it,
re-encode H.264/AAC faststart with a fresh muxer, then upload a NEW distinct
revision via official YouTube API as public + madeForKids. Confirm processed.
Never touch Kids' two successful Shorts or the Fofinhos serialized animation.
Do not delete the original ID (separate privileged consent required).
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from kids_static_90s_20261107 import probe,digest,CHANNEL_ID
from kids_static_90s_upload_20261107 import configure_resumable_transport
from youtube_new_channels_oauth import validate_token_fields
from youtube_public_tags import public_tags

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"cloud-kids-static-20261107"
BASE=SRC/"kids-101-elefantinho-agua-escondida"
TARGET=ROOT/"kids-elefantinho-reencoded-replacement-20261108"
MANIFEST=ROOT/"conteudos/kids-elefantinho-reencoded-replacement-launch-20261108.json"
WORKFLOW="Emanuelly Kids - recover stuck Elefantinho public processed replacement"
OLD_ID="d7hjFP6Ky6w"
EXPECTED_SOURCE_SHA="a886f63c89b7def376e8d08e4e9b6d899670a99c277ecd8c30554592c2d4661f"
EXPECTED_COVER_SHA="7ac96978c4c858bf33e1a52a40b6e785ce62956a8acd63080c04e0a67be04880"
IDS_ALLOWLIST={"ax0ude5BUhE","It-7R1o9k7Q"}
DESCRIPTION_SUFFIX="\n\nVersão revisada com codificação de vídeo corrigida. A história e as ilustrações originais foram preservadas."
class KidsRecoverBlocked(ValueError):pass

def source()->dict:
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if d != {
        "schema":"autoeditorvideo/kids-elefantinho-stuck-reencode-one/v1",
        "source_render_run_id":42393346725,
        "source_artifact":"emanuelly-kids-static-three-mp4-20261107",
        "original_youtube_id":OLD_ID,
        "target_channel_id":CHANNEL_ID,
        "output_visibility":"public",
        "made_for_kids":True,
        "reencode_h264_aac_faststart":True,
        "reupload_only_one_video":True,
        "avoid_duplicate_by_new_version_description":True,
        "keep_original_until_new_processed":True,
        "untouched_successful_other_kids_video_ids":sorted(IDS_ALLOWLIST),
        "fofinhos_series_untouched":True,
        "no_image_generation":True,
        "creator_authorized_at":"2026-11-08"
    }:raise KidsRecoverBlocked("SOURCE_MANIFEST_OR_CREATOR_AUTH_CHANGED")
    meta=json.loads((BASE/"metadata.json").read_text(encoding="utf-8"))
    qa=json.loads((BASE/"qa.json").read_text(encoding="utf-8"))
    summary=json.loads((SRC/"summary.json").read_text(encoding="utf-8"))
    if (summary.get("schema")!="autoeditorvideo/kids-static-90s-batch/v1"
            or summary.get("target_channel")!=CHANNEL_ID
            or summary["videos"][0]["id"]!="kids-101-elefantinho-agua-escondida"
            or summary["videos"][0].get("mp4_sha256")!=EXPECTED_SOURCE_SHA
            or qa.get("automated_technical_qa")!="passed"
            or qa.get("mp4_sha256")!=EXPECTED_SOURCE_SHA
            or qa.get("cover_sha256")!=EXPECTED_COVER_SHA
            or meta.get("channel_id")!=CHANNEL_ID
            or meta.get("selfDeclaredMadeForKids") is not True
            or meta.get("containsSyntheticMedia") is not True
            or meta.get("mp4_sha256")!=EXPECTED_SOURCE_SHA
            or not (BASE/"final.mp4").is_file()
            or not (BASE/"thumb.jpg").is_file()
            or digest(BASE/"final.mp4")!=EXPECTED_SOURCE_SHA
            or digest(BASE/"thumb.jpg")!=EXPECTED_COVER_SHA):
        raise KidsRecoverBlocked("SOURCE_ORIGINAL_MEDIA_NOT_SHA_VERIFIED")
    return meta

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("KIDS_ELEFANTINHO_REPLACE_APPROVED")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or any(e.get(k) for k in (
                "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
                "PROXY_API_KEY","PROXY_ACCOUNTS_JSON"))):
        raise KidsRecoverBlocked("EXACT_ONE_KIDS_REPLACEMENT_MAIN_OAUTH_REQUIRED")

def reencode():
    meta=source()
    if TARGET.exists():
        raise KidsRecoverBlocked("REENCODE_OUTPUT_EXISTS_DO_NOT_DUPLICATE")
    TARGET.mkdir(parents=True,exist_ok=False)
    out=TARGET/"elefantinho-revised-h264-aac.mp4"
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
         "-i",str(BASE/"final.mp4"),"-map","0:v:0","-map","0:a:0",
         "-c:v","libx264","-preset","medium","-crf","21",
         "-pix_fmt","yuv420p","-profile:v","high","-level:v","4.2",
         "-r","30","-c:a","aac","-b:a","160k","-ar","48000",
         "-movflags","+faststart",str(out)]
    subprocess.run(cmd,check=True,timeout=1000)
    p=probe(out)
    seconds=float(p["format"]["duration"])
    video=[s for s in p["streams"] if s.get("codec_type")=="video"]
    audio=[s for s in p["streams"] if s.get("codec_type")=="audio"]
    if (not 105<=seconds<=115 or len(video)!=1 or not audio
            or video[0].get("codec_name")!="h264"
            or video[0].get("width")!=1080
            or video[0].get("height")!=1920
            or out.stat().st_size<300_000):
        raise KidsRecoverBlocked("NEW_MP4_CODEC_OR_DURATION_FAILED")
    print("KIDS_ELEFANTINHO_NEW_H264_AAC_FASTSTART_VERIFIED_"+str(round(seconds,2)),flush=True)
    return meta,out

def yt():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    client=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
    token=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
    validate_token_fields(client,token)
    credentials=Credentials.from_authorized_user_info(
        token,scopes=["https://www.googleapis.com/auth/youtube.upload",
                      "https://www.googleapis.com/auth/youtube.readonly"])
    if not credentials.valid:credentials.refresh(Request())
    http=AuthorizedHttp(credentials,http=configure_resumable_transport(httplib2.Http(timeout=180)))
    api=build("youtube","v3",http=http,cache_discovery=False)
    ch=api.channels().list(part="id,contentDetails",mine=True).execute().get("items",[])
    if len(ch)!=1 or ch[0]["id"]!=CHANNEL_ID:
        raise KidsRecoverBlocked("NOT_AUTHENTICATED_KIDS_CHANNEL")
    uploads=ch[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not uploads:raise KidsRecoverBlocked("OWN_UPLOAD_PLAYLIST_MISSING")
    return api,uploads

def all_uploads(api,playlist):
    ids=[]
    page=None
    for _ in range(15):
        kw={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page:kw["pageToken"]=page
        res=api.playlistItems().list(**kw).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId") for x in res.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=res.get("nextPageToken")
        if not page:break
    if page:raise KidsRecoverBlocked("OWN_UPLOAD_HISTORY_SCAN_NOT_EXHAUSTIVE")
    return ids

def find_new(api,playlist,meta):
    ids=all_uploads(api,playlist)
    found=[]
    for i in range(0,len(ids),50):
        for v in api.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute().get("items",[]):
            sn=v.get("snippet",{})
            if sn.get("title")!=meta["title"]:continue
            if v["id"]==OLD_ID:continue
            if (v["id"] in IDS_ALLOWLIST
                    or sn.get("channelId")!=CHANNEL_ID):
                raise KidsRecoverBlocked("UNEXPECTED_CHANNEL_OR_VIDEO_COLLISION")
            if sn.get("description")==meta["description"]+DESCRIPTION_SUFFIX:
                found.append(v["id"])
            else:
                raise KidsRecoverBlocked("UNKNOWN_VIDEO_WITH_SAME_KIDS_TITLE")
    if len(found)>1:raise KidsRecoverBlocked("MULTIPLE_CORRECTED_ELEFANTINHO_VIDEOS")
    return found

def record(data):
    TARGET.mkdir(exist_ok=True)
    (TARGET/"kids-elefantinho-replacement-result.json").write_text(
        json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def verify_new(api,id,meta):
    v=api.videos().list(part="snippet,status,processingDetails,contentDetails",
                         id=id).execute().get("items",[])
    if len(v)!=1:return False
    r=v[0]
    sn=r.get("snippet",{})
    st=r.get("status",{})
    proc=r.get("processingDetails",{})
    if (sn.get("channelId")!=CHANNEL_ID
            or sn.get("title")!=meta["title"]
            or sn.get("description")!=meta["description"]+DESCRIPTION_SUFFIX
            or st.get("privacyStatus")!="public"
            or st.get("madeForKids") is not True):
        raise KidsRecoverBlocked("NEW_KIDS_VIDEO_OWNER_OR_AUDIENCE_OR_PUBLIC_CHANGED")
    if (st.get("uploadStatus") in ("failed","rejected","deleted")
            or proc.get("processingStatus") in ("failed","terminated")):
        raise KidsRecoverBlocked("NEW_VIDEO_PROCESSING_FAILED")
    return (st.get("uploadStatus")=="processed"
            and proc.get("processingStatus")=="succeeded"
            and r.get("contentDetails",{}).get("duration") not in (None,"","P0D","PT0S"))

def upload():
    guard()
    meta,out=reencode()
    api,playlist=yt()
    old=api.videos().list(part="snippet,status,contentDetails,processingDetails",
                          id=OLD_ID).execute().get("items",[])
    if len(old)!=1 or old[0].get("snippet",{}).get("channelId")!=CHANNEL_ID:
        raise KidsRecoverBlocked("ORIGINAL_STUCK_KIDS_VIDEO_NOT_IDENTIFIED")
    status=old[0].get("status",{})
    processing=old[0].get("processingDetails",{})
    dur=old[0].get("contentDetails",{}).get("duration")
    if status.get("uploadStatus")=="processed" and processing.get("processingStatus")=="succeeded" and dur not in ("P0D","PT0S",None,""):
        print("KIDS_ELEFANTINHO_ORIGINAL_IS_NOW_PROCESSED_ABORT_DUPLICATE",flush=True)
        record({"status":"original_already_processed_no_reupload","old_id":OLD_ID})
        return
    present=find_new(api,playlist,meta)
    row={"old_id":OLD_ID,"new_id":None,"new_sha256":digest(out),
         "old_state":{"privacy":status.get("privacyStatus"),
                      "upload":status.get("uploadStatus"),
                      "processing":processing.get("processingStatus"),"duration":dur},
         "status":"insert_uncertain","made_for_kids":True,"new_public_processed":False,
         "cover_acknowledged":False,"old_video_deleted":False}
    record(row)
    if present:
        new_id=present[0]
    else:
        from googleapiclient.http import MediaFileUpload
        body={"snippet":{"title":meta["title"],
                         "description":meta["description"]+DESCRIPTION_SUFFIX,
                         "tags":public_tags(meta["tags"]),
                         "categoryId":"1","defaultLanguage":"pt-BR"},
              "status":{"privacyStatus":"public","selfDeclaredMadeForKids":True,
                        "containsSyntheticMedia":True}}
        command=api.videos().insert(
            part="snippet,status",body=body,
            media_body=MediaFileUpload(str(out),mimetype="video/mp4",
                                       resumable=True,chunksize=8*1024*1024),
            notifySubscribers=False)
        try:
            response=None
            while response is None:
                _,response=command.next_chunk(num_retries=0)
            new_id=(response or {}).get("id")
            if not isinstance(new_id,str) or not re.fullmatch("[A-Za-z0-9_-]{11}",new_id):
                raise KidsRecoverBlocked("NEW_ID_UNCONFIRMED")
        except Exception:
            new_id=None
            for t in (10,20,35):
                time.sleep(t)
                matches=find_new(api,playlist,meta)
                if matches:new_id=matches[0];break
            if not new_id:
                raise KidsRecoverBlocked("YOUTUBE_UPLOAD_AMBIGUOUS_STOP_NO_BLIND_RETRY") from None
    row["new_id"]=new_id
    row["status"]="id_confirmed_wait_processing"
    record(row)
    for i in range(32):
        if verify_new(api,new_id,meta):
            row["new_public_processed"]=True
            row["status"]="new_public_processed"
            record(row)
            break
        if i<31:time.sleep(15)
    if not row["new_public_processed"]:
        raise KidsRecoverBlocked("NEW_KIDS_VIDEO_PROCESSING_PENDING_OR_STUCK")
    from googleapiclient.http import MediaFileUpload
    try:
        time.sleep(45)
        res=api.thumbnails().set(videoId=new_id,
            media_body=MediaFileUpload(str(BASE/"thumb.jpg"),mimetype="image/jpeg")).execute()
        row["cover_acknowledged"]=bool(res.get("items"))
    except Exception:
        row["cover_acknowledged"]=False
        row["thumbnail_studio_review_required"]=True
    row["status"]="new_public_processed_cover_acked" if row["cover_acknowledged"] else "new_public_processed_cover_requires_review"
    record(row)
    print("KIDS_ELEFANTINHO_REPLACEMENT_NEW_PUBLIC_"+new_id,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("preflight","upload"),default="preflight")
    args=p.parse_args()
    try:
        if args.action=="preflight":
            m=json.loads(MANIFEST.read_text(encoding="utf-8"))
            if m.get("original_youtube_id")!=OLD_ID or m.get("target_channel_id")!=CHANNEL_ID:
                raise KidsRecoverBlocked("KIDS_LAUNCH_GUARD")
            print("KIDS_ELEFANTINHO_ONE_REENCODE_PUBLIC_REPLACEMENT_APPROVED")
        else:upload()
        return 0
    except Exception as e:
        msg=str(e) if isinstance(e,KidsRecoverBlocked) else type(e).__name__
        print("KIDS_ELEFANTINHO_REPLACEMENT_BLOCKED_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
