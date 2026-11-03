#!/usr/bin/env python3
"""Prepare caption groups from real TTS word boundaries for Remotion.

No ASR estimates, hardcoded phrase offsets or extra media/network calls.
Edge WordBoundary and VoiceStudio-ASR markers are both supported.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path


FPS = 30


def marker_for_voice(voice: Path) -> Path:
    filename = voice.name
    if filename.startswith("voz-voicestudio-") and filename.endswith(".mp3"):
        token = filename[len("voz-voicestudio-"):-len(".mp3")]
        if len(token) != 16 or any(c not in "0123456789abcdef" for c in token):
            raise ValueError("Nome de voz VoiceStudio inválido")
        return voice.parent / f"marcacoes-voicestudio-{token}.json"
    if filename == "voz-master.mp3":
        return voice.parent / "marcacoes-voz.json"
    raise ValueError(f"Áudio sem origem de marcações identificável: {filename}")


def captions_from_markers(voice: Path, script: str, duration: float,
                          *, fps: int = FPS) -> list[dict] | None:
    """Return word-synced groups or None only when a legacy marker is absent."""
    if not script.strip() or not math.isfinite(duration) or duration <= 0 or fps < 1:
        raise ValueError("Roteiro, duração ou FPS inválidos para legendas")
    marker = marker_for_voice(voice)
    if not marker.exists():
        return None
    data = json.loads(marker.read_text(encoding="utf-8"))
    checksum = sha256(script.strip().encode("utf-8")).hexdigest()
    if data.get("script_sha256") != checksum:
        # Never pretend a stale audio/marker pair is synchronized.
        raise ValueError("Marcações de legenda não correspondem ao roteiro atual")
    raw = data.get("words")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Áudio sem limites reais de palavra para as legendas")
    total_frames = math.ceil(duration * fps)
    words = []
    last_start = -1
    for item in raw:
        try:
            text = str(item.get("text") or item.get("word") or "").strip()
            start = float(item["start"])
            end = float(item["end"])
        except (AttributeError, KeyError, ValueError, TypeError) as exc:
            raise ValueError("Marcações TTS inválidas") from exc
        if not text or not all(map(math.isfinite, (start, end))) or start < 0 or end <= start:
            raise ValueError("Palavra sem texto ou duração válida")
        start_frame = round(start * fps)
        end_frame = max(start_frame + 1, round(end * fps))
        if start_frame < last_start:
            raise ValueError("Palavras TTS fora de ordem")
        if start_frame >= total_frames:
            raise ValueError("Palavra fora da duração do áudio")
        words.append({
            "text": text, "startFrame": start_frame,
            "endFrame": min(end_frame, total_frames)
        })
        last_start = start_frame
    # Two to three words shown together; highlight only the spoken word.
    # This avoids the slow one-word-at-a-time stagger described by vidIQ.
    groups = []
    current = []
    for word in words:
        prior = current[-1] if current else None
        if prior and (
            len(current) >= 3
            or word["startFrame"] - current[0]["startFrame"] >= round(1.35 * fps)
            or word["startFrame"] - prior["endFrame"] > round(.24 * fps)
            or prior["text"].rstrip().endswith((".", "!", "?", "…"))
        ):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    captions = []
    for group in groups:
        start = group[0]["startFrame"]
        end = min(total_frames, max(w["endFrame"] for w in group))
        if end <= start:
            raise ValueError("Grupo de legenda sem quadros visíveis")
        captions.append({
            "startFrame": start, "endFrame": end,
            "text": " ".join(w["text"] for w in group),
            "words": group
        })
    return captions
