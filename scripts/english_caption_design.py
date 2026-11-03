#!/usr/bin/env python3
"""English Shorts: group timed TTS words while keeping per-word highlight data."""
from __future__ import annotations


def grouped_captions(words: list[dict], *, fps: int = 30, max_words: int = 3,
                     max_seconds: float = 1.2, max_chars: int = 23) -> list[dict]:
    if fps <= 0 or max_words < 1 or max_seconds <= 0:
        raise ValueError("Parametros de caption invalidos")
    valid = []
    for word in words:
        start = int(word["startFrame"])
        end = int(word["endFrame"])
        text = str(word["text"]).strip()
        if end > start and text:
            valid.append({"startFrame": start, "endFrame": end, "text": text})
    if not valid:
        raise ValueError("TTS sem palavras validas")
    groups = []
    current: list[dict] = []

    def emit():
        if not current:
            return
        text = " ".join(w["text"] for w in current)
        groups.append({
            "startFrame": current[0]["startFrame"],
            "endFrame": current[-1]["endFrame"],
            "text": text,
            "words": list(current),
        })

    for word in valid:
        next_words = current + [word]
        candidate = " ".join(w["text"] for w in next_words)
        gap = word["startFrame"] - current[-1]["endFrame"] if current else 0
        too_long = (
            len(next_words) > max_words or len(candidate) > max_chars
            or next_words[-1]["endFrame"] - next_words[0]["startFrame"] > fps * max_seconds
            or gap > round(fps * 0.16)
            or gap < -round(fps * 0.25)
        )
        if current and too_long:
            emit()
            current = [word]
        else:
            current = next_words
    emit()
    return groups
