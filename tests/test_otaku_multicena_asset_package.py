"""Verify four animated scenes and authentic-media prerequisites, fully offline."""
import importlib
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
pkg=importlib.import_module("otaku_multicena_asset_package")
quality=importlib.import_module("otaku_multicena_quality_v3")

def test_five_pending_shorts_have_requirements_but_no_artwork():
    report=pkg.package_plan([5,4,3,2,1])
    assert report["publication_paused"] is True
    assert report["video_generated"] is False
    assert report["youtube_uploads"]==0
    assert len(report["packages"])==5
    assert report["planned_background_files"]==50
    assert report["planned_pose_files"]==40
    for template in report["packages"]:
        assert template["schema"]=="autoeditorvideo/quality-preview/v3"
        assert len(template["shots"])==10
        assert len(template["sha256"])==0
        assert template["duration_frames"] is None
        assert template["voice_rights"]["type"] is None
        assert template["editorial_approval"] is False
        assert template["publish_authorized"] is False
        assert template["manual_visual_review"] is False
        assert template["animation_target_shots"]==[1,4,6,9]
        pose_shots=[shot for shot in template["shots"] if shot.get("pose_frames")]
        assert len(pose_shots)==4
        assert len(template["required_file_checklist"])==20
        assert all(shot["rights"]["type"] is None for shot in template["shots"])
        assert all(shot["character_consistency_review"] is False for shot in template["shots"])

def test_template_must_fail_v3_validation_until_real_approved_media_exists(tmp_path):
    doc=pkg.package_plan([5])["packages"][0]
    manifest=tmp_path/"quality.json"
    manifest.write_text(json.dumps(doc),encoding="utf-8")
    captions=tmp_path/"markers.json"
    captions.write_text("[]",encoding="utf-8")
    with pytest.raises(quality.QualityBlocked,match="VIDEO_DURATION_OUT_OF_RANGE"):
        quality.build_preview(manifest,captions,tmp_path/"public")

def test_no_side_effectful_generator_is_imported_by_asset_package():
    source=(ROOT/"scripts/otaku_multicena_asset_package.py").read_text(encoding="utf-8")
    for name in ("request_image(", "ensure_voice(", "render:master",
                 "gh workflow run", "youtube.videos().insert", "proxy_key("):
        assert name not in source

def test_duplicate_or_invalid_number_rejected():
    for numbers in ([5,5],[0],[51],[]):
        with pytest.raises(ValueError):
            pkg.package_plan(numbers)
