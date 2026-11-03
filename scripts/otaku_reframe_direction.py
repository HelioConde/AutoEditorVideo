#!/usr/bin/env python3
"""Storyboard English-language retention directions. No AI, uploads or PT edits.

The EN storyboard is pinned separately from the Brazilian production plan.
Every newly generated shot requires human approval before rendering.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from roteiro_para_storyboard import build_storyboard

MAX_HOLD = 4.2

# Per narration beat: distinctive location/action, no reused dark bedroom
# and no Shinigami on screen before the reveal.
BEATS = (
    ("school courtyard at dawn", "extreme close-up on a BLACK notebook landing on pavement, Light's hand entering frame", "Light's hand only", "hard"),
    ("Japanese high school walkway", "Light discovers the BLACK notebook on the ground; school exterior, cautious expression", "Light Yagami", "hard"),
    ("Light's bedroom with television news", "side angle, Light WRITES in the notebook while an ordinary news broadcast plays", "Light Yagami", "hard"),
    ("television broadcast inset inside Light's room", "TV screen shows a fictional criminal collapsing; Light reacts in a separate perspective, non-graphic", "Light Yagami", "hard"),
    ("quiet Japanese street at dusk", "Light witnesses a threatening motorcycle rider and considers testing the notebook again; no graphic impact", "Light Yagami", "hard"),
    ("desk illuminated by notebook pages", "macro close-up of notebook and trembling hand as Light realizes the second test succeeded", "Light's hand only", "hard"),
    ("urban skyline with abstract news screens", "wide city panorama, anonymous headlines and news screens imply rising criminal deaths; no readable words", "No named characters", "crossfade"),
    ("empty school rooftop under storm clouds", "ominous notebook falling through dramatic sky; mysterious origin but no Shinigami yet", "No named characters", "hard"),
    ("dark supernatural realm with swirling clouds", "wide shot of eerie empty gothic realm; presence implied but no character visible", "No named characters", "hard"),
    ("Light's bedroom at night", "FIRST on-screen reveal of Ryuk in the doorway, dramatic opposing silhouette with Light reacting", "Light Yagami and Ryuk", "hard"),
    ("Light's bedroom, reverse low angle", "Light declares his plan with notebook raised, Ryuk reacts in the background", "Light Yagami and Ryuk", "hard"),
    ("city rooftop overlooking Japan at night", "final portrait of Light and the notebook with distant city lights, a questioning expression", "Light Yagami", "hard"),
)


def build_english_plan(item: dict, *, max_hold: float = MAX_HOLD) -> dict:
    beats = item.get("scenes") or []
    if not beats or len(beats) != len(BEATS):
        raise ValueError("O roteiro de EP01 requer 12 blocos de continuidade.")
    if item.get("id") != "101-death-note-ep01":
        raise ValueError("Esta direcao visual cobre apenas Death Note EP01.")
    episode = dict(item)
    episode.update(
        effect="recap",
        character="Light Yagami, brown-haired Japanese high school student",
        object="single plain black Death Note notebook",
        background="location changes between school, town street, city and bedroom",
        blocos_visuais=[beat["narration"] for beat in beats],
    )
    storyboard = build_storyboard(episode, max_hold=max_hold, duration=56)
    for shot in storyboard["scenes"]:
        beat_idx = int(shot["bloco_id"]) - 1
        location, action, allowed, transition = BEATS[beat_idx]
        no_ryuk = beat_idx < 9
        # High-priority directions go first, before generic shot/style text.
        direction = (
            f"CANON CONTINUITY — scene {beat_idx + 1}/12. SETTING: {location}. "
            f"VISUAL ACTION: {action}. ALLOWED PEOPLE: {allowed}. "
            "Change location, light and camera framing from the previous shot. "
            "Illustrate this precise narration beat, not a generic character poster. "
            "Only one coherent cinematic shot, no split screen, no overlaid typography. "
        )
        if no_ryuk:
            direction += (
                "HARD EXCLUSION: Ryuk must NOT appear; no shinigami, demon, "
                "winged silhouette, yellow eyes or supernatural figure. "
                "His first visible appearance is reserved for scene 10. "
            )
        if beat_idx == 9:
            direction += "Reveal Ryuk for the FIRST TIME here: a strong cinematic surprise. "
        shot["prompt"] = direction + shot["prompt"]
        shot["setting"] = location
        shot["beat_role"] = beats[beat_idx]["role"]
        shot["transition_style"] = transition
        shot["correcao_visual"] = {
            "requires_manual_approval": True,
            "reason": "New English visual continuity and no-Ryuk-before-reveal policy",
        }
    storyboard["language"] = "en-US"
    storyboard["editorial_revision"] = "otaku-reframe/retention-v2"
    storyboard["source_script_sha256"] = hashlib.sha256(
        item["script"].encode("utf-8")
    ).hexdigest()
    storyboard["visual_rule"] = "first Ryuk reveal in beat 10; unique locations; <=4.2s holds"
    return storyboard


def ensure_english_plan(item: dict, folder: Path) -> Path:
    """Fail closed on changed narration, preserving any approved local cache."""
    path = folder / "storyboard-reframe-v2.json"
    fingerprint = hashlib.sha256(item["script"].encode("utf-8")).hexdigest()
    if path.is_file():
        current = json.loads(path.read_text(encoding="utf-8"))
        if current.get("source_script_sha256") != fingerprint:
            raise ValueError(
                "Roteiro EN mudou desde o plano fixado; revise manualmente o "
                "storyboard existente antes de qualquer regeneracao."
            )
        if current.get("editorial_revision") != "otaku-reframe/retention-v2":
            raise ValueError("Storyboard EN fixado tem versao desconhecida.")
        return path
    plan = build_english_plan(item)
    folder.mkdir(parents=True, exist_ok=True)
    # No touching PT storyboard, existing MP4s or generated images.
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
