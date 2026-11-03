"""Offline QA for English Death Note editorial continuity and cut timing."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from otaku_reframe_direction import MAX_HOLD, BEATS, build_english_plan, ensure_english_plan

MANIFEST = ROOT / "conteudos" / "otaku-reframe-ep01-en.json"


def _episode():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["episodes"][0]


def test_every_english_beat_has_distinct_visual_narration_and_review():
    plan = build_english_plan(_episode())
    assert plan["language"] == "en-US"
    assert plan["editorial_revision"] == "otaku-reframe/retention-v2"
    assert len(plan["scenes"]) >= 12
    assert len(BEATS) == 12
    assert len({x[0] for x in BEATS}) >= 9  # no repetitive bedroom montage
    assert all(s["duracao_estimada_s"] <= MAX_HOLD + .01 for s in plan["scenes"])
    assert all(s["correcao_visual"]["requires_manual_approval"] for s in plan["scenes"])
    assert all(s["transition_style"] in ("hard", "crossfade") for s in plan["scenes"])
    assert plan["scenes"][0]["beat_role"] == "hook"
    assert plan["scenes"][-1]["beat_role"] == "cta"


def test_shinigami_reveal_is_delayed_and_early_prompts_forbid_ryuk():
    plan = build_english_plan(_episode())
    early = [s for s in plan["scenes"] if int(s["bloco_id"]) < 10]
    reveal = [s for s in plan["scenes"] if int(s["bloco_id"]) == 10]
    assert early and reveal
    assert all("HARD EXCLUSION: Ryuk must NOT appear" in s["prompt"] for s in early)
    assert all("Reveal Ryuk for the FIRST TIME" in s["prompt"] for s in reveal)
    assert all(s["transition_style"] == "hard" for s in reveal)
    assert "school" in plan["scenes"][1]["prompt"].lower()
    assert "motorcycle" in " ".join(s["prompt"] for s in plan["scenes"])


def test_pinned_english_storyboard_is_stable_and_rejects_changed_script(tmp_path):
    episode = _episode()
    path = ensure_english_plan(episode, tmp_path)
    original = path.read_bytes()
    assert ensure_english_plan(episode, tmp_path) == path
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="Roteiro EN mudou"):
        ensure_english_plan({**episode, "script": episode["script"] + " revised"}, tmp_path)
    assert path.read_bytes() == original


def test_non_ep1_cannot_reuse_ep1_art_directives():
    with pytest.raises(ValueError, match="apenas Death Note EP01"):
        build_english_plan({**_episode(), "id": "102-death-note-ep02"})
