#!/usr/bin/env python3
"""Private YouTube uploads for three ORIGINAL 90-120s still-image episodes per channel.

Only the exact approved batch: EN, Gamer, Alchemy; never Kids/BR. Validate the
original rendered MP4s and covers before opening OAuth. Verify channel identity
and scan own uploads for the exact title + description before videos.insert.
Treat an uncertain insert as possibly accepted: read-only reconciliation only.
All three clips must remain PRIVATE and not made for kids.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from five_channel_fifteen_20261108 import (
    OWNER, EXPECTED, CATEGORY, TOKENS, output, validate, BatchBlocked as RemainingBlocked
)
from youtube_channel_registry import KNOWN_IDS, get_channel
from youtube_new_channels_oauth import validate_token_fields
from kids_static_90s_20261107 import digest, probe
from kids_static_90s_upload_20261107 import configure_resumable_transport
from youtube_public_tags import public_tags

WORKFLOW="AutoEditorVideo - 15 new Shorts BR EN Gamer Kids Alchemy private-first"
class RemainingUploadBlocked(ValueError):pass

def guard(channel:str)->None:
    e=os.environ
    if (channel not in EXPECTED or
            e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW") != WORKFLOW
            or e.get("BATCH15_CHANNEL")!=channel
            or e.get("BATCH15_PRIVATE_UPLOAD_AUTHORIZED")!="yes"):
        raise RemainingUploadBlocked("EXACT_FIRST_MAIN_PUSH_AND_USER_UPLOAD_AUTHORIZATION_REQUIRED")
    if (not e.get("YOUTUBE_CLIENT_JSON") or
            not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise RemainingUploadBlocked("EXCLUSIVE_CHANNEL_OAUTH_MISSING")
    if any(e.get(name) for name in (
            "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_BR_TOKEN_JSON",
            "PROXY_ACCOUNTS_JSON","PROXY_API_KEY")):
        raise RemainingUploadBlocked("OTHER_CHANNEL_OR_IMAGE_GENERATION_SECRETS_FORBIDDEN")
    if get_channel(channel).get("oauth_token_secret_name")!=TOKENS[channel]:
        raise RemainingUploadBlocked("CHANNEL_TOKEN_REGISTRY_MISMATCH")
    if (output(channel)/"youtube-private-receipts.json").exists():
        raise RemainingUploadBlocked("EXISTING_RECEIPTS_DISALLOW_REUPLOAD")

def media_to_upload(channel:str)->list[dict]:
    rows=validate(channel)
    out=output(channel)
    report_file=out/"summary.json"
    if not report_file.is_file():
        raise RemainingUploadBlocked("RENDER_ARTIFACT_SUMMARY_MISSING")
    report=json.loads(report_file.read_text(encoding="utf-8"))
    if (report.get("schema")!="autoeditorvideo/remaining-three-static-original-90s-batch/v1"
            or report.get("owner")!=OWNER or report.get("channel")!=channel
            or report.get("target_channel_id")!=KNOWN_IDS[channel]
            or report.get("artifact_state")!="rendered_upload_not_performed"
            or report.get("video_count")!=3):
        raise RemainingUploadBlocked("RENDER_BATCH_PROVENANCE_MISMATCH")
    rendered=report.get("videos",[])
    if [v.get("id") for v in rendered]!=list(EXPECTED[channel]):
        raise RemainingUploadBlocked("EXPECTED_THREE_EPISODES_MISMATCH")
    outputs=[]
    for row, record in zip(rows,rendered):
        folder=(out/row["id"]).resolve()
        if folder.parent != out.resolve():
            raise RemainingUploadBlocked("ESCAPE_ARTIFACT_DIRECTORY")
        paths={name:folder/name for name in ("final.mp4","thumb.jpg","qa.json","metadata.json")}
        if not all(p.is_file() for p in paths.values()):
            raise RemainingUploadBlocked("MISSING_MP4_THUMB_QA_METADATA_"+row["id"])
        qa=json.loads(paths["qa.json"].read_text(encoding="utf-8"))
        meta=json.loads(paths["metadata.json"].read_text(encoding="utf-8"))
        if (qa.get("schema")!="autoeditorvideo/remaining-static-original-90s-qa/v1"
                or qa.get("channel")!=channel or qa.get("channel_id")!=KNOWN_IDS[channel]
                or qa.get("episode_id")!=row["id"]
                or qa.get("automated_technical_qa")!="passed"
                or qa.get("character_warp_mesh_animation") is not False
                or qa.get("word_boundaries_synced") is not True
                or qa.get("manual_visual_review") is not False
                or qa.get("youtube_upload")!="not_performed"):
            raise RemainingUploadBlocked("RENDER_QA_FAILED_"+row["id"])
        if (meta.get("channel")!=channel or meta.get("id")!=row["id"]
                or meta.get("channel_id")!=KNOWN_IDS[channel]
                or meta.get("title")!=row["title"]
                or meta.get("description")!=row["description"]
                or meta.get("tags")!=row["tags"]
                or meta.get("categoryId")!=CATEGORY[channel]
                or meta.get("defaultLanguage")!=row["language"]
                or meta.get("privacyStatus")!="private"
                or meta.get("selfDeclaredMadeForKids") is not (channel=="kids")
                or meta.get("containsSyntheticMedia") is not True):
            raise RemainingUploadBlocked("ORIGINAL_METADATA_CHANGED_"+row["id"])
        vidhash=digest(paths["final.mp4"])
        thumbhash=digest(paths["thumb.jpg"])
        if (vidhash!=qa.get("mp4_sha256")
                or vidhash!=meta.get("mp4_sha256")
                or vidhash!=record.get("mp4_sha256")
                or thumbhash!=qa.get("cover_sha256")
                or thumbhash!=meta.get("cover_sha256")
                or thumbhash!=record.get("cover_sha256")):
            raise RemainingUploadBlocked("MP4_OR_THUMB_SHA256_MISMATCH_"+row["id"])
        media=probe(paths["final.mp4"])
        length=float(media["format"]["duration"])
        video=[s for s in media["streams"] if s.get("codec_type")=="video"]
        audio=[s for s in media["streams"] if s.get("codec_type")=="audio"]
        if (not 90<=length<=121 or len(video)!=1 or not audio
                or video[0].get("width")!=1080 or video[0].get("height")!=1920
                or paths["final.mp4"].stat().st_size<300_000
                or paths["thumb.jpg"].stat().st_size<25000
                or len(meta["title"])>100 or len(",".join(meta["tags"]))>500):
            raise RemainingUploadBlocked("VIDEO_AUDIO_DURATION_OR_METADATA_LIMIT_FAILED_"+row["id"])
        outputs.append({"episode_id":row["id"],"metadata":meta,
                        "video":paths["final.mp4"],"cover":paths["thumb.jpg"],
                        "sha256":vidhash,"seconds":round(length,2)})
    return outputs

def youtube(channel:str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        c=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        t=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
        validate_token_fields(c,t)
        credential=Credentials.from_authorized_user_info(
            t,scopes=["https://www.googleapis.com/auth/youtube.upload",
                      "https://www.googleapis.com/auth/youtube.readonly"])
        if not credential.valid:
            credential.refresh(Request())
        transport=configure_resumable_transport(httplib2.Http(timeout=180))
        api=build("youtube","v3",
                  http=AuthorizedHttp(credential,http=transport),
                  cache_discovery=False)
        rows=api.channels().list(part="id,contentDetails",mine=True).execute().get("items",[])
        if len(rows)!=1 or rows[0].get("id")!=KNOWN_IDS[channel]:
            raise RemainingUploadBlocked("AUTHENTICATED_CHANNEL_ID_MISMATCH")
        playlist=rows[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
        if not playlist:
            raise RemainingUploadBlocked("OWN_UPLOADS_PLAYLIST_MISSING")
        print("REMAINING_YOUTUBE_CHANNEL_VERIFIED_"+channel+"_"+KNOWN_IDS[channel],flush=True)
        return api,playlist
    except RemainingUploadBlocked:
        raise
    except Exception:
        raise RemainingUploadBlocked("OAUTH_IDENTITY_OR_API_FAILED") from None

def scan_existing(api,playlist:str,item:dict,channel:str)->list[str]:
    """Match exact original title+description for privately uploaded own videos.

    Ambiguous/public/mismatching result blocks any new upload. No secret IDs in
    public tags, titles or descriptions. Never use an unowned video.
    """
    ids=[]
    page=None
    for _ in range(10):
        args={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page:args["pageToken"]=page
        response=api.playlistItems().list(**args).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId")
                   for x in response.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=response.get("nextPageToken")
        if not page:break
    if page:
        raise RemainingUploadBlocked("OWN_UPLOAD_SCAN_NOT_EXHAUSTIVE_STOP")
    matches=[]
    meta=item["metadata"]
    for n in range(0,len(ids),50):
        videos=api.videos().list(part="snippet,status",id=",".join(ids[n:n+50])).execute()
        for v in videos.get("items",[]):
            snip=v.get("snippet",{})
            if snip.get("title")!=meta["title"]:
                continue
            status=v.get("status",{})
            if (snip.get("channelId")!=KNOWN_IDS[channel]
                    or snip.get("description")!=meta["description"]
                    or status.get("privacyStatus")!="private"
                    or status.get("madeForKids") is not (channel=="kids")):
                raise RemainingUploadBlocked("EXISTING_TITLE_NOT_EXACT_PRIVATE_OR_WRONG_CHANNEL")
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",v.get("id","")):
                raise RemainingUploadBlocked("EXISTING_ID_INVALID")
            matches.append(v["id"])
    if len(matches)>1:
        raise RemainingUploadBlocked("DUPLICATE_TITLE_PRIVATE_UPLOAD_MANUAL_REVIEW")
    return matches

def insert_private(api,item:dict)->str:
    from googleapiclient.http import MediaFileUpload
    meta=item["metadata"]
    req=api.videos().insert(part="snippet,status",
        body={
            "snippet":{"title":meta["title"],"description":meta["description"],
                       "tags":public_tags(meta["tags"]),
                       "categoryId":meta["categoryId"],
                       "defaultLanguage":meta["defaultLanguage"]},
            "status":{"privacyStatus":"private",
                      "selfDeclaredMadeForKids":meta["selfDeclaredMadeForKids"],
                      "containsSyntheticMedia":True}
        },
        media_body=MediaFileUpload(str(item["video"]),
                                  mimetype="video/mp4",resumable=True,
                                  chunksize=8*1024*1024),
        notifySubscribers=False)
    result=None
    while result is None:
        _,result=req.next_chunk(num_retries=0)
    vid=(result or {}).get("id")
    if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):
        raise RemainingUploadBlocked("VIDEO_ID_RESPONSE_UNCONFIRMED_STOP")
    return vid

def verify_video(api,video_id:str,channel:str,item:dict)->bool:
    result=api.videos().list(part="snippet,status",id=video_id).execute()
    videos=result.get("items",[])
    if len(videos)!=1:
        return False
    s=videos[0].get("snippet",{})
    st=videos[0].get("status",{})
    return (s.get("channelId")==KNOWN_IDS[channel] and
            s.get("title")==item["metadata"]["title"] and
            s.get("description")==item["metadata"]["description"] and
            st.get("privacyStatus")=="private" and
            st.get("madeForKids") is (channel=="kids"))

def persist(folder:Path,rows:list[dict])->None:
    (folder/"youtube-private-receipts.json").write_text(
        json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def upload(channel:str)->None:
    guard(channel)
    items=media_to_upload(channel)
    api,playlist=youtube(channel)
    # Scan all 3 before any insert to catch a prior unacknowledged upload.
    existing={item["episode_id"]:scan_existing(api,playlist,item,channel)
              for item in items}
    print("REMAINING_READONLY_DEDUP_COMPLETE_"+channel,flush=True)
    out=output(channel)
    receipts=[]
    for item in items:
        matches=existing[item["episode_id"]]
        recovered=bool(matches)
        record={
            "episode_id":item["episode_id"],"channel":channel,
            "channel_id":KNOWN_IDS[channel],"video_sha256":item["sha256"],
            "duration_seconds":item["seconds"],"visibility":"private",
            "made_for_kids":channel=="kids","youtube_id":None,
            "upload_state":"matched_existing_video" if matches else "insert_started_result_uncertain",
            "confirmed_private":False,"thumbnail_acknowledged":False
        }
        receipts.append(record)
        persist(out,receipts)
        if matches:
            video_id=matches[0]
            print("REMAINING_PREVIOUS_PRIVATE_RECONCILED_"+item["episode_id"],flush=True)
        else:
            try:
                video_id=insert_private(api,item)
            except Exception:
                # 308/upload response ambiguity may mean YouTube already
                # accepted the video. NEVER call videos.insert twice.
                recovered_id=None
                for delay in (12,24,35):
                    time.sleep(delay)
                    found=scan_existing(api,playlist,item,channel)
                    if found:
                        recovered_id=found[0]
                        break
                if recovered_id is None:
                    raise RemainingUploadBlocked(
                        "AMBIGUOUS_UPLOAD_STOP_DO_NOT_REUPLOAD_"+item["episode_id"]
                    ) from None
                video_id=recovered_id
                recovered=True
        record["youtube_id"]=video_id
        record["upload_state"]="youtube_id_received"
        record["recovered_from_previous"]=recovered
        persist(out,receipts)
        for seconds in (0,12,24,35):
            if seconds:time.sleep(seconds)
            if verify_video(api,video_id,channel,item):
                record["confirmed_private"]=True
                record["upload_state"]="private_verified"
                persist(out,receipts)
                break
        if not record["confirmed_private"]:
            raise RemainingUploadBlocked(
                "EXISTING_YOUTUBE_ID_UNCONFIRMED_STOP_NO_NEW_UPLOAD_"+item["episode_id"]
            )
        # YouTube may reject custom Shorts thumbnails, never re-upload video.
        try:
            from googleapiclient.http import MediaFileUpload
            if not recovered:time.sleep(75)
            resp=api.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(item["cover"]),
                                           mimetype="image/jpeg")).execute()
            record["thumbnail_acknowledged"]=bool(resp.get("items"))
        except Exception:
            record["thumbnail_review_required"]=True
        persist(out,receipts)
        print("REMAINING_PRIVATE_VERIFIED_"+channel+"_"+item["episode_id"]+"_"+video_id,flush=True)
    if len(receipts)!=3 or not all(r.get("confirmed_private") for r in receipts):
        raise RemainingUploadBlocked("THREE_CHANNEL_UPLOADS_NOT_CONFIRMED")
    print("REMAINING_THREE_PRIVATE_VIDEOS_VERIFIED_"+channel,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",required=True,choices=EXPECTED)
    p.add_argument("--action",choices=("preflight","upload"),default="preflight")
    args=p.parse_args()
    try:
        if args.action=="preflight":
            validate(args.channel)
            print("REMAINING_UPLOAD_PREFLIGHT_"+args.channel+"_THREE_RESERVED")
        else:
            upload(args.channel)
        return 0
    except Exception as exc:
        name=(str(exc) if isinstance(exc,(RemainingUploadBlocked,RemainingBlocked))
              else type(exc).__name__)
        print("REMAINING_PRIVATE_UPLOAD_BLOCKED_"+name,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
