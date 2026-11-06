"""Safe, deterministic experiments derived from creator-provided channel audit."""
import importlib
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
strategy=importlib.import_module("otaku_multicena_strategy_plan")

def test_editorial_plan_keeps_pause_and_refuses_algorithm_certainty():
    import json
    d=json.loads(strategy.DATA.read_text(encoding="utf-8"))
    result=strategy.experiment_plan(d)
    assert result["mode"]=="offline_only_generation_and_upload_paused"
    assert result["release"]=={"generated":False,"published":False,"resume_authorized":False}
    assert result["planned_total"]==15
    assert [r["shorts_per_day"] for r in result["cadence_hypotheses"]]==[2,3]
    assert "Not evidence" in result["cadence_assumption"]
    assert not result["longform_idea"]["approved_for_production"]
    assert len(result["top_examples"])==5
    assert result["top_five_death_note_count"]==2
    assert result["channel_views_per_video"]==112.36
    assert result["reported_shorts_average"]==130
    assert result["means_are_not_same_metric"] is True

def test_headline_patterns_are_optional_not_hardcoded():
    a=strategy.analyze_title("Zenitsu luta melhor DORMINDO?! ⚡")
    assert a["checks"]["reasonable_length"]
    assert a["checks"]["direct_promise"]
    assert a["predicted_views"] is None
    b=strategy.analyze_title("Steel Ball Run: A corrida que muda tudo 🏁")
    assert "direct_promise" in b["review_reasons"]
    assert b["human_factual_check_required"] is True
    assert strategy.analyze_title("LIGHT VENCE!!!")["review_reasons"]

def test_empty_or_unverified_snapshot_cannot_authorize_a_plan():
    with pytest.raises(strategy.StrategyBlocked):
        strategy.analyze_title("  ")
    with pytest.raises(strategy.StrategyBlocked):
        strategy.experiment_plan({})
    with pytest.raises(strategy.StrategyBlocked):
        strategy.experiment_plan({"audit_snapshots":[{"top_five":[]}]})

def test_strategy_source_never_invokes_youtube_or_image_provider():
    text=(ROOT/"scripts/otaku_multicena_strategy_plan.py").read_text(encoding="utf-8")
    assert "youtube.videos()" not in text
    assert "request_image(" not in text
    assert "gh workflow run" not in text
