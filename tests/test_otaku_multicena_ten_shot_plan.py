"""Ten-shot read-only editorial proposals for pending anime Shorts."""
from pathlib import Path
import importlib
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
planner=importlib.import_module("otaku_multicena_ten_shot_plan")
from otaku_br_50_reverso import validate
from otaku_multicena_quality_v3 import words,phrase_position

def test_five_pending_episodes_get_ten_distinct_shots_each_without_new_media():
    report=planner.build_report([5,4,3,2,1])
    assert report["videos_generated"] is False
    assert report["youtube_uploads"]==0
    assert report["creator_pause_preserved"] is True
    assert report["files_created"] is False
    assert report["planned_episode_numbers"]==[5,4,3,2,1]
    for plan in report["plans"]:
        assert plan["planned_shot_count"]==10
        assert plan["media_generated"] is False
        assert plan["youtube_authorized"] is False
        assert plan["rights_checked"] is False
        assert plan["narration_script"] == validate()[plan["episode_number"]-1]["narration_script"]
        assert len({s["start_phrase_candidate"] for s in plan["shots"]})==10
        assert len({s["shot_type"] for s in plan["shots"]})>=5
        assert all(not s["artwork_exists"] and not s["pose_frames_exist"] for s in plan["shots"])
        assert plan["shots"][0]["beat_role"]=="hook"
        assert plan["shots"][-1]["beat_role"]=="cta"

def test_cues_are_unique_in_narration_and_in_correct_order():
    row=validate()[0]
    plan=planner.plan_one(row)
    tokenized=words(plan["narration_script"])
    markers=[{"text":word} for word in tokenized]
    indexes=[phrase_position(markers,s["start_phrase_candidate"]) for s in plan["shots"]]
    assert indexes==sorted(indexes)
    assert indexes[0]==0
    assert all(right-left>=4 for left,right in zip(indexes,indexes[1:]))

def test_rejects_short_story_instead_of_inventing_extra_dialogue():
    row=validate()[0].copy()
    row["narration_script"]="uma historia curta"
    with pytest.raises(planner.StoryboardBlocked,match="TEN_SHOTS_REQUIRE"):
        planner.plan_one(row)

def test_requires_unique_episode_selection_and_supported_bounds():
    for ids in ([1,1],[0],[51],[]):
        with pytest.raises(planner.StoryboardBlocked):
            planner.build_report(ids)

def test_planner_has_no_media_provider_or_publication_side_effects():
    source=(ROOT/"scripts/otaku_multicena_ten_shot_plan.py").read_text(encoding="utf-8")
    for token in ("request_image(", "ensure_voice(", "youtube.videos().insert",
                  "render:master", "gh workflow run"):
        assert token not in source
