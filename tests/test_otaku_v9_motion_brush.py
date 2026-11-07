"""CPU mask-guided V9 brush QA, no network/YouTube/image-provider calls."""
from pathlib import Path
import sys

import numpy as np
import pytest
pytest.importorskip("cv2")

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import otaku_v9_motion_brush_preview as v9
from motion_brush_2d import MotionBrush2D,load_config,WIDTH,HEIGHT

ENV={
"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
"GITHUB_REF":"refs/heads/main",
"GITHUB_EVENT_NAME":"push",
"GITHUB_RUN_ATTEMPT":"1",
"GITHUB_WORKFLOW":v9.WORKFLOW,
"OTAKU_V9_BRUSH_REVIEW":"1",
"MAX_IMAGE_CALLS":"0"
}

def test_exact_reserved_review_no_paid_calls_no_youtube():
    assert v9.preflight(ENV)["anime"]=="Death Note"
    for key,value in [
        ("MAX_IMAGE_CALLS","20"),("GITHUB_REF","refs/heads/unsafe"),
        ("GITHUB_EVENT_NAME","workflow_dispatch"),("GITHUB_RUN_ATTEMPT","2"),
        ("OTAKU_V9_BRUSH_REVIEW","0"),("PROXY_API_KEY","deny"),
        ("YOUTUBE_BR_TOKEN_JSON","deny")
    ]:
        with pytest.raises(v9.Blocked):
            v9.preflight({**ENV,key:value})

def test_brush_configuration_and_protected_regions():
    c=load_config(ROOT/"config/otaku-v9-motion-brush.json")
    assert len(c["brushes"])==3
    assert "face" in [x["id"] for x in c["protections"]]
    assert all(x["motion"]["kind"] in ("sway","gesture") for x in c["brushes"])
    a=MotionBrush2D(c)
    assert a.protection[465,505]>.99
    assert a.protection[900,520]>.99
    for t in (0,1.5,2.4,3.8,5.3,7.3,8):
        assert a.quality(t)["within_safe_bounds"]
    assert a.quality(5.3)["max_displacement_px"]>2

def test_one_source_no_face_motion_no_opacity_ghost():
    c=load_config(ROOT/"config/otaku-v9-motion-brush.json")
    a=MotionBrush2D(c)
    original=np.zeros((HEIGHT,WIDTH,4),np.uint8)
    original[220:1450,220:815]=[188,78,47,255]
    original[390:555,420:605]=[245,188,140,255]
    assert np.array_equal(a.warp(original,0),original)
    assert np.array_equal(a.warp(original,8),original)
    animated=a.warp(original,5.3)
    assert not np.array_equal(animated,original)
    assert np.array_equal(animated[447:500,477:537],
                          original[447:500,477:537])
    before=original[:,:,3]>32
    after=animated[:,:,3]>32
    assert np.logical_and(before,after).sum()/np.logical_or(before,after).sum()>.94

def test_frame_interpolation_smooth_and_no_multibody_crossfade():
    animator=MotionBrush2D(load_config(ROOT/"config/otaku-v9-motion-brush.json"))
    x,y=animator.displacement(5)
    a,b=animator.displacement(5+1/30)
    assert max(float(np.max(abs(x-a))),float(np.max(abs(y-b))))<2
    remotion=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    assert "mode==='brush2d'?layer.meshFrames" in remotion
    assert "return <Img key={layer.id}" in remotion
    preview=(ROOT/"scripts/otaku_v9_motion_brush_preview.py").read_text(encoding="utf-8")
    assert "animator.warp(original,second)" in preview
    assert 'new_image_ai_calls":0' in preview
    assert "youtube.videos().insert" not in preview
