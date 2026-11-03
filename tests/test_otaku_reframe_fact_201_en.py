"""Did You Know (Death Note name+face rule) English production checks; offline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from otaku_reframe_direction import MAX_HOLD, build_english_plan, ensure_english_plan
from renderizar_shorts_en import english_metadata, load_english

MANIFEST = ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json"


def episode():
    return load_english(MANIFEST)[0]


def test_did_you_know_has_a_canon_rule_and_original_english_hook():
    ep = episode()
    assert ep["id"] == "201-death-note-rosto-nome"
    assert ep["format"] == "did-you-know"
    assert ep["channel"] == "Otaku Reframe"
    assert ep["hook"].lower().startswith("did you know?")
    assert ep["script"].startswith(ep["hook"])
    assert ep["script"].endswith(ep["cta"])
    assert "subscribe to Otaku Reframe" in ep["cta"]
    assert "face" in ep["script"].lower()
    assert "same name" in ep["script"].lower()
    assert 110 <= len(ep["script"].split()) <= 155
    assert len(ep["scenes"]) == 12
    assert " ".join(b["narration"] for b in ep["scenes"]) == ep["script"]


def test_fact_storyboard_has_unique_settings_and_kira_rehook():
    plan = build_english_plan(episode())
    scenes = plan["scenes"]
    assert len(scenes) >= 12
    assert all(0 < scene["duracao_estimada_s"] <= MAX_HOLD + 0.01 for scene in scenes)
    assert len({b["visual_direction"]["setting"] for b in episode()["scenes"]}) >= 10
    assert any(scene["beat_role"] == "rehook" for scene in scenes)
    assert scenes[0]["beat_role"] == "hook"
    assert scenes[-1]["beat_role"] == "cta"
    assert any("ALLOWED PEOPLE" in s["prompt"] for s in scenes)
    assert all(s["correcao_visual"]["requires_manual_approval"] for s in scenes)
    assert all("no collage" in s["prompt"].lower() for s in scenes)


def test_fact_video_uses_focused_english_metadata():
    meta = english_metadata(episode())
    assert meta["idioma"] == "en"
    assert meta["categoria"] == "1"
    assert "#Shorts" in meta["descricao"]
    assert "What" in meta["descricao"] or "what" in meta["descricao"]
    assert "Death Note rules" in meta["tags"]
    assert "anime in hindi" not in meta["tags"]
    assert "full movie" not in meta["tags"]
    assert len(meta["tags"]) <= 15


def test_storyboard_is_pinned_for_this_fact_and_not_pt(tmp_path):
    ep = episode()
    output = ensure_english_plan(ep, tmp_path / "en-US")
    assert output.name == "storyboard-reframe-v2.json"
    original = output.read_bytes()
    assert ensure_english_plan(ep, tmp_path / "en-US").read_bytes() == original
    changed = json.loads(json.dumps(ep))
    changed["scenes"][2]["visual_direction"]["setting"] = "different train"
    with pytest.raises(ValueError, match="Direcao visual EN mudou"):
        ensure_english_plan(changed, tmp_path / "en-US")
    assert output.read_bytes() == original


def test_missing_visual_direction_fails_closed():
    changed = json.loads(json.dumps(episode()))
    del changed["scenes"][1]["visual_direction"]
    with pytest.raises(ValueError, match="direcoes explicitas|visual_direction"):
        build_english_plan(changed)
