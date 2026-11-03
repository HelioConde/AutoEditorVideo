#!/usr/bin/env python3
"""Arquivo Otaku: regra editorial obrigatoria de duracao dos Shorts.

MAX_SECONDS is a hard production/publishing limit for our project, not an
assertion about the limits of any video platform.
"""
from __future__ import annotations

import math
from pathlib import Path
import subprocess

MAX_SECONDS = 60.0
TARGET_MIN_SECONDS = 55.0
TARGET_MAX_SECONDS = 59.0
RENDER_TAIL_SECONDS = 0.4


def validate_seconds(seconds: float, *, stage: str = "Short") -> float:
    """Raise before consuming more resources or uploading an overlong video."""
    duration = float(seconds)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"[60S] Duracao invalida em {stage}: {seconds!r}")
    if duration > MAX_SECONDS:
        raise ValueError(
            f"[60S BLOQUEADO] {stage}: {duration:.3f}s excede o limite "
            f"obrigatorio de {MAX_SECONDS:.0f}s. Resuma e regrave o roteiro, "
            "preservando o gancho e o CTA. Nao acelere a voz nem corte o final."
        )
    return duration


def validate_planned_audio(audio_seconds: float, *, stage: str = "Narração") -> float:
    """The audio and the final .4s render tail must fit within 60 seconds."""
    return validate_seconds(
        float(audio_seconds) + RENDER_TAIL_SECONDS, stage=stage
    )


def probe_video_seconds(path: Path) -> float:
    """Read actual MP4 duration via ffprobe (not estimated narration length)."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"[60S] MP4 nao encontrado: {source}")
    try:
        completed = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(source)],
            check=True, capture_output=True, text=True, timeout=45,
        )
    except (FileNotFoundError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"[60S] Nao foi possivel verificar a duracao via ffprobe: {source}") from exc
    try:
        return float(completed.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"[60S] FFprobe nao retornou uma duracao valida: {source}") from exc


def validate_video(path: Path, *, stage: str = "Upload") -> float:
    """Fail closed before upload and immediately after render, in all languages."""
    return validate_seconds(probe_video_seconds(path), stage=stage)
