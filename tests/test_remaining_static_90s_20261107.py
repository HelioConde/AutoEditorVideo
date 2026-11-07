"""Offline regression for nine original static videos and isolated private uploads."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from remaining_static_90s_20261107 import (
    OWNER,EXPECTED,IMAGE_BUDGET,VOICES,PROFILE,validate,RemainingBlocked
)
from remaining_static_90s_upload_20261107 import TOKENS,CATEGORY,RemainingUploadBlocked
from kids_static_90s_upload_20261107 import configure_resumable_transport
from types import SimpleNamespace
import pytest

def test_all_nine_reservations_scripts_and_real_editor_constraints():
    assert sum(len(x) for x in EXPECTED.values())==9
    assert len({id for ids in EXPECTED.values() for id in ids})==9
    assert set(EXPECTED)=={"en","games","alchemy"}
    for channel,ids in EXPECTED.items():
        rows=validate(channel)
        assert len(rows)==3
        assert tuple(r["id"] for r in rows)==ids
        assert all(r["channel"]==channel for r in rows)
        assert all(r["made_for_kids"] is False for r in rows)
        assert all(r["production_state"]["upload"]=="not_started" for r in rows)
        assert all(len(r["scenes"])==8 for r in rows)
        assert all(r["duration"]["minimum_seconds"]==90 for r in rows)
        assert all(r["duration"]["maximum_seconds"]==120 for r in rows)
        assert all(not s["generated_asset_ready"] for r in rows for s in r["scenes"])
    assert IMAGE_BUDGET==24
    assert VOICES["en"].startswith("en-")
    assert VOICES["games"].startswith("pt-BR-")
    assert VOICES["alchemy"].startswith("pt-BR-")
    assert PROFILE["en"]=="original"

def test_not_authorized_to_generate_or_publish_kids_or_br():
    for channel in ("kids","br",""):
        with pytest.raises(RemainingBlocked):
            validate(channel)
    assert "kids" not in EXPECTED and "br" not in EXPECTED
    assert "kids" not in TOKENS and "br" not in TOKENS

def test_all_three_tokens_are_distinct_and_categories_match():
    assert TOKENS=={
        "en":"YOUTUBE_EN_TOKEN_JSON",
        "games":"YOUTUBE_GAMES_TOKEN_JSON",
        "alchemy":"YOUTUBE_ALCHEMY_TOKEN_JSON",
    }
    assert len(set(TOKENS.values()))==3
    assert CATEGORY=={"en":"24","games":"20","alchemy":"28"}

def test_custom_httplib2_transport_uses_308_upload_resume():
    c=SimpleNamespace(redirect_codes={301,302,303,307,308})
    assert configure_resumable_transport(c).redirect_codes=={301,302,303,307}

def test_ambiguous_http_308_never_has_blind_retry():
    src=(ROOT/"scripts"/"remaining_static_90s_upload_20261107.py").read_text()
    assert "num_retries=0" in src
    assert "scan_existing(" in src
    assert "for delay in (12,24,35)" in src
    assert "public_tags(meta[\"tags\"])" in src
    assert "privacyStatus\":\"private\"" in src
    assert "selfDeclaredMadeForKids\":False" in src
    assert "videos().delete(" not in src
    assert "videos().update(" not in src

def test_all_topics_are_original_static_frames_not_gameplay():
    src=(ROOT/"scripts"/"remaining_static_90s_20261107.py").read_text()
    assert '"animationMode":"desligada"' in src
    assert '"renderMode":"master_static"' in src
    assert '"character_warp_mesh_animation":False' in src
    assert 'render_cover(' in src
    assert '"word_boundaries_synced":True' in src
