"""Automatic QA must never falsify approvals or ignore explicit rejections."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import qa_automatico_reframe_en as qa


def plan():
    return {
        "id": "201-death-note-rosto-nome",
        "language": "en-US",
        "source_script_sha256": "a" * 64,
        "scenes": [
            {"id": "01", "correcao_visual": {"requires_manual_approval": True}},
            {"id": "02", "correcao_visual": {"requires_manual_approval": True}},
        ],
    }


def test_auto_mode_accepts_unreviewed_without_forging_manual_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(qa, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(qa, "read_review", lambda p: None)
    original = plan()
    checked, report = qa.prepare_qa_storyboard(original, "gpt-image-1.5")
    assert report == {
        "mode": "automatico", "total_scenes": 2,
        "explicitly_approved": 0, "auto_checked": 2,
        "manual_approvals_forged": False,
    }
    assert all(not scene["correcao_visual"]["requires_manual_approval"]
               for scene in checked["scenes"])
    assert all(scene["correcao_visual"]["automatic_technical_qa"]
               for scene in checked["scenes"])
    assert all(scene["correcao_visual"]["requires_manual_approval"]
               for scene in original["scenes"])


def test_explicitly_rejected_scene_always_blocks_auto_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(qa, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(qa, "read_review", lambda p: {"status": "reprovado"})
    with pytest.raises(ValueError, match="reprovada"):
        qa.prepare_qa_storyboard(plan(), "gpt-image-1.5")


def test_manual_mode_still_blocks_unreviewed_scene(monkeypatch, tmp_path):
    monkeypatch.setattr(qa, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(qa, "read_review", lambda p: None)
    with pytest.raises(ValueError, match="aguarda revisao"):
        qa.prepare_qa_storyboard(plan(), "gpt-image-1.5", "manual")


def test_requires_original_signed_english_storyboard(monkeypatch, tmp_path):
    monkeypatch.setattr(qa, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(qa, "read_review", lambda p: None)
    for bad in ({**plan(), "language": "pt-BR"},
                {**plan(), "source_script_sha256": ""}):
        with pytest.raises(ValueError, match="EN originais assinados"):
            qa.prepare_qa_storyboard(bad, "gpt-image-1.5")


def test_manual_mode_with_explicit_approval_remains_available(monkeypatch, tmp_path):
    monkeypatch.setattr(qa, "scene_dir", lambda *a: tmp_path)
    monkeypatch.setattr(qa, "read_review", lambda p: {"status": "aprovado"})
    checked, report = qa.prepare_qa_storyboard(plan(), "gpt-image-1.5", "manual")
    assert report["explicitly_approved"] == 2
    assert report["auto_checked"] == 0
    assert all(s["correcao_visual"]["requires_manual_approval"] for s in checked["scenes"])
