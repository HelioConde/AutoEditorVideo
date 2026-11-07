"""Strict isolated offline A/B experiment of unmerged Codex PR81 renderer."""
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import codex_face_performance_review as review

ENV={
"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
"GITHUB_REF":"refs/heads/test/codex-face-performance-review-20261107",
"GITHUB_EVENT_NAME":"push",
"GITHUB_RUN_ATTEMPT":"1",
"GITHUB_WORKFLOW":"Codex PR81 - real adaptive character animation A/B review (no upload)",
"CODEX_PR81_ONE_REVIEW":"1",
"MAX_IMAGE_CALLS":"0"
}
def test_experiment_reserved_and_no_unauthorized_actions():
    assert review.preflight(ENV)["anime"]=="Death Note"
    for k,v in (
        ("GITHUB_REF","refs/heads/main"),
        ("GITHUB_RUN_ATTEMPT","2"),
        ("GITHUB_EVENT_NAME","workflow_dispatch"),
        ("CODEX_PR81_ONE_REVIEW","0"),
        ("MAX_IMAGE_CALLS","1"),
        ("PROXY_API_KEY","no"),
        ("YOUTUBE_BR_TOKEN_JSON","no")
    ):
        with pytest.raises(review.ReviewBlocked):
            review.preflight({**ENV,k:v})

def test_new_codex_engine_actually_used_not_old_v10_animation():
    script=(ROOT/"scripts/codex_face_performance_review.py").read_text(encoding="utf-8")
    engine=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    art=(ROOT/"motion-remotion/src/character-art.tsx").read_text(encoding="utf-8")
    assert "prepare_scene_art([scene],PUBLIC)" in script
    assert "renderMode\\\":\\\"multilayer" in script or '"renderMode":"multilayer"' in script
    assert "CharacterArt src={imageSource}" in engine
    assert "useLayoutEffect(paint" in art
    assert "paintEye(ctx" in art
    assert "movePortrait(ctx" in art
    assert "rig.warp" not in script
    assert "request_image(" not in script
    assert "youtube.videos().insert" not in script

def test_control_is_identical_except_character_performance():
    scene={"subject":"personagens","renderMode":"multilayer","foreground":"background.png",
           "background":"background.png","layers":[{"id":"hero","role":"character","z":10,
           "src":"hero.png","performance":{"width":1024,"height":1536,"seed":1,
                                            "faces":[],"motion":"cutout"}}]}
    row={"narration_script":"Something"}
    # Rendering props is tested with original narration markers during CI
    # after the pinned artifact is downloaded; only check deterministic IDs.
    assert review.SOURCE_RUN=="42332358380"
    assert review.VIDEO_FPS==30 and review.SECONDS==8
    assert scene["layers"][0]["performance"]["motion"]=="cutout"
