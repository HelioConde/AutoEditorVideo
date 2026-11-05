#!/usr/bin/env python3
"""Repair ONLY the two existing Gachiakuta 5011 Shorts' thumbnails.

Pinned YouTube video IDs and render SHA provenance. This script NEVER calls
videos.insert, videos.update, image generation, or scheduled publication.
Private videos stay private. Separate credential per channel.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
from cloud_youtube_private_5011 import authorized_youtube, validate_review, UploadBlocked, REVIEW, ID
from youtube_short_thumbnail import attach_thumbnail, ThumbnailBlocked

CHANNEL_VIDEO_ID={
    'br':'F8kIJBor9wY',
    'en':'0urpb0yCcWw',
}

class RepairBlocked(ValueError):
    pass

def preflight(env:dict[str,str],channel:str)->None:
    if channel not in CHANNEL_VIDEO_ID:
        raise RepairBlocked('UNAPPROVED_CHANNEL')
    if env.get('GITHUB_REPOSITORY')!='HelioConde/AutoEditorVideo':
        raise RepairBlocked('WRONG_REPOSITORY')
    if env.get('GITHUB_REF')!='refs/heads/main':
        raise RepairBlocked('MAIN_ONLY')
    if env.get('GITHUB_EVENT_NAME')!='push':
        raise RepairBlocked('ONE_SHOT_MERGE_ONLY')
    if env.get('GITHUB_RUN_ATTEMPT')!='1':
        raise RepairBlocked('NO_RETRY_WITHOUT_APPROVAL')
    if env.get('REPAIR_ONLY_5011')!='true':
        raise RepairBlocked('EXPLICIT_REPAIR_GATE_REQUIRED')
    if not env.get('YOUTUBE_CLIENT_JSON') or not env.get('YOUTUBE_'+channel.upper()+'_TOKEN_JSON'):
        raise RepairBlocked('SEPARATE_YOUTUBE_OAUTH_SECRET_MISSING')

def repair(channel:str,env:dict[str,str],*,review:Path=REVIEW,
           attach=attach_thumbnail,authorized=authorized_youtube)->dict:
    preflight(env,channel)
    # Validate exact immutable artifact and protected original cover.
    path,meta,digest=validate_review(channel,review)
    if not path.is_file() or not digest:
        raise RepairBlocked('INCOMPLETE_SOURCE')
    video_id=CHANNEL_VIDEO_ID[channel]
    if video_id == CHANNEL_VIDEO_ID['en' if channel=='br' else 'br']:
        raise RepairBlocked('CROSS_CHANNEL_VIDEO_ID')
    youtube,_=authorized(env,channel)
    cover=review/f'{channel}-{ID}-cover.jpg'
    result=attach(youtube,video_id,cover)
    return {'channel':channel,'episode':ID,'video_id':video_id,
            'thumbnail_status':result['status'],'video_upload_attempted':False,
            'privacy_modified':False,'metadata_modified':False}

def main(argv=None)->int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--channel',choices=('br','en'),required=True)
    args=parser.parse_args(argv)
    try:
        result=repair(args.channel,os.environ)
        receipt=REVIEW/f'{args.channel}-{ID}-thumbnail-repair-result.json'
        receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(f'[THUMBNAIL {args.channel.upper()}] SET_API_ACKNOWLEDGED_VIDEO_ID_{result["video_id"]}')
        print('[SAFETY] ZERO_MP4_UPLOADS_ZERO_PRIVACY_CHANGES_ZERO_IMAGE_GENERATIONS')
        return 0
    except (RepairBlocked,UploadBlocked,ThumbnailBlocked) as exc:
        # Safe fixed codes only; no provider error body or OAuth details.
        print('[THUMBNAIL] '+str(exc),file=sys.stderr)
        return 1
    except Exception:
        print('[THUMBNAIL] UNCLASSIFIED_REPAIR_ERROR_NO_TOKEN_DETAILS',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
