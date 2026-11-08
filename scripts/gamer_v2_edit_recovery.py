#!/usr/bin/env python3
"""Bounded, character-anchored Gamer image-edit repair for provider HTTP 400.

A 400 is not automatically a retryable transport exception. In this explicit
creator-approved recovery path, ONE extra request with a materially different,
shorter story prompt may resolve an unsupported/overlong provider payload.
That request still uses the SAME genuine character reference image and never
falls back to text-to-image or unrelated stock/gameplay footage.

No provider response body, tokens, or individual account information is logged.
"""
from __future__ import annotations

from pathlib import Path
import re

class GamerEditBlocked(ValueError):
    pass

MAX_EXTRA_EDITS=6

def scene_core(scene:dict)->str:
    text=scene.get("visual_instruction","")
    # The old manifest repeats the full voice line in the visual instructions.
    # Remove that boilerplate; preserve the actual distinct scene's storyboard.
    marker=" Make an authentic original still editorial illustration"
    if marker in text:text=text.split(marker,1)[0]
    prefix=". "
    if prefix in text:text=text.split(prefix,1)[1]
    return text.strip().rstrip(".")[:230]

def compact_scene_prompt(row:dict,scene:dict,chars:list[dict],*,fallback:bool)->str:
    selected=[c for c in chars if c["key"] in scene["character_keys"]]
    if not selected or row.get("channel")!="games":
        raise GamerEditBlocked("GAMER_ONLY_NAMED_REFERENCE_REQUIRED")
    subjects="; ".join(c["name"]+" — "+c["canonical_appearance"][:265] for c in selected)
    task=scene_core(scene)
    if len(task)<16:raise GamerEditBlocked("STORYBOARD_SCENE_NOT_DEFINED")
    if fallback:
        # Compact alternative: references remain, but unsupported repeated
        # details are intentionally removed. This is NOT an identical retry.
        return (
            "EDIT THE ATTACHED REFERENCE IMAGE. Keep exactly the same "
            "recognizable block-shaped game character, voxel geometry, colors "
            "and clothes. Make a fresh coherent original vertical game-art "
            "illustration, natural square block proportions. "
            "Scene: "+task+". "
            "Do not add text, logos, subtitles, gameplay UI or watermarks."
        )
    return (
        "Use the ATTACHED REAL REFERENCE IMAGE as the mandatory appearance of "
        "the same character. Change the pose, background and framing to this "
        "new original illustrated game scene; no generic character swaps. "
        "Reference identity: "+subjects+". "
        "Scene action: "+task+". "
        "Narration context: "+scene["editorial_beat"][:130]+". "
        "Preserve signature game shapes, block colors and costume. "
        "Portrait 1024x1536, one frame, anatomically consistent block-built "
        "subject, no words, typography, logos, watermarks or video screenshots."
    )

def edit_with_bounded_http400_repair(
    master:Path,row:dict,scene:dict,chars:list[dict],
    model:str,key:str,edit_call,extra_budget:list[int]
)->tuple[bytes,str]:
    """Return (image_bytes, strategy). Never call text-only generation.

    Callers must pass the real reference image, a proven image-edit function,
    and a shared [remaining] extra budget across all videos in one run.
    """
    if (model!="gpt-image-2" or not master.is_file() or master.stat().st_size<30_000
            or len(extra_budget)!=1 or not 0<=extra_budget[0]<=MAX_EXTRA_EDITS):
        raise GamerEditBlocked("EXACT_REAL_ANCHOR_REFERENCE_BUDGET_REQUIRED")
    first=compact_scene_prompt(row,scene,chars,fallback=False)
    try:
        return edit_call(master,first,model,key,transparent=False),"compact_reference_edit"
    except RuntimeError as exc:
        if "HTTP 400" not in str(exc):
            # Do not retry missing permissions, bad keys, server errors or
            # unidentified proxy failures; no blind duplicate provider calls.
            raise
        if extra_budget[0]<=0:
            raise GamerEditBlocked("GLOBAL_SIX_EXTRA_EDIT_CALLS_EXHAUSTED") from None
        fallback=compact_scene_prompt(row,scene,chars,fallback=True)
        if fallback==first:
            raise GamerEditBlocked("DUPLICATE_HTTP400_PROMPT_NOT_RETRIED") from None
        extra_budget[0]-=1
        print("GAMER_V2_HTTP400_RECOVERY_SHORT_PROMPT_SAME_REAL_ANCHOR",flush=True)
        # At most ONE additional request for this scene.
        return edit_call(master,fallback,model,key,transparent=False),"short_reference_edit_after_http400"
