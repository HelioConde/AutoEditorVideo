"""Preserve hero chess pieces when 2.5D extraction might erase them.

A chess king and the hand touching it are a single foreground/occlusion
problem; generic "personagens" segmentation plus inpainting can remove the
king from the recomposition while master.png still contains it.
"""
from __future__ import annotations

HERO_CHESS_SHOTS=frozenset({
    "light_moves_king",
    "l_moves_king",
    "king_hand_macro",
    "top_board",
})


def master_static_for_chess_action(scene:dict)->bool:
    """Fail safe, independent of image similarity or perceptual QA score."""
    return scene.get("shot_type") in HERO_CHESS_SHOTS


def hero_prop_prompt(scene:dict)->str:
    """Keep future extraction focused on both the player hand and chess king."""
    if not master_static_for_chess_action(scene):
        return ""
    return (
        "IMPORTANT HERO OBJECT: preserve the EXACT visible chess king and the "
        "hand moving it as ONE complete action. Do not remove, recolor, "
        "duplicate, hallucinate, shrink or erase the chess king. "
        "Keep the original contact between fingertips and piece and preserve "
        "their X/Y geometry. The wooden board and its squares remain static "
        "background; the king is a distinct foreground object. "
        "Never create floating fingers or a hand gripping empty air."
    )
