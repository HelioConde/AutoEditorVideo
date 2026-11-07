"""Offline QA: inverse-TPS pinned puppet, reserved 8s preview, no paid provider."""
import sys
from pathlib import Path
import numpy as np
import pytest
pytest.importorskip("cv2")
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from puppet_pin_warp import PINS,pin_positions,pin_offsets,warp_rgba,WIDTH,HEIGHT,SECONDS
import otaku_v8_pins_preview as v8

ENV={
"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
"GITHUB_REF":"refs/heads/main",
"GITHUB_EVENT_NAME":"push",
"GITHUB_RUN_ATTEMPT":"1",
"GITHUB_WORKFLOW":v8.WORKFLOW,
"OTAKU_V8_PIN_REVIEW":"1",
"MAX_IMAGE_CALLS":"0"
}
def test_only_reserved_zero_cost_single_private_review():
    assert v8.preflight(ENV)["anime"]=="Death Note"
    assert len(PINS)>=30
    for name,value in (
        ("GITHUB_RUN_ATTEMPT","2"),
        ("MAX_IMAGE_CALLS","1"),
        ("GITHUB_REF","refs/heads/other"),
        ("OTAKU_V8_PIN_REVIEW","0"),
        ("GITHUB_EVENT_NAME","workflow_dispatch"),
    ):
        with pytest.raises(v8.Blocked):
            v8.preflight({**ENV,name:value})
    for key in ("PROXY_API_KEY","YOUTUBE_CLIENT_JSON"):
        with pytest.raises(v8.Blocked):
            v8.preflight({**ENV,key:"not-permitted"})

def test_real_fixed_pins_never_drift():
    for t in (0,.2,2,3.8,5,6.5,7.9,8):
        now=pin_positions(t)
        assert set(now)==set(PINS)
        for name,source in PINS.items():
            if name.startswith("fixed_border_") or name in (
              "hip_left","hip_right","belt","foot_left","foot_right"):
                assert now[name]==source
    assert pin_offsets(0)["wrist_right"]==(0,0)
    assert pin_offsets(8)["wrist_right"]==(0,0)
    assert max(abs(x) for x in pin_offsets(5)["wrist_right"])>10

def test_warp_preserves_one_rgba_source_and_returns_to_original():
    src=np.zeros((HEIGHT,WIDTH,4),np.uint8)
    src[250:1400,240:790]=[170,88,24,255]
    src[250:530,350:650]=[250,185,140,255]
    assert np.array_equal(warp_rgba(src,0),src)
    assert np.array_equal(warp_rgba(src,SECONDS),src)
    animated=warp_rgba(src,5)
    assert not np.array_equal(animated,src)
    mask=src[:,:,3]>32
    warped=animated[:,:,3]>32
    assert float(np.logical_and(mask,warped).sum()/
                 np.logical_or(mask,warped).sum())>.90
    assert animated.dtype==src.dtype

def test_pin_motion_is_continuous_between_near_frames():
    pins_a=pin_positions(5.0)
    pins_b=pin_positions(5.0+1/15)
    assert max(abs(pins_b[k][i]-pins_a[k][i])
               for k in PINS for i in (0,1))<5

def test_no_ghost_crossfades_and_only_original_pipeline():
    v8src=(ROOT/"scripts/otaku_v8_pins_preview.py").read_text(encoding="utf-8")
    remotion=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    assert "warp_rgba(original,seconds)" in v8src
    assert '"animationMode":"pins2d"' in v8src
    assert "mode==='pins2d'?layer.meshFrames" in remotion
    assert "request_image(" not in v8src
    assert "youtube.videos().insert" not in v8src
    assert '"MAX_IMAGE_CALLS":"0"' in v8src
