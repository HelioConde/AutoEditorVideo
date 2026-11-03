"""No local EN Short can be marked ready without manual per-shot QA."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validar_reframe_en as gate


def _plan():
    return {"id": "201-death-note-rosto-nome", "scenes": [
        {"id": "01", "correcao_visual": {"requires_manual_approval": True}},
        {"id": "02", "correcao_visual": {"requires_manual_approval": True}},
    ]}


def test_blocks_missing_first_review(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gate, "read_review", lambda p: None)
    with pytest.raises(ValueError, match="Cena 01 ainda nao aprovada"):
        gate.require_approved_scenes(_plan(), "gpt-image-1.5")


def test_blocks_rejected_review(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gate, "read_review", lambda p: {"status": "reprovado"})
    with pytest.raises(ValueError, match="Cena 01 ainda nao aprovada"):
        gate.require_approved_scenes(_plan(), "gpt-image-1.5")


def test_accepts_approved_caches_only(monkeypatch, tmp_path):
    monkeypatch.setattr(gate, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gate, "read_review", lambda p: {"status": "aprovado"})
    assert gate.require_approved_scenes(_plan(), "gpt-image-1.5") == 2


def test_no_audio_render_if_review_is_missing(monkeypatch, tmp_path):
    item = {"id": "201-death-note-rosto-nome", "scenes": [{"number": 1}]}
    monkeypatch.setattr(gate, "ensure_english_plan", lambda *a: tmp_path / "plan.json")
    monkeypatch.setattr(gate, "read_storyboard", lambda p: _plan())
    monkeypatch.setattr(gate, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gate, "read_review", lambda p: None)
    monkeypatch.setattr(gate.master, "validate_scenes", lambda *a, **kw:
                        pytest.fail("image QA must not start before approval"))
    monkeypatch.setattr(gate, "audio_for", lambda *a, **kw:
                        pytest.fail("audio QA must not start before approval"))
    with pytest.raises(ValueError, match="ainda nao aprovada"):
        gate.validate_item(item, "gpt-image-1.5", mode="manual", out=tmp_path)


def test_after_review_checks_audio_captions_and_image_qa(monkeypatch, tmp_path):
    item = {"id": "201-death-note-rosto-nome", "scenes": [{"number": 1}]}
    monkeypatch.setattr(gate, "ensure_english_plan", lambda *a: tmp_path / "plan.json")
    monkeypatch.setattr(gate, "read_storyboard", lambda p: _plan())
    monkeypatch.setattr(gate, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(gate, "read_review", lambda p: {"status": "aprovado"})
    monkeypatch.setattr(gate, "prepare_qa_storyboard", lambda plan, model, mode:
                        (plan, {"mode": mode, "explicitly_approved": len(plan["scenes"]),
                                "auto_checked": 0}))
    monkeypatch.setattr(gate.master, "validate_scenes", lambda *a, **kw: [1, 2])
    monkeypatch.setattr(gate, "audio_for", lambda *a, **kw: (tmp_path / "en.mp3", tmp_path / "en.ass"))
    monkeypatch.setattr(gate, "audio_duration", lambda *_: 52.0)
    monkeypatch.setattr(gate, "validate_planned_audio", lambda n, **kw: n)
    monkeypatch.setattr(gate, "captions_from_ass", lambda *a: [
        {"startFrame": 0, "endFrame": 20, "text": "Did"},
        {"startFrame": 20, "endFrame": 40, "text": "you"},
        {"startFrame": 40, "endFrame": 60, "text": "know?"}
    ])
    result = gate.validate_item(item, "gpt-image-1.5", out=tmp_path)
    assert result["status"] == "pronto_para_render_local"
    assert result["verified_visual_shots"] == 2
    assert result["captions"] >= 1
    assert result["renderer"] == "AutoEditorVideo/Remotion"
    assert result["youtube_published"] is False
