#!/usr/bin/env python3
"""Publish ONLY visually approved V2 Otaku Multicena Shorts, then safe old-ID cleanup.

Review approval is explicit and SHA-256 bound to rendered original artwork.
Read-only owner channel lookup + exhaustive title check precedes insertion.
Safeguards: only main first push, BR channel ID, known source artifact,
no fake manual QA, one-shot private OAuth, API 308 resume, no blind insert retry.
Original bad version may be deleted only AFTER ALL 3 new videos are PUBLIC,
PROCESSED with validated original thumbnails, and deletion OAuth is granted.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

from otaku_br_character_v2_20261108 import (
    OWNER,CHANNEL_ID,IDS,output,validate,RenderBlocked
)
from otaku_character_identity_policy import EXPECTED_SCHEMA,digest,load_policy
from kids_static_90s_upload_20261107 import configure_resumable_transport
from remaining_static_90s_20261107 import probe
from youtube_new_channels_oauth import validate_token_fields
from youtube_public_tags import public_tags

APPROVAL=Path("conteudos/otaku-br-character-v2-public-approval-20261108.json")
RECEIPTS="br-three-character-v2-youtube-receipts.json"
WORKFLOW="Otaku Multicena BR - publish character-faithful V2 after visual QA"
SOURCE_RUN=42444319178
SOURCE_ARTIFACT="otaku-br-three-canonical-characters-v2-review-20261108"
DESCRIPTION_SUFFIX="\n\nNesta edição, as ilustrações foram refeitas para manter a aparência dos personagens consistente com a história."
DELETE_SCOPE="https://www.googleapis.com/auth/youtube.force-ssl"
ALT_DELETE_SCOPES={"https://www.googleapis.com/auth/youtube",DELETE_SCOPE,
                   "https://www.googleapis.com/auth/youtubepartner"}

class PublishBlocked(ValueError): pass

def guard()->dict:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("OTAKU_V2_VISUAL_REVIEW_AND_PUBLIC_AUTHORIZED")!="yes"
            or not e.get("YOUTUBE_CLIENT_JSON")
            or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")
            or any(e.get(x) for x in (
                "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_GAMES_TOKEN_JSON",
                "YOUTUBE_EN_TOKEN_JSON","YOUTUBE_ALCHEMY_TOKEN_JSON",
                "PROXY_API_KEY","PROXY_ACCOUNTS_JSON"))):
        raise PublishBlocked("EXACT_ONE_SHOT_BR_PUBLIC_OAUTH_AND_REVIEW_REQUIRED")
    if (output()/RECEIPTS).exists():
        raise PublishBlocked("LOCAL_UPLOAD_RECEIPTS_EXIST_NEVER_DUPLICATE")
    load_policy()
    if not APPROVAL.is_file():
        raise PublishBlocked("NO_VISUAL_REVIEW_APPROVAL_DOCUMENT")
    a=json.loads(APPROVAL.read_text(encoding="utf-8"))
    if (a.get("schema")!="autoeditorvideo/otaku-br-v2-character-review-approval/v1"
            or a.get("source_run_id")!=SOURCE_RUN
            or a.get("source_artifact")!=SOURCE_ARTIFACT
            or a.get("channel_id")!=CHANNEL_ID
            or a.get("visual_review_by_assistant") is not True
            or a.get("reviewed_all_anchors_and_story_scenes") is not True
            or a.get("creator_publication_authorized") is not True
            or a.get("no_fake_approvals") is not True
            or a.get("preserve_originals_until_replacement_verified") is not True):
        raise PublishBlocked("VISUAL_REVIEW_APPROVAL_CONTRACT_NOT_MET")
    return a

def artifact_items(approval:dict)->list[dict]:
    rows=validate()
    root=output()
    summary_path=root/"summary.json"
    if not summary_path.is_file():
        raise PublishBlocked("THREE_ORIGINAL_V2_MP4_ARTIFACT_NOT_AVAILABLE")
    summary=json.loads(summary_path.read_text(encoding="utf-8"))
    if (summary.get("schema")!="autoeditorvideo/otaku-br-3-canonical-character-render/v2"
            or summary.get("owner")!=OWNER or summary.get("channel")!="br"
            or summary.get("channel_id")!=CHANNEL_ID
            or summary.get("publication")!="none_awaiting_character_visual_review"
            or summary.get("target_count")!=3):
        raise PublishBlocked("SOURCE_RENDER_QUALITY_PROVENANCE_CHANGED")
    records=summary.get("videos",[])
    if [x.get("id") for x in records]!=list(IDS):
        raise PublishBlocked("WRONG_SOURCE_EPISODE_SEQUENCE")
    if [x.get("id") for x in approval.get("approved_episodes",[])]!=list(IDS):
        raise PublishBlocked("THREE_EPISODE_VISUAL_APPROVAL_MISSING")
    rendered=[]
    for original,record,approval_record in zip(rows,records,approval["approved_episodes"]):
        folder=(root/original["id"]).resolve()
        if folder.parent!=root.resolve():
            raise PublishBlocked("ESCAPE_MEDIA_ARTIFACT_DIR")
        paths={k:folder/name for k,name in {
            "video":"final.mp4","cover":"thumb.jpg","qa":"qa.json",
            "metadata":"metadata.json","provenance":"character-identity-provenance.json"}.items()}
        if any(not p.is_file() for p in paths.values()):
            raise PublishBlocked("MISSING_MP4_ART_ORIGINAL_CHARACTER_PROVENANCE")
        qa=json.loads(paths["qa"].read_text(encoding="utf-8"))
        meta=json.loads(paths["metadata"].read_text(encoding="utf-8"))
        prov=json.loads(paths["provenance"].read_text(encoding="utf-8"))
        if (qa.get("automated_technical_qa")!="passed"
                or qa.get("identity_policy_schema")!=EXPECTED_SCHEMA
                or qa.get("all_scene_edits_use_anchor") is not True
                or qa.get("identity_bible_complete") is not True
                or qa.get("scenes_aligned_to_story") is not True
                or qa.get("editorial_visual_review_status")!="pending"
                or qa.get("publication_qa")!="not_approved"
                or qa.get("word_boundaries_synced") is not True
                or qa.get("image_count")!=8
                or qa.get("character_warp_mesh_animation") is not False
                or qa.get("youtube_upload")!="not_performed"
                or meta.get("channel_id")!=CHANNEL_ID
                or meta.get("id")!=original["id"]
                or meta.get("title")!=original["title"]
                or meta.get("description")!=original["description"]
                or meta.get("tags")!=original["tags"]
                or meta.get("privacyStatus")!="private"
                or meta.get("version")!=2
                or meta.get("character_identity_policy")!=EXPECTED_SCHEMA
                or meta.get("publication_target")!="public_after_approved_visual_review"
                or meta.get("selfDeclaredMadeForKids") is not False
                or meta.get("containsSyntheticMedia") is not True):
            raise PublishBlocked("V2_ARTIFACT_OR_METADATA_NOT_VISUALLY_APPROVABLE")
        if (prov.get("policy_schema")!=EXPECTED_SCHEMA
                or prov.get("image_generation_mode")!="canonical-anchor-then-reference-edits"
                or prov.get("independent_text_to_image_scene_generations")!=0
                or prov.get("scene_edit_generations")!=8
                or prov.get("publication_allowed") is not False
                or len(prov.get("scenes",[]))!=8
                or any(s.get("generation_endpoint")!="images/edits" for s in prov["scenes"])):
            raise PublishBlocked("INDEPENDENT_GENERIC_FRAMES_OR_UNVERIFIED_IMAGES")
        ah={k:digest(folder/("anchor-"+k+".png")) for k in prov["anchors_sha256"]}
        if ah!=prov["anchors_sha256"] or ah!=qa.get("anchor_image_sha256"):
            raise PublishBlocked("VISUAL_CHARACTER_ANCHOR_HASH_INVALID")
        for s in prov["scenes"]:
            n=s["scene"]
            p=folder/("scene-%02d.png"%n)
            if not p.is_file() or digest(p)!=s["image_sha256"]:
                raise PublishBlocked("STORY_FRAME_HASH_INVALID")
        mp4sha=digest(paths["video"])
        coverhash=digest(paths["cover"])
        if (mp4sha!=qa.get("mp4_sha256") or mp4sha!=meta.get("mp4_sha256")
                or mp4sha!=record.get("mp4_sha256")
                or coverhash!=qa.get("cover_sha256")
                or coverhash!=meta.get("cover_sha256")
                or coverhash!=record.get("cover_sha256")
                or approval_record.get("mp4_sha256")!=mp4sha
                or approval_record.get("cover_sha256")!=coverhash
                or approval_record.get("anchors_sha256")!=ah
                or approval_record.get("eight_story_scenes_visually_confirmed") is not True
                or approval_record.get("characters_recognizable_and_consistent") is not True):
            raise PublishBlocked("PUBLISHED_ASSETS_NOT_ACTUALLY_VISUALLY_REVIEWED")
        details=probe(paths["video"])
        seconds=float(details["format"]["duration"])
        vids=[x for x in details["streams"] if x.get("codec_type")=="video"]
        audios=[x for x in details["streams"] if x.get("codec_type")=="audio"]
        if (not 90<=seconds<=121 or len(vids)!=1 or not audios
                or vids[0].get("width")!=1080 or vids[0].get("height")!=1920):
            raise PublishBlocked("V2_BAD_FINAL_MP4_TECHNICAL_QA")
        prepared=dict(meta)
        prepared["description"]=meta["description"]+DESCRIPTION_SUFFIX
        if len(prepared["description"])>5000:
            raise PublishBlocked("V2_DESCRIPTION_EXCEEDS_YOUTUBE_LIMIT")
        rendered.append({"id":original["id"],"original_episode_id":original["original_episode_id"],
                         "video":paths["video"],"cover":paths["cover"],"meta":prepared,
                         "sha":mp4sha,"cover_sha":coverhash,"seconds":round(seconds,2)})
    return rendered

def oauth():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2
    try:
        client=json.loads(os.environ["YOUTUBE_CLIENT_JSON"])
        token=json.loads(os.environ["YOUTUBE_CHANNEL_TOKEN_JSON"])
        validate_token_fields(client,token)
        scopes=token.get("scopes",[])
        recorded=set(scopes.split()) if isinstance(scopes,str) else set(scopes)
        granted_delete=bool(recorded & ALT_DELETE_SCOPES)
        creds=Credentials.from_authorized_user_info(token,scopes=list(recorded))
        if not creds.valid:creds.refresh(Request())
        http=configure_resumable_transport(httplib2.Http(timeout=180))
        youtube=build("youtube","v3",http=AuthorizedHttp(creds,http=http),
                      cache_discovery=False)
        channel=youtube.channels().list(part="id,contentDetails",mine=True).execute().get("items",[])
        if len(channel)!=1 or channel[0].get("id")!=CHANNEL_ID:
            raise PublishBlocked("WRONG_YOUTUBE_BR_OWNER")
        playlist=channel[0].get("contentDetails",{}).get("relatedPlaylists",{}).get("uploads")
        if not playlist:
            raise PublishBlocked("BR_UPLOAD_PLAYLIST_NOT_VERIFIED")
        print("OTAKU_BR_CANONICAL_V2_OAUTH_CORRECT_CHANNEL_"+CHANNEL_ID,flush=True)
        return youtube,playlist,granted_delete
    except PublishBlocked:raise
    except Exception:
        raise PublishBlocked("YOUTUBE_BR_OWNER_AUTHENTICATION_FAILED") from None

def owner_matches(youtube,playlist:str,items:list[dict],old_ids:set[str])->dict[str,list[str]]:
    # Need complete private/public upload history before any insert.
    ids=[]
    page=None
    for _ in range(100):
        kw={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page:kw["pageToken"]=page
        response=youtube.playlistItems().list(**kw).execute()
        ids.extend(x.get("contentDetails",{}).get("videoId")
                   for x in response.get("items",[])
                   if x.get("contentDetails",{}).get("videoId"))
        page=response.get("nextPageToken")
        if not page:break
    if page:
        raise PublishBlocked("OWN_UPLOAD_HISTORY_NOT_EXHAUSTIVELY_VERIFIED")
    matching={i["id"]:[] for i in items}
    titles={i["meta"]["title"]:i for i in items}
    for pos in range(0,len(ids),50):
        result=youtube.videos().list(part="snippet,status",id=",".join(ids[pos:pos+50])).execute()
        for v in result.get("items",[]):
            snippet=v.get("snippet",{})
            name=snippet.get("title")
            if name not in titles:continue
            vid=v.get("id","")
            if snippet.get("channelId")!=CHANNEL_ID:
                raise PublishBlocked("SAME_TITLE_UNOWNED_OR_UNEXPECTED_OWNER")
            if vid in old_ids:
                continue # explicit original, never confuse with replacement.
            item=titles[name]
            if snippet.get("description")!=item["meta"]["description"]:
                raise PublishBlocked("SAME_TITLE_OTHER_UNKNOWN_VIDEO_MANUAL_DEDUP")
            matching[item["id"]].append(vid)
    if any(len(found)>1 for found in matching.values()):
        raise PublishBlocked("MULTIPLE_ALREADY_UPLOADED_V2_VIDEOS")
    return matching

def insert_public(youtube,item:dict)->str:
    from googleapiclient.http import MediaFileUpload
    m=item["meta"]
    cmd=youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet":{"title":m["title"],"description":m["description"],
                       "tags":public_tags(m["tags"]),"categoryId":"24",
                       "defaultLanguage":"pt-BR"},
            "status":{"privacyStatus":"public","selfDeclaredMadeForKids":False,
                      "containsSyntheticMedia":True}
        },
        media_body=MediaFileUpload(str(item["video"]),mimetype="video/mp4",
                                   chunksize=8*1024*1024,resumable=True),
        notifySubscribers=False)
    r=None
    while r is None:
        _,r=cmd.next_chunk(num_retries=0)
    video_id=(r or {}).get("id","")
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id):
        raise PublishBlocked("BR_V2_VIDEO_ID_NOT_CONFIRMED_NO_DUPLICATE")
    return video_id

def one_video(youtube,video_id,item):
    result=youtube.videos().list(part="snippet,status,processingDetails,contentDetails",
                                 id=video_id).execute().get("items",[])
    if len(result)!=1:
        raise PublishBlocked("YOUTUBE_VIDEO_ID_LOOKUP_MISSING")
    v=result[0]
    snip=v.get("snippet",{})
    if (snip.get("channelId")!=CHANNEL_ID
            or snip.get("title")!=item["meta"]["title"]
            or snip.get("description")!=item["meta"]["description"]):
        raise PublishBlocked("PUBLIC_V2_TITLE_DESCRIPTION_OR_BR_OWNER_MISMATCH")
    return v

def wait_processed_public(youtube,video_id,item,tries=30):
    for n in range(tries):
        v=one_video(youtube,video_id,item)
        s=v.get("status",{})
        p=v.get("processingDetails",{})
        if (s.get("privacyStatus") not in ("public",None)
                or s.get("madeForKids") is True
                or s.get("selfDeclaredMadeForKids") is True):
            raise PublishBlocked("YOUTUBE_PUBLIC_OR_NOT_FOR_KIDS_STATUS_INVALID")
        if (s.get("uploadStatus")=="processed"
                and p.get("processingStatus")=="succeeded"
                and s.get("privacyStatus")=="public"
                and v.get("contentDetails",{}).get("duration") not in ("",None,"P0D","PT0S")):
            return
        if (s.get("uploadStatus") in ("failed","rejected","deleted")
                or p.get("processingStatus") in ("failed","terminated")):
            raise PublishBlocked("YOUTUBE_REJECTED_NEW_V2_VIDEO")
        if n<tries-1:time.sleep(12)
    raise PublishBlocked("PUBLIC_VIDEO_NOT_FINISHED_PROCESSING_STOP")

def save(records):
    (output()/RECEIPTS).write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",
                                   encoding="utf-8")

def publish():
    approved=guard()
    items=artifact_items(approved)
    youtube,playlist,can_delete=oauth()
    manifest=json.loads((Path(__file__).resolve().parents[1]/
                         "conteudos/otaku-br-three-character-faithful-v2-20261108.json").read_text())
    old={id for v in manifest["allowed_old_video_ids_by_episode"].values() for id in v}
    if old!={"alHbSHUN0dA"}:
        raise PublishBlocked("OLD_VIDEO_ALLOWLIST_EXPANDED_OR_CHANGED")
    old_candidate=youtube.videos().list(part="snippet,status,contentDetails",
                                         id="alHbSHUN0dA").execute().get("items",[])
    if old_candidate:
        x=old_candidate[0]
        source_title=items[0]["meta"]["title"]
        if (x.get("snippet",{}).get("channelId")!=CHANNEL_ID
                or x.get("snippet",{}).get("title")!=source_title):
            raise PublishBlocked("OLD_VIDEO_NOT_THE_ORIGINAL_BR_UPLOAD_STOP")
    else:
        print("OTAKU_BR_V2_ORIGINAL_YOUTUBE_VIDEO_NOT_PRESENT_WILL_NOT_DELETE",flush=True)
    prior=owner_matches(youtube,playlist,items,old)
    receipts=[]
    for item in items:
        record={
            "episode_id":item["id"],"channel_id":CHANNEL_ID,"old_id_allowlist":[],
            "new_youtube_id":None,"mp4_sha256":item["sha"],
            "new_public_processed":False,"thumbnail_acknowledged":False,
            "status":"insert_started_result_uncertain"
        }
        receipts.append(record)
        save(receipts)
        seen=prior[item["id"]]
        if seen:
            video_id=seen[0]
        else:
            try:
                video_id=insert_public(youtube,item)
            except Exception:
                # Upload API errors may happen after YouTube accepted the file.
                # Read own upload history: NEVER blindly repeat videos.insert.
                video_id=None
                for pause in (15,25,35):
                    time.sleep(pause)
                    now=owner_matches(youtube,playlist,[item],old)[item["id"]]
                    if now:
                        video_id=now[0]
                        break
                if not video_id:
                    raise PublishBlocked("INSERT_UNCERTAIN_NO_DUPLICATE_RETRY_"+item["id"]) from None
        record["new_youtube_id"]=video_id
        record["status"]="youtube_id_received"
        save(receipts)
        wait_processed_public(youtube,video_id,item)
        record["new_public_processed"]=True
        record["status"]="new_video_public_processed"
        save(receipts)
        from googleapiclient.http import MediaFileUpload
        try:
            time.sleep(45)
            result=youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(item["cover"]),mimetype="image/jpeg")).execute()
            record["thumbnail_acknowledged"]=bool(result.get("items"))
        except Exception:
            record["thumbnail_acknowledged"]=False
            record["thumbnail_review_required"]=True
        save(receipts)
        if not record["thumbnail_acknowledged"]:
            raise PublishBlocked("PUBLIC_V2_EXISTS_BUT_COVER_NOT_ACKNOWLEDGED_NO_REUPLOAD")
        wait_processed_public(youtube,video_id,item,tries=2)
        record["status"]="new_public_processed_cover_acknowledged"
        save(receipts)
        print("OTAKU_BR_V2_NEW_PUBLIC_VERIFIED_"+item["id"]+"_"+video_id,flush=True)
    if not len(receipts)==3 or not all(x["new_public_processed"] and x["thumbnail_acknowledged"] for x in receipts):
        raise PublishBlocked("NOT_ALL_THREE_V2_NEW_PUBLIC_NO_OLD_DELETION")
    # User explicitly requested cleanup, but tokens historically only have
    # youtube.upload + youtube.readonly. Deletion requires youtube.force-ssl,
    # youtube or youtubepartner; never try without granted OAuth scope.
    if old_candidate and can_delete:
        original=old_candidate[0]
        if (original.get("id")!="alHbSHUN0dA"
                or original.get("snippet",{}).get("channelId")!=CHANNEL_ID
                or original.get("snippet",{}).get("title")!=items[0]["meta"]["title"]
                or receipts[0]["new_youtube_id"]=="alHbSHUN0dA"):
            raise PublishBlocked("DELETE_OLD_VIDEO_NOT_SAFELY_IDENTIFIED")
        youtube.videos().delete(id="alHbSHUN0dA").execute()
        receipts[0]["original_delete_status"]="deleted_after_three_verified_public_replacements"
    elif old_candidate:
        receipts[0]["original_delete_status"]="pending_youtube_force_ssl_or_youtube_scope"
        print("OTAKU_BR_V2_OLD_VIDEO_NOT_DELETED_NEEDS_ELEVATED_OAUTH_SCOPE",flush=True)
    else:
        receipts[0]["original_delete_status"]="original_id_absent_no_delete"
    save(receipts)
    print("OTAKU_BR_V2_THREE_NEW_PUBLIC_UPLOADED_AND_VERIFIED",flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--action",choices=("preflight","publish"),default="preflight")
    args=parser.parse_args()
    try:
        if args.action=="preflight":
            validate()
            print("OTAKU_V2_PUBLISH_PREPARED_REQUIRES_VISUAL_APPROVAL_AND_ARTIFACT")
        else:publish()
        return 0
    except Exception as ex:
        message=str(ex) if isinstance(ex,(PublishBlocked,RenderBlocked)) else type(ex).__name__
        print("OTAKU_BR_V2_PUBLISH_BLOCKED_"+message,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
