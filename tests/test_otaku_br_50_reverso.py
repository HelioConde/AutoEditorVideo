"""Offline contract for the Otaku Multicena 50 Short reverse-order experiment."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import otaku_br_50_reverso as batch


def test_fifty_unique_metadata_and_reserved_before_production():
    rows = batch.validate()
    assert len(rows) == 50
    assert [r["position"] for r in rows] == list(range(1, 51))
    assert [r["position"] for r in batch.ordered(rows)] == list(range(50, 0, -1))
    assert len({r["title"].casefold() for r in rows}) == 50
    assert len({r["hook"].casefold() for r in rows}) == 50
    assert len({r["id"] for r in rows}) == 50
    assert all(len(", ".join(r["tags"])) <= 500 for r in rows)
    assert all(len(r["storyboard"]) >= 5 for r in rows)
    assert all(r["description"].count("#Shorts") == 1 for r in rows)


def test_reverse_limit_selects_last_numbers_first():
    rows = batch.validate()
    assert [r["position"] for r in batch.candidates(rows, 3)] == [50, 49, 48]
    assert [r["position"] for r in batch.candidates(rows, 0)][-3:] == [3, 2, 1]


def test_draft_files_are_not_media_or_public_approval(monkeypatch, tmp_path):
    monkeypatch.setattr(batch, "OUTPUT", tmp_path)
    rows = batch.validate()
    output = batch.prepare(rows, 2)
    assert len(output) == 2
    assert [x["position"] for x in output] == [50, 49]
    assert not list(tmp_path.rglob("*.mp4"))
    assert not list(tmp_path.rglob("*.jpg"))
    assert not list(tmp_path.rglob("*.png"))
    report = batch.file_report(rows[-1], root=tmp_path)
    assert not report["ready_for_publication"]
    assert len(report["missing_artifacts"]) >= 10
    assert not report["qa_approved"]
    assert not report["rights_approved"]


def test_fail_closed_on_metadata_change(monkeypatch, tmp_path):
    original = json.loads(batch.PLAN.read_text(encoding="utf-8"))
    original["episodes"][0]["tags"].append("autoeditorvideo-internal-private")
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(batch, "PLAN", path)
    with pytest.raises(batch.PreflightError, match="INTERNAL_TAG_LEAK"):
        batch.validate()


def test_fail_closed_when_reservations_missing(monkeypatch, tmp_path):
    registry = json.loads(batch.RESERVATIONS.read_text(encoding="utf-8"))
    registry["entries"] = [
        e for e in registry["entries"]
        if not (e["channel"] == "br" and e["id"] == "6150-multicena-experimento-novembro")
    ]
    path = tmp_path / "missing-reservation.json"
    path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(batch, "RESERVATIONS", path)
    with pytest.raises(batch.PreflightError, match="EPISODE_NOT_RESERVED"):
        batch.validate()
