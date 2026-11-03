"""The guided AutoEditorVideo reviewer must never auto-approve a shot."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import revisar_reframe_en as review


def row(tmp_path: Path) -> dict:
    (tmp_path / "master.png").write_bytes(b"master")
    (tmp_path / "comparacao.jpg").write_bytes(b"comparison")
    return {
        "id": "01",
        "folder": tmp_path,
        "master": tmp_path / "master.png",
        "comparison": tmp_path / "comparacao.jpg",
        "missing": [],
        "status": "pendente",
    }


def test_pular_does_not_approve(tmp_path, monkeypatch):
    rec = []
    monkeypatch.setattr(review, "write_review", lambda *args, **kw: rec.append(kw))
    opened = []
    assert review.perform_review(
        row(tmp_path), opener=lambda path: opened.append(path),
        input_func=lambda prompt: "PULAR"
    ) == "pular"
    assert len(opened) == 2
    assert not rec


def test_approve_requires_exact_scene_id_and_reason(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(review, "write_review", lambda *args, **kw: calls.append(kw))
    r = row(tmp_path)
    assert review.perform_review(r, opener=lambda p: None,
                                 input_func=lambda p: "APROVAR 02") == "pular"
    assert not calls
    commands = iter(["APROVAR 01", "Sem problemas visuais, revisado pessoalmente"])
    assert review.perform_review(r, opener=lambda p: None,
                                 input_func=lambda p: next(commands)) == "aprovado"
    assert calls[0]["status"] == "aprovado"
    assert "revisado" in calls[0]["reason"]


def test_short_or_empty_reason_cannot_approve(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(review, "write_review", lambda *args, **kw: calls.append(kw))
    commands = iter(["APROVAR 01", "ok"])
    assert review.perform_review(row(tmp_path), opener=lambda p: None,
                                 input_func=lambda p: next(commands)) == "pular"
    assert calls == []


def test_reject_needs_reason_and_is_not_published(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(review, "write_review", lambda *args, **kw: calls.append(kw))
    commands = iter(["REPROVAR 01", "Mao deformada na imagem principal"])
    assert review.perform_review(row(tmp_path), opener=lambda p: None,
                                 input_func=lambda p: next(commands)) == "reprovado"
    assert calls[0]["status"] == "reprovado"


def test_cannot_approve_missing_comparison(tmp_path):
    r = row(tmp_path)
    r["comparison"].unlink()
    r["missing"] = ["comparacao.jpg"]
    with pytest.raises(FileNotFoundError, match="comparacao.jpg"):
        review.perform_review(r, opener=lambda p: None,
                              input_func=lambda p: "APROVAR 01")
