"""Offline regression tests for the new five-channel 15-video private-first batch."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import five_channel_fifteen_20261108 as batch


def test_exact_fifteen_original_reservations():
    d=json.loads(batch.MANIFEST.read_text(encoding="utf-8"))
    assert len(d["episodes"])==15
    assert sum(len(batch.validate(c)) for c in batch.CHANNELS)==15
    assert len({(r["channel"],r["id"]) for r in d["episodes"]})==15
    for c in batch.CHANNELS:
        rows=batch.validate(c)
        assert len(rows)==3
        assert all(r["channel"]==c for r in rows)
        assert all(r["production_state"]["youtube_id"] is None for r in rows)


def test_kids_audience_and_original_standalone_only():
    kids=batch.validate("kids")
    assert all(r["made_for_kids"] is True for r in kids)
    assert all("fofinhos" not in r["narration_script"].lower() for r in kids)
    assert all(r["series"]=="standalone_children_story_not_fofinhos" for r in kids)
    assert not any(r["made_for_kids"] for c in ("br","en","games","alchemy") for r in batch.validate(c))


def test_no_false_gameplay_or_ai_demo_claims():
    for r in batch.validate("games"):
        assert "não são capturas de gameplay" in r["description"].lower()
        assert "joguei" not in r["narration_script"].lower()
    for r in batch.validate("alchemy"):
        assert any(s in r["description"].lower() for s in ("conceitual","conceituais"))


def test_private_only_and_no_secret_names_in_render_script():
    p=(ROOT/"scripts"/"five_channel_fifteen_upload_20261108.py").read_text(encoding="utf-8")
    assert '"privacyStatus":"private"' in p
    assert 'meta["selfDeclaredMadeForKids"]' in p
    for c in batch.CHANNELS:
        assert batch.TOKENS[c].startswith("YOUTUBE_")
    assert batch.IMAGE_BUDGET==24
    assert batch.WORKFLOW.endswith("private-first")
