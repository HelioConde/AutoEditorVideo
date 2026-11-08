#!/usr/bin/env python3
"""Privately stage 9 visually corrected Shorts when their ORIGINAL render completes.

No public publication, deletion, replay of image generation or modification of
previous videos. Confirm original-source GitHub run and artifact, all SHA256
integrity, named-character reference-edit provenance, exact channel OAuth, and
read-only de-duplication including own formerly PUBLIC videos with same title.
A missing/ambiguous upload response is NEVER blindly inserted a second time.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time

import nine_visual_replacements_v2_20261108 as visual
from otaku_character_identity_policy import digest,EXPECTED_SCHEMA,load_policy
from youtube_channel_registry import KNOWN_IDS
from remaining_static_90s_upload_20261107 import (
    youtube as youtube_owner,
    insert_private,verify_video
)
from remaining_static_90s_20261107 import probe


WORKFLOW="AutoEditorVideo - auto stage nine corrected MP4 replacements privately"
GAMER_RETRY_WORKFLOW="AutoEditorVideo - retry Gamer-only V2 after exact failed original render"
SOURCE_WORKFLOW="AutoEditorVideo - nine image-corrected replacements EN Gamer Alchemy"
SOURCE_RUN_ID=42449154499
SOURCE_COMMIT="0841f7523e5a50bb48ab4f6399cd95350a82a36a"
RECEIPT_NAME="youtube-v2-private-upload-receipts.json"
class StageBlocked(ValueError): pass

def guard(channel):
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="workflow_run"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW") not in (WORKFLOW,GAMER_RETRY_WORKFLOW)
            or (e.get("GITHUB_WORKFLOW")==GAMER_RETRY_WORKFLOW
                and (channel!="games" or e.get("REPLACEMENTS_RETRY_APPROVED")!="yes"))
            or e.get("REPLACEMENTS_PRIVATE_STAGE_APPROVED")!="yes"
            or e.get("REPLACEMENTS_CHANNEL")!=channel
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or any(e.get(k) for k in (
                "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
                "YOUTUBE_BR_DELETE_TOKEN_JSON","PROXY_API_KEY","PROXY_ACCOUNTS_JSON"))):
        raise StageBlocked("EXACT_APPROVED_NO_CROSS_CHANNEL_WORKFLOW_RUN_OAUTH_REQUIRED")
    p=Path(e.get("GITHUB_EVENT_PATH",""))
    if not p.is_file():raise StageBlocked("GITHUB_WORKFLOW_RUN_EVENT_REQUIRED")
    event=json.loads(p.read_text(encoding="utf-8"))
    run=event.get("workflow_run",{})
    if (run.get("id")!=SOURCE_RUN_ID
            or run.get("name")!=SOURCE_WORKFLOW
            or run.get("head_sha")!=SOURCE_COMMIT
            or run.get("head_branch")!="main"
            or run.get("conclusion") not in ("success","failure")
            or run.get("event")!="push"
            or run.get("repository",{}).get("full_name")!="HelioConde/AutoEditorVideo"):
        raise StageBlocked("SOURCE_JOB_MUST_BE_EXACT_SUCCESSFUL_NINE_RENDER")
    load_policy()
    out=visual.output(channel)
    if (out/RECEIPT_NAME).exists():
        raise StageBlocked("EXISTING_RECEIPT_NO_NEW_UPLOAD")
    return visual.validate(channel)

def prepare(channel):
    rows=visual.validate(channel)
    base=visual.output(channel)
    summary_file=base/"summary.json"
    if not summary_file.is_file():
        raise StageBlocked("MISSING_THREE_RENDERED_MP4_SUMMARY")
    doc=json.loads(summary_file.read_text(encoding="utf-8"))
    if (doc.get("schema")!="autoeditorvideo/nine-visual-replacements-rendered/v2"
            or doc.get("owner")!=visual.OWNER
            or doc.get("channel")!=channel
            or doc.get("channel_id")!=KNOWN_IDS[channel]
            or doc.get("privacy")!="not_uploaded_visual_review_pending"
            or doc.get("count")!=3
            or doc.get("max_image_calls")!=visual.CALLS[channel]
            or doc.get("image_process")!="character_anchor_then_images_edits_for_every_scene"
            or [x.get("id") for x in doc.get("videos",[])]!=list(visual.IDS[channel])):
        raise StageBlocked("SOURCE_RENDER_REPORT_OR_EXPECTED_VIDEO_IDS_MISMATCH")
    output=[]
    for row,record in zip(rows,doc["videos"]):
        root=(base/row["id"]).resolve()
        if root.parent!=base.resolve():raise StageBlocked("ARTIFACT_DIR_ESCAPE")
        files={k:root/n for k,n in {
            "video":"final.mp4","cover":"thumb.jpg","qa":"qa.json",
            "metadata":"metadata.json","provenance":"character-identity-provenance.json"}.items()}
        if not all(p.is_file() for p in files.values()):
            raise StageBlocked("ONE_OF_3_VIDEO_ARTIFACTS_INCOMPLETE")
        qa=json.loads(files["qa"].read_text(encoding="utf-8"))
        meta=json.loads(files["metadata"].read_text(encoding="utf-8"))
        prov=json.loads(files["provenance"].read_text(encoding="utf-8"))
        if (qa.get("automated_technical_qa")!="passed"
                or qa.get("word_boundaries_synced") is not True
                or qa.get("character_warp_mesh_animation") is not False
                or qa.get("image_count")!=8
                or qa.get("all_scene_edits_use_anchor") is not True
                or qa.get("identity_bible_complete") is not True
                or qa.get("editorial_visual_review_status")!="pending"
                or qa.get("publication_qa")!="not_approved"
                or qa.get("youtube_upload")!="not_performed"
                or qa.get("channel_id")!=KNOWN_IDS[channel]
                or qa.get("episode_id")!=row["id"]):
            raise StageBlocked("IDENTITY_OR_MEDIA_TECHNICAL_QA_MISSING")
        if (meta.get("id")!=row["id"]
                or meta.get("channel")!=channel
                or meta.get("channel_id")!=KNOWN_IDS[channel]
                or meta.get("title")!=row["title"]
                or meta.get("description")!=row["description"]
                or meta.get("tags")!=row["tags"]
                or meta.get("defaultLanguage")!=row["language"]
                or meta.get("categoryId")!=visual.editor.CATEGORY[channel]
                or meta.get("privacyStatus")!="private"
                or meta.get("selfDeclaredMadeForKids") is not False
                or meta.get("containsSyntheticMedia") is not True
                or meta.get("previous_youtube_id")!=row["old_youtube_id"]
                or meta.get("original_public_video_preserved") is not True
                or meta.get("replacement_review")!="pending"):
            raise StageBlocked("CHANNEL_AUDIENCE_OR_VERSIONED_METADATA_INVALID")
        if (prov.get("image_generation_mode")!="canonical-anchor-then-reference-edits"
                or prov.get("independent_text_to_image_scene_generations")!=0
                or prov.get("scene_edit_generations")!=8
                or prov.get("publication_allowed") is not False
                or len(prov.get("scenes",[]))!=8):
            raise StageBlocked("IMAGE_NOT_REFERENCE_BASED")
        if channel=="en" and prov.get("policy_schema")!=EXPECTED_SCHEMA:
            raise StageBlocked("ANIME_CHARACTER_IDENTITY_POLICY_CHANGED")
        for a,sha in prov["anchors_sha256"].items():
            p=root/("anchor-"+a+".png")
            if not p.is_file() or digest(p)!=sha:
                raise StageBlocked("ANCHOR_IMAGE_HASH_CHANGED")
        for s in prov["scenes"]:
            p=root/("scene-%02d.png"%s["scene"])
            if (not p.is_file() or digest(p)!=s.get("image_sha256")
                    or s.get("generation_endpoint")!="images/edits"):
                raise StageBlocked("SCENE_IMAGE_SHA_OR_REFERENCE_ENDPOINT_INVALID")
        h=digest(files["video"])
        cover=digest(files["cover"])
        if (h!=qa.get("mp4_sha256") or h!=meta.get("mp4_sha256")
                or h!=record.get("mp4_sha256")
                or cover!=qa.get("cover_sha256")
                or cover!=meta.get("cover_sha256")
                or cover!=record.get("cover_sha256")):
            raise StageBlocked("SOURCE_MP4_COVER_SHA256_INVALID")
        video=probe(files["video"])
        seconds=float(video["format"]["duration"])
        streams=[x for x in video["streams"] if x.get("codec_type")=="video"]
        audio=[x for x in video["streams"] if x.get("codec_type")=="audio"]
        if (not 90<=seconds<=121 or len(streams)!=1 or not audio
                or streams[0].get("width")!=1080
                or streams[0].get("height")!=1920
                or files["video"].stat().st_size<300_000
                or files["cover"].stat().st_size<25_000
                or len(meta["title"])>100
                or len(",".join(meta["tags"]))>500):
            raise StageBlocked("MEDIA_DIMENSIONS_DURATION_AUDIO_OR_COVER_INVALID")
        output.append({"episode_id":row["id"],"old_youtube_id":row["old_youtube_id"],
                       "metadata":meta,"video":files["video"],"cover":files["cover"],
                       "sha256":h,"seconds":round(seconds,2)})
    return output

def scan_owned(api,playlist,channel,item):
    # Other public previous version with the SAME title is expected; only the
    # exact allowlisted old id may be skipped.
    ids=[]
    page=None
    for i in range(80):
        args={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page:args["pageToken"]=page
        res=api.playlistItems().list(**args).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId")
                   for x in res.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=res.get("nextPageToken")
        if not page:break
    if page:raise StageBlocked("CANNOT_EXHAUSTIVELY_SCAN_OWN_UPLOADS")
    matches=[]
    for p in range(0,len(ids),50):
        res=api.videos().list(part="snippet,status",id=",".join(ids[p:p+50])).execute()
        for v in res.get("items",[]):
            sn=v.get("snippet",{})
            if sn.get("title")!=item["metadata"]["title"]:continue
            if sn.get("channelId")!=KNOWN_IDS[channel]:
                raise StageBlocked("TITLE_OWNERSHIP_MISMATCH")
            if v.get("id")==item["old_youtube_id"]:
                continue
            if sn.get("description")!=item["metadata"]["description"]:
                raise StageBlocked("UNKNOWN_SAME_TITLE_OTHER_VIDEO_STOP")
            if (v.get("status",{}).get("madeForKids") is not False
                    or v.get("status",{}).get("privacyStatus")!="private"):
                raise StageBlocked("PREVIOUS_NEW_V2_NOT_PRIVATE_STOP")
            matches.append(v["id"])
    if len(matches)>1:raise StageBlocked("DUPLICATE_PRIVATE_REPLACEMENTS_STOP")
    return matches

def persist(folder,rows):
    (folder/RECEIPT_NAME).write_text(
        json.dumps(rows,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def upload(channel):
    rows=guard(channel)
    items=prepare(channel)
    api,playlist=youtube_owner(channel)
    # The first read-only pass happens before ANY new insert.
    existing={r["episode_id"]:scan_owned(api,playlist,channel,r) for r in items}
    receipts=[]
    root=visual.output(channel)
    for item in items:
        current=existing[item["episode_id"]]
        rec={
            "episode_id":item["episode_id"],"channel":channel,
            "channel_id":KNOWN_IDS[channel],"old_video_id":item["old_youtube_id"],
            "new_private_youtube_id":None,"video_sha256":item["sha256"],
            "duration_seconds":item["seconds"],"source_render_run":SOURCE_RUN_ID,
            "source_character_anchors_verified":True,"source_all_scene_edits_verified":True,
            "review_status":"private_visual_review_pending",
            "old_public_video_unchanged":True,
            "confirmed_private":False,"thumbnail_acknowledged":False,
            "status":"insert_uncertain" if not current else "reconcile_existing"
        }
        receipts.append(rec)
        persist(root,receipts)
        if current:
            id=current[0]
            reused=True
        else:
            try:
                id=insert_private(api,item)
                reused=False
            except Exception:
                id=None
                for t in (12,22,32):
                    time.sleep(t)
                    new=scan_owned(api,playlist,channel,item)
                    if new:id=new[0];break
                if not id:
                    raise StageBlocked("AMBIGUOUS_UPLOAD_DO_NOT_RETRY_"+item["episode_id"]) from None
                reused=True
        rec["new_private_youtube_id"]=id
        rec["status"]="new_youtube_id_received"
        persist(root,receipts)
        for delay in (0,12,24):
            if delay:time.sleep(delay)
            if verify_video(api,id,channel,item):
                rec["confirmed_private"]=True
                rec["status"]="private_youtube_identity_verified"
                persist(root,receipts)
                break
        if not rec["confirmed_private"]:
            raise StageBlocked("NEW_VIDEO_NOT_VERIFIED_PRIVATE_STOP_"+item["episode_id"])
        try:
            from googleapiclient.http import MediaFileUpload
            if not reused:time.sleep(75)
            resp=api.thumbnails().set(
                videoId=id,
                media_body=MediaFileUpload(str(item["cover"]),mimetype="image/jpeg")).execute()
            rec["thumbnail_acknowledged"]=bool(resp.get("items"))
        except Exception:
            rec["thumbnail_review_required"]=True
        rec["status"]="private_staged_for_creator_visual_review"
        persist(root,receipts)
        print("NINE_V2_"+channel.upper()+"_NEW_PRIVATE_REPLACEMENT_VERIFIED_"+item["episode_id"]+"_"+id,flush=True)
    if len(receipts)!=3 or any(not x["confirmed_private"] for x in receipts):
        raise StageBlocked("NOT_ALL_THREE_PRIVATE_VERIFIED")
    print("NINE_V2_"+channel.upper()+"_THREE_PRIVATE_REPLACEMENTS_STAGED",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--channel",choices=visual.CHANNELS,required=True)
    p.add_argument("--action",choices=("preflight","upload"),default="preflight")
    x=p.parse_args()
    try:
        if x.action=="preflight":
            visual.validate(x.channel)
            print("NINE_V2_"+x.channel.upper()+"_UPLOAD_STAGING_CONTRACT_PASSED")
        else:upload(x.channel)
        return 0
    except Exception as ex:
        text=str(ex) if isinstance(ex,StageBlocked) else type(ex).__name__
        print("NINE_V2_STAGE_UPLOAD_BLOCKED_"+text,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
