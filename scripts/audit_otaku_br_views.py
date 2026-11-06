#!/usr/bin/env python3
"""A strictly READ-ONLY snapshot of PUBLIC Otaku Multicena video statistics.

Uses existing protected BR OAuth to verify the YouTube channel, then calls
only channels.list, playlistItems.list, videos.list. Never uploads or edits.
Prints public aggregate data and highest/lowest videos for evidence-based audit.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from cloud_youtube_private_5011 import authorized_youtube

CHANNEL="UCXGYTuBYn-0Ziqin5ajKhOw"
OUT=ROOT/"audit-output"/"otaku-multicena-public-stats.json"
WORKFLOW="otaku-br-readonly-audit.yml"

def denied(message:str):
    raise ValueError(message)

def fetch() -> dict:
    if os.getenv("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        denied("REPOSITORY_NOT_ALLOWED")
    if os.getenv("GITHUB_REF")!="refs/heads/main":
        denied("MAIN_ONLY")
    if os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        denied("NO_REPEAT_UNCONTROLLED_AUDITS")
    youtube,playlist=authorized_youtube(os.environ,"br")
    ids=[]
    page=None
    for _ in range(20):
        request={"part":"contentDetails","playlistId":playlist,"maxResults":50}
        if page: request["pageToken"]=page
        data=youtube.playlistItems().list(**request).execute()
        ids.extend((x.get("contentDetails") or {}).get("videoId") for x in data.get("items") or [])
        page=data.get("nextPageToken")
        if not page: break
    else: denied("HISTORY_TOO_LARGE_OR_INCOMPLETE")
    ids=list(dict.fromkeys(x for x in ids if isinstance(x,str) and len(x)==11))
    if not ids: denied("NO_UPLOADS_FOUND")
    now=datetime.now(timezone.utc)
    rows=[]
    for i in range(0,len(ids),50):
        v=youtube.videos().list(part="snippet,status,statistics,contentDetails",id=",".join(ids[i:i+50]),maxResults=50).execute()
        for item in v.get("items") or []:
            status=item.get("status") or {}
            if status.get("privacyStatus")!="public":
                continue
            snippet=item.get("snippet") or {}
            if snippet.get("channelId")!=CHANNEL:
                denied("VIDEO_CHANNEL_ID_MISMATCH")
            stats=item.get("statistics") or {}
            published=snippet.get("publishedAt") or ""
            age_hours=None
            try:
                age_hours=max(0.0,(now-datetime.fromisoformat(published.replace("Z","+00:00"))).total_seconds()/3600)
            except (TypeError,ValueError):
                pass
            vid=item.get("id") or ""
            title=snippet.get("title") or ""
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):
                continue
            views=int(stats.get("viewCount") or 0)
            likes=int(stats.get("likeCount") or 0)
            comments=int(stats.get("commentCount") or 0)
            rows.append({
              "id":vid,"title":title,"published_at":published,
              "views":views,"likes":likes,"comments":comments,
              "like_rate_percent":round(100*likes/views,2) if views else None,
              "age_hours":round(age_hours,2) if age_hours is not None else None,
              "views_per_elapsed_hour":round(views/age_hours,2) if age_hours and age_hours>0 else None,
              "duration":(item.get("contentDetails") or {}).get("duration"),
              "url":"https://www.youtube.com/watch?v="+vid,
            })
    rows.sort(key=lambda x:x["published_at"],reverse=True)
    count=len(rows)
    if count==0: denied("NO_PUBLIC_VIDEOS_FOUND")
    channel=youtube.channels().list(part="statistics",id=CHANNEL).execute().get("items") or []
    if len(channel)!=1: denied("CHANNEL_STATISTICS_NOT_VERIFIED")
    ch=channel[0].get("statistics") or {}
    summary={
      "channel_id":CHANNEL,
      "measured_at_utc":now.isoformat(),
      "source":"YouTube Data API v3 via protected BR read-only OAuth",
      "public_video_count":count,
      "public_video_total_views":sum(x["views"] for x in rows),
      "channel_lifetime_views":int(ch.get("viewCount") or 0),
      "channel_subscribers":int(ch.get("subscriberCount") or 0),
      "channel_public_video_count":int(ch.get("videoCount") or 0),
      "publisher": "Otaku Multicena",
      "recent_2026_11_06_count":sum(x["published_at"][:10]=="2026-11-06" for x in rows),
      "rank_by_views":sorted(rows,key=lambda x:x["views"],reverse=True)[:20],
      "rank_by_like_rate_min_40_views":sorted((x for x in rows if x["views"]>=40),key=lambda x:x["like_rate_percent"] or 0,reverse=True)[:15],
      "videos":rows,
      "limitations":"Views and likes are cumulative snapshots (not Shorts engaged views, retention, completion, scroll-away, or watch time). Age normalization is not the same as live VPH."
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Printed content is PUBLIC statistics only: no private videos or OAuth data.
    print("[AUDIT] CHANNEL_PUBLIC_STATS "+json.dumps({
       "snapshot":summary["measured_at_utc"],
       "public_videos":count,
       "total_public_video_views":summary["public_video_total_views"],
       "channel_lifetime_views":summary["channel_lifetime_views"],
       "subscribers":summary["channel_subscribers"]},ensure_ascii=False),flush=True)
    for i,v in enumerate(rows,1):
        print("[PUBLIC_VIDEO] "+json.dumps(v,ensure_ascii=False),flush=True)
    print("[AUDIT] COMPLETED_READ_ONLY_NO_CHANGES",flush=True)
    return summary

if __name__=="__main__":
    try:
        fetch()
    except Exception:
        raise SystemExit("[AUDIT BLOCKED] READ_ONLY_CHANNEL_STATS_FAILED_NO_VIDEOS_MODIFIED") from None
