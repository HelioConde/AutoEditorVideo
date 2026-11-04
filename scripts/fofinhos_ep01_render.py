#!/usr/bin/env python3
"""Fofinhos EP01 Part 1: approved 15-scene long-form animation preview.

This is a NEW production lane. Never touches the old 9-beat voice, images,
renders, or the public YouTube channel. All TTS runs on creator's Windows PC.
No image-generation API calls; independent layers reuse existing approved assets.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

import fofinhos_ep01_canon as canon
import kids_emanuelly_cenarios_camadas_v1 as scenery
import kids_emanuelly_series_assets_v2 as assets
import gerar_poses_emanuelly_gpt_image_2 as poses
import serie_kids_emanuelly_v1 as legacy
from kids_musicas_fundo_v1 import prepare_kids_music, music_signature
from kids_narracao_acolhedora_v1 import (
    _decode_pcm, _encode_mp3, _fetch_segment, _ffprobe_duration, RATE as PCM_RATE,
)
from produzir_piloto_canais_v3 import _synthesize

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "fofinhos/ep01-approved-long-preview/v1"
FPS = 30
VOICE = legacy.VOICE
RATE = legacy.RATE
MAX_SECONDS = 600
OUTPUT_REL = Path("assets/gerados/fofinhos/ep01-parte01-canonico")
PUBLIC_REL = Path("motion-remotion/public/generated/fofinhos-ep01-parte01")
PLACEMENT_FILE = "canteiro-flores.json"
VIDEO_NAME = "previa-canonica.mp4"
FLOWER_VIEWS = ("jardim-03", "jardim-04")
AMBIENT_VERSION = "fofinhos/ep01-ambiente-vivo/v1"
# Ordem: nuvens, borboletas, pétalas, pólen, brilhos do ovo, poeira luminosa.
# Nunca usar borboletas ou chuva de pétalas durante a revelação do ovo.
AMBIENT_SCENES = (
    (2, 2, 3, 8, 0, 0),  # 01: apresentação; jardim alegre
    (2, 2, 2, 6, 0, 0),  # 02: Emanuelly brinca entre as flores
    (1, 1, 1, 3, 0, 0),  # 03: primeira curiosidade; ambiente desacelera
    (0, 0, 0, 0, 3, 0),  # 04: primeiro close do ovo azul
    (0, 0, 0, 0, 1, 0),  # 05: decisão de investigar
    (0, 0, 0, 0, 1, 0),  # 06: aproximação lenta
    (0, 0, 0, 0, 2, 0),  # 07: ovo entre as flores (protagonista visual)
    (0, 0, 0, 0, 1, 0),  # 08: ajoelhar e estender a mão
    (0, 0, 0, 0, 5, 0),  # 09: ovo brilha mais
    (0, 0, 1, 2, 0, 0),  # 10: sai do jardim segurando ovo
    (0, 0, 0, 0, 0, 5),  # 11: luz morna no quarto
    (0, 0, 0, 0, 0, 3),  # 12: promessa
    (0, 0, 0, 0, 1, 2),  # 13: noite silenciosa
    (0, 0, 0, 0, 4, 1),  # 14: ovo balança; toque de magia
    (0, 0, 0, 0, 3, 0),  # 15: mistério, sem distração
)


def ambient_profiles(root: Path = ROOT) -> list[dict]:
    """Ambiência 2D gratuita, discreta e vinculada às 15 cenas canônicas."""
    script_scenes = scenes(root)
    if len(script_scenes) != len(AMBIENT_SCENES):
        raise ValueError("Tabela de ambiente não corresponde às cenas aprovadas")
    rows = []
    for scene, values in zip(script_scenes, AMBIENT_SCENES):
        index = scene["index"]
        clouds, butterflies, petals, pollen, egg_sparkles, motes = values
        garden = scene["background"].startswith("jardim")
        if (index in range(4, 10) and (clouds or butterflies or petals or pollen)):
            raise ValueError("Ambiente está distraindo da descoberta do ovo")
        if ((not garden or scene["night"]) and
                (clouds or butterflies or petals or pollen)):
            raise ValueError("Borboletas, nuvens e pétalas não pertencem ao quarto")
        if (scene["egg_location"] == "ausente" and egg_sparkles):
            raise ValueError("Brilhos do ovo antes da descoberta")
        if max(values) > 8 or min(values) < 0:
            raise ValueError("Densidade de partículas fora do limite infantil")
        rows.append(dict(
            index=index, clouds=clouds, butterflies=butterflies,
            petals=petals, pollen=pollen, eggSparkles=egg_sparkles,
            motes=motes,
        ))
    return rows


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def output(root: Path = ROOT) -> Path:
    return root / OUTPUT_REL


def public(root: Path = ROOT) -> Path:
    return root / PUBLIC_REL


def placements_file(root: Path = ROOT) -> Path:
    return output(root) / PLACEMENT_FILE


def voice_paths(root: Path = ROOT) -> tuple[Path, Path]:
    return output(root) / "narracao-canonica.mp3", output(root) / "narracao-canonica.json"


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def scenes(root: Path = ROOT) -> list[dict]:
    return canon.read_canon(root)["scenes"]


def voice_signature(root: Path = ROOT) -> str:
    data = canon.read_canon(root)
    content = {
        "schema": SCHEMA, "scenes": [s["spoken_text"] for s in data["scenes"]],
        "pauses": data["pauses"], "voice": VOICE, "rate": RATE,
        "default_rest_s": 0.35,
    }
    return digest(json.dumps(content, sort_keys=True, ensure_ascii=False).encode())


def pauses(root: Path = ROOT) -> list[float]:
    data = canon.read_canon(root)
    chosen = {p["after_scene"]: p["seconds"] for p in data["pauses"]}
    return [float(chosen.get(i, .35)) for i in range(1, 16)]


def valid_voice(root: Path = ROOT) -> bool:
    audio, marker = voice_paths(root)
    if not audio.is_file() or not marker.is_file():
        return False
    try:
        meta = json.loads(marker.read_text(encoding="utf-8"))
        return (
            meta.get("schema") == SCHEMA
            and meta.get("voice_signature") == voice_signature(root)
            and meta.get("mp3_sha256") == digest(audio.read_bytes())
            and len(meta.get("segments", [])) == 15
            and len(meta.get("words", [])) > 15
            and 0 < float(meta["duration_s"]) <= MAX_SECONDS
        )
    except (ValueError, KeyError, OSError, TypeError):
        return False


def make_voice(root: Path = ROOT, *, refazer: bool = False,
               synthesizer=None, decode=None, encoder=None,
               probe=None) -> dict:
    """Synthesize precisely approved wording, preserve intentional gaps."""
    audio, marker = voice_paths(root)
    if valid_voice(root) and not refazer:
        data = json.loads(marker.read_text(encoding="utf-8"))
        return {"status": "cache", "duration_s": data["duration_s"],
                "audio": str(audio), "uploads": 0}
    if (audio.exists() or marker.exists()) and not refazer:
        raise ValueError("Narracao canonica diferente/incompleta ja existe. "
                         "Use -Refazer para arquivar o resultado anterior.")
    folder = output(root)
    folder.mkdir(parents=True, exist_ok=True)
    segment_dir = folder / "falas-canonicas"
    segment_dir.mkdir(exist_ok=True)
    if synthesizer is None:
        async def synthesizer(text, voice, rate):
            return await _synthesize(text, voice, rate, minimum_words=1)
    decode = decode or _decode_pcm
    encoder = encoder or _encode_mp3
    probe = probe or _ffprobe_duration

    async def collect():
        chunks = []
        for index, scene in enumerate(scenes(root), 1):
            text = scene["spoken_text"].replace("\n", " ")
            path, boundaries = await _fetch_segment(
                text, VOICE, RATE, segment_dir=segment_dir,
                index=index, synthesizer=synthesizer)
            raw = decode(path)
            duration = len(raw) / (PCM_RATE * 2)
            if duration < .3 or any(
                w["start"] < 0 or w["end"] <= w["start"]
                or w["end"] > duration + .35 for w in boundaries
            ):
                raise ValueError("Trecho da voz sem alinhamento confiavel: " + str(index))
            chunks.append((raw, boundaries, duration))
        return chunks

    parts = asyncio.run(collect())
    audio_pcm = bytearray()
    timeline, words = [], []
    moment = 0.0
    for i, ((pcm, boundaries, duration), rest) in enumerate(zip(parts, pauses(root))):
        start = moment
        audio_pcm.extend(pcm)
        for word in boundaries:
            words.append({
                "segment": i, "text": word["text"],
                "start": round(start + word["start"], 4),
                "end": round(start + min(duration, word["end"]), 4),
            })
        spoken_end = start + duration
        pad = round(rest * PCM_RATE)
        audio_pcm.extend(b"\0\0" * pad)
        moment = spoken_end + pad / PCM_RATE
        timeline.append({
            "index": i + 1, "start_s": round(start, 4),
            "speech_end_s": round(spoken_end, 4),
            "end_s": round(moment, 4), "pause_after_s": rest,
        })
    if moment <= 10 or moment > MAX_SECONDS:
        raise ValueError(f"Duracao da narracao fora do limite de previa: {moment:.2f}s")
    partial_mp3 = folder / "narracao-canonica.partial.mp3"
    partial_wav = folder / "narracao-canonica.partial.wav"
    try:
        encoder(bytes(audio_pcm), partial_wav, partial_mp3)
        measured = float(probe(partial_mp3))
        if abs(measured - moment) > .5 or measured > MAX_SECONDS:
            raise ValueError("MP3 final e falas nao correspondem em duracao")
        metadata = {
            "schema": SCHEMA, "voice_signature": voice_signature(root),
            "script_sha256": digest(canon.approved_text(root).encode()),
            "voice": VOICE, "rate": RATE,
            "duration_s": round(measured, 4),
            "segments": timeline, "words": words,
            "mp3_sha256": digest(partial_mp3.read_bytes()),
            "recommended_format": "video_longo" if measured > 59.2 else "short",
            "ready_for_shorts": measured <= 59.2,
            "no_speech_cuts": True,
            "music_rights_review": "pending_before_publication",
            "uploads": 0,
        }
        if audio.exists():
            history = folder / "historico-voz"
            history.mkdir(exist_ok=True)
            prior = history / ("narracao-" + digest(audio.read_bytes())[:12] + ".mp3")
            if not prior.exists():
                shutil.copy2(audio, prior)
            if marker.exists():
                before = history / ("marcacoes-" + digest(audio.read_bytes())[:12] + ".json")
                if not before.exists():
                    shutil.copy2(marker, before)
        partial_mp3.replace(audio)
        save_json(marker, metadata)
        return {"status": "gerada_canonica", "duration_s": measured,
                "audio": str(audio), "format": metadata["recommended_format"],
                "uploads": 0}
    finally:
        partial_wav.unlink(missing_ok=True)


def read_placement(root: Path = ROOT, *, approved: bool = True) -> dict:
    path = placements_file(root)
    if not path.is_file():
        raise FileNotFoundError(
            "Localizacao das flores nao definida. Execute -Acao GuiaFlores "
            "e configure canteiro-flores.json a partir das imagens reais.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "fofinhos/flowerbed-positions/v1":
        raise ValueError("Schema de canteiro invalido")
    for view in FLOWER_VIEWS:
        item = data.get("angles", {}).get(view, {})
        x, y = item.get("x"), item.get("y")
        if not (isinstance(x, (int, float)) and not isinstance(x, bool)
                and isinstance(y, (int, float)) and not isinstance(y, bool)
                and .12 <= x <= .88 and .15 <= y <= .90):
            raise ValueError(
                f"Selecione manualmente X,Y (0..1) para o canteiro do {view}. "
                "Consulte os PNGs da pasta guias-flores.")
        if approved and item.get("aprovado_visual") is not True:
            raise ValueError(f"O ovo entre as flores em {view} ainda exige "
                             "aprovado_visual=true apos olhar o PNG real.")
        if approved:
            img = scenery.official(view, root)
            if item.get("background_sha256") != digest(img.read_bytes()):
                raise ValueError(f"O jardim {view} mudou; reavalie as flores.")
    return data


def guide_flowers(root: Path = ROOT) -> dict:
    """Grid overlay with meaningful coordinates; no fabricated placements."""
    directory = output(root) / "guias-flores"
    directory.mkdir(parents=True, exist_ok=True)
    path = placements_file(root)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != "fofinhos/flowerbed-positions/v1":
            raise ValueError("Arquivo de coordenadas existente nao reconhecido")
    else:
        data = {"schema": "fofinhos/flowerbed-positions/v1", "angles": {}}
    results = []
    for view in FLOWER_VIEWS:
        img = scenery.official(view, root)
        if not scenery.installed(view, root):
            raise FileNotFoundError(f"Cenario oficial {view} nao encontrado.")
        fingerprint = digest(img.read_bytes())
        item = data["angles"].get(view, {})
        if item.get("background_sha256") != fingerprint:
            item = {"x": None, "y": None, "aprovado_visual": False,
                    "background_sha256": fingerprint}
        data["angles"][view] = item
        with Image.open(img) as source:
            picture = source.convert("RGB")
            w, h = picture.size
            canvas = ImageDraw.Draw(picture, "RGBA")
            for t in range(1, 10):
                x, y = round(w * t / 10), round(h * t / 10)
                canvas.line((x, 0, x, h), fill=(250, 250, 250, 110), width=3)
                canvas.line((0, y, w, y), fill=(250, 250, 250, 110), width=3)
                canvas.text((x + 4, 10), f"{t/10:.1f}", fill=(0, 0, 0, 255))
                canvas.text((8, y + 2), f"{t/10:.1f}", fill=(0, 0, 0, 255))
            if isinstance(item.get("x"), (float, int)) and isinstance(item.get("y"), (float, int)):
                cx, cy = w * item["x"], h * item["y"]
                canvas.ellipse((cx - 30, cy - 30, cx + 30, cy + 30),
                               fill=(0, 110, 255, 185), outline=(255, 255, 255, 255), width=6)
            dest = directory / (view + "-grade.png")
            picture.save(dest)
            results.append(str(dest))
    save_json(path, data)
    return {"status": "guias_prontos", "coordinate_file": str(path),
            "guides": results, "usage": "Escolher X,Y sobre flores, preencher "
            "o JSON, gerar guias novamente e aprovar somente apos olhar.",
            "uploads": 0}


def missing_assets(root: Path = ROOT) -> list[str]:
    needs = []
    for view in sorted({s["background"] for s in scenes(root)}):
        if not scenery.installed(view, root):
            needs.append("cenario:" + view)
    if not scenery.installed("ovo-azul", root):
        needs.append("ovo:ovo-azul")
    if not assets.valid("caminha-ovo", root):
        needs.append("objeto:caminha-ovo")
    for pose in sorted({s["pose"] for s in scenes(root) if s["pose"]}):
        if not poses.valid(pose, root):
            needs.append("pose:" + pose)
    return needs


def plan(root: Path = ROOT) -> dict:
    data = canon.read_canon(root)
    voice_ok = valid_voice(root)
    measured = None
    if voice_ok:
        measured = json.loads(voice_paths(root)[1].read_text(encoding="utf-8"))["duration_s"]
    flower_status = "nao_calibrado"
    if placements_file(root).exists():
        try:
            read_placement(root, approved=True)
            flower_status = "aprovado"
        except (ValueError, FileNotFoundError, KeyError):
            flower_status = "revisao_pendente"
    needs = missing_assets(root)
    return {
        "schema": SCHEMA, "series": "Fofinhos",
        "approved_scenes": len(data["scenes"]),
        "voice_ready": voice_ok, "duration_s": measured,
        "recommended_format": ("video_longo" if measured > 59.2 else "short") if measured else "apos_tts",
        "visual_assets_missing": needs,
        "flowers": flower_status,
        "ready_for_preview": voice_ok and not needs and flower_status == "aprovado",
        "old_short_untouched": True,
        "ambience": {"version": AMBIENT_VERSION,
                     "effect_types": ["nuvens", "borboletas", "petalas",
                                      "polen", "brilhos_ovo", "poeira_luminosa"],
                     "new_images_required": 0,
                     "human_audiovisual_review": True},
        "calls_gpt_image_2": 0, "uploads": 0,
    }


def layout(scene: dict, positions: dict) -> dict:
    garden = scene["background"].startswith("jardim")
    index = scene["index"]
    pose = scene["pose"]
    animation = ("rock" if index == 14 else
                 "lift" if index == 10 else
                 "prepare" if index == 11 else
                 "approach" if index in (6, 8) else
                 "walk" if index in (2, 6) else
                 "promise" if index == 12 else "still")
    flower = scene["egg_location"] == "entre_flores"
    egg_x, egg_y = (.68, .76) if not garden else (.51, .58)
    if flower:
        point = positions["angles"][scene["background"]]
        egg_x, egg_y = float(point["x"]), float(point["y"])
    return {
        "index": index, "poseX": .35 if garden else .36,
        "poseY": .12, "poseSize": .72 if garden else .69,
        "eggX": egg_x, "eggY": egg_y,
        "eggSize": .18 if flower else .2,
        "showEgg": scene["egg_location"] != "ausente",
        "nestX": .69, "nestY": .83, "nestSize": .35,
        "animation": animation,
        "night": scene["night"], "magic": index in (4, 9, 15),
        "futureGlow": False, "kittenMotion": "idle",
        "waterCount": 0,
        "eggLocation": scene["egg_location"],
        "visualReviewRequired": True,
    }


def props_build(root: Path = ROOT) -> tuple[dict, Path, str]:
    status = plan(root)
    if not status["ready_for_preview"]:
        raise ValueError(
            "Previa Fofinhos bloqueada: " + json.dumps(status, ensure_ascii=False))
    positions = read_placement(root, approved=True)
    audio, marker_path = voice_paths(root)
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    total = math.ceil((float(marker["duration_s"]) + .45) * FPS)
    if not 0 < total <= MAX_SECONDS * FPS:
        raise ValueError("Numero de frames da previa fora do limite")
    target = public(root)
    target.mkdir(parents=True, exist_ok=True)
    copied = {}
    def use(path: Path) -> str:
        digest_value = digest(path.read_bytes())
        # Avoid collisions: same names can represent different images.
        name = path.stem + "-" + digest_value[:10] + path.suffix
        dest = target / name
        if not dest.is_file() or digest(dest.read_bytes()) != digest_value:
            shutil.copy2(path, dest)
        copied[name] = digest_value
        return "generated/fofinhos-ep01-parte01/" + name

    layers = []
    for s, time in zip(scenes(root), marker["segments"]):
        row = layout(s, positions)
        row["startFrame"] = round(time["start_s"] * FPS)
        row["endFrame"] = (round(marker["segments"][s["index"]]["start_s"] * FPS)
                           if s["index"] < 15 else total)
        row["background"] = use(scenery.official(s["background"], root))
        row["pose"] = use(poses.paths(s["pose"], root)[0]) if s["pose"] else None
        row["egg"] = (use(scenery.official("ovo-azul", root)) if row["showEgg"] else "")
        row["nest"] = use(assets.reference("caminha-ovo", root)) if s["index"] >= 11 else None
        row["kitty"] = None
        if row["endFrame"] <= row["startFrame"]:
            raise ValueError("Cena sem frames: " + str(s["index"]))
        layers.append(row)
    captions = []
    for i in range(15):
        speech = [w for w in marker["words"] if w["segment"] == i]
        for begin in range(0, len(speech), 3):
            group = speech[begin:begin + 3]
            captions.append({
                "startFrame": round(group[0]["start"] * FPS),
                "endFrame": round(group[-1]["end"] * FPS) + 1,
                "text": " ".join(w["text"] for w in group),
            })
    if not captions:
        raise ValueError("Narração sem alinhamento de legenda")
    music = None
    track = root / "Wondertrail _Main Theme_.mp3"
    if track.is_file():
        music = prepare_kids_music(root, "kids-emanuelly-ep01-p01-ovo-azul")
        copied["music_sha"] = music_signature(root, "kids-emanuelly-ep01-p01-ovo-azul")
    audio_path = use(audio)
    props = {
        "episodeId": "fofinhos-ep01-parte01-canonico",
        "title": "O Ovo Azul", "brand": "Fofinhos",
        "chapter": "EP 01 · O OVO AZUL",
        "durationFrames": total, "frames": [],
        "layeredScenes": layers, "captions": captions,
        "audio": audio_path, "music": music,
        "ambientScenes": ambient_profiles(root),
        "ambientEnabled": True,
        "madeForKids": True, "referenceSha": voice_signature(root),
    }
    dest = target / "props-canonicos.json"
    save_json(dest, props)
    signature = digest(json.dumps({
        "schema": SCHEMA, "images": copied, "positions": positions,
        "voice_signature": voice_signature(root), "duration_frames": total,
        "ambient_version": AMBIENT_VERSION, "ambient_scenes": ambient_profiles(root),
    }, ensure_ascii=False, sort_keys=True).encode())
    return props, dest, signature


def render(root: Path = ROOT, *, refazer: bool = False,
           runner=None, probe=None) -> dict:
    props, props_path, fingerprint = props_build(root)
    folder = output(root)
    final = folder / VIDEO_NAME
    qa = folder / "qa-previa-canonica.json"
    if final.exists() and not refazer:
        if qa.is_file():
            before = json.loads(qa.read_text(encoding="utf-8"))
            if (before.get("signature") == fingerprint
                    and before.get("video_sha256") == digest(final.read_bytes())):
                return {"status": "cache", "mp4": str(final), "uploads": 0}
        raise ValueError("Previa anterior diverge do roteiro. "
                         "Use -Refazer para preservar o historico.")
    motion = root / "motion-remotion"
    if runner is None:
        if not (motion / "node_modules").is_dir():
            raise FileNotFoundError(
                "Remotion nao instalado. Execute npm.cmd install em motion-remotion.")
        npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
        if not npm:
            raise FileNotFoundError("npm nao encontrado")
        def runner(destination):
            subprocess.run(
                [npm, "run", "render:fofinhos", "--", str(destination.resolve()),
                 "--props", str(props_path.resolve()), "--concurrency", "2"],
                cwd=motion, check=True, timeout=7200)
    temp = folder / "previa-canonica.partial.mp4"
    temp.unlink(missing_ok=True)
    runner(temp)
    if not temp.is_file() or temp.stat().st_size < 10000:
        raise ValueError("Nenhum MP4 valido foi produzido")
    if probe is None:
        def probe(path):
            proc = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                check=True, capture_output=True, text=True)
            return float(proc.stdout.strip())
    duration = probe(temp)
    expected = props["durationFrames"] / FPS
    if not 0 < duration <= MAX_SECONDS or abs(duration - expected) > .65:
        raise ValueError("Tempo do MP4 difere do storyboard/voz")
    if final.exists():
        history = folder / "historico-previas"
        history.mkdir(exist_ok=True)
        old = history / ("previa-" + digest(final.read_bytes())[:12] + ".mp4")
        if not old.exists():
            shutil.copy2(final, old)
    temp.replace(final)
    save_json(qa, {
        "schema": SCHEMA, "signature": fingerprint,
        "video_sha256": digest(final.read_bytes()),
        "seconds": duration, "scenes": 15,
        "narration": "approved_15_scenes",
        "flowerbed": "manually_approved_coordinates_only",
        "ambient_version": AMBIENT_VERSION,
        "ambient_effects": "borboletas/nuvens/petalas/polen/brilhos/poeira_svg",
        "ambient_human_review": "pending",
        "new_ambient_images": 0,
        "articulated_animation": False,
        "quality_review": "pending_human_watch_of_entire_mp4",
        "music_rights_review": "pending_before_publication",
        "uploads": 0,
    })
    return {"status": "previa_para_revisao", "mp4": str(final),
            "seconds": duration, "uploads": 0}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fofinhos EP01 Parte 1 - narração canônica")
    p.add_argument("--acao", choices=("planejar", "voz", "guia-flores", "renderizar"),
                   default="planejar")
    p.add_argument("--refazer", action="store_true")
    args = p.parse_args(argv)
    if args.refazer and args.acao not in ("voz", "renderizar"):
        p.error("Refazer permitido somente para voz/renderizar")
    if args.acao == "planejar":
        result = plan()
    elif args.acao == "voz":
        result = make_voice(refazer=args.refazer)
    elif args.acao == "guia-flores":
        result = guide_flowers()
    else:
        result = render(refazer=args.refazer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("[FOFINHOS CANONICO BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
