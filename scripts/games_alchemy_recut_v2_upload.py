#!/usr/bin/env python3
"""Private-only upload of 3 verified revision-v2 Shorts per named YouTube channel.

No edit/deletion of original private videos. Enforces reviewed source artifact,
unique revision marker in internal tags, exact per-channel OAuth identity,
write-ahead receipts and 75-second delay before custom thumbnails.
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from games_alchemy_ai_upload import get_youtube,confirm_private,set_thumbnail

FOLDER=ROOT/"cloud-games-alchemy-recut-v2"
OWNER="games_alchemy_six_shorts_v2_20261105"
ORIGIN=42055957229   # set by protected workflow env to exact successful render run
TAG="autoeditorvideo-recut-v2-20261105"
EXPECTED={
"games":["game-001-gta4-gta5-v2","game-002-primeira-noite-minecraft-v2","game-003-minecraft-sem-amarelo-v2"],
"alchemy":["alchemy-001-chatgpt-gifs-v2","alchemy-002-images-26-consistencia-v2","alchemy-003-gif-animado-tutorial-v2"]}
WAIT=75

class V2UploadBlocked(ValueError):
    pass

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def guard(channel:str)->None:
    e=os.environ
    if channel not in EXPECTED:
        raise V2UploadBlocked("UNEXPECTED_CHANNEL")
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!="Gamer + Alchemy - private upload six corrected v2 Shorts"):
        raise V2UploadBlocked("ONE_SHOT_REPO_BRANCH_WORKFLOW_REQUIRED")
    if (e.get("V2_CREATOR_APPROVED")!="true" or
        e.get("SOURCE_RECUT_RUN_ID")!=str(ORIGIN) or
        not e.get("YOUTUBE_CLIENT_JSON") or
        not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise V2UploadBlocked("APPROVAL_OR_CREDENTIALS_MISSING")
    if not FOLDER.is_dir():
        raise V2UploadBlocked("RECUT_ARTIFACT_NOT_DOWNLOADED")

def artifact_jobs(channel:str)->list[dict]:
    data=json.loads((FOLDER/"summary.json").read_text(encoding="utf-8"))
    if data.get("schema")!="autoeditorvideo/games-alchemy-six-recut-v2-output/v1":
        raise V2UploadBlocked("INCORRECT_REVISED_ARTIFACT")
    if data.get("source_run")!=42044136670 or data.get("publication")!="not_performed" or data.get("owner")!=OWNER:
        raise V2UploadBlocked("INCORRECT_ORIGINAL_SOURCE_OR_OWNER")
    rows=[p for p in data.get("videos",[]) if p.get("channel")==channel]
    if [p.get("id") for p in rows]!=EXPECTED[channel]:
        raise V2UploadBlocked("UNEXPECTED_CHANNEL_EPISODE_ORDER")
    jobs=[]
    for p in rows:
        id=p["id"]
        assert_reserved(channel,id,OWNER)
        target=FOLDER/id
        video,cover=target/"final.mp4",target/"thumb.jpg"
        meta=json.loads((target/"metadata.json").read_text(encoding="utf-8"))
        qa=json.loads((target/"qa.json").read_text(encoding="utf-8"))
        if (not video.is_file() or not cover.is_file() or
            sha(video)!=qa.get("mp4_sha256") or
            sha(video)!=p.get("sha256") or
            sha(cover)!=qa.get("cover_sha256") or
            qa.get("structural_qa")!="passed" or
            qa.get("recut_revision")!="v2" or
            qa.get("speech_cta_at_end") is not True or
            qa.get("spoken_ai_disclosure") is not False or
            meta.get("channel_id")!=KNOWN_IDS[channel] or
            meta.get("id")!=id or
            meta.get("revision")!="v2" or
            meta.get("containsSyntheticMedia") is not True or
            meta.get("ai_visuals_only") is not True or
            "🎨" not in meta.get("description","")):
            raise V2UploadBlocked("MEDIA_OR_CHANNEL_QA_FAILED_"+id)
        if len(meta["title"])>100 or len(meta.get("tags",[]))<2:
            raise V2UploadBlocked("SEO_MISSING_"+id)
        jobs.append({"episode":id,"meta":meta,"video":video,"thumb":cover})
    return jobs

def recent_uploads(youtube)->list[dict]:
    c=youtube.channels().list(part="contentDetails",mine=True).execute().get("items",[])
    if len(c)!=1:
        raise V2UploadBlocked("OWN_CHANNEL_LOOKUP_AMBIGUOUS")
    playlist=c[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
    if not playlist:
        raise V2UploadBlocked("UPLOAD_PLAYLIST_MISSING")
    ids=[];nextp=None
    for _ in range(5):
        args={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if nextp: args["pageToken"]=nextp
        result=youtube.playlistItems().list(**args).execute()
        ids.extend(p["contentDetails"]["videoId"] for p in result.get("items",[]) if p.get("contentDetails",{}).get("videoId"))
        nextp=result.get("nextPageToken")
        if not nextp:break
    found=[]
    for i in range(0,len(ids),50):
        result=youtube.videos().list(part="snippet,status",id=",".join(ids[i:i+50])).execute()
        found.extend(result.get("items",[]))
    return found

def find_prior_revision(youtube,channel:str,title:str)->list[str]:
    matches=[]
    for row in recent_uploads(youtube):
        snippet=row.get("snippet",{})
        if (snippet.get("channelId")==KNOWN_IDS[channel] and
            row.get("status",{}).get("privacyStatus")=="private" and
            snippet.get("title")==title and
            TAG in snippet.get("tags",[])):
            matches.append(row["id"])
    return matches

def upload_one(youtube,job:dict)->str:
    meta=job["meta"]
    body={"snippet":{"title":meta["title"],
                      "description":meta["description"],
                      "tags":list(dict.fromkeys(meta["tags"]+[TAG])),
                      "categoryId":meta["categoryId"],
                      "defaultLanguage":"pt-BR"},
          "status":{"privacyStatus":"private",
                    "selfDeclaredMadeForKids":False,
                    "containsSyntheticMedia":True}}
    request=youtube.videos().insert(part="snippet,status",body=body,
                                   media_body=MediaFileUpload(str(job["video"]),
                                   mimetype="video/mp4",resumable=True,chunksize=8*1024*1024),
                                   notifySubscribers=False)
    result=None
    while result is None:
        _,result=request.next_chunk(num_retries=0)
    id=(result or {}).get("id")
    if not id or not re.fullmatch(r"[A-Za-z0-9_-]{11}",id):
        raise V2UploadBlocked("YOUTUBE_VIDEO_ID_MISSING")
    return id

def perform(channel:str)->None:
    guard(channel)
    jobs=artifact_jobs(channel)
    youtube=get_youtube(channel,dict(os.environ))
    # Old versions remain PRIVATE; never create a public duplicate by accident.
    for job in jobs:
        old_id=job["meta"]["original_private_youtube_video_id"]
        if not confirm_private(youtube,old_id,KNOWN_IDS[channel]):
            raise V2UploadBlocked("ORIGINAL_VIDEO_NOT_PRIVATE_OR_WRONG_CHANNEL_"+job["episode"])
    receipt_path=FOLDER/(channel+"-v2-private-upload-receipts.json")
    if receipt_path.exists():
        raise V2UploadBlocked("RECEIPTS_ALREADY_EXIST_NO_REPLAY")
    receipts=[]
    for job in jobs:
        id=job["episode"]
        prior=find_prior_revision(youtube,channel,job["meta"]["title"])
        if len(prior)>1:
            raise V2UploadBlocked("AMBIGUOUS_PRIOR_REVISION_"+id)
        if len(prior)==1:
            video_id=prior[0]
            rec={"episode":id,"channel":channel,"youtube_video_id":video_id,
                 "visibility":"private","reused_existing_revision":True,
                 "confirmed_private":confirm_private(youtube,video_id,KNOWN_IDS[channel]),
                 "thumbnail_api_acknowledged":None}
            receipts.append(rec)
            receipt_path.write_text(json.dumps(receipts,indent=2)+"\n",encoding="utf-8")
            if not rec["confirmed_private"]:
                raise V2UploadBlocked("EXISTING_REVISION_WRONG_CHANNEL")
            print("V2_ALREADY_UPLOADED_PRIVATE_"+id+"_"+video_id,flush=True)
            continue
        # Abort on any ambiguous insert. No second videos.insert request.
        try:
            video_id=upload_one(youtube,job)
        except Exception:
            raise V2UploadBlocked("UPLOAD_AMBIGUOUS_STOP_DO_NOT_RETRY_"+id) from None
        rec={"episode":id,"channel":channel,"youtube_video_id":video_id,
             "visibility":"private","original_private_id":job["meta"]["original_private_youtube_video_id"],
             "reused_existing_revision":False,
             "confirmed_private":False,"thumbnail_api_acknowledged":False,
             "source_sha256":sha(job["video"])}
        receipts.append(rec)
        receipt_path.write_text(json.dumps(receipts,indent=2)+"\n",encoding="utf-8")
        if not confirm_private(youtube,video_id,KNOWN_IDS[channel]):
            raise V2UploadBlocked("NEW_REVISION_PRIVATE_NOT_CONFIRMED_"+id)
        rec["confirmed_private"]=True
        receipt_path.write_text(json.dumps(receipts,indent=2)+"\n",encoding="utf-8")
        print("V2_VIDEO_UPLOADED_PRIVATE_"+id+"_"+video_id,flush=True)
        time.sleep(WAIT)
        rec["thumbnail_api_acknowledged"]=set_thumbnail(youtube,video_id,job["thumb"])
        rec["thumbnail_wait_seconds"]=WAIT
        rec["thumbnail_studio_visible"]="not_verified"
        receipt_path.write_text(json.dumps(receipts,indent=2)+"\n",encoding="utf-8")
        print("V2_THUMB_API_"+id+"_"+("ACK" if rec["thumbnail_api_acknowledged"] else "REJECTED"),flush=True)
        if not rec["thumbnail_api_acknowledged"]:
            raise V2UploadBlocked("THUMB_NOT_ACKNOWLEDGED_KEEP_PRIVATE_NO_VIDEO_RETRY_"+id)
    if len(receipts)!=3 or any(not r["confirmed_private"] for r in receipts):
        raise V2UploadBlocked("THREE_REVISED_PRIVATE_VIDEOS_NOT_PROVEN")
    print("V2_ALL_THREE_PRIVATE_UPLOADED_"+channel,flush=True)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=tuple(EXPECTED),required=True)
    args=p.parse_args()
    try:
        perform(args.channel);return 0
    except Exception as e:
        reason=str(e) if isinstance(e,V2UploadBlocked) else type(e).__name__
        print("V2_UPLOADER_BLOCKED_"+reason,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
