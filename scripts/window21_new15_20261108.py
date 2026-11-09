#!/usr/bin/env python3
"""Window 21h 2026-11-08: a SECOND, distinct reserved batch of 15 original Shorts.

Reuses tested rendering and private-upload code WITHOUT reusing previous episodes,
media, receipts or YouTube IDs. No public publishing and no editorial image-call cap.
The provider's technical quota and auth/safety controls remain mandatory.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import five_channel_fifteen_20261108 as batch
import five_channel_fifteen_upload_20261108 as uploader
from youtube_channel_registry import KNOWN_IDS

WORKFLOW = "AutoEditorVideo - janela 21h novos 15 privados 20261108"
OWNER = "janela21_novos_20261108"
MANIFEST = ROOT / "conteudos" / "lote-15-janela21-20261108.json"
LAUNCH = ROOT / "conteudos" / "lote-15-janela21-20261108-launch.json"
OUTPUT_ROOT = ROOT / "cloud-lote-15-janela21-20261108"
EXPECTED = {
    "br": ("5018-blue-box-silencios", "5019-apothecary-pistas", "5020-cyberpunk-implantes"),
    "en": ("7017-death-note-memories", "7018-bleach-bankai", "7019-steel-ball-run-spin"),
    "games": ("game-107-hollow-knight-mapa", "game-108-hades-escolhas", "game-109-oxygen-not-included-calor"),
    "kids": ("kids-107-passarinhos-ninho", "kids-108-sementinha-jardim", "kids-109-peixinho-coragem"),
    "alchemy": ("alchemy-108-aprovacao-humana", "alchemy-109-contexto-ia", "alchemy-110-fontes-confiaveis"),
}

class WindowBlocked(RuntimeError):
    pass

def initialize():
    batch.MANIFEST = MANIFEST
    batch.OUTPUT_ROOT = OUTPUT_ROOT
    batch.OWNER = OWNER
    batch.WORKFLOW = WORKFLOW
    batch.EXPECTED = EXPECTED
    batch.engine.OUTPUT_ROOT = OUTPUT_ROOT
    uploader.OWNER = OWNER
    uploader.EXPECTED = EXPECTED
    uploader.WORKFLOW = WORKFLOW
    uploader.output = batch.output
    uploader.validate = batch.validate
    batch.guard = render_guard

def verify_manifest():
    launch = json.loads(LAUNCH.read_text(encoding="utf-8"))
    if launch != {
        "schema": "autoeditorvideo/new-window21-private-once/v1",
        "date": "2026-11-08",
        "time_local": "21:00",
        "timezone": "America/Sao_Paulo",
        "creator_authorized": True,
        "intent": "new_15_videos_five_channels_private_fallback_after_21h",
        "production_owner": OWNER,
        "no_public_publish": True,
        "no_duplicate_episodes": True,
        "no_editorial_image_call_cap": True,
        "requires_channel_id_verification": True
    }:
        raise WindowBlocked("LAUNCH_INTENT_OR_PRIVACY_CHANGED")
    d = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if d.get("production_owner") != OWNER or d.get("status") != "new_original_narrations_pending_render":
        raise WindowBlocked("MANIFEST_OR_OWNER_CHANGED")
    ids = [(x.get("channel"),x.get("id")) for x in d.get("episodes",[])]
    if len(ids)!=15 or len(set(ids))!=15:
        raise WindowBlocked("REQUIRES_15_NEW_UNIQUE_EPISODES")
    previous = json.loads((ROOT/"dados/publicacoes/2026-11-08-lote15-recibos-verificados.json").read_text(encoding="utf-8"))
    prior = {(x["channel"],x["episode_id"]) for x in previous["videos"]}
    if prior.intersection(ids):
        raise WindowBlocked("OVERLAP_WITH_15_ALREADY_UPLOADED")
    for channel,seq in EXPECTED.items():
        if tuple(x["id"] for x in d["episodes"] if x["channel"]==channel)!=seq:
            raise WindowBlocked("CHANNEL_EPISODES_CHANGED")
        for ep in (x for x in d["episodes"] if x["channel"]==channel):
            if ep.get("channel_id")!=KNOWN_IDS[channel] or ep.get("made_for_kids") is not (channel=="kids"):
                raise WindowBlocked("CHANNEL_OR_AUDIENCE_MISMATCH")
    return d

def render_guard(channel):
    e=os.environ
    if not (
        channel in EXPECTED and
        e.get("GITHUB_REPOSITORY")=="HelioConde/AutoEditorVideo" and
        e.get("GITHUB_REF")=="refs/heads/main" and
        e.get("GITHUB_EVENT_NAME")=="push" and
        e.get("GITHUB_RUN_ATTEMPT")=="1" and
        e.get("GITHUB_WORKFLOW")==WORKFLOW and
        e.get("BATCH15_CHANNEL")==channel and
        e.get("BATCH15_RENDER_AUTHORIZED")=="yes" and
        e.get("IMAGE_MODEL")=="gpt-image-2"
    ):
        raise WindowBlocked("MAIN_FIRST_PUSH_RENDER_AUTHORIZATION_REQUIRED")
    if any(e.get(k) for k in (
        "YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
        "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
        "YOUTUBE_GAMES_TOKEN_JSON","YOUTUBE_KIDS_TOKEN_JSON",
        "YOUTUBE_ALCHEMY_TOKEN_JSON"
    )):
        raise WindowBlocked("YOUTUBE_SECRETS_MUST_NOT_REACH_IMAGE_RENDER")
    # Deliberately DO NOT check/set MAX_IMAGE_CALLS or IMAGE_BUDGET:
    # the creator removed editorial hard caps. Provider quotas still apply.

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",required=True,choices=tuple(EXPECTED))
    ap.add_argument("--action",required=True,choices=("validate","render","upload"))
    args=ap.parse_args()
    try:
        initialize()
        verify_manifest()
        if args.action=="validate":
            batch.validate(args.channel)
            print("WINDOW21_VALIDATED_"+args.channel,flush=True)
        elif args.action=="render":
            batch.produce(args.channel)
            print("WINDOW21_RENDERED_"+args.channel,flush=True)
        else:
            uploader.upload(args.channel)
            print("WINDOW21_PRIVATE_UPLOAD_VERIFIED_"+args.channel,flush=True)
        return 0
    except Exception as ex:
        print("WINDOW21_BLOCKED_"+type(ex).__name__+
              ("_"+str(ex) if isinstance(ex,WindowBlocked) else ""),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
