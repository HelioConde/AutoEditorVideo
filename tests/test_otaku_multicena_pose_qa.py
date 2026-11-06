"""Offline character-pose geometry checks for original V3 Shorts."""
from pathlib import Path
import importlib
import sys

from PIL import Image, ImageDraw
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
pose=importlib.import_module("otaku_multicena_pose_qa")

def frame(folder:Path,name:str,*,x:int=240,color=(225,85,145,255),
          compress:int=6)->Path:
    img=Image.new("RGBA",(1024,1536),(0,0,0,0))
    ImageDraw.Draw(img).rectangle((x,270,x+220,640),fill=color)
    path=folder/name
    img.save(path,compress_level=compress)
    return path

def test_valid_motion_reports_real_pixel_difference_without_claiming_identity(tmp_path):
    a=frame(tmp_path,"a.png",x=200)
    b=frame(tmp_path,"b.png",x=238)
    result=pose.inspect_poses([a,b])
    assert result["pose_frame_count"]==2
    assert result["minimum_changed_subject_fraction"]>.008
    assert result["technical_pose_geometry_checked"] is True
    assert result["actual_character_identity_or_action_verified"] is False
    assert result["human_visual_review_required"] is True

def test_expression_pixel_change_is_allowed_with_same_alpha_shape(tmp_path):
    a=frame(tmp_path,"a.png",color=(225,85,145,255))
    b=frame(tmp_path,"b.png",color=(20,75,235,255))
    data=pose.inspect_poses([a,b])
    assert data["pose_frame_count"]==2

def test_reencoding_identical_pose_is_not_fake_animation(tmp_path):
    a=frame(tmp_path,"a.png",compress=1)
    b=frame(tmp_path,"b.png",compress=9)
    assert a.read_bytes()!=b.read_bytes()
    with pytest.raises(pose.PoseBlocked,match="VISUALLY_IDENTICAL"):
        pose.inspect_poses([a,b])

def test_cutoff_character_is_rejected(tmp_path):
    a=frame(tmp_path,"a.png",x=0)
    b=frame(tmp_path,"b.png",x=20)
    with pytest.raises(pose.PoseBlocked,match="POSE_CUT_OFF_AT_FRAME_EDGE"):
        pose.inspect_poses([a,b])

def test_teleporting_subject_is_rejected(tmp_path):
    a=frame(tmp_path,"a.png",x=140)
    b=frame(tmp_path,"b.png",x=430)
    with pytest.raises(pose.PoseBlocked,match="POSE_TELEPORTS_BETWEEN_FRAMES"):
        pose.inspect_poses([a,b])

def test_quality_v3_requires_pose_inspection_before_marking_multilayer():
    source=(ROOT/"scripts/otaku_multicena_quality_v3.py").read_text(encoding="utf-8")
    assert "from otaku_multicena_pose_qa import inspect_poses" in source
    assert "inspect_poses(pose_paths)" in source
    assert '"pose_geometry_checks": pose_geometry_reports' in source
    assert "request_image(" not in source
    assert "youtube.videos().insert" not in source
