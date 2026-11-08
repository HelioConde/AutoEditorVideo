"""Offline tests for creator-authorized 3 public BR originals; no YouTube calls."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_br_three_public_20261107 import (
    validate,guard,OWNER,CHANNEL_ID,IDS,BRBlocked,MAX_CALLS
)
from otaku_br_three_public_upload_20261107 import (
    validate_artifacts,guard as guard_upload,PublicBlocked
)
from kids_static_90s_upload_20261107 import configure_resumable_transport
from production_reservations import get_entry

def test_three_distinct_new_reserved_br_origins():
    videos=validate()
    assert len(videos)==3
    assert [v["id"] for v in videos]==list(IDS)
    assert len({v["title"].casefold() for v in videos})==3
    for v in videos:
        entry=get_entry("br",v["id"])
        assert entry["status"]=="reserved" and entry["reservation_owner"]==OWNER
        assert v["channel_id"]==CHANNEL_ID
        assert v["made_for_kids"] is False
        assert v["visibility_intent"]=="public_after_automated_qa"
        assert len(v["scenes"])==8
        assert 245<=len(v["narration_script"].split())<=350
        assert len(",".join(v["tags"]))<500

def test_no_use_paused_50_video_queue():
    d=json.loads((ROOT/"conteudos"/"otaku-multicena-br-50-inéditos-reverso-20261106.json").read_text(encoding="utf-8-sig"))
    prior_ids={v["id"] for v in d["episodes"]}
    assert not (prior_ids&set(IDS))
    assert MAX_CALLS==24

def test_render_cannot_start_outside_one_shot_branch(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY",raising=False)
    with pytest.raises(BRBlocked):
        guard()

def test_public_upload_requires_channel_exclusive_oauth(monkeypatch):
    monkeypatch.delenv("YOUTUBE_CHANNEL_TOKEN_JSON",raising=False)
    with pytest.raises(PublicBlocked):
        guard_upload()

def test_no_media_artifact_means_no_upload():
    with pytest.raises(PublicBlocked):
        validate_artifacts()

def test_http_308_is_resumable_not_redirect():
    http=SimpleNamespace(redirect_codes={301,302,303,307,308})
    assert configure_resumable_transport(http).redirect_codes=={301,302,303,307}

def test_uploader_checks_exact_channel_public_processing_and_thumbnail():
    s=(ROOT/"scripts"/"otaku_br_three_public_upload_20261107.py").read_text()
    assert 'existing_title_matches(api,playlist,items)' in s
    assert 'num_retries=0' in s
    assert '"privacyStatus":"public"' in s
    assert '"selfDeclaredMadeForKids":False' in s
    assert 'public_tags(meta["tags"])' in s
    assert 'processingStatus' in s and 'thumbnails().set(' in s
    assert 'videos().delete(' not in s
    assert 'videos().update(' not in s
