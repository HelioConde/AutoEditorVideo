"""Score editorial planning, never claim produced media or guaranteed retention."""
from pathlib import Path
import copy
import importlib
import json
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
score=importlib.import_module("otaku_multicena_editorial_score_v5")
duration=importlib.import_module("otaku_multicena_duration_90")

def test_five_pilots_meet_nine_planning_checks_but_media_is_unapproved():
    result=score.audit()
    assert result["score"]==9 and result["out_of"]==10
    assert result["unwritten_anime_stories"]==45
    assert len(result["pilot_results"])==5
    assert result["published_short_count_from_this_plan"]==0
    assert result["generation_or_upload_authorized"] is False
    for row in result["pilot_results"]:
        assert row["planning_score"]==9
        assert sum(row["checks"].values())==9
        assert row["checks"]["measured_media_and_human_approval"] is False
        assert row["editorial_gate"].startswith("BLOCKED_")
        assert row["published"] is False

def test_real_lore_sources_and_story_micro_beats_are_present():
    plan=duration.load(duration.PLAN)
    for row in plan["items"][:5]:
        v5=row["story_quality_v5"]
        assert len(v5["canon_claims"])==3
        assert all(c["source_url"].startswith("https://") and
                   c["human_verified"] is False for c in v5["canon_claims"])
        assert [x["approx_second"] for x in v5["micro_reveals"]]==[15,31,51,70]
        for idx,beat in enumerate(v5["micro_reveals"]):
            assert row["narration_script"].count(beat["anchor"])==1
            assert beat["anchor"] in row["story_segments"][idx+1]["text"]
        assert len(v5["visual_shots"])==10
        assert len(set(shot["shot_type"] for shot in v5["visual_shots"]))>=5
        assert not any(shot["asset_ready"] for shot in v5["visual_shots"])
        assert v5["experiment_pair"]["both_no_cta"] is True
        assert v5["experiment_pair"]["control_script_ready"] is False

def test_quality_score_decreases_for_missing_lore_or_mid_story_reveal():
    plan=duration.load(duration.PLAN)
    catalog=duration.load(duration.CURATION)
    original=plan["items"][0]
    assert score.check_record(original,catalog["items"][0])["planning_score"]==9
    for change in ("fake_lore","remove_reveal","fake_visuals","remove_voice"):
        row=copy.deepcopy(original)
        v5=row["story_quality_v5"]
        if change=="fake_lore":
            v5["canon_claims"][0]["source_url"]="https://spam.example/untrusted"
        elif change=="remove_reveal":
            v5["micro_reveals"][1]["anchor"]="No such dialogue appears here"
        elif change=="fake_visuals":
            v5["visual_shots"][0]["asset_ready"]=True
        else:
            v5["narration"]["measured_tts_seconds"]=90  # cannot claim non-existent audio
        assert score.check_record(row,catalog["items"][0])["planning_score"]==8

def test_missing_pilot_score_is_not_patched_with_fake_facts():
    plan=duration.load(duration.PLAN)
    catalog=duration.load(duration.CURATION)
    row=copy.deepcopy(plan["items"][0])
    row["title"]="Unverified title"
    with pytest.raises(score.PlanBlocked,match="CATALOG_AND_PILOT_TITLE_NOT_ALIGNED"):
        score.check_record(row,catalog["items"][0])

def test_editorial_plan_is_never_a_media_generation_script():
    text=(ROOT/"scripts/otaku_multicena_editorial_score_v5.py").read_text(encoding="utf-8")
    for action in ("request_image(", "ensure_voice(", "youtube.videos().insert",
                   "gh workflow run", "render:master", "youtube.upload"):
        assert action not in text
