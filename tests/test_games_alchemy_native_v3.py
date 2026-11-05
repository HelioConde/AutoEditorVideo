"""Offline tests: existing AutoEditorVideo native captions and cover generator."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from games_alchemy_native_v3 import validate_plan,guard,build_scene_props,NativeRecutBlocked,IDS
from capa_cinematografica import STYLE as COVER_STYLE

def test_six_revisions_reserved_for_existing_program_renderer():
    data=validate_plan()
    assert len(data["projects"])==6
    assert [p["source_episode_id"] for p in data["projects"]]==IDS
    for p in data["projects"]:
        assert "se inscreve" in p["narration"].lower()
        assert "🎨" in p["description"]
        assert p["thumbnail"]["lines"]

def test_native_renderer_uses_exact_previous_remotion_caption_structure():
    entry=validate_plan()["projects"][0]
    words=[
        {"text":"Se","startFrame":0,"endFrame":7},
        {"text":"inscreve","startFrame":8,"endFrame":19},
        {"text":"aqui","startFrame":20,"endFrame":27}
    ]
    captions=[{"startFrame":0,"endFrame":27,"text":"Se inscreve aqui","words":words}]
    from pathlib import Path
    frames=[Path(f"scene-{i}.png") for i in range(5)]
    props=build_scene_props(entry,frames,Path("voz-master.mp3"),captions,5.0,"test-native")
    assert props["animationMode"]=="cinematica"
    assert props["captions"][0]["words"][1]["text"]=="inscreve"
    assert props["scenes"][0]["background"].startswith("generated/test-native/")
    assert len(props["scenes"])==5

def test_creator_pinned_program_is_the_official_cover_generator():
    from games_alchemy_native_v3 import render_cover
    assert render_cover.__module__=="capa_cinematografica"
    assert COVER_STYLE=="duelo-cinematografico"

def test_no_generation_without_one_time_workflow(monkeypatch):
    for x in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME","GITHUB_RUN_ATTEMPT","GITHUB_WORKFLOW","NATIVE_REDO_APPROVED","SOURCE_RUN_ID"):
        monkeypatch.delenv(x,raising=False)
    with pytest.raises(NativeRecutBlocked,match="WRONG_REPOSITORY"):
        guard()
