"""Proof that new English Shorts cannot silently use a third-party editor."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from otaku_reframe_production import REQUIRED, validate_english_production
from renderizar_shorts_en import load_english


@pytest.mark.parametrize("manifest", [
    "otaku-reframe-ep01-en.json",
    "otaku-reframe-did-you-know-201-en.json",
])
def test_canonical_english_episodes_use_only_autoeditorvideo(manifest):
    items = load_english(ROOT / "conteudos" / manifest)
    assert items
    assert all(item["production"] == REQUIRED for item in items)
    assert all(validate_english_production(item, item["production"]) == REQUIRED for item in items)


@pytest.mark.parametrize("field,invalid", [
    ("engine", "vidIQ"),
    ("images", "stock-vector-slideshow"),
    ("editor", "Cloudinary"),
    ("narration", "external-voice"),
    ("external_rendering", True),
    ("auto_publish", True),
    ("qa", "automatic-no-review"),
])
def test_external_production_paths_are_rejected(field, invalid):
    item = load_english(ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json")[0]
    unsafe = {**item["production"], field: invalid}
    with pytest.raises(ValueError, match="Pipeline EN invalido"):
        validate_english_production(item, unsafe)


def test_new_short_without_production_policy_is_rejected():
    item = load_english(ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json")[0]
    with pytest.raises(ValueError, match="production"):
        validate_english_production(item, None)


def test_legacy_dubbed_batch_stays_backward_compatible():
    for item in load_english():
        assert validate_english_production(item, None) == REQUIRED
