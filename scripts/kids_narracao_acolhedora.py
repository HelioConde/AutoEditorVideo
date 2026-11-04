#!/usr/bin/env python3
"""PT-BR Kids: fala em blocos, pausas reais e legendas sem antecipar respostas.

O texto nao inclui marcações "(pausa)" na voz. O audio e montado em PCM
com intervalos de silencio medidos em amostras. Nenhum video e publicado.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import subprocess
from typing import Callable

SAMPLE_RATE = 48000
FRAME_BYTES = 2  # mono signed int16, 48 kHz
QUESTION_BEATS = {"red-question", "yellow-question", "blue-question"}
STYLE = "kids-acolhedora-v1"


def timeline_fingerprint(episode: dict) -> str:
    payload = {"script": episode.get("script"), "style": episode.get("narration_style"),
               "timeline": episode.get("narration_timeline")}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def validate_timeline(episode: dict) -> list[dict]:
    if episode.get("id") != "kids-001-estrela-azul":
        raise ValueError("Primeiro teste Narracao Acolhedora exclusivo da estrelinha azul")
    if episode.get("narration_style") != STYLE:
        raise ValueError("Estilo Kids Acolhedora nao identificado")
    beats = episode.get("narration_timeline")
    if not isinstance(beats, list) or len(beats) < 8:
        raise ValueError("Narracao Acolhedora exige blocos curtos com pausas")
    if len({b.get("id") for b in beats}) != len(beats):
        raise ValueError("IDs dos blocos narrados nao podem repetir")
    scenes = episode.get("scenes", [])
    ordered_stages = [str(s["id"]) for s in scenes]
    stages = [b.get("stage") for b in beats]
    if any(stage not in ordered_stages for stage in stages):
        raise ValueError("Bloco de narracao sem cena correspondente")
    if [x for i, x in enumerate(stages) if i == 0 or x != stages[i-1]] != ordered_stages:
        raise ValueError("Blocos de narracao precisam seguir as 5 cenas na ordem")
    for stage, scene in zip(ordered_stages, scenes):
        group = [b["text"] for b in beats if b["stage"] == stage]
        if " ".join(group) != scene["narration"]:
            raise ValueError("Roteiro, linha de tempo e cena divergentes: " + stage)
    if " ".join(b["text"] for b in beats) != episode.get("script"):
        raise ValueError("Audio e texto de roteiro divergentes")
    total_pause = 0.0
    for i, beat in enumerate(beats):
        if not isinstance(beat.get("text"), str) or not beat["text"].strip():
            raise ValueError("Bloco sem texto narrado")
        if not isinstance(beat.get("headline"), str) or not beat["headline"]:
            raise ValueError("Bloco Kids sem titulo visual")
        pause = beat.get("pause_after_s")
        if not isinstance(pause, (int, float)) or not math.isfinite(pause) or not 0 <= pause <= 2.5:
            raise ValueError("Pausa fora do intervalo de 0 a 2.5 segundos")
        if beat["id"] in QUESTION_BEATS and pause < 1.5:
            raise ValueError("Pergunta Kids sem tempo para a crianca pensar: " + beat["id"])
        if i == len(beats)-1 and pause != 0:
            raise ValueError("Narracao deve terminar sem silencio artificial excessivo")
        total_pause += pause
    if not 6 <= total_pause <= 17:
        raise ValueError("Pausas totais Kids fora do ritmo do experimento")
    if beats[0]["text"] != episode.get("hook"):
        raise ValueError("A primeira pergunta deve ser o gancho")
    return beats


def _decode_mp3_pcm(audio: bytes) -> bytes:
    if not audio:
        raise ValueError("TTS sem dados")
    args = ["ffmpeg", "-hide_banner", "-v", "error",
            "-i", "pipe:0", "-ar", str(SAMPLE_RATE), "-ac", "1",
            "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"]
    proc = subprocess.run(args, input=audio, capture_output=True, check=True, timeout=35)
    if len(proc.stdout) < SAMPLE_RATE * FRAME_BYTES // 6:
        raise ValueError("Trecho TTS vazio ou curto demais")
    if len(proc.stdout) % FRAME_BYTES:
        raise ValueError("Trecho PCM desalinhado")
    return proc.stdout


def _encode_pcm_mp3(pcm: bytes) -> bytes:
    args = ["ffmpeg", "-hide_banner", "-v", "error",
            "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1",
            "-i", "pipe:0", "-c:a", "libmp3lame",
            "-b:a", "160k", "-f", "mp3", "pipe:1"]
    proc = subprocess.run(args, input=pcm, capture_output=True, check=True, timeout=55)
    if len(proc.stdout) < 1000:
        raise ValueError("MP3 final da narracao invalido")
    return proc.stdout


async def compose_timeline(
    episode: dict,
    voice: str,
    rate: str,
    synthesizer: Callable,
    *,
    decode: Callable[[bytes], bytes] = _decode_mp3_pcm,
    encode: Callable[[bytes], bytes] = _encode_pcm_mp3,
) -> tuple[bytes, dict]:
    """Synthesize each beat independently, then assemble verified real silences."""
    beats = validate_timeline(episode)
    pcm_parts: list[bytes] = []
    words: list[dict] = []
    segments: list[dict] = []
    cursor = 0  # integer PCM frames, so no cumulative float timing drift
    for beat in beats:
        blob, boundaries = await synthesizer(beat["text"], voice, rate)
        pcm = decode(blob)
        duration_frames = len(pcm) // FRAME_BYTES
        if duration_frames <= 0 or not boundaries:
            raise ValueError("Trecho sem voz ou WordBoundary: " + beat["id"])
        start = cursor / SAMPLE_RATE
        speak_end = (cursor + duration_frames) / SAMPLE_RATE
        seg_words: list[dict] = []
        for boundary in boundaries:
            t0, t1 = float(boundary["start"]), float(boundary["end"])
            if t1 <= t0 or t0 < 0 or t1 > duration_frames/SAMPLE_RATE + .25:
                raise ValueError("WordBoundary fora do trecho: " + beat["id"])
            seg_words.append({
                "start": round(start+t0, 4),
                "end": round(min(start+t1, speak_end), 4),
                "text": str(boundary["text"]),
                "beat_id": beat["id"],
            })
        # Boundary entries arrive sorted; ensure no word moves backwards.
        if any(a["start"] > b["start"] for a, b in zip(seg_words, seg_words[1:])):
            raise ValueError("Marcas de palavras fora de ordem em: " + beat["id"])
        pause_frames = round(beat["pause_after_s"]*SAMPLE_RATE)
        next_start = (cursor + duration_frames + pause_frames)/SAMPLE_RATE
        segments.append({
            "id": beat["id"],
            "stage": beat["stage"],
            "headline": beat["headline"],
            "text": beat["text"],
            "start": round(start, 4),
            "speech_end": round(speak_end, 4),
            "end": round(next_start, 4),
            "pause_after_s": beat["pause_after_s"],
        })
        words.extend(seg_words)
        pcm_parts.append(pcm)
        if pause_frames:
            pcm_parts.append(bytes(pause_frames*FRAME_BYTES))
        cursor += duration_frames + pause_frames
    seconds = cursor/SAMPLE_RATE
    if seconds > 59.15:
        raise ValueError(
            f"Narracao Kids com pausas ficou com {seconds:.2f}s. Limite 59.15s "
            "para deixar margem no Short. Edite/reduza as falas em vez de "
            "acelerar a voz ou remover o tempo das respostas."
        )
    if seconds < 30:
        raise ValueError("Narracao Kids artificialmente curta; verificar falas TTS")
    if any(w["end"] <= w["start"] for w in words):
        raise ValueError("WordBoundary sem duracao apos sincronizacao")
    audio = encode(b"".join(pcm_parts))
    metadata = {
        "schema": "piloto-canais/kids-acolhedora/v1",
        "style": STYLE,
        "timeline_sha256": timeline_fingerprint(episode),
        "duration_pcm_s": round(seconds, 4),
        "total_pause_s": round(sum(b["pause_after_s"] for b in beats), 3),
        "words": words,
        "segments": segments,
        "review_required": True,
        "review_guidance": "Assistir MP4 final, volume e ritmo no YouTube Studio privado",
    }
    return audio, metadata
