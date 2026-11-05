#!/usr/bin/env python3
"""Upload six full reference-style V4 Shorts PRIVATE, by exact YouTube channel.

Only reads the 1080x1920 original-program Remotion MP4 and
capa_cinematografica JPEG from the verified V4 artifact. Never changes,
deletes, unlists or publishes V1/V2 videos; no AI generation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from googleapiclient.http import MediaFileUpload
from games_alchemy_ai_upload import get_youtube,confirm_private,set_thumbnail
from youtube_public_tags import public_tags
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS,get_channel

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"cloud-games-alchemy-reference-v4"
OWNER="games_alchemy_six_reference_v4_20261105"
RUN_ID="same-github-run"
TAG="autoeditorvideo-reference-v4-20261105"
EXPECTED={
 "games":["game-001-gta4-gta5-v4","game-002-primeira-noite-minecraft-v4","game-003-minecraft-sem-amarelo-v4"],
 "alchemy":["alchemy-001-chatgpt-gifs-v4","alchemy-002-images-26-consistencia-v4","alchemy-003-gif-animado-tutorial-v4"]
}

class ReferenceV4UploadBlocked(ValueError):pass

def sha(f:Path)->str:
    return hashlib.sha256(f.read_bytes()).hexdigest()

def preflight(channel:str)->None:
    e=os.environ
    if (channel not in EXPECTED or
        e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!="Gamer + Alchemy - approved reference style six V4 private Shorts"):
        raise ReferenceV4UploadBlocked("PRIVATE_ONE_SHOT_MAIN_ONLY")
    if (e.get("REFERENCE_V4_UPLOAD_APPROVED")!="true" or
        e.get("SOURCE_REFERENCE_RENDER_RUN_ID")!=e.get("GITHUB_RUN_ID") or
        not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise ReferenceV4UploadBlocked("APPROVAL_OR_CHANNEL_CREDENTIAL_MISSING")
    cfg=get_channel(channel)
    if cfg.get("youtube_environment")!="youtube-private-upload":
        raise ReferenceV4UploadBlocked("ENVIRONMENT_MISMATCH")
    wanted="YOUTUBE_GAMES_TOKEN_JSON" if channel=="games" else "YOUTUBE_ALCHEMY_TOKEN_JSON"
    if cfg.get("oauth_token_secret_name")!=wanted:
        raise ReferenceV4UploadBlocked("WRONG_CHANNEL_TOKEN")
    if not SOURCE.is_dir():
        raise ReferenceV4UploadBlocked("NO_RENDER_ARTIFACT")

def verified_jobs(channel:str)->list[dict]:
    a=json.loads((SOURCE/"summary.json").read_text(encoding="utf-8"))
    if (a.get("schema")!="autoeditorvideo/games-alchemy-six-native-remotion-v4/v1" or
        a.get("source_run")!=42044136670 or a.get("owner")!=OWNER or
        a.get("no_new_image_api_calls") is not True or
        a.get("renderer")!="AutoEditorVideo/ArquivoOtakuMaster" or
        a.get("cover_generator")!="AutoEditorVideo/scripts/capa_cinematografica.py" or
        a.get("visual_profile")!="gamer-alchemy-reference" or
        a.get("cover_template")!="gamer-alchemy-reference"):
        raise ReferenceV4UploadBlocked("NOT_NATIVE_PROGRAM_RENDER")
    allrows=a.get("videos",[])
    if len(allrows)!=6:
        raise ReferenceV4UploadBlocked("NOT_SIX_VIDEOS")
    entries=[v for v in allrows if v["channel"]==channel]
    if [j["id"] for j in entries]!=EXPECTED[channel]:
        raise ReferenceV4UploadBlocked("WRONG_EPISODE_LIST")
    found=[]
    for item in entries:
        id=item["id"]
        assert_reserved(channel,id,OWNER)
        folder=SOURCE/id
        movie,cover,meta_path,qa_path=(
            folder/"final.mp4",folder/"thumb.jpg",folder/"metadata.json",folder/"qa.json")
        if any(not p.is_file() for p in [movie,cover,meta_path,qa_path]):
            raise ReferenceV4UploadBlocked("RENDERED_FILES_MISSING_"+id)
        meta=json.loads(meta_path.read_text(encoding="utf-8"))
        qa=json.loads(qa_path.read_text(encoding="utf-8"))
        if (sha(movie)!=item["sha256"] or sha(movie)!=qa.get("video_sha256") or
            sha(cover)!=qa.get("cover_sha256") or
            meta.get("video_sha256")!=item["sha256"] or
            meta.get("cover_sha256")!=sha(cover) or
            meta.get("id")!=id or meta.get("channel")!=channel or
            meta.get("channel_id")!=KNOWN_IDS[channel] or
            meta.get("revision")!="v4" or
            meta.get("containsSyntheticMedia") is not True or
            "🎨" not in meta.get("description","") or
            qa.get("render_engine")!="ArquivoOtakuMaster" or
            qa.get("cover_engine")!="duelo-cinematografico" or
            qa.get("cover_template")!="gamer-alchemy-reference" or
            qa.get("visual_profile")!="gamer-alchemy-reference" or
            meta.get("cover_template")!="gamer-alchemy-reference" or
            meta.get("visual_profile")!="gamer-alchemy-reference" or
            qa.get("cover_size")!=[1080,1920] or
            qa.get("caption_max_group_words")>3 or
            qa.get("highlight_by_word_boundaries") is not True or
            qa.get("script_cta") is not True or
            qa.get("silent_production_disclosure") is not True or
            qa.get("structural_qa")!="passed" or
            not 20<=qa.get("video_seconds",0)<=90):
            raise ReferenceV4UploadBlocked("SOURCE_PROVENANCE_OR_STYLING_QA_FAILED_"+id)
        found.append({"id":id,"meta":meta,"video":movie,"cover":cover})
    return found

def recent_private_v4(youtube,channel:str,title:str)->list[str]:
    response=youtube.channels().list(part="contentDetails",mine=True).execute()
    items=response.get("items",[])
    if len(items)!=1 or items[0]["id"]!=KNOWN_IDS[channel]:
        raise ReferenceV4UploadBlocked("YOUTUBE_IDENTITY_MISMATCH")
    playlist=items[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not playlist:raise ReferenceV4UploadBlocked("NO_OWN_UPLOAD_PLAYLIST")
    result_ids=[];token=None
    for _ in range(6):
        kw={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if token:kw["pageToken"]=token
        resp=youtube.playlistItems().list(**kw).execute()
        result_ids.extend(x.get("contentDetails",{}).get("videoId")
                          for x in resp.get("items",[])
                          if x.get("contentDetails",{}).get("videoId"))
        token=resp.get("nextPageToken")
        if not token:break
    matches=[]
    for n in range(0,len(result_ids),50):
        videos=youtube.videos().list(part="snippet,status",
                                    id=",".join(result_ids[n:n+50])).execute()
        for video in videos.get("items",[]):
            s=video.get("snippet",{})
            if (s.get("channelId")==KNOWN_IDS[channel] and
                s.get("title")==title and
                TAG in s.get("tags",[]) and
                video.get("status",{}).get("privacyStatus")=="private"):
                matches.append(video["id"])
    return matches

def insert_private(youtube,job:dict)->str:
    meta=job["meta"]
    body={
      "snippet":{"title":meta["title"],"description":meta["description"],
                 "tags":public_tags(meta["tags"]),
                 "categoryId":meta["categoryId"],"defaultLanguage":"pt-BR"},
      "status":{"privacyStatus":"private",
                "selfDeclaredMadeForKids":False,
                "containsSyntheticMedia":True}
    }
    req=youtube.videos().insert(part="snippet,status",body=body,
       media_body=MediaFileUpload(str(job["video"]),mimetype="video/mp4",
                                   resumable=True,chunksize=8*1024*1024),
       notifySubscribers=False)
    done=None
    while done is None:
        _,done=req.next_chunk(num_retries=0)
    video_id=(done or {}).get("id")
    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        raise ReferenceV4UploadBlocked("YOUTUBE_VIDEO_ID_MISSING")
    return video_id

def upload(channel:str)->None:
    preflight(channel)
    jobs=verified_jobs(channel)
    youtube=get_youtube(channel,dict(os.environ))
    receipts_path=SOURCE/(channel+"-native-v4-youtube-receipts.json")
    if receipts_path.exists():
        raise ReferenceV4UploadBlocked("UPLOAD_ALREADY_ATTEMPTED")
    receipts=[]
    for job in jobs:
        matches=recent_private_v4(youtube,channel,job["meta"]["title"])
        if len(matches)>1:raise ReferenceV4UploadBlocked("AMBIGUOUS_EXISTING_V4_UPLOAD")
        if matches:
            id=matches[0]
            record={"id":job["id"],"channel":channel,
                    "video_id":id,"visibility":"private",
                    "from_prior_v4":True,
                    "confirmed_private":confirm_private(youtube,id,KNOWN_IDS[channel]),
                    "thumbnail_api_acknowledged":None}
        else:
            try:
                id=insert_private(youtube,job)
            except Exception:
                # Google can return a resumable-upload redirect without Location
                # AFTER accepting the video (RedirectMissingLocation).
                # Never call videos.insert twice: query the private uploads
                # playlist by the V4 idempotency tag and exact title instead.
                # A successful insert can lose its HTTP redirect response:
                # query again without ever duplicating videos.insert.
                recovered=[]
                for delay in (20,20,20):
                    time.sleep(delay)
                    recovered=recent_private_v4(youtube,channel,job["meta"]["title"])
                    if recovered:
                        break
                if len(recovered)!=1:
                    raise ReferenceV4UploadBlocked("AMBIGUOUS_UPLOAD_STOP_NO_RETRY_"+job["id"]) from None
                id=recovered[0]
            # Persist the accepted ID before waiting for the separate cover.
            record={"id":job["id"],"channel":channel,
                    "video_id":id,"visibility":"private",
                    "from_prior_v4":False,
                    "confirmed_private":False,
                    "thumbnail_api_acknowledged":False,
                    "source_sha256":sha(job["video"])}
        receipts.append(record)
        receipts_path.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if not confirm_private(youtube,id,KNOWN_IDS[channel]):
            raise ReferenceV4UploadBlocked("PRIVATE_CHANNEL_UNVERIFIED_"+job["id"])
        record["confirmed_private"]=True
        receipts_path.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        # Also apply the program-generated cover when an already-accepted
        # video was recovered after an ambiguous upload. Never reinsert MP4.
        if not matches:
            time.sleep(75)
        record["thumbnail_api_acknowledged"]=set_thumbnail(youtube,id,job["cover"])
        record["thumbnail_wait_seconds"]=75 if not matches else 0
        record["thumbnail_studio_visibility"]="not_verified"
        receipts_path.write_text(json.dumps(receipts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if not record["thumbnail_api_acknowledged"]:
            raise ReferenceV4UploadBlocked("COVER_API_UNACKNOWLEDGED_NO_REUPLOAD_"+job["id"])
        print("NATIVE_V4_PRIVATE_"+job["id"]+"_"+id,flush=True)
    if len(receipts)!=3 or any(not x["confirmed_private"] for x in receipts):
        raise ReferenceV4UploadBlocked("THREE_PRIVATE_UPLOADS_NOT_CONFIRMED")
    print("NATIVE_V4_ALL_THREE_PRIVATE_"+channel,flush=True)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",choices=("games","alchemy"),required=True)
    args=ap.parse_args()
    try:
        upload(args.channel);return 0
    except Exception as exc:
        name=str(exc) if isinstance(exc,ReferenceV4UploadBlocked) else type(exc).__name__
        print("NATIVE_V4_UPLOAD_BLOCKED_"+name,file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
