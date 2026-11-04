#!/usr/bin/env python3
"""Narração acolhedora Kids v1: pausas PCM reais, não pontuação ou voz artificial.

O objetivo é áudio pt-BR com intervalos intencionais de observação.
NÃO envia nada ao YouTube; NÃO modifica o catálogo Games ou canais Otaku.
As falas TTS são cacheadas individualmente por conteúdo/voz.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave

RATE = 48000
FPS = 30
SCHEMA = "mini-mundo/narracao-acolhedora/v1"


def signature(pacing: dict) -> str:
    return hashlib.sha256(
        json.dumps(pacing, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _segment_signature(text: str, voice: str, rate: str) -> str:
    return hashlib.sha256(json.dumps(
        [text, voice, rate], ensure_ascii=False
    ).encode("utf-8")).hexdigest()


def _decode_pcm(path: Path) -> bytes:
    try:
        process = subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
             "-f", "s16le", "-ac", "1", "-ar", str(RATE), "pipe:1"],
            capture_output=True, check=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("FFmpeg nao conseguiu decodificar a fala: " + str(path)) from exc
    if len(process.stdout) < RATE or len(process.stdout) % 2:
        raise ValueError("Trecho de narracao vazio ou PCM corrompido: " + str(path))
    return process.stdout


def _encode_mp3(pcm: bytes, wav_path: Path, mp3_path: Path) -> None:
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm)
    try:
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", str(wav_path), "-vn", "-ar", str(RATE), "-ac", "1",
             "-codec:a", "libmp3lame", "-q:a", "3", str(mp3_path)],
            check=True, capture_output=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("FFmpeg nao conseguiu exportar a narracao acolhedora") from exc
    if not mp3_path.is_file() or mp3_path.stat().st_size < 1000:
        raise ValueError("Exportacao MP3 Kids incompleta")


async def _fetch_segment(
    text: str, voice: str, rate: str, *,
    segment_dir: Path, index: int, synthesizer,
) -> tuple[Path, list[dict]]:
    key = _segment_signature(text, voice, rate)
    mp3 = segment_dir / f"{index:02d}.mp3"
    metadata = segment_dir / f"{index:02d}.json"
    if mp3.is_file() and metadata.is_file():
        try:
            saved = json.loads(metadata.read_text(encoding="utf-8"))
            if (saved["key"] == key and saved["sha256"] ==
                    hashlib.sha256(mp3.read_bytes()).hexdigest()
                    and saved.get("words")):
                return mp3, saved["words"]
        except (ValueError, KeyError, OSError):
            pass
    blob, words = await synthesizer(text, voice, rate)
    if len(blob) < 1000 or not words:
        raise RuntimeError(f"Falha na voz do trecho {index:02d}; nenhum silencio falso gerado")
    temp = mp3.with_suffix(".partial.mp3")
    temp.write_bytes(blob)
    # Only replace segment artifacts after verifying the received bytes.
    temp.replace(mp3)
    saved = {"key": key, "sha256": hashlib.sha256(blob).hexdigest(), "words": words}
    metadata.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    return mp3, words


async def assemble_paced_voice(
    episode: dict, voice: str, rate: str, output_dir: Path,
    *, synthesizer, probe=None, encode=None,
) -> dict:
    """Create a composed MP3 + real word/scene times, leaving old output intact.

    Chunk voice synthesis and PCM decoding can be retried from cache.
    This function writes only partial files until the complete MP3 is verified.
    """
    pacing = episode["kids_pacing"]
    if pacing.get("schema") != SCHEMA:
        raise ValueError("Formato de narracao acolhedora invalido")
    segments = pacing["segments"]
    output_dir.mkdir(parents=True, exist_ok=True)
    segment_dir = output_dir / "falas-acolhedoras"
    segment_dir.mkdir(parents=True, exist_ok=True)
    decode = _decode_pcm
    chunks = []
    for i, item in enumerate(segments, 1):
        path, boundaries = await _fetch_segment(
            item["text"], voice, rate, segment_dir=segment_dir,
            index=i, synthesizer=synthesizer,
        )
        pcm = decode(path)
        duration = len(pcm) / (RATE * 2)
        for word in boundaries:
            if (word["start"] < 0 or word["end"] <= word["start"]
                    or word["end"] > duration + .35):
                raise ValueError("Tempos Edge TTS incoerentes no trecho " + str(i))
        chunks.append((item, pcm, boundaries, duration))
    audio = bytearray()
    words = []
    timeline = []
    clock = 0.0
    for index, (item, chunk, boundaries, duration) in enumerate(chunks):
        start = clock
        audio.extend(chunk)
        for word in boundaries:
            words.append({
                "start": round(start + max(0, word["start"]), 4),
                "end": round(start + min(duration, word["end"]), 4),
                "text": word["text"], "segment": index,
            })
        speech_end = start + duration
        silence_samples = round(item["pause_after_s"] * RATE)
        audio.extend(b"\x00\x00" * silence_samples)
        clock = speech_end + silence_samples / RATE
        timeline.append({
            "segment": index,
            "scene": item["scene"],
            "cue": item["cue"],
            "headline": item["headline"],
            "text": item["text"],
            "start_s": round(start, 4),
            "speech_end_s": round(speech_end, 4),
            "end_s": round(clock, 4),
            "pause_after_s": item["pause_after_s"],
        })
    if clock >= 59.2:
        raise ValueError(
            f"Narracao Kids com pausas: {clock:.1f}s, ultrapassa limite interno "
            "de 59,2s. Edite o roteiro, nao acelere a voz sem revisar."
        )
    if clock < 25:
        raise ValueError("Narração Kids incompleta: duração insuficiente")
    if not words or not timeline or any(
        word["end"] <= word["start"] for word in words
    ):
        raise ValueError("Alinhamento da voz Kids invalido")

    wav_partial = output_dir / "narracao-acolhedora.partial.wav"
    mp3_partial = output_dir / "narracao-acolhedora.partial.mp3"
    if mp3_partial.exists():
        mp3_partial.unlink()
    try:
        (encode or _encode_mp3)(bytes(audio), wav_partial, mp3_partial)
        measured = (probe or _ffprobe_duration)(mp3_partial)
        if not 25 <= measured <= 59.2 or abs(measured - clock) > .35:
            raise ValueError(
                "MP3 final nao corresponde aos intervalos sintetizados: "
                f"PCM={clock:.2f}s, MP3={measured:.2f}s"
            )
        content = {
            "schema": "piloto-canais/voice-boundaries/v3",
            "pacing_schema": SCHEMA,
            "pacing_sha256": signature(pacing),
            "locale": "pt-BR", "voice": voice, "rate": rate,
            "script_sha256": hashlib.sha256(episode["script"].encode()).hexdigest(),
            "words": words,
            "segments": timeline,
            "duration_s": round(measured, 4),
            "target_seconds": pacing["target_seconds"],
            "pause_total_s": round(sum(x["pause_after_s"] for x in timeline), 3),
            "review_required": True,
            "review_stage": "youtube_studio_private_video",
            "mp3_sha256": hashlib.sha256(mp3_partial.read_bytes()).hexdigest(),
        }
        return {"audio_temp": mp3_partial, "marker": content, "seconds": measured,
                "target_reached": pacing["target_seconds"]["min"] <= measured <=
                                  pacing["target_seconds"]["max"]}
    finally:
        wav_partial.unlink(missing_ok=True)


def _ffprobe_duration(path: Path) -> float:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            text=True, capture_output=True, timeout=30, check=True,
        )
        return float(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise RuntimeError("FFprobe nao conseguiu verificar a narracao") from exc


def commit_voice(output_dir: Path, result: dict) -> None:
    """Backup previously created original mp3 before replacement."""
    audio = output_dir / "narracao.mp3"
    marker = output_dir / "marcacoes-voz.json"
    history = output_dir / "historico-voz"
    if audio.is_file():
        history.mkdir(parents=True, exist_ok=True)
        old_sha = hashlib.sha256(audio.read_bytes()).hexdigest()[:12]
        old_audio = history / ("narracao-" + old_sha + ".mp3")
        if not old_audio.exists():
            shutil.copy2(audio, old_audio)
        if marker.is_file():
            old_marker = history / ("marcacoes-" + old_sha + ".json")
            if not old_marker.exists():
                shutil.copy2(marker, old_marker)
    new_marker = output_dir / "marcacoes-voz.partial.json"
    new_marker.write_text(
        json.dumps(result["marker"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result["audio_temp"].replace(audio)
    new_marker.replace(marker)


def scene_props(episode: dict, marker: dict, duration_frames: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Exact timings from TTS PCM chunks; never estimate from word counts."""
    original = marker.get("segments", [])
    if len(original) != len(episode["kids_pacing"]["segments"]):
        raise ValueError("Quantidade de segmentos Kids nao confere")
    scenes = []
    beats = []
    previous = 0
    for index, item in enumerate(original):
        start = round(item["start_s"] * FPS)
        if start < previous:
            raise ValueError("Segmentos narrados fora de ordem")
        previous = start
        end = (round(original[index + 1]["start_s"] * FPS)
               if index + 1 < len(original) else duration_frames)
        if end <= start:
            raise ValueError("Falas sem espaço no vídeo")
        beats.append({
            "startFrame": start, "endFrame": end,
            "sceneIndex": int(item["scene"]) - 1,
            "cue": item["cue"], "headline": item["headline"],
            "pauseFrames": round(item["pause_after_s"] * FPS),
        })
    boundaries = [0]
    for scene_idx in range(1, 5):
        starts = [b["startFrame"] for b in beats if b["sceneIndex"] == scene_idx]
        if not starts:
            raise ValueError("Uma cena Kids ficou sem fala")
        boundaries.append(starts[0])
    boundaries.append(duration_frames)
    for idx, source in enumerate(episode["scenes"]):
        scenes.append({
            "id": source["id"], "startFrame": boundaries[idx],
            "endFrame": boundaries[idx + 1],
            "headline": source["on_screen_text"], "visual": source["visual"],
            "video": None,
        })
    captions = []
    for index, item in enumerate(original):
        # Never display a caption through an intentional pause or across segments.
        segment_words = [w for w in marker["words"] if w.get("segment") == index]
        for start in range(0, len(segment_words), 3):
            chunk = segment_words[start:start + 3]
            t1 = round(chunk[0]["start"] * FPS)
            t2 = round(chunk[-1]["end"] * FPS) + 1
            if t2 > t1:
                captions.append({
                    "startFrame": t1,
                    "endFrame": min(duration_frames, t2),
                    "text": " ".join(w["text"] for w in chunk),
                })
    if not captions or any(x["endFrame"] <= x["startFrame"] for x in scenes):
        raise ValueError("Cena/legendas Kids sem sincronia")
    return scenes, captions, beats
