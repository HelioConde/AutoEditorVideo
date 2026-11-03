"""Offline editorial regression from vidIQ Short reports; no image generation."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from diversidade_visual import direction, direction_prompt


def test_first_non_chess_short_starts_with_narrative_conflict():
    episode = {
        "id": "qa-interaction",
        "effect": "recap",
        "character": "Misa Amane e Light Yagami",
        "object": "Death Note",
    }
    shot = direction(
        episode, 0,
        "Misa procurava Light, enquanto ele escondia um segredo.",
        "gancho",
    )
    prompt = direction_prompt(episode, shot)
    assert shot["shot_type"] == "establishing"
    assert "OPENING HOOK COMPOSITION" in prompt
    assert "If the hook names two characters" in prompt
    assert "Do NOT invent a later event" in prompt
    assert shot["focus_subject"] == "Misa Amane e Light Yagami"


def test_chess_opening_is_not_only_a_static_two_character_portrait():
    episode = {
        "id": "qa-chess",
        "effect": "chess",
        "character": "Light e L",
        "object": "rei preto no tabuleiro",
    }
    shot = direction(episode, 0, "Light e L travavam um duelo mental.", "gancho")
    prompt = direction_prompt(episode, shot)
    assert shot["shot_type"] == "wide_duel"
    assert "Avoid a solitary motionless portrait" in prompt
    assert "metaphor" in prompt.lower()
    assert "Do NOT invent a later event" in prompt
