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
    """Storyboard canonico: EP01 legado ou episodio EN com direcoes por beat."""
    beats = item.get("scenes") or []
    if not beats or not isinstance(beats, list):
        raise ValueError("Short EN precisa de cenas narrativas.")
    legacy = item.get("id") == "101-death-note-ep01"
    if legacy and len(beats) != len(BEATS):
        raise ValueError("O roteiro EP01 requer 12 blocos de continuidade.")
    if not legacy and not all(isinstance(b.get("visual_direction"), dict) for b in beats):
        raise ValueError("Direcao visual automatica disponivel apenas Death Note EP01; "
                         "outros Shorts exigem visual_direction em cada beat.")
    script = item.get("script", "")
    if " ".join(b["narration"] for b in beats) != script:
        raise ValueError("Blocos EN precisam preservar exatamente o roteiro narrado.")

    episode = dict(item)
    episode.update(
        effect=item.get("effect", "recap"),
        character="Light Yagami, brown-haired Japanese high school student",
        object="single plain black Death Note notebook",
        background="scene-specific places, never one repetitive dark room",
        blocos_visuais=[beat["narration"] for beat in beats],
    )
    storyboard = build_storyboard(episode, max_hold=max_hold, duration=56)
    for shot in storyboard["scenes"]:
        beat_idx = int(shot["bloco_id"]) - 1
        beat = beats[beat_idx]
        instructions = beat.get("visual_direction")
        if instructions:
            required = ("setting", "action", "allowed_people", "transition_style")
            if any(not str(instructions.get(k, "")).strip() for k in required):
                raise ValueError(f"Direcao EN incompleta no beat {beat_idx + 1}")
            location, action, allowed = (
                instructions["setting"], instructions["action"], instructions["allowed_people"]
            )
            transition = instructions["transition_style"]
            if transition not in ("hard", "crossfade"):
                raise ValueError("Transicao EN invalida")
        else:
            location, action, allowed, transition = BEATS[beat_idx]
        direction = (
            f"CANON CONTINUITY — beat {beat_idx + 1}/{len(beats)}. "
            f"SETTING: {location}. VISUAL ACTION: {action}. "
            f"ALLOWED PEOPLE: {allowed}. "
            "Change location, lighting, camera perspective and focal subject "
            "from previous shots. The image must represent the narrated fact, "
            "not a generic anime poster. Compose one coherent vertical cinematic "
            "image only, no collage, typography, captions or watermark. "
        )
        if legacy and beat_idx < 9:
            direction += (
                "HARD EXCLUSION: Ryuk must NOT appear; no shinigami, demon, "
                "winged silhouette, yellow eyes or supernatural figure. "
                "His first visible appearance is reserved for beat 10. "
            )
        if legacy and beat_idx == 9:
            direction += "Reveal Ryuk for the FIRST TIME here, as a surprise. "
        if instructions and instructions.get("exclude"):
            direction += "HARD EXCLUSION: " + str(instructions["exclude"]) + ". "
        shot["prompt"] = direction + shot["prompt"]
        shot["setting"] = location
        shot["beat_role"] = beat["role"]
        shot["headline"] = beat.get("headline", "")
        shot["transition_style"] = transition
        shot["correcao_visual"] = {
            "requires_manual_approval": True,
            "reason": "New English editorial visual direction; individual human QA is mandatory",
        }
    storyboard["language"] = "en-US"
    storyboard["editorial_revision"] = "otaku-reframe/retention-v2"
    storyboard["source_script_sha256"] = hashlib.sha256(
        script.encode("utf-8")
    ).hexdigest()
    storyboard["source_visual_sha256"] = hashlib.sha256(
        json.dumps(beats, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    storyboard["visual_rule"] = (
        "first Ryuk reveal in beat 10; distinctive locations; <=4.2s holds"
        if legacy else "unique visual beats; original EN narrative; <=4.2s holds"
    )
    return storyboard

def ensure_english_plan(item: dict, folder: Path) -> Path:
    """Fail closed on changed narration, preserving any approved local cache."""
    path = folder / "storyboard-reframe-v2.json"
    fingerprint = hashlib.sha256(item["script"].encode("utf-8")).hexdigest()
    visual_fingerprint = hashlib.sha256(
        json.dumps(item.get("scenes", []), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if path.is_file():
        current = json.loads(path.read_text(encoding="utf-8"))
        if current.get("source_visual_sha256") and (
                current["source_visual_sha256"] != visual_fingerprint):
            raise ValueError("Direcao visual EN mudou; revise o cache fixado antes de regenerar.")
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


def main(argv: list[str] | None = None) -> int:
    """First-time bootstrap: pure stdlib visual planning before Pillow is installed."""
    import argparse
    parser = argparse.ArgumentParser(description="Pin EN-only visual storyboard; no AI or TTS")
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    data = json.loads(args.manifesto.read_text(encoding="utf-8-sig"))
    items = [ep for ep in data.get("episodes", []) if ep.get("id") == args.id]
    if len(items) != 1:
        raise ValueError("EP nao encontrado ou duplicado no manifesto EN")
    root = Path(__file__).resolve().parents[1]
    folder = root / "assets" / "gerados" / "shorts-animados" / args.id / "en-US"
    plan = ensure_english_plan(items[0], folder)
    print(f"[EN PLAN PINNED] {plan} (no image credits or uploads)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
