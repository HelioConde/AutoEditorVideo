#!/usr/bin/env python3
"""Two real Shorts (BR + EN) from the ORIGINAL AutoEditorVideo engine on GitHub.

One Gachiakuta storyboard / one scene-layer generation; two separate Edge TTS
voices, captions, Remotion videos, cover/metadata and independent QA. Never
calls YouTube without verified OAuth for BOTH separate channel identities.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from production_reservations import assert_reserved
from shorts_duration import validate_video
from renderizar_shorts_en import load_english, english_metadata
from roteiro_para_storyboard import select_episode

ID="5011-gachiakuta"
OWNER="github_cloud_br_en_5011"
BUDGET_MAX=21
EN_MANIFEST=ROOT/'conteudos'/'otaku-reframe-5011-gachiakuta-en.json'
DEST=ROOT/'cloud-br-en-review-5011'
BR_CHANNEL="UCXGYTuBYn-0Ziqin5ajKhOw"
EN_CHANNEL="UCBoNbQjaMYdpJqPLRZAFkvQ"

class CloudBlocked(ValueError):
    pass

def preflight(env:dict[str,str],calls:int)->None:
    if env.get('GITHUB_REPOSITORY')!='HelioConde/AutoEditorVideo':
        raise CloudBlocked('WRONG_REPOSITORY')
    if env.get('GITHUB_REF')!='refs/heads/main' or env.get('GITHUB_EVENT_NAME')!='push':
        raise CloudBlocked('MAIN_ONE_SHOT_ONLY')
    if env.get('GITHUB_RUN_ATTEMPT')!='1':
        raise CloudBlocked('NO_RERUN_ALLOWED')
    if env.get('IMAGE_MODEL')!='gpt-image-2':
        raise CloudBlocked('WRONG_IMAGE_MODEL')
    if calls != 21:
        raise CloudBlocked('IMAGE_CALL_BUDGET_MUST_EQUAL_21')
    if not env.get('PROXY_API_KEY','').strip():
        raise CloudBlocked('MISSING_PROTECTED_PROXY_KEY')
    assert_reserved('br',ID,OWNER)
    assert_reserved('en',ID,OWNER)
    english = load_english(EN_MANIFEST)
    if len(english)!=1 or english[0]['id']!=ID:
        raise CloudBlocked('WRONG_ENGLISH_EPISODE')
    if json.loads(EN_MANIFEST.read_text(encoding='utf-8')).get('target_channel_id')!=EN_CHANNEL:
        raise CloudBlocked('EN_CHANNEL_MISMATCH')
    if select_episode(ID).get('series') != 'Gachiakuta':
        raise CloudBlocked('BR_STORYBOARD_MISMATCH')
    if DEST.exists():
        raise CloudBlocked('PREVIEW_FOLDER_ALREADY_EXISTS')

def command(args:list[str],name:str)->None:
    print('[DUAL CLOUD] ORIGINAL_ENGINE_STEP_'+name,flush=True)
    subprocess.run([sys.executable,*args],check=True,cwd=ROOT)

def assert_final_video(path:Path,label:str)->tuple[float,str]:
    if not path.is_file() or path.stat().st_size < 100_000:
        raise CloudBlocked('MISSING_FINAL_VIDEO_'+label)
    if path.stat().st_size > 450_000_000:
        raise CloudBlocked('OVERSIZE_FINAL_VIDEO_'+label)
    dur=validate_video(path,stage='AutoEditorVideo GitHub '+label)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return dur,digest

def package_both()->dict:
    folder=ROOT/'assets'/'gerados'/'shorts-animados'/ID
    br_video=folder/f'{ID}-master-multicenas-personagens-v3-equilibrado.mp4'
    en_video=folder/'en-US'/f'{ID}-en-US-master-multicenas-personagens-v3-equilibrado.mp4'
    br_cover=folder/f'{ID}-master-capa.jpg'
    en_cover=folder/'en-US'/f'{ID}-en-US-master-capa.jpg'
    br_qa=folder/'qa-master-multicenas.json'
    en_qa=folder/'en-US'/'qa-en-US.json'
    originals=[
        ('br',br_video,br_cover,br_qa),
        ('en',en_video,en_cover,en_qa)
    ]
    summary={'schema':'autoeditorvideo/dual-cloud-review/v1',
             'episode':ID,'youtube_uploads':[],
             'upload_request':'private to separate BR/EN channels after independently verified YouTube OAuth',
             'render_origin':'original AutoEditorVideo Remotion in GitHub Actions',
             'videos':[],'publication':'not_performed'}
    for channel,video,cover,qa_file in originals:
        if not cover.is_file() or not qa_file.is_file():
            raise CloudBlocked('MISSING_COVER_OR_QA_'+channel)
        duration,digest=assert_final_video(video,channel)
        with Image.open(cover) as im:
            im.load()
            if im.format!='JPEG' or abs(im.width/im.height-9/16)>.02:
                raise CloudBlocked('INVALID_COVER_'+channel)
        qa=json.loads(qa_file.read_text(encoding='utf-8'))
        if qa.get('id')!=ID or qa.get('published') is not False:
            raise CloudBlocked('QA_WRONG_EPISODE_OR_ALREADY_PUBLISHED_'+channel)
        if channel=='br' and qa.get('status')!='renderizado-aguardando-revisao':
            raise CloudBlocked('INVALID_BR_QA')
        if channel=='en':
            if qa.get('language')!='en-US' or qa.get('video_sha256')!=digest:
                raise CloudBlocked('EN_QA_NOT_BOUND_TO_EN_MP4')
            if qa.get('status') not in ('renderizado_qa_automatico','renderizado_aguardando_revisao'):
                raise CloudBlocked('INVALID_EN_QA')
        summary['videos'].append({
            'channel':channel,
            'expected_youtube_channel_id':BR_CHANNEL if channel=='br' else EN_CHANNEL,
            'language':'pt-BR' if channel=='br' else 'en-US',
            'mp4':f'{channel}-{ID}-autoeditorvideo.mp4',
            'cover':f'{channel}-{ID}-cover.jpg',
            'duration_s':round(duration,2),'sha256':digest,
            'qa_status':qa['status']
        })
    # Do not release ANY partially rendered single-channel video.
    DEST.mkdir(parents=True,mode=0o700)
    for channel,video,cover,qa in originals:
        shutil.copyfile(video,DEST/f'{channel}-{ID}-autoeditorvideo.mp4')
        shutil.copyfile(cover,DEST/f'{channel}-{ID}-cover.jpg')
        # Extract safe QA aggregate only; full QA paths/caches can be sensitive.
    br=select_episode(ID)
    en=load_english(EN_MANIFEST)[0]
    (DEST/f'br-{ID}-metadata.json').write_text(json.dumps({
        'channel_id':BR_CHANNEL,'title':br['title'],
        'description':br['description_youtube'],'tags':['Gachiakuta','Rudo','Otaku Multicena'],
        'privacy':'private','scheduled_at':None
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DEST/f'en-{ID}-metadata.json').write_text(json.dumps({
        'channel_id':EN_CHANNEL,**english_metadata(en),
        'privacy':'private','scheduled_at':None
    },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DEST/'review-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary

def main(argv=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--max-image-calls',type=int,required=True)
    args=ap.parse_args(argv)
    try:
        preflight(os.environ,args.max_image_calls)
        from master_scenes import production_storyboard,read_storyboard,estimate
        plan=read_storyboard(production_storyboard(ID,6))
        missing=len(estimate(plan,plan['scenes'],'gpt-image-2'))
        print(f'[DUAL CLOUD] BR_SCENES_{len(plan["scenes"])}_ESTIMATED_IMAGE_CALLS_{missing}',flush=True)
        if missing > args.max_image_calls:
            raise CloudBlocked('CALLS_EXCEED_AUTHORIZED_LIMIT')
        command(['scripts/fluxo_unico_short.py','--id',ID,
                 '--modelo','gpt-image-2','--voz-motor','edge',
                 '--perfil','equilibrado','--max-chamadas',str(args.max_image_calls),
                 '--tentativas','1','--privacidade','private'],'BR')
        # Reuse the exact official BR layered scene cache. New English voice,
        # English subtitles, independent cover and Remotion render.
        command(['scripts/renderizar_shorts_en.py','--acao','renderizar',
                 '--manifesto',str(EN_MANIFEST),'--id',ID,
                 '--modelo','gpt-image-2','--perfil','equilibrado'],'EN')
        info=package_both()
        print('[DUAL CLOUD] VALIDATED_TWO_MP4S_'+str(len(info['videos'])),flush=True)
        print('[DUAL CLOUD] YOUTUBE_UPLOAD_PENDING_SEPARATE_OAUTH_AND_CHANNEL_CHECK',flush=True)
        return 0
    except (CloudBlocked,ValueError,RuntimeError,OSError,subprocess.CalledProcessError) as exc:
        # Never include arbitrary provider messages/tokens in log.
        if isinstance(exc,CloudBlocked):
            print('[DUAL CLOUD] BLOCKED_'+str(exc),file=sys.stderr)
        else:
            print('[DUAL CLOUD] ORIGINAL_PIPELINE_OR_QA_FAILED_NO_PUBLICATION',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
