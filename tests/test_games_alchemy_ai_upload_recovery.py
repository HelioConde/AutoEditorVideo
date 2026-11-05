"""No-paid-media tests for the pinned six-short private-upload recovery."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from games_alchemy_ai_recovery_gate import guard_event,RecoveryBlocked
from games_alchemy_ai_upload import preflight,UploadBlocked

def _push_event(tmp_path, *, message="feat(games-alchemy): submit finished six AI Shorts for private upload"):
    target=tmp_path/"event.json"
    target.write_text(json.dumps({
        "ref":"refs/heads/main",
        "head_commit":{"id":"the-once-only-commit","message":message}
    }),encoding="utf-8")
    return {"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_RUN_ATTEMPT":"1",
            "GITHUB_WORKFLOW":"Gamer + Alchemy - private upload from completed AI render",
            "GITHUB_EVENT_PATH":str(target),
            "GITHUB_SHA":"the-once-only-commit",
            "GH_TOKEN":"synthetic-no-real-secret"}

def test_guard_blocks_any_replay(tmp_path):
    env=_push_event(tmp_path)
    env["GITHUB_RUN_ATTEMPT"]="2"
    with pytest.raises(RecoveryBlocked,match="SINGLE_PUSH_ATTEMPT_ONLY"):
        guard_event(env)

def test_guard_blocks_unapproved_commit(tmp_path):
    env=_push_event(tmp_path,message="unrelated deployment")
    with pytest.raises(RecoveryBlocked,match="UNAUTHORIZED_COMMIT_OR_REF"):
        guard_event(env)

def test_guard_requires_exact_channel_and_parent_run(tmp_path):
    env=_push_event(tmp_path)
    env.update({
        "AI_SIX_PILOT_USER_APPROVED":"true",
        "AI_SIX_PILOT_ORIGINAL_RUN_ID":"wrong",
        "AI_SIX_PILOT_ORIGINAL_SHA":"a414b9aea8d778f27c765cfb3d45e94612d0ee05",
        "YOUTUBE_CLIENT_JSON":"synthetic",
        "YOUTUBE_CHANNEL_TOKEN_JSON":"synthetic"
    })
    with pytest.raises(UploadBlocked,match="UNAUTHORIZED_ORIGINAL_RENDER"):
        preflight("games",env)

def test_guard_rejects_any_unknown_channel(tmp_path):
    env=_push_event(tmp_path)
    with pytest.raises(UploadBlocked,match="UNSUPPORTED_CHANNEL"):
        preflight("br",env)
