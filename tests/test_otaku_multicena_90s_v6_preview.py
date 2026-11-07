"""Offline checks of authentic AutoEditorVideo V6 motion/voice pipeline.

Must NEVER call Edge TTS, image model, rendering, or YouTube from tests.
"""
import copy
from pathlib import Path
import sys

import numpy as np
from PIL import Image,ImageDraw
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import otaku_multicena_90s_v6_preview as v6
from otaku_multicena_pose_qa import inspect_poses

ENV={
    "OTAKU_V6_ONE_PREVIEW":"1",
    "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
    "GITHUB_REF":"refs/heads/main",
    "GITHUB_RUN_ATTEMPT":"1",
    "GITHUB_EVENT_NAME":"push",
    "GITHUB_WORKFLOW":v6.WORKFLOW,
    "IMAGE_MODEL":"gpt-image-2",
    "MAX_IMAGE_CALLS":"20",
}

def test_explicit_authorization_cannot_unlock_publishing_or_old_queue():
    doc=v6.check_env(ENV)
    assert doc["rank"]==1 and doc["anime"]=="Death Note"
    assert doc["ending_policy"]=="answer_only_no_cta"
    for key,value in (("OTAKU_V6_ONE_PREVIEW","0"),
                      ("GITHUB_REF","refs/heads/fork"),
                      ("GITHUB_EVENT_NAME","workflow_dispatch"),
                      ("GITHUB_RUN_ATTEMPT","2"),
                      ("MAX_IMAGE_CALLS","21"),
                      ("GITHUB_WORKFLOW","Otaku V5 - REAL 90s MP4 review from AutoEditorVideo (no upload)")):
        with pytest.raises(v6.V6Blocked):
            v6.check_env({**ENV,key:value})
    with pytest.raises(v6.V6Blocked,match="YOUTUBE_CREDENTIALS_ARE_FORBIDDEN"):
        v6.check_env({**ENV,"YOUTUBE_CLIENT_JSON":"dummy"})
    pause=v6.load(v6.PAUSE)
    assert pause["pause_requested"] and not pause["authorized_public"]
    assert not pause["resume_authorized_after_maintenance"]

def test_storyboard_is_varied_and_creates_real_pose_pairs_without_fake_fallback():
    assert v6.SCENES==10 and v6.ART_REQUESTS==20
    assert v6.ANIMATED_SHOTS==(0,2,4,6,8)
    assert all(len(item)==2 for item in v6.POSES.values())
    assert len(set(v6.DIRECTIONS))==10
    assert all("No people" in v6.DIRECTIONS[i] or "No characters" in v6.DIRECTIONS[i]
               for i in v6.ANIMATED_SHOTS)
    for i in v6.ANIMATED_SHOTS:
        for pose in range(2):
            prompt=v6.original_prompt(i,pose=pose)
            assert "TRANSPARENT" in prompt
            assert "pose" in prompt
            assert "NO furniture" in prompt
    assert "NOT a screenshot" not in v6.original_prompt(1) or "copied existing illustration" in v6.original_prompt(1)

def test_subject_normalization_keeps_character_visible_inside_alpha_frame(tmp_path):
    paths=[]
    for i in range(2):
        original=Image.new("RGBA",(1024,1536),(0,0,0,0))
        pen=ImageDraw.Draw(original)
        pen.ellipse((270,220+i*20,710,950+i*20),fill=(80,130,210,255))
        pen.rectangle((375,720,610,1455),fill=(140+i*60,100,65,255))
        fixed=v6.standardize_pose(original)
        assert fixed.mode=="RGBA" and fixed.size==(1024,1536)
        path=tmp_path/f"frame_{i}.png"
        fixed.save(path)
        paths.append(path)
    report=inspect_poses(paths)
    assert report["technical_pose_geometry_checked"] is True
    assert report["actual_character_identity_or_action_verified"] is False

def test_authentic_animation_and_original_music_are_explicitly_in_render_code():
    script=(ROOT/"scripts/otaku_multicena_90s_v6_preview.py").read_text(encoding="utf-8")
    master=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    assert 'request_image(prompt,MODEL,key' in script
    assert 'background="transparent" if alpha else None' in script
    assert 'inspect_poses(files)' in script
    assert '"render:master"' in script
    assert '"animationMode":"esqueleto2d"' in script
    assert '"visualProfile":"otaku-v6-vertical"' in script
    assert '"rigFrames":{"fps":.43' in script
    assert "original-score.wav" in script
    assert "WordBoundary" in script
    assert "otaku-v6-vertical" in master
    assert "rigBlend" in master
    assert "youtube.videos().insert" not in script
    assert "--publicar" not in script

def test_there_is_no_claim_of_human_approved_8_out_of_10():
    script=(ROOT/"scripts/otaku_multicena_90s_v6_preview.py").read_text(encoding="utf-8")
    assert '"ready_to_publish":False' in script
    assert '"true_skeletal_2d_bones":False' in script
    assert '"humans_verified_identity_or_animation":False' in script
    assert '"publishing_pause_unchanged":True' in script
