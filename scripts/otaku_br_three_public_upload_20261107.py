#!/usr/bin/env python3
"""Sequential PUBLIC publication of 3 original Otaku Multicena BR Shorts.

Creator explicitly authorized public visibility. Before a new videos.insert:
(1) all 3 original MP4+official covers pass SHA/metadata/ffprobe QA;
(2) OAuth proves exact BR channel; (3) own uploads playlist is scanned
exhaustively for exact titles (including private). The 308 resumable transport
is patched. NEVER repeat an ambiguous videos.insert, even on network errors.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from otaku_br_three_public_20261107 import (
    BRBlocked,OWNER,CHANNEL_ID,IDS,OUTPUT_ROOT,WORKFLOW,output,validate
)
from remaining_static_90s_20261107 import run,probe,digest
from youtube_public_tags import public_tags
from kids_static_90s_upload_20261107 import configure_resumable_transport
from youtube_new_channels_oauth import validate_token_fields
from youtube_channel_registry import get_channel

class PublicBlocked(ValueError):
    pass

RECEIPTS="br-three-public-youtube-receipts.json"

def guard():
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("OTAKU_BR_THREE_PUBLIC_AUTHORIZED")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise PublicBlocked("EXPLICIT_ONE_SHOT_MAIN_BR_PUBLIC_OAUTH_NOT_AUTHORIZED")
    if any(e.get(x) for x in (
            "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
            "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
            "PROXY_API_KEY","PROXY_ACCOUNTS_JSON")):
        raise PublicBlocked("CROSS_CHANNEL_OR_IMAGE_SECRETS_FORBIDDEN")
    if get_channel("br").get("oauth_token_secret_name")!="YOUTUBE_BR_TOKEN_JSON":
        raise PublicBlocked("BR_EXCLUSIVE_TOKEN_REGISTRY_CHANGED")
    if (output()/RECEIPTS).exists():
        raise PublicBlocked("LOCAL_RECEIPT_EXISTS_STOP_RECONCILE_FIRST")

def validate_artifacts()->list[dict]:
    rows=validate()
    root=output()
    report_file=root/"summary.json"
    if not report_file.is_file():
        raise PublicBlocked("THREE_MP4_ARTIFACT_MISSING")
    report=json.loads(report_file.read_text(encoding="utf-8"))
    if (report.get("schema")!="autoeditorvideo/otaku-br-three-public-render/v1"
            or report.get("owner")!=OWNER
            or report.get("channel")!="br"
            or report.get("channel_id")!=CHANNEL_ID
            or report.get("target_count")!=3
            or report.get("media_status")!="rendered_and_QA_passed_not_uploaded"):
        raise PublicBlocked("THREE_ARTIFACT_PROVENANCE_MISMATCH")
    products=report.get("videos",[])
    if [v.get("id") for v in products]!=list(IDS):
        raise PublicBlocked("EXACT_THREE_ARTIFACT_IDS_REQUIRED")
    ready=[]
    for row,entry in zip(rows,products):
        directory=(root/row["id"]).resolve()
        if directory.parent!=root.resolve():
            raise PublicBlocked("ARTIFACT_PATH_ESCAPE")
        files={key:directory/name for key,name in {
            "video":"final.mp4","cover":"thumb.jpg","qa":"qa.json",
            "metadata":"metadata.json"}.items()}
        if not all(x.is_file() for x in files.values()):
            raise PublicBlocked("MP4_COVER_QA_METADATA_INCOMPLETE_"+row["id"])
        qa=json.loads(files["qa"].read_text(encoding="utf-8"))
        meta=json.loads(files["metadata"].read_text(encoding="utf-8"))
        if (qa.get("schema")!="autoeditorvideo/remaining-static-original-90s-qa/v1"
                or qa.get("channel")!="br"
                or qa.get("channel_id")!=CHANNEL_ID
                or qa.get("episode_id")!=row["id"]
                or qa.get("automated_technical_qa")!="passed"
                or qa.get("word_boundaries_synced") is not True
                or qa.get("character_warp_mesh_animation") is not False
                or qa.get("creator_public_authorized") is not True
                or qa.get("youtube_upload")!="not_performed"
                or qa.get("image_count")!=8):
            raise PublicBlocked("ORIGINAL_QA_CHECK_FAILED_"+row["id"])
        if (meta.get("channel")!="br"
                or meta.get("channel_id")!=CHANNEL_ID
                or meta.get("id")!=row["id"]
                or meta.get("title")!=row["title"]
                or meta.get("description")!=row["description"]
                or meta.get("tags")!=row["tags"]
                or meta.get("defaultLanguage")!="pt-BR"
                or meta.get("categoryId")!="24"
                or meta.get("privacyStatus")!="private"
                or meta.get("publication_target")!="public_after_youtube_processed_cover_qa"
                or meta.get("creator_public_authorized") is not True
                or meta.get("selfDeclaredMadeForKids") is not False):
            raise PublicBlocked("PUBLIC_METADATA_AUTHORIZATION_CHANGED_"+row["id"])
        video_hash=digest(files["video"])
        cover_hash=digest(files["cover"])
        if (video_hash!=qa.get("mp4_sha256")
                or video_hash!=entry.get("mp4_sha256")
                or video_hash!=meta.get("mp4_sha256")
                or cover_hash!=qa.get("cover_sha256")
                or cover_hash!=entry.get("cover_sha256")
                or cover_hash!=meta.get("cover_sha256")):
            raise PublicBlocked("MP4_OR_COVER_SHA256_INVALID_"+row["id"])
        streams=probe(files["video"])
        seconds=float(streams["format"]["duration"])
        video=[x for x in streams["streams"] if x.get("codec_type")=="video"]
        audio=[x for x in streams["streams"] if x.get("codec_type")=="audio"]
        if (not 90<=seconds<=121
                or len(video)!=1 or not audio
                or video[0].get("width")!=1080 or video[0].get("height")!=1920
                or files["video"].stat().st_size<300_000
                or files["cover"].stat().st_size<25_000):
            raise PublicBlocked("MEDIA_TECHNICAL_QA_OR_DURATION_FAILED_"+row["id"])
        if len(meta["title"])>100 or len(",".join(meta["tags"]))>500:
            raise PublicBlocked("PUBLIC_SEO_LIMIT_"+row["id"])
        ready.append({"id":row["id"],"video":files["video"],"cover":files["cover"],
                      "meta":meta,"seconds":round(seconds,2),
                      "video_sha256":video_hash})
    return ready

def youtube_client():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        client=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        token=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
        validate_token_fields(client,token)
        cred=Credentials.from_authorized_user_info(
            token,scopes=["https://www.googleapis.com/auth/youtube.upload",
                          "https://www.googleapis.com/auth/youtube.readonly"])
        if not cred.valid:
            cred.refresh(Request())
        transport=configure_resumable_transport(httplib2.Http(timeout=180))
        api=build("youtube","v3",http=AuthorizedHttp(cred,http=transport),
                  cache_discovery=False)
        channels=api.channels().list(part="id,contentDetails",mine=True).execute().get("items") or []
        if len(channels)!=1 or channels[0].get("id")!=CHANNEL_ID:
            raise PublicBlocked("OAUTH_BELONGS_TO_WRONG_YOUTUBE_CHANNEL")
        playlist=channels[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
        if not playlist:
            raise PublicBlocked("CHANNEL_UPLOAD_PLAYLIST_MISSING")
        print("BR_THREE_PUBLIC_AUTHENTICATED_EXACT_CHANNEL_"+CHANNEL_ID,flush=True)
        return api,playlist
    except PublicBlocked:
        raise
    except Exception:
        raise PublicBlocked("BR_OAUTH_OR_YOUTUBE_API_UNAVAILABLE") from None

def existing_title_matches(api,playlist:str,items:list[dict])->dict[str,list[str]]:
    titles={x["meta"]["title"]:x for x in items}
    found={x["id"]:[] for x in items}
    ids=[]
    page=None
    for _ in range(40):
        query={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page:query["pageToken"]=page
        res=api.playlistItems().list(**query).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId")
                   for x in res.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=res.get("nextPageToken")
        if not page:break
    if page:
        raise PublicBlocked("BR_UPLOAD_HISTORY_INCOMPLETE_STOP_DUPLICATION_GUARD")
    for n in range(0,len(ids),50):
        vids=api.videos().list(part="snippet,status",id=",".join(ids[n:n+50])).execute()
        for v in vids.get("items",[]):
            s=v.get("snippet",{})
            t=s.get("title")
            if t not in titles:continue
            target=titles[t]
            if (s.get("channelId")!=CHANNEL_ID
                    or s.get("description")!=target["meta"]["description"]
                    or v.get("status",{}).get("madeForKids") is not False):
                raise PublicBlocked("SAME_TITLE_ALREADY_EXISTS_DIFFERENT_METADATA_STOP")
            found[target["id"]].append(v["id"])
    if any(len(x)>1 for x in found.values()):
        raise PublicBlocked("MULTIPLE_IDENTICAL_PUBLIC_TITLES_MANUAL_REVIEW")
    return found

def insert_public(api,item:dict)->str:
    from googleapiclient.http import MediaFileUpload
    meta=item["meta"]
    req=api.videos().insert(
        part="snippet,status",
        body={"snippet":{
            "title":meta["title"],"description":meta["description"],
            "tags":public_tags(meta["tags"]),
            "categoryId":"24","defaultLanguage":"pt-BR"
        },"status":{
            "privacyStatus":"public","selfDeclaredMadeForKids":False,
            "containsSyntheticMedia":True
        }},
        media_body=MediaFileUpload(str(item["video"]),mimetype="video/mp4",
                                   chunksize=8*1024*1024,resumable=True),
        notifySubscribers=False)
    result=None
    while result is None:
        _,result=req.next_chunk(num_retries=0)
    vid=(result or {}).get("id")
    if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):
        raise PublicBlocked("PUBLIC_VIDEO_INSERT_ID_AMBIGUOUS_DO_NOT_RETRY")
    return vid

def single_video(api,id:str,item:dict)->dict:
    result=api.videos().list(part="snippet,status,processingDetails,contentDetails",
                             id=id).execute()
    vids=result.get("items") or []
    if len(vids)!=1:
        raise PublicBlocked("CONFIRMED_VIDEO_ID_NOT_FOUND")
    row=vids[0]
    snippet=row.get("snippet",{})
    if (snippet.get("channelId")!=CHANNEL_ID
            or snippet.get("title")!=item["meta"]["title"]
            or snippet.get("description")!=item["meta"]["description"]):
        raise PublicBlocked("PUBLISHED_VIDEO_OWNER_TITLE_OR_DESCRIPTION_CHANGED")
    return row

def verify_processed_public(api,id:str,item:dict,attempts:int=28)->None:
    for n in range(attempts):
        v=single_video(api,id,item)
        s=v.get("status",{})
        p=v.get("processingDetails",{})
        length=v.get("contentDetails",{}).get("duration")
        if (s.get("privacyStatus")!="public"
                or s.get("madeForKids") is not False):
            raise PublicBlocked("YOUTUBE_PUBLIC_OR_AUDIENCE_NOT_CONFIRMED")
        if (s.get("uploadStatus")=="processed"
                and p.get("processingStatus")=="succeeded"
                and isinstance(length,str) and length not in ("","P0D","PT0S")):
            return
        if (s.get("uploadStatus") in ("rejected","failed","deleted")
                or p.get("processingStatus") in ("failed","terminated")):
            raise PublicBlocked("YOUTUBE_PROCESSING_FAILED_OR_REJECTED")
        if n<attempts-1:
            time.sleep(15)
    raise PublicBlocked("YOUTUBE_PROCESSING_PENDING_STOP_NEXT_PUBLIC_VIDEO")

def persist(records:list[dict])->None:
    (output()/RECEIPTS).write_text(
        json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def upload()->None:
    guard()
    items=validate_artifacts()
    api,playlist=youtube_client()
    prior=existing_title_matches(api,playlist,items)
    print("BR_THREE_ALL_UPLOAD_HISTORY_CHECKED_BEFORE_FIRST_INSERT",flush=True)
    receipts=[]
    for item in items:
        found=prior[item["id"]]
        record={
            "id":item["id"],"channel":"br","channel_id":CHANNEL_ID,
            "title":item["meta"]["title"],"video_sha256":item["video_sha256"],
            "youtube_id":None,"visibility":"public_requested",
            "upload_state":"existing_video" if found else "insert_started_result_uncertain",
            "confirmed_public_processed":False,"thumbnail_acknowledged":False
        }
        receipts.append(record)
        persist(receipts)
        if found:
            video_id=found[0]
            print("BR_THREE_PREVIOUS_VIDEO_RECONCILED_"+item["id"],flush=True)
        else:
            try:
                video_id=insert_public(api,item)
            except Exception:
                # YouTube might have accepted a request even if the HTTP
                # response failed. No second insert is permitted.
                video_id=None
                for delay in (15,25,35):
                    time.sleep(delay)
                    candidates=existing_title_matches(api,playlist,[item])[item["id"]]
                    if candidates:
                        video_id=candidates[0]
                        break
                if not video_id:
                    raise PublicBlocked("AMBIGUOUS_PUBLIC_INSERT_DO_NOT_RETRY_"+item["id"]) from None
        record["youtube_id"]=video_id
        record["upload_state"]="real_youtube_id_confirmed"
        persist(receipts)
        verify_processed_public(api,video_id,item)
        record["confirmed_public_processed"]=True
        record["upload_state"]="public_processed_confirmed"
        persist(receipts)
        from googleapiclient.http import MediaFileUpload
        try:
            time.sleep(30)
            response=api.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(item["cover"]),
                                           mimetype="image/jpeg")).execute()
            record["thumbnail_acknowledged"]=bool(response.get("items"))
        except Exception:
            record["thumbnail_acknowledged"]=False
            record["thumbnail_review_required"]=True
        persist(receipts)
        if not record["thumbnail_acknowledged"]:
            raise PublicBlocked("PUBLIC_VIDEO_EXISTS_BUT_COVER_NOT_ACKNOWLEDGED_STOP_NO_REUPLOAD")
        verify_processed_public(api,video_id,item,attempts=1)
        record["upload_state"]="public_processed_cover_acknowledged"
        persist(receipts)
        print("BR_THREE_PUBLIC_PROCESSED_COVER_ACKNOWLEDGED_"+item["id"]+"_"+video_id,flush=True)
    if len(receipts)!=3 or any(not r["confirmed_public_processed"] or not r["thumbnail_acknowledged"] for r in receipts):
        raise PublicBlocked("NOT_ALL_THREE_PUBLIC_AND_COVER_CONFIRMED")
    print("BR_THREE_ALL_PUBLIC_VIDEOS_CONFIRMED",flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--action",choices=("preflight","upload"),default="preflight")
    action=ap.parse_args().action
    try:
        if action=="preflight":
            print("BR_THREE_PUBLIC_RESERVED_PRODUCTION_VALID_"+",".join(x["id"] for x in validate()))
        else:upload()
        return 0
    except Exception as exc:
        msg=str(exc) if isinstance(exc,(PublicBlocked,BRBlocked)) else type(exc).__name__
        print("BR_THREE_PUBLIC_UPLOAD_BLOCKED_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
