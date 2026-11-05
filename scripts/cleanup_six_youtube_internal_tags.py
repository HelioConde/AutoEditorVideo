#!/usr/bin/env python3
"""Remove ONLY technical AutoEditorVideo tags on six owner-approved Shorts.

No videos.insert/delete, no thumbnails, no privacy changes. Read each current
YouTube snippet, copy EVERY writable snippet field, change tags only, then
re-fetch and verify the preserved data. Fail closed for a wrong OAuth channel.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys

from youtube_channel_registry import get_channel,KNOWN_IDS
from youtube_public_tags import public_tags,internal_tags

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"youtube-clean-tags-receipts"
MARKER=ROOT/"conteudos/games-alchemy-six-clean-internal-tags-20261105.json"
WORKFLOW="Gamer + Alchemy - remove internal YouTube SEO tags from six Shorts"
EXPECTED={
  "games":("GPJa03DRf5Y","BCqrEmJa77E","j7_cAomsPvM"),
  "alchemy":("WNlK9OYe1jc","bk433QOIdK0","iKlsUANJ8og"),
}

class TagCleanupBlocked(ValueError): pass

def preflight(channel:str)->list[str]:
    e=os.environ
    if (channel not in EXPECTED or
        e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo" or
        e.get("GITHUB_REF")!="refs/heads/main" or
        e.get("GITHUB_EVENT_NAME")!="push" or
        e.get("GITHUB_RUN_ATTEMPT")!="1" or
        e.get("GITHUB_WORKFLOW")!=WORKFLOW or
        e.get("REMOVE_INTERNAL_TAGS_APPROVED")!="true"):
        raise TagCleanupBlocked("ONE_SHOT_MAIN_SCOPE_REQUIRED")
    cfg=get_channel(channel)
    secret="YOUTUBE_GAMES_TOKEN_JSON" if channel=="games" else "YOUTUBE_ALCHEMY_TOKEN_JSON"
    if (cfg.get("youtube_channel_id")!=KNOWN_IDS[channel] or
        cfg.get("oauth_token_secret_name")!=secret or
        cfg.get("youtube_environment")!="youtube-private-upload" or
        not e.get("YOUTUBE_CLIENT_JSON") or not e.get("YOUTUBE_CHANNEL_TOKEN_JSON")):
        raise TagCleanupBlocked("OAUTH_CHANNEL_SCOPE_FAILED")
    marker=json.loads(MARKER.read_text(encoding="utf-8"))
    if (marker.get("schema")!="autoeditorvideo/six-private-shorts-internal-tags-cleanup/v1" or
        marker.get("approved_by_creator") is not True or
        marker.get("scope")!="existing_uploads_only_no_new_video" or
        marker.get("channels",{}).get(channel)!=list(EXPECTED[channel]) or
        marker.get("preserve_titles_descriptions_privacy_thumbnails") is not True):
        raise TagCleanupBlocked("APPROVAL_MANIFEST_NOT_MATCHED")
    if (OUTPUT/(channel+".json")).exists():
        raise TagCleanupBlocked("OUTPUT_ALREADY_EXISTS_REFUSE_REPLAY")
    return list(EXPECTED[channel])

def read(api,video_id:str,channel:str)->dict:
    response=api.videos().list(part="snippet,status",id=video_id).execute()
    items=response.get("items",[])
    if len(items)!=1:
        raise TagCleanupBlocked("VIDEO_NOT_VISIBLE_TO_OWNER_"+video_id)
    v=items[0]
    if (v.get("id")!=video_id or v.get("snippet",{}).get("channelId")!=KNOWN_IDS[channel] or
        v.get("status",{}).get("privacyStatus") not in ("private","unlisted","public")):
        raise TagCleanupBlocked("WRONG_IDENTITY_OR_UNKNOWN_PRIVACY_"+video_id)
    s=v["snippet"]
    if not s.get("title") or not s.get("categoryId"):
        raise TagCleanupBlocked("REQUIRED_SNIPPET_FIELDS_MISSING_"+video_id)
    return v

def preserved_snippet(s:dict,tags:list[str])->dict:
    # YouTube replaces all mutable fields of a part on videos.update.
    # title/categoryId are required; description/defaultLanguage are copied.
    payload={
       "title":s["title"],
       "description":s.get("description",""),
       "categoryId":s["categoryId"],
       "tags":tags,
    }
    if s.get("defaultLanguage"):
        payload["defaultLanguage"]=s["defaultLanguage"]
    return payload

def cleanup(channel:str)->None:
    ids=preflight(channel)
    from games_alchemy_ai_upload import get_youtube
    api=get_youtube(channel,dict(os.environ))
    mine=api.channels().list(part="id",mine=True).execute().get("items",[])
    if [x.get("id") for x in mine]!=[KNOWN_IDS[channel]]:
        raise TagCleanupBlocked("AUTHENTICATED_CHANNEL_IS_NOT_EXPECTED_"+channel)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    receipt_path=OUTPUT/(channel+".json")
    results=[]
    for id in ids:
        before=read(api,id,channel)
        s=before["snippet"]
        before_tags=s.get("tags",[])
        removed=internal_tags(before_tags)
        keep=public_tags(before_tags)
        if not keep:
            raise TagCleanupBlocked("WILL_NOT_REMOVE_ALL_TAGS_"+id)
        entry={"video_id":id,"channel":channel,"original_count":len(before_tags),
               "removed_internal_tags":removed,"preserved_count":len(keep),
               "action":"pending","verified":False}
        results.append(entry)
        # Save which IDs are about to be changed before starting a write.
        receipt_path.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        if removed:
            api.videos().update(
              part="snippet",
              body={"id":id,"snippet":preserved_snippet(s,keep)}
            ).execute(num_retries=0)
            entry["action"]="removed_internal_tags"
        else:
            entry["action"]="already_clean"
        after=read(api,id,channel)
        now=after["snippet"]
        if (now.get("tags",[])!=keep or
            now.get("title")!=s.get("title") or
            now.get("description","")!=s.get("description","") or
            now.get("categoryId")!=s.get("categoryId") or
            now.get("defaultLanguage")!=s.get("defaultLanguage") or
            after.get("status",{}).get("privacyStatus")!=before.get("status",{}).get("privacyStatus")):
            raise TagCleanupBlocked("VIDEO_SNIPPET_PRESERVATION_FAILED_"+id)
        entry["verified"]=True
        receipt_path.write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(f"SEO_TAG_CLEANUP_{channel}_{id}_removed_{len(removed)}_preserved_{len(keep)}_verified",flush=True)
    if len(results)!=3 or not all(x["verified"] for x in results):
        raise TagCleanupBlocked("THREE_RESULTS_NOT_VERIFIED")
    print("SEO_TAG_CLEANUP_THREE_VERIFIED_"+channel,flush=True)

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--channel",choices=list(EXPECTED),required=True)
    opts=parser.parse_args()
    try:
        cleanup(opts.channel)
    except Exception as exc:
        print("SEO_TAG_CLEANUP_BLOCKED_"+(str(exc) if isinstance(exc,TagCleanupBlocked) else type(exc).__name__),file=sys.stderr)
        raise SystemExit(2)
