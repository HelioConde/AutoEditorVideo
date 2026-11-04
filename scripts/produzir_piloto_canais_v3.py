#!/usr/bin/env python3
"""Producao local PT-BR de seis Shorts novos (3 Games, 3 Kids).

NUNCA publica. TTS so na acao voz. Kids: vetores animados originais Remotion.
Games: exige cinco capturas reais por episodio. Nao fabrica gameplay.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from piloto_canais_3x2_v3 import load_manifest, selected, verify_video, ROOT
from kids_musicas_fundo_v1 import MUSIC_POLICY, music_signature, prepare_kids_music, choose_track
from kids_narracao_acolhedora_v1 import (
    assemble_paced_voice, commit_voice, scene_props, signature as pacing_signature,
)

OUT = ROOT / "assets" / "gerados" / "piloto-canais-v3"
MOTION = ROOT / "motion-remotion"
VIDEO_PUBLIC = MOTION / "public" / "generated" / "piloto-canais-v3"
BR_VOICES = {"games": ("pt-BR-AntonioNeural", "+2%"),
             "kids": ("pt-BR-FranciscaNeural", "-15%")}
FPS = 30


def hash_script(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def folder_of(channel: dict, episode: dict) -> Path:
    return OUT / channel["id"] / episode["id"]


def read_voice(channel: dict, episode: dict) -> tuple[Path, dict]:
    folder = folder_of(channel, episode)
    audio = folder / "narracao.mp3"
    marker = folder / "marcacoes-voz.json"
    if not audio.is_file() or not marker.is_file():
        raise FileNotFoundError("Narração PT-BR não encontrada. Execute -Acao voz.")
    data = json.loads(marker.read_text(encoding="utf-8-sig"))
    voice, rate = BR_VOICES[channel["id"]]
    if data.get("script_sha256") != hash_script(episode["script"]):
        raise ValueError("Roteiro mudou: cache da narração antiga bloqueado")
    if data.get("voice") != voice or data.get("rate") != rate:
        raise ValueError("Idioma, voz ou velocidade não correspondem ao canal")
    pacing = episode.get("kids_pacing")
    if pacing is not None:
        if (data.get("pacing_sha256") != pacing_signature(pacing)
                or data.get("pacing_schema") != pacing.get("schema")):
            raise ValueError("Ritmo e pausas Kids mudaram: renove a voz com -Refazer")
        if data.get("mp3_sha256") != hashlib.sha256(audio.read_bytes()).hexdigest():
            raise ValueError("Narracao Kids alterada sem atualizar os tempos/QA")
    elif data.get("pacing_sha256"):
        raise ValueError("Cache Kids pertence a roteiro ritmado diferente")
    words = data.get("words", [])
    if not isinstance(words, list) or not words:
        raise ValueError("Voz sem tempos reais das palavras")
    last = -1.0
    for w in words:
        if not isinstance(w.get("start"), (int, float)) or w["start"] < last:
            raise ValueError("WordBoundary fora da ordem")
        if not isinstance(w.get("end"), (int, float)) or w["end"] <= w["start"]:
            raise ValueError("WordBoundary inválido")
        last = w["start"]
    if audio.stat().st_size < 1000:
        raise ValueError("MP3 de narração muito pequeno para ser válido")
    return audio, data


async def _synthesize(script: str, voice: str, rate: str, *,
                      minimum_words: int = 10) -> tuple[bytes, list[dict]]:
    import edge_tts
    actor = edge_tts.Communicate(script, voice, rate=rate, boundary="WordBoundary")
    audio = bytearray()
    words: list[dict] = []
    async for packet in actor.stream():
        if packet.get("type") == "audio":
            audio.extend(packet.get("data", b""))
        elif packet.get("type") == "WordBoundary":
            start = packet["offset"] / 10_000_000
            duration = packet["duration"] / 10_000_000
            if duration > 0:
                words.append({"start": round(start, 4), "end": round(start + duration, 4),
                              "text": packet.get("text", "")})
    if len(audio) < 1000 or len(words) < minimum_words:
        raise RuntimeError("Edge TTS não retornou narração e alinhamento válidos")
    return bytes(audio), words


def create_voice(channel: dict, episode: dict, *, replace: bool = False) -> dict:
    folder = folder_of(channel, episode)
    marker = folder / "marcacoes-voz.json"
    voice, rate = BR_VOICES[channel["id"]]
    if (folder / "narracao.mp3").is_file() and marker.is_file() and not replace:
        audio, _ = read_voice(channel, episode)
        return {"status": "cache_ptbr_aprovado_tecnicamente", "audio": str(audio),
                "voice": voice, "review_required": True}
    if (folder / "narracao.mp3").exists() and not replace:
        raise ValueError("Cache de voz anterior diverge; especifique --refazer para renovar")
    folder.mkdir(parents=True, exist_ok=True)
    if channel["id"] == "kids" and episode.get("kids_pacing"):
        async def short_speech(text: str, selected_voice: str, selected_rate: str):
            return await _synthesize(text, selected_voice, selected_rate, minimum_words=1)
        completed = asyncio.run(assemble_paced_voice(
            episode, voice, rate, folder, synthesizer=short_speech,
        ))
        commit_voice(folder, completed)
        audio, data = read_voice(channel, episode)
        return {
            "status": "voz_kids_acolhedora_com_pausas", "voice": voice,
            "audio": str(audio), "words": len(data["words"]),
            "segments": len(data["segments"]),
            "pause_total_s": data["pause_total_s"],
            "pause_adaptation": data.get("pause_adaptation"),
            "duration_s": completed["seconds"],
            "target_reached": completed["target_reached"],
            "review_required": True, "published": False,
        }
    blob, words = asyncio.run(_synthesize(episode["script"], voice, rate))
    # Write new audio atomically without destroying approved data on failure.
    tmp = folder / "narracao.partial.mp3"
    tmp.write_bytes(blob)
    tmp.replace(folder / "narracao.mp3")
    content = {
        "schema": "piloto-canais/voice-boundaries/v3",
        "locale": "pt-BR",
        "voice": voice,
        "rate": rate,
        "script_sha256": hash_script(episode["script"]),
        "words": words,
        "review_required": True,
    }
    marker.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    audio, _ = read_voice(channel, episode)
    return {"status": "voz_gerada_requer_revisao", "voice": voice, "audio": str(audio),
            "words": len(words), "review_required": True}


def audio_seconds(path: Path) -> float:
    try:
        cmd = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30, check=True,
        )
        value = float(cmd.stdout.strip())
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Duração inválida")
        return value
    except (OSError, subprocess.SubprocessError, ValueError) as err:
        raise RuntimeError("FFprobe não conseguiu verificar narração: " + str(path)) from err


def _scenes_with_audio_timings(episode: dict, words: list[dict],
                               duration_frames: int) -> list[dict]:
    """Frame splits from true word timings; keep each storyboard beat contiguous."""
    beats = episode["narration_beats"]
    totals = [len(b.split()) for b in beats]
    cumulative = 0
    boundaries = [0]
    ratio = len(words) / sum(totals)
    for length in totals[:-1]:
        cumulative += length
        idx = max(0, min(len(words) - 1, round(cumulative * ratio)))
        # Start next scene slightly before the next spoken beat.
        at = round(words[idx]["start"] * FPS)
        boundaries.append(max(boundaries[-1] + 1, min(at, duration_frames - (5-len(boundaries)))))
    boundaries.append(duration_frames)
    if len(boundaries) != 6 or any(b <= a for a, b in zip(boundaries, boundaries[1:])):
        raise ValueError("Cenas com duração inválida ao alinhar narração")
    return [
        {"id":scene["id"], "startFrame":boundaries[i],
         "endFrame":boundaries[i+1], "headline":scene["on_screen_text"],
         "visual":scene["visual"], "video":None}
        for i, scene in enumerate(episode["scenes"])
    ]


def _caption_groups(words: list[dict], duration_frames: int) -> list[dict]:
    captions: list[dict] = []
    for start in range(0, len(words), 3):
        segment = words[start:start+3]
        if not segment:
            continue
        t1 = max(0, round(segment[0]["start"] * FPS))
        t2 = min(duration_frames, round(segment[-1]["end"] * FPS) + 2)
        if t2 <= t1:
            continue
        captions.append({
            "startFrame": t1, "endFrame": t2,
            "text": " ".join(str(w["text"]) for w in segment).strip()
        })
    if not captions:
        raise ValueError("Sem legendas baseadas na narração")
    return captions


def ffprobe_capture(clip: Path, required_s: float) -> None:
    if not clip.is_file() or clip.stat().st_size < 100_000:
        raise FileNotFoundError("Captura de gameplay real ausente: " + str(clip))
    duration = audio_seconds(clip)
    if duration + .08 < required_s:
        raise ValueError(
            f"Gameplay insuficiente para cena: {clip.name}, "
            f"{duration:.2f}s disponiveis e {required_s:.2f}s necessarios."
        )
    check = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(clip)],
        capture_output=True, text=True, timeout=30, check=True,
    )
    streams = json.loads(check.stdout).get("streams", [])
    if not streams or not streams[0].get("width") or not streams[0].get("height"):
        raise ValueError("Captura sem quadro de vídeo válido")


def prepare_props(channel: dict, episode: dict, *, root: Path = ROOT) -> tuple[dict, Path, Path]:
    voice, marker = read_voice(channel, episode)
    seconds = audio_seconds(voice)
    if seconds > 59.2:
        raise ValueError("Narração ultrapassa limite interno de 60s; revisar roteiro sem acelerar")
    total_frames = math.ceil((seconds + 0.45) * FPS)
    if channel["id"] == "kids" and episode.get("kids_pacing"):
        scenes, captions, kids_beats = scene_props(episode, marker, total_frames)
    else:
        scenes = _scenes_with_audio_timings(episode, marker["words"], total_frames)
        captions = _caption_groups(marker["words"], total_frames)
        kids_beats = []
    target = root / "motion-remotion" / "public" / "generated" / "piloto-canais-v3" / channel["id"] / episode["id"]
    target.mkdir(parents=True, exist_ok=True)
    sound = target / "narracao.mp3"
    shutil.copy2(voice, sound)
    if channel["id"] == "games":
        for idx, scene in enumerate(scenes):
            source = root / episode["scenes"][idx]["required_asset"]
            ffprobe_capture(source, (scene["endFrame"] - scene["startFrame"]) / FPS)
            dest = target / f"cena-{idx+1:02d}.mp4"
            shutil.copy2(source, dest)
            scene["video"] = (
                f"generated/piloto-canais-v3/{channel['id']}/{episode['id']}/{dest.name}"
            )
    music = prepare_kids_music(root, episode["id"]) if channel["id"] == "kids" else None
    props = {
        "episodeId": episode["id"], "channel": channel["id"],
        "brand": channel["name"],
        "durationFrames": total_frames,
        "scenes": scenes,
        "captions": captions,
        "kidsBeats": kids_beats,
        "music": music,
        "audio": f"generated/piloto-canais-v3/{channel['id']}/{episode['id']}/narracao.mp3",
    }
    props_file = root / "motion-remotion" / f"props-{episode['id']}-v3.json"
    props_file.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    return props, props_file, target


def render(channel: dict, episode: dict, *, replace: bool = False,
           root: Path = ROOT) -> dict:
    folder = root / "assets" / "gerados" / "piloto-canais-v3" / channel["id"] / episode["id"]
    final = folder / "final.mp4"
    qa_file = folder / "qa-local.json"
    if final.exists() and not replace:
        if not qa_file.is_file():
            raise ValueError("MP4 existente sem QA assinado; nenhum arquivo foi substituido")
        qa = json.loads(qa_file.read_text(encoding="utf-8-sig"))
        digest = hashlib.sha256(final.read_bytes()).hexdigest()
        if (qa.get("video_sha256") == digest and
                qa.get("script_sha256") == hash_script(episode["script"]) and
                qa.get("pacing_sha256") == (
                    pacing_signature(episode["kids_pacing"]) if episode.get("kids_pacing") else None
                ) and
                qa.get("channel") == channel["id"] and
                (channel["id"] != "kids" or
                 (qa.get("music_policy") == MUSIC_POLICY and
                  qa.get("music_sha256") == music_signature(root, episode["id"])))):
            return {"status": "render_existente_sem_publicacao", "file": str(final)}
        raise ValueError("MP4 existente diverge do roteiro ou assinatura; usar --refazer")
    props, propfile, _ = prepare_props(channel, episode, root=root)
    motion = root / "motion-remotion"
    if not (motion / "node_modules").is_dir():
        raise RuntimeError("Remotion ausente. Execute npm.cmd install em motion-remotion")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if npm is None:
        raise RuntimeError("Node/npm nao encontrado")
    folder.mkdir(parents=True, exist_ok=True)
    temp_output = folder / "render-temp.mp4"
    if temp_output.is_file():
        temp_output.unlink()
    cmd = [npm, "run", "render:pilot", "--", str(temp_output.resolve()),
           "--props", str(propfile.resolve()), "--concurrency", "2"]
    subprocess.run(cmd, cwd=motion, check=True, timeout=2400)
    status = verify_video(temp_output)
    if status.get("technical_status") != "passed":
        raise ValueError("Render PT-BR nao passou no FFprobe: " + json.dumps(status))
    sha = hashlib.sha256(temp_output.read_bytes()).hexdigest()
    # Preserve an earlier video version rather than silently overwriting it.
    if final.is_file():
        history = folder / "historico-renders"
        history.mkdir(parents=True, exist_ok=True)
        old_sha = hashlib.sha256(final.read_bytes()).hexdigest()[:12]
        old_video = history / ("final-" + old_sha + ".mp4")
        if not old_video.is_file():
            shutil.copy2(final, old_video)
        if qa_file.is_file():
            old_qa = history / ("qa-" + old_sha + ".json")
            if not old_qa.is_file():
                shutil.copy2(qa_file, old_qa)
    temp_output.replace(final)
    qa = {
        "schema": "piloto-canais/render-qa/v3",
        "channel": channel["id"], "locale": "pt-BR",
        "episode_id": episode["id"], "video_sha256": sha,
        "script_sha256": hash_script(episode["script"]),
        "pacing_sha256": (pacing_signature(episode["kids_pacing"])
                          if episode.get("kids_pacing") else None),
        "motion": ("original_animated_vectors" if channel["id"] == "kids"
                   else "original_gameplay_capture_required"),
        "render_engine": "AutoEditorVideo/local/remotion",
        "music_policy": MUSIC_POLICY if channel["id"] == "kids" else None,
        "music_sha256": (music_signature(root, episode["id"])
                         if channel["id"] == "kids" else None),
        "music_source": (choose_track(episode["id"])[1]
                         if channel["id"] == "kids" else None),
        "music_rights_review": ("pending_before_publication" if channel["id"] == "kids" else None),
        "technical": status,
        "pause_total_s": sum(b["pause_after_s"] for b in episode.get("kids_pacing", {}).get("segments", [])),
        "human_visual_audio_rights_review": "pending",
        "youtube_channel_id_verified": False,
        "upload_approved": False,
        "published": False,
    }
    qa["visual_review_stage"] = "post_upload_youtube_studio"
    qa_file.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    try:
        from organizar_videos_por_canal import refresh_library_after_render
        archive = refresh_library_after_render(root)
        if archive["status"] == "updated":
            print("[BIBLIOTECA] Shorts novos sincronizados: " + str(archive["videos"]))
    except (OSError, ValueError) as exc:
        print("[BIBLIOTECA AVISO] MP4 preservado: " + str(exc))
    return {"status": "renderizado_aguardando_revisao", "file": str(final),
            "seconds": status["duration"], "video_sha256": sha, "published": False}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Criar voz PT-BR e render local Kids/Games")
    ap.add_argument("--acao", choices=("voz", "renderizar", "inspecionar"), default="inspecionar")
    ap.add_argument("--canal", choices=("games", "kids"), required=True)
    ap.add_argument("--id", required=True)
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--manifesto", type=Path)
    args = ap.parse_args(argv)
    data = load_manifest(args.manifesto) if args.manifesto else load_manifest()
    [(channel, episode)] = selected(data, channel_name=args.canal, episode_id=args.id)
    if args.acao == "inspecionar":
        result = {"voice": BR_VOICES[channel["id"]], "locale": "pt-BR",
                  "requires_gameplay": channel["id"] == "games", "published": False,
                  "voice_present": (folder_of(channel, episode) / "narracao.mp3").is_file()}
    elif args.acao == "voz":
        result = create_voice(channel, episode, replace=args.refazer)
    else:
        result = render(channel, episode, replace=args.refazer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print("[BLOQUEADO PILOTO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
