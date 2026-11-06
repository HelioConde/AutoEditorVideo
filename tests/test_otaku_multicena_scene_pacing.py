"""Scene cuts follow real speech markers while respecting minimum hold lengths."""
import importlib
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
pacing=importlib.import_module("otaku_multicena_scene_pacing")

def markers(fps=30,seconds=36):
    result=[]
    for sec in range(2,seconds,2):
        frame=sec*fps
        result.append({
            "startFrame":frame-fps,
            "endFrame":frame,
            "words":[{"text":"terminou.","startFrame":frame-15,"endFrame":frame}]
        })
    return result

def test_cuts_are_sorted_and_near_real_sentence_ends():
    fps=30
    total=36*fps
    cuts=pacing.story_cuts(markers(),total,fps)
    assert len(cuts)==6
    assert cuts[0]==0 and cuts[-1]==total
    assert all(right-left>=2*fps for left,right in zip(cuts,cuts[1:]))
    assert all(cut%(2*fps)==0 for cut in cuts[1:-1])
    assert all(isinstance(c,int) for c in cuts)

def test_shorter_than_20_seconds_is_not_silently_stretched():
    with pytest.raises(pacing.PacingBlocked):
        pacing.story_cuts(markers(),19*30)

def test_malformed_word_timing_blocks_scene_planner():
    with pytest.raises(pacing.PacingBlocked,match="INVALID_CAPTION_MARKERS"):
        pacing.story_cuts([{"startFrame":60,"endFrame":60}],36*30)

def test_future_render_uses_speech_aligned_scene_planner_not_equal_divisions():
    source=(ROOT/"scripts/otaku_br_50_render.py").read_text(encoding="utf-8")
    assert "cuts = story_cuts(captions, frames, fps=FPS)" in source
    assert "cuts = [round(frames * i / len(art))" not in source
    assert '"cut_strategy": "narration_word_aligned_v2"' in source
    assert "youtube.videos()" not in source
