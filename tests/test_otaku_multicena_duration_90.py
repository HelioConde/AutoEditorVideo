"""90-second YouTube Shorts editorial A/B test; never synthesizes or uploads."""
import importlib
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
duration=importlib.import_module("otaku_multicena_duration_90")

def test_all_fifty_anime_have_ninety_second_plan_and_five_complete_pilots():
    report=duration.verify_catalog()
    assert report["total_anime"]==50
    assert report["target_duration_seconds"]==90
    assert report["allowed_audio_duration_seconds"]==[87,93]
    assert report["fully_drafted_pilots_needing_review"]==5
    assert report["outlines_without_complete_scripts"]==45
    assert report["creator_pause_enforced"] is True
    assert report["no_videos_generated"] is True
    assert report["no_upload"] is True
    assert report["no_actual_audio_measured"] is True
    assert [row["rank"] for row in report["stories"]]==list(range(1,51))
    assert all(x["safe_to_render"] is False for x in report["stories"])

def test_pilots_are_fully_different_stories_with_short_hooks_and_six_beats():
    plan=duration.load(duration.PLAN)
    drafted=[r for r in plan["items"] if r["narration_script"]]
    assert len(drafted)==5
    assert len({r["narration_script"] for r in drafted})==5
    assert len({r["anime"] for r in drafted})==5
    for row in drafted:
        assert 190<=duration.word_count(row["narration_script"])<=225
        assert row["story_segments"][0]["word_count"]<=8
        assert [s["role"] for s in row["story_segments"]]==list(duration.ROLES)
        assert row["estimated_seconds_at_150_wpm"]<90
        assert row["real_tts_measured_seconds"] is None
        assert row["factual_review"] is False
        assert row["ready_to_render"] is False

def test_actual_voice_must_be_measured_to_enforce_ninety_seconds():
    for valid in (87,89.7,90,92.9,93):
        assert duration.validate_measured_seconds(valid)==round(valid,3)
    for invalid in (0,59.9,86.9,93.1,180):
        with pytest.raises(duration.DurationBlocked,match="TTS_AUDIO_OUTSIDE_ALLOWED"):
            duration.validate_measured_seconds(invalid)
    with pytest.raises(duration.DurationBlocked,match="REAL_AUDIO_FILE_REQUIRED"):
        duration.measure_audio_seconds(ROOT/"missing.mp3")

def test_tampered_profiles_or_faked_scripts_are_blocked():
    p=duration.load(duration.PLAN)
    p["items"][0]["story_segments"][0]["word_count"]=999
    with pytest.raises(duration.DurationBlocked,match="SEGMENT_WORD_COUNT_MISMATCH"):
        duration.verify_record(p,p["items"][0])
    p=duration.load(duration.PLAN)
    p["items"][5]["narration_script"]="some fake story"
    with pytest.raises(duration.DurationBlocked,match="OUTLINE_CANNOT_PRETEND"):
        duration.verify_record(p,p["items"][5])
    p=duration.load(duration.PLAN)
    p["items"][0]["ready_to_render"]=True
    with pytest.raises(duration.DurationBlocked,match="INVALID_UNAPPROVED"):
        duration.verify_record(p,p["items"][0])

def test_comparison_is_made_at_equal_age_not_mixed_upload_windows():
    report=duration.verify_catalog()
    comparison=report["editorial_test_comparison"]
    assert comparison["control_duration_seconds"]==[35,45]
    assert comparison["experiment_duration_seconds"]==[87,93]
    assert "views_48h" in comparison["matched_metrics"]
    assert "percentage_viewed" in comparison["matched_metrics"]
    assert "subscribers_per_1000_views" in comparison["matched_metrics"]

def test_planning_script_has_no_generation_and_upload_side_effects():
    source=(ROOT/"scripts/otaku_multicena_duration_90.py").read_text(encoding="utf-8")
    for token in ("youtube.videos().insert", "gh workflow run", "request_image(",
                  "ensure_voice(", "render:master", "youtube.upload", "proxy_key("):
        assert token not in source
