#!/usr/bin/env python3
"""Fail-closed production policy for original English Otaku Reframe Shorts.

These are pure configuration checks: no network, image generation, billing or
publication. The canonical production engine is the local GitHub AutoEditorVideo
pipeline, never a third-party cloud preview builder.
"""
from __future__ import annotations

REQUIRED = {
    "engine": "AutoEditorVideo",
    "runtime": "local-windows",
    "images": "codex-proxy",
    "narration": "edge-tts",
    "captions": "WordBoundary",
    "editor": "remotion",
    "qa": "manual-per-scene",
    "external_rendering": False,
    "auto_publish": False,
}


def validate_english_production(item: dict, production: dict | None) -> dict:
    """Apply to original scene-based EN Shorts; legacy dubbed batches are kept."""
    if not item.get("scenes"):
        return dict(REQUIRED)
    if not isinstance(production, dict):
        raise ValueError("Producao original EN exige production do AutoEditorVideo local.")
    mismatch = [
        key for key, expected in REQUIRED.items()
        if type(production.get(key)) is not type(expected)
        or production.get(key) != expected
    ]
    if mismatch:
        raise ValueError(
            "Pipeline EN invalido: somente AutoEditorVideo local, imagens pelo "
            "Codex Proxy, Edge TTS, Remotion e QA manual; campos: "
            + ", ".join(mismatch)
        )
    return dict(REQUIRED)
