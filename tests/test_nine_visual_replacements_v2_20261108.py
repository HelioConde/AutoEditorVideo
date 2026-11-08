"""Offline correctness checks before any of 83 image generations."""
from pathlib import Path
import sys
from collections import Counter
import json
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import nine_visual_replacements_v2_20261108 as v2
from otaku_character_identity_policy import verify_manifest_identity,load_policy
from production_reservations import get_entry
import otaku_br_three_public_20261107 as old_br

def test_nine_distinct_versioned_reservations_across_three_channels():
    d=json.loads(v2.PLAN.read_text(encoding="utf-8"))
    assert d["target_total"]==9 and len(d["episodes"])==9
    assert len({x["id"] for x in d["episodes"]})==9
    assert Counter(x["channel"] for x in d["episodes"])==Counter({"en":3,"games":3,"alchemy":3})
    assert sum(v2.CALLS.values())==83
    for ch in v2.CHANNELS:
        rows=v2.validate(ch)
        assert tuple(x["id"] for x in rows)==v2.IDS[ch]
        assert sum(len(x["character_identity_bible"])+8 for x in rows)==v2.CALLS[ch]
        for x in rows:
            entry=get_entry(ch,x["id"])
            assert entry["reservation_owner"]==v2.OWNER
            assert x["old_youtube_id"] and x["old_youtube_id"]!=x["id"]
            assert x["made_for_kids"] is False
            assert len(x["scenes"])==8
            assert len(x["narration_script"].split())>=240

def test_en_forces_canonical_recognizable_appearance_on_every_scene():
    assert load_policy()["required_rules"]["scene_generation_requires_anchor_image_edit"]
    for r in v2.validate("en"):
        chars=verify_manifest_identity(r)
        assert chars
        assert all("canonical_appearance" in c for c in chars)
        assert all(s["character_keys"] for s in r["scenes"])
        assert all("generic athlete" not in s["visual_instruction"].lower() for s in r["scenes"])

def test_all_scenes_use_real_character_anchor_images_not_random_unrelated_stills():
    src=(ROOT/"scripts"/"nine_visual_replacements_v2_20261108.py").read_text()
    assert "br_v2.generate_anchored_art(row,folder,key)" in src
    assert "editor.render_one(row,folder,audio,sec,words,frames,channel)" in src
    assert '"editorial_visual_review_status":"pending"' in src
    assert '"privacyStatus":"private"' in src
    assert "videos().delete(" not in src
    assert "videos().insert(" not in src
    assert "request_image(" not in src

def test_only_allowed_channels():
    for slug in ("br","kids","unknown"):
        with pytest.raises(v2.ReplacementBlocked):
            v2.validate(slug)
