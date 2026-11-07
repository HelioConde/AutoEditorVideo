"""V10 review-only performance beats, source coherence and CPU deformation QA."""
from pathlib import Path
import sys

import numpy as np
import pytest
pytest.importorskip("cv2")
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from performance_brush_2d import PerformanceBrush2D,blink_envelope,WIDTH,HEIGHT
import otaku_v10_performance_preview as v10

ENV={
"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
"GITHUB_REF":"refs/heads/main",
"GITHUB_EVENT_NAME":"push",
"GITHUB_RUN_ATTEMPT":"1",
"GITHUB_WORKFLOW":v10.WORKFLOW,
"OTAKU_V10_ONE_PERFORMANCE":"1",
"MAX_IMAGE_CALLS":"0"
}

def test_exact_single_approval_no_paid_images_or_youtube():
    assert v10.preflight(ENV)["anime"]=="Death Note"
    for key,value in (
        ("MAX_IMAGE_CALLS","1"),("GITHUB_RUN_ATTEMPT","2"),
        ("GITHUB_EVENT_NAME","workflow_dispatch"),
        ("GITHUB_REF","refs/heads/other"),
        ("OTAKU_V10_ONE_PERFORMANCE","0"),
        ("PROXY_API_KEY","not-allowed"),
        ("YOUTUBE_BR_TOKEN_JSON","not-allowed"),
    ):
        with pytest.raises(v10.Blocked):
            v10.preflight({**ENV,key:value})

def test_distinct_blink_nod_and_hand_beats_are_temporally_authored():
    rig=PerformanceBrush2D()
    assert blink_envelope(0)==0
    assert blink_envelope(1.54)>.98
    assert blink_envelope(5.64)>.98
    assert blink_envelope(2.5)==0
    assert rig.quality(2.5)["head_yaw"]>.5
    assert rig.quality(5.4)["arm_beat"]>.5
    assert rig.quality(5.4)["maximum_motion_px"]>10
    assert rig.quality(2.5)["blink_fraction"]==0
    for t in (0,1.54,2.5,3.3,4.7,5.4,5.64,6.2,7.5,8):
        assert rig.quality(t)["safe"],t

def test_same_original_rgba_blinks_without_changing_identity():
    rig=PerformanceBrush2D()
    art=np.zeros((HEIGHT,WIDTH,4),np.uint8)
    art[230:1490,220:800,:]=[177,112,77,255]
    art[426:452,420:590,:]=[22,40,65,255]
    a=rig.warp(art,0)
    b=rig.warp(art,8)
    c=rig.warp(art,1.54)
    assert np.array_equal(a,art)
    assert np.array_equal(b,art)
    assert c.dtype==np.uint8 and c.shape==art.shape
    assert not np.array_equal(c[420:459,420:592],art[420:459,420:592])
    ref=art[:,:,3]>32
    after=c[:,:,3]>32
    assert (ref & after).sum()/(ref | after).sum()>.975

def test_no_moving_anchor_jump_or_ghost_pose_crossfade():
    rig=PerformanceBrush2D()
    prev=None
    for frame in range(0,240,3):
        flow=rig.displacement(frame/30)
        if prev is not None:
            dx,dy=flow
            assert max(float(np.max(abs(dx-prev[0]))),
                       float(np.max(abs(dy-prev[1]))))<4
        prev=flow
    video=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    assert "mode==='performance2d'?layer.meshFrames" in video
    src=(ROOT/"scripts/otaku_v10_performance_preview.py").read_text(encoding="utf-8")
    assert "rig.warp(original,second)" in src
    assert '\"MAX_IMAGE_CALLS\":\"0\"' in src
    assert "youtube.videos().insert" not in src
    assert "request_image(" not in src

def test_lid_moves_down_before_covering_lower_iris():
    rig = PerformanceBrush2D()
    art = np.full((HEIGHT, WIDTH, 4), [200, 140, 100, 255], np.uint8)
    art[422:441, 445:458, :3] = [20, 35, 40]
    half_closed = rig._blink(art, 1.49)
    assert not np.array_equal(half_closed[426, 452], art[426, 452])
    assert np.array_equal(half_closed[437, 452], art[437, 452])
    assert np.array_equal(half_closed[:, :, 3], art[:, :, 3])
    assert blink_envelope(1.54 + .07) > blink_envelope(1.54 - .07)
