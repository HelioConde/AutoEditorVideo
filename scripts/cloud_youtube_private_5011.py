#!/usr/bin/env python3
"""Publish the two verified AutoEditorVideo 5011 Shorts as PRIVATE to YouTube.

Only when expressly triggered by user with correct, separate YouTube OAuth
for both channels. No interactive OAuth on CI, no scheduling, no proxy tokens.
No raw provider errors or credential fields printed. Source MP4s must match
the SHA-256 stored in the first successful AutoEditorVideo Actions artifact.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from youtube_short_thumbnail import attach_thumbnail, ThumbnailBlocked, verified_generated_cover
from youtube_upload_profiles import build_insert_body, upload_notify_subscribers, UploadProfileError

ROOT=Path(__file__).resolve().parents[1]
REVIEW=ROOT/'cloud-br-en-review-5011'
ID='5011-gachiakuta'
EXPECTED={
    'br':('UCXGYTuBYn-0Ziqin5ajKhOw','YOUTUBE_BR_TOKEN_JSON'),
    'en':('UCBoNbQjaMYdpJqPLRZAFkvQ','YOUTUBE_EN_TOKEN_JSON'),
}
CLIENT_SECRET='YOUTUBE_CLIENT_JSON'
SCOPES=['https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube.readonly']


class UploadBlocked(ValueError):
    pass


def preflight(env:dict[str,str],channel:str)->None:
    if channel not in ('br','en'):
        raise UploadBlocked('CHANNEL_NOT_ALLOWED')
    if env.get('GITHUB_REPOSITORY')!='HelioConde/AutoEditorVideo':
        raise UploadBlocked('WRONG_REPOSITORY')
    if env.get('GITHUB_REF')!='refs/heads/main' or env.get('GITHUB_EVENT_NAME')!='workflow_dispatch':
        raise UploadBlocked('UNAUTHORIZED_EVENT')
    if env.get('GITHUB_RUN_ATTEMPT')!='1':
        raise UploadBlocked('RERUN_BLOCKED')
    if env.get('PRIVATE_UPLOAD_CONFIRMED')!='true':
        raise UploadBlocked('EXPLICIT_PRIVATE_APPROVAL_REQUIRED')
    expected,token_var=EXPECTED[channel]
    if not env.get(CLIENT_SECRET) or not env.get(token_var):
        raise UploadBlocked('YOUTUBE_CHANNEL_OAUTH_NOT_CONFIGURED')
    if env.get('EXPECTED_CHANNEL_ID')!=expected:
        raise UploadBlocked('EXPECTED_CHANNEL_ID_MISMATCH')


def validate_review(channel:str,dir:Path=REVIEW)->tuple[Path,dict,str]:
    summary=json.loads((dir/'review-summary.json').read_text(encoding='utf-8'))
    if summary.get('schema') not in ('autoeditorvideo/dual-cloud-review/v1','autoeditorvideo/dual-cloud-review/v2') or summary.get('episode')!=ID:
        raise UploadBlocked('BAD_SOURCE_ARTIFACT')
    if summary.get('publication')!='not_performed' or len(summary.get('videos',[]))!=2:
        raise UploadBlocked('NOT_A_TWO_CHANNEL_REVIEW_ARTIFACT')
    # Fail BEFORE videos.insert if the exact original generated thumbnail is
    # missing. Never choose a random frame or use YouTube-generated alternatives.
    verified_generated_cover(dir,summary,channel,ID)
    item=next((x for x in summary['videos'] if x.get('channel')==channel),None)
    if not item:
        raise UploadBlocked('MISSING_CHANNEL_IN_ARTIFACT')
    expected_id=EXPECTED[channel][0]
    if item.get('expected_youtube_channel_id')!=expected_id:
        raise UploadBlocked('ARTIFACT_CHANNEL_MISMATCH')
    path=dir/f'{channel}-{ID}-autoeditorvideo.mp4'
    if item.get('mp4')!=path.name or not path.is_file() or path.stat().st_size<100_000:
        raise UploadBlocked('MISSING_OR_WRONG_MP4')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=item.get('sha256'):
        raise UploadBlocked('MP4_HASH_MISMATCH')
    metadata=json.loads((dir/f'{channel}-{ID}-metadata.json').read_text(encoding='utf-8'))
    if metadata.get('channel_id')!=expected_id or metadata.get('privacy')!='private':
        raise UploadBlocked('NON_PRIVATE_OR_WRONG_CHANNEL_METADATA')
    if metadata.get('scheduled_at') is not None:
        raise UploadBlocked('UNAPPROVED_SCHEDULE')
    title=metadata.get('title') if channel=='br' else metadata.get('titulo')
    description=metadata.get('description') if channel=='br' else metadata.get('descricao')
    if not isinstance(title,str) or not 1<=len(title)<=100:
        raise UploadBlocked('BAD_TITLE')
    if not isinstance(description,str) or not 20<=len(description)<=5000:
        raise UploadBlocked('BAD_DESCRIPTION')
    return path,metadata,digest


def authorized_youtube(env:dict[str,str],channel:str):
    _,token_var=EXPECTED[channel]
    try:
        client=json.loads(env[CLIENT_SECRET])
        token=json.loads(env[token_var])
        if not isinstance(client,dict) or not isinstance(token,dict):
            raise UploadBlocked('INVALID_OAUTH_JSON')
        installed=client.get('installed') or client.get('web')
        if not isinstance(installed,dict):
            raise UploadBlocked('BAD_OAUTH_CLIENT')
        if not installed.get('client_id') or not installed.get('client_secret'):
            raise UploadBlocked('MISSING_OAUTH_CLIENT_FIELDS')
        # Token JSON from Google auth's Credentials.to_json() contains its own
        # client_id/client_secret and refresh_token; cross-check client identity.
        if token.get('client_id')!=installed.get('client_id'):
            raise UploadBlocked('CLIENT_AND_TOKEN_MISMATCH')
        credentials=Credentials.from_authorized_user_info(token,scopes=SCOPES)
        if not credentials.refresh_token:
            raise UploadBlocked('MISSING_YOUTUBE_REFRESH_TOKEN')
        if not credentials.valid:
            credentials.refresh(Request())
        youtube=build('youtube','v3',credentials=credentials,cache_discovery=False)
        response=youtube.channels().list(part='id,contentDetails',mine=True).execute()
        channels=response.get('items') or []
        if len(channels)!=1 or channels[0].get('id')!=EXPECTED[channel][0]:
            raise UploadBlocked('OAUTH_BELONGS_TO_ANOTHER_YOUTUBE_CHANNEL')
        playlist=channels[0].get('contentDetails',{}).get('relatedPlaylists',{}).get('uploads')
        if not isinstance(playlist,str) or not playlist:
            raise UploadBlocked('CHANNEL_UPLOAD_PLAYLIST_UNVERIFIED')
        return youtube,playlist
    except UploadBlocked:
        raise
    except Exception:
        # Never print Google OAuth client/token or YouTube private error bodies.
        raise UploadBlocked('YOUTUBE_AUTHENTICATION_FAILED') from None


def exists_in_playlist(youtube,playlist:str,marker:str,title:str)->str|None:
    page=None
    # Read all pages, including private uploads, to avoid duplicate uploads.
    # If API pagination is abnormal, fail closed rather than skip the check.
    for _ in range(100):
        args={'part':'snippet,contentDetails','playlistId':playlist,'maxResults':50}
        if page:
            args['pageToken']=page
        data=youtube.playlistItems().list(**args).execute()
        for row in data.get('items') or []:
            snippet=row.get('snippet') or {}
            item_title=snippet.get('title') or ''
            video_id=(row.get('contentDetails') or {}).get('videoId')
            desc=snippet.get('description') or ''
            if marker in desc or (item_title==title and video_id):
                if not video_id:
                    raise UploadBlocked('AMBIGUOUS_PRIOR_UPLOAD')
                return video_id
        page=data.get('nextPageToken')
        if not page:
            return None
    raise UploadBlocked('UPLOAD_HISTORY_PAGINATION_INCOMPLETE')


def publish_one(env:dict[str,str],channel:str,output_dir:Path=REVIEW)->dict:
    preflight(env,channel)
    path,meta,digest=validate_review(channel,output_dir)
    youtube,playlist=authorized_youtube(env,channel)
    title=meta.get('title') if channel=='br' else meta['titulo']
    description=meta.get('description') if channel=='br' else meta['descricao']
    tags=meta.get('tags') or []
    # Legacy uploads may contain this tracking marker in their description.
    # Read it ONLY to detect historical duplicates; never write it publicly.
    internal_upload_key=f'AUTOEDITORVIDEO-5011-{channel}-{digest[:16]}'
    prior=exists_in_playlist(youtube,playlist,internal_upload_key,title)
    if prior:
        # A prior upload, private or otherwise, MUST NOT be repeated.
        print(f'[YOUTUBE {channel.upper()}] ALREADY_EXISTS_NO_SECOND_UPLOAD')
        return {'channel':channel,'id':ID,'status':'existing','video_id':prior,
                'internal_upload_key':internal_upload_key}
    prepared=dict(meta)
    # Upload idempotency belongs in the internal receipt, NOT the published
    # title/description/hashtags/tags. The upload profile also strips any
    # legacy IDs accidentally present inside an authored manifest.
    prepared['description' if channel=='br' else 'descricao']=description
    body=build_insert_body(channel,prepared,privacy='private')
    if body['status']['privacyStatus']!='private':
        raise UploadBlocked('PRIVATE_ONLY_CLOUD_UPLOAD')
    print(f'[YOUTUBE {channel.upper()}] CHANNEL_VERIFIED_SENDING_PRIVATE')
    media=MediaFileUpload(str(path),mimetype='video/mp4',chunksize=4*1024*1024,resumable=True)
    command=youtube.videos().insert(part='snippet,status',body=body,
                                    notifySubscribers=upload_notify_subscribers(channel),
                                    media_body=media)
    response=None
    try:
        while response is None:
            _,response=command.next_chunk()
        video_id=response.get('id') or ''
        if len(video_id)!=11 or (response.get('status') or {}).get('privacyStatus')!='private':
            raise UploadBlocked('UPLOAD_NOT_CONFIRMED_PRIVATE_DO_NOT_RETRY')
        print(f'[YOUTUBE {channel.upper()}] PRIVATE_UPLOAD_CONFIRMED_VIDEO_ID_{video_id}')
        return {'channel':channel,'id':ID,'status':'private','video_id':video_id,
                'internal_upload_key':internal_upload_key}
    except UploadBlocked:
        raise
    except Exception:
        raise UploadBlocked('UPLOAD_AMBIGUOUS_CHECK_STUDIO_BEFORE_ANY_RETRY') from None


def main(argv=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--channel',choices=('br','en'),required=True)
    args=ap.parse_args(argv)
    try:
        record=publish_one(os.environ,args.channel)
        file=REVIEW/f'private-upload-result-{args.channel}.json'
        # Persist the UPLOAD RECEIPT before any thumbnail API request.
        # Thumbnail errors MUST NEVER be treated as reasons to resend MP4.
        file.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        try:
            youtube,_=authorized_youtube(os.environ,args.channel)
            summary=json.loads((REVIEW/'review-summary.json').read_text(encoding='utf-8'))
            cover,digest=verified_generated_cover(REVIEW,summary,args.channel,ID)
            record['generated_cover_sha256']=digest
            result=attach_thumbnail(youtube,record['video_id'],cover)
        except (UploadBlocked,ThumbnailBlocked) as exc:
            record['thumbnail_status']='pending'
            record['thumbnail_error_code']=str(exc)
            file.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            print('[YOUTUBE] MP4_ALREADY_UPLOADED_DO_NOT_REUPLOAD',file=sys.stderr)
            raise
        record['thumbnail_status']=result['status']
        file.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        print('[YOUTUBE] PRIVATE_MP4_AND_COVER_API_ACKNOWLEDGED')
        return 0
    except (UploadBlocked,ThumbnailBlocked,UploadProfileError) as exc:
        print('[YOUTUBE] '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
