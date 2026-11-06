#!/usr/bin/env python3
"""Versioned, fail-closed production registry for all five YouTube channels.

Statuses 'published', 'in_production', 'reserved', 'existing_assets_unverified'
are not eligible for automatic selection. Reservation happens in the *GitHub
repository* before ChatGPT writes a PS script, batch command or cloud workflow.
A specific reserved workflow must explicitly claim the reservation owner.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
from youtube_channel_registry import KNOWN_IDS

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'conteudos'/'otaku-production-reservations.json'
ACTIVE={'published','in_production','reserved','existing_assets_unverified','ready_for_review','private_uploaded','scheduled'}
ALL_STATUSES=ACTIVE | {'available','failed_requires_review'}
EPISODE_PATTERNS={
    'br':r'[0-9]{4}-[a-z0-9-]+',
    'en':r'[0-9]{4}-[a-z0-9-]+',
    'games':r'game-[0-9]{3}-[a-z0-9-]+',
    # A serie Fofinhos usa IDs canonicos por episodio/parte; preservar tambem
    # os IDs numerados legados. Nao aceitar outros formatos arbitrarios.
    'kids':r'(?:kids-[0-9]{3}-[a-z0-9-]+|fofinhos-[0-9]{3}-[a-z0-9-]+|kids-emanuelly-ep[0-9]{2}-p[0-9]{2}-[a-z0-9-]+)',
    'alchemy':r'alchemy-[0-9]{3}-[a-z0-9-]+',
}

def load(path:Path=LEDGER)->dict:
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema')!='autoeditorvideo/production-reservations/v1':
        raise ValueError('PRODUCTION_REGISTRY_SCHEMA_MISMATCH')
    channels=data.get('channels')
    if not isinstance(channels,dict) or set(channels)!=set(KNOWN_IDS):
        raise ValueError('PRODUCTION_CHANNELS_NOT_REGISTERED')
    for slug,expected in KNOWN_IDS.items():
        if channels[slug].get('youtube_channel_id')!=expected:
            raise ValueError('PRODUCTION_CHANNEL_ID_MISMATCH')
    rows=data.get('entries')
    if not isinstance(rows,list):
        raise ValueError('PRODUCTION_REGISTRY_ENTRIES_MISSING')
    keys=set()
    for row in rows:
        channel=row.get('channel')
        if channel not in KNOWN_IDS or not re.fullmatch(EPISODE_PATTERNS[channel],row.get('id','')):
            raise ValueError('PRODUCTION_REGISTRY_INVALID_ENTRY')
        key=(row['channel'],row['id'])
        if key in keys:
            raise ValueError('PRODUCTION_REGISTRY_DUPLICATE_ENTRY')
        if row.get('status') not in ALL_STATUSES:
            raise ValueError('PRODUCTION_REGISTRY_INVALID_STATUS')
        keys.add(key)
    return data

def get_entry(channel:str,episode_id:str,data:dict|None=None)->dict|None:
    if channel not in KNOWN_IDS:
        raise ValueError('UNKNOWN_CHANNEL')
    data=data if data is not None else load()
    return next((r for r in data['entries'] if r['channel']==channel and r['id']==episode_id),None)

def assert_reserved(channel:str,episode_id:str,owner:str,
                    *,data:dict|None=None)->dict:
    entry=get_entry(channel,episode_id,data)
    if not entry:
        raise ValueError('NOT_RESERVED_IN_GITHUB_BEFORE_GENERATION')
    if entry.get('status')!='reserved' or entry.get('reservation_owner')!=owner:
        raise ValueError('ALREADY_PUBLISHED_OR_RESERVED_BY_ANOTHER_WORKFLOW')
    return entry

def next_available(channel:str,data:dict|None=None)->str:
    data=data if data is not None else load()
    # Only BR grade-50 is a canonical ordering; EN is explicitly selected.
    if channel!='br':
        raise ValueError('CHANNEL_REQUIRES_EXPLICIT_EDITORIAL_SELECTION')
    roots=[ROOT/'conteudos'/'otaku-multicena-grade-50-a.json',
           ROOT/'conteudos'/'otaku-multicena-grade-50-b.json']
    for path in roots:
        for ep in json.loads(path.read_text(encoding='utf-8-sig'))['episodes']:
            entry=get_entry('br',ep['id'],data)
            if not entry or entry['status']=='available':
                return ep['id']
    raise ValueError('NO_FREE_EPISODE')

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--acao',choices=('proximo','verificar-reserva','status'),default='proximo')
    ap.add_argument('--canal',choices=tuple(KNOWN_IDS),default='br')
    ap.add_argument('--id',default='')
    ap.add_argument('--owner',default='')
    args=ap.parse_args()
    data=load()
    if args.acao=='proximo':
        print('[PROXIMO DISPONIVEL]',next_available(args.canal,data))
    elif args.acao=='status':
        item=get_entry(args.canal,args.id,data)
        print(json.dumps(item if item is not None else {'status':'available'},ensure_ascii=False))
    else:
        assert_reserved(args.canal,args.id,args.owner,data=data)
        print('[RESERVA VALIDADA]',args.canal,args.id)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
