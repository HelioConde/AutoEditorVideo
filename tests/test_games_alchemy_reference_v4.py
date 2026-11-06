"""Offline QA: six full-length V4 Shorts must preserve 5-second approved style."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from games_alchemy_reference_v4 import (
    validate_plan,guard,build_scene_props,IDS,SCENE_TIMES,
    NativeRecutBlocked,OWNER,OUTPUT
)
from capa_cinematografica import render_cover

def test_six_reserved_reference_version():
    plan=validate_plan()
    assert len(plan["projects"])==6
    assert [r["source_episode_id"] for r in plan["projects"]]==IDS
    assert OWNER=="games_alchemy_six_reference_v4_20261105"
    assert OUTPUT.name=="cloud-games-alchemy-reference-v4"
    for r in plan["projects"]:
        assert r["channel"] in ("games","alchemy")
        assert "se inscreve" in r["narration"].lower()
        assert "não é gameplay" not in r["narration"].lower()
        assert r["description"].count("🎨")>=1
        assert r["thumbnail"]["scene_index"] in (1,2,3,4,5)

def test_story_fitting_timeline_skips_mismatched_old_endings():
    assert set(SCENE_TIMES)==set(IDS)
    for id,times in SCENE_TIMES.items():
        assert len(times)==5
        assert all(.01<=t<=.95 for t in times)
    # GTA ends on its race-car sequence, not fantasy portrait;
    # AI GIFs end on the robot, not the off-topic soccer figure.
    assert SCENE_TIMES["game-001-gta4-gta5"][-1]<.50
    assert SCENE_TIMES["alchemy-001-chatgpt-gifs"][-1]<.50

def test_native_captions_keep_reference_profile():
    row=validate_plan()["projects"][0]
    captions=[{"startFrame":0,"endFrame":40,"text":"Se inscreve",
               "words":[{"startFrame":0,"endFrame":20,"text":"Se"},
                        {"startFrame":20,"endFrame":40,"text":"inscreve"}]}]
    props=build_scene_props(row,[Path(f"scene-{i}.png") for i in range(5)],
                            Path("voice.mp3"),captions,30.0,"native-v4-test")
    assert props["visualProfile"]=="gamer-alchemy-reference"
    assert props["hook"].count("\n")==1
    assert len(props["scenes"])==5
    assert props["captions"]==captions
    assert props["id"].endswith("-v4")

def test_cover_is_always_official_program():
    assert render_cover.__module__=="capa_cinematografica"
    source=(ROOT/"scripts/games_alchemy_reference_v4.py").read_text(encoding="utf-8")
    assert 'template="gamer-alchemy-reference"' in source
    assert 'qa' in source
    assert '"cover_template":"gamer-alchemy-reference"' in source
    assert '"revision":"v4"' in source

def test_one_shot_upload_does_not_run_without_approval(monkeypatch):
    for name in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME",
                 "GITHUB_RUN_ATTEMPT","GITHUB_WORKFLOW","REFERENCE_V4_APPROVED","SOURCE_RUN_ID"):
        monkeypatch.delenv(name,raising=False)
    with pytest.raises(NativeRecutBlocked,match="WRONG_REPOSITORY"):
        guard()


def test_historic_v4_private_upload_is_readable_but_cannot_be_rendered_again():
    from production_reservations import get_entry
    plan=validate_plan()
    assert len(plan["projects"])==6
    for project in plan["projects"]:
        episode=project["source_episode_id"]+"-v4"
        item=get_entry(project["channel"],episode)
        assert item is not None
        assert item["reservation_owner"]==OWNER
        assert item["status"]=="private_uploaded"
        assert item["publication_target"]=="private_first"
    # Reviewing old metadata must never make an already uploaded clip
    # eligible for another rendering/upload.
    with pytest.raises(ValueError,match="ALREADY_PUBLISHED_OR_RESERVED_BY_ANOTHER_WORKFLOW"):
        validate_plan(for_render=True)
