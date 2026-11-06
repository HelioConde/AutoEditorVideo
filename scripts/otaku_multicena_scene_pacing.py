#!/usr/bin/env python3
"""Plan five story images around real TTS word/sentence boundaries.

Changes scene timing only; it does NOT add frames, rigging or character animation.
Safe to audit offline. Never runs image generation or YouTube uploads.
"""
from __future__ import annotations

import math

class PacingBlocked(ValueError):
    pass

DEFAULT_FRACTIONS=(.12,.34,.58,.81)

def story_cuts(captions:list[dict],total_frames:int,fps:int=30,
               fractions:tuple[float,...]=DEFAULT_FRACTIONS)->list[int]:
    if (fps<=0 or total_frames<fps*20 or len(fractions)!=4
        or any(not 0<value<1 for value in fractions)
        or sorted(fractions)!=list(fractions)
        or not captions):
        raise PacingBlocked("INVALID_TTS_SCENE_TIMELINE")
    min_hold=max(2*fps,math.floor(total_frames*.05))
    if 5*min_hold>total_frames:
        raise PacingBlocked("NOT_ENOUGH_FRAMES_FOR_FIVE_SCENES")
    sentence_ends=[]
    caption_ends=[]
    for cap in captions:
        start=cap.get("startFrame")
        end=cap.get("endFrame")
        if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start:
            raise PacingBlocked("INVALID_CAPTION_MARKERS")
        caption_ends.append(end)
        for word in cap.get("words",[]):
            if (isinstance(word,dict) and
                    isinstance(word.get("text"),str) and
                    word["text"].rstrip().endswith((".","!","?","…")) and
                    isinstance(word.get("endFrame"),int)):
                sentence_ends.append(word["endFrame"])
    selected=[0]
    for i,frac in enumerate(fractions):
        earliest=selected[-1]+min_hold
        latest=total_frames-(4-i)*min_hold
        if earliest>latest:
            raise PacingBlocked("NO_ROOM_FOR_SCENE_CUT")
        wanted=round(total_frames*frac)
        preferred=[
            f for f in sentence_ends
            if earliest<=f<=latest and abs(f-wanted)<=round(fps*1.8)
        ]
        if not preferred:
            preferred=[
                f for f in caption_ends
                if earliest<=f<=latest and abs(f-wanted)<=round(fps*.85)
            ]
        chosen=min(preferred,key=lambda f:(abs(f-wanted),f)) if preferred else max(
            earliest,min(latest,wanted))
        selected.append(chosen)
    selected.append(total_frames)
    if len(selected)!=6 or any(right-left<min_hold for left,right in zip(selected,selected[1:])):
        raise PacingBlocked("INVALID_FINAL_SCENE_CUTS")
    return selected
