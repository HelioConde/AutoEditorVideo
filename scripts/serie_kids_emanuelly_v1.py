#!/usr/bin/env python3
"""Emanuelly EP01: 4 Shorts Kids PT-BR com imagem REFERENCIADA, TTS e Remotion.

A foto privada permanece LOCAL e e enviada apenas ao endpoint de edicao
quando o usuario executa a acao imagens/testar. NUNCA vai para GitHub.
NUNCA publica ou autentica no YouTube. Sem fallback de arte generica.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from fofinhos_ep01_canon import ensure_approved_script
from kids_narracao_acolhedora_v1 import (
    assemble_paced_voice, commit_voice, scene_props, signature as pacing_signature,
)
from piloto_canais_3x2_v3 import verify_video
from produzir_piloto_canais_v3 import _synthesize, audio_seconds
from kids_musicas_fundo_v1 import (
    MUSIC_POLICY, choose_track, music_signature, prepare_kids_music,
)
from kids_emanuelly_continuidade_v2 import (
    MODEL, POLICY, allowed_characters, role_for, scene_prompt,
    check_isolated_ref, prepare_isolated_references,
)

MANIFEST = ROOT / "conteudos" / "kids-emanuelly-ep01-shortserie-v1.json"
REFERENCE = ROOT / "assets" / "referencias-privadas" / "emanuelly-elenco.png"
OUT = ROOT / "assets" / "gerados" / "kids-emanuelly"
MOTION = ROOT / "motion-remotion"
PUBLIC = MOTION / "public" / "generated" / "kids-emanuelly"
VOICE, RATE = "pt-BR-FranciscaNeural", "-15%"
FPS = 30
MAX_AUDIO = 59.2
VALID_ID = re.compile(r"^kids-emanuelly-ep01-p0[1-4]-[a-z0-9-]+$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    temp.replace(path)


def load_parts(manifest: Path = MANIFEST) -> list[dict]:
    data = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if (data.get("schema") != "mini-mundo/emanuelly-serie-shorts/v1"
            or data.get("publish_enabled") is not False
            or data.get("upload_authorized") is not False
            or data.get("made_for_kids") is not True
            or data.get("language") != "pt-BR"
            or data.get("max_video_duration_seconds") != 60
            or data.get("max_audio_duration_seconds") != MAX_AUDIO):
        raise ValueError("Manifesto Kids invalido ou com risco de publicacao")
    parts = data.get("parts", [])
    if len(parts) != 4:
        raise ValueError("A origem de Fofinho exige quatro partes")
    for i, part in enumerate(parts, 1):
        if (part.get("part") != i or not VALID_ID.fullmatch(part.get("id", ""))
                or len(part.get("segments", [])) < 7
                or part.get("voice") != VOICE):
            raise ValueError(f"Parte Kids {i} invalida")
        segments = part["segments"]
        if part.get("narration") != " ".join(s.get("spoken_text", "") for s in segments):
            raise ValueError("Frases e narracao Kids divergentes")
        for j, beat in enumerate(segments, 1):
            if (beat.get("index") != j or not beat.get("visual_cue")
                    or not beat.get("spoken_text")
                    or not 0.35 <= float(beat.get("pause_after_s", -1)) <= 2.5):
                raise ValueError("Cena Kids invalida: " + part["id"])
        if i > 1 and parts[i-2]["continuity_to_next"] != part["continuity_from_previous"]:
            raise ValueError("Quebra de continuidade entre Shorts Kids")
    return parts


def select(parts: list[dict], part: int | None) -> list[dict]:
    if part is None:
        return parts
    if not 1 <= part <= 4:
        raise ValueError("Parte deve ser 1, 2, 3 ou 4")
    return [parts[part - 1]]


def output_for(part: dict, root: Path = ROOT) -> Path:
    return root / "assets" / "gerados" / "kids-emanuelly" / part["id"]


def segment_scene(index: int, total: int) -> str:
    # 9 -> 01,01,02,02,03,03,04,04,05; preserves five scenes.
    return f"{min(4, index * 5 // total) + 1:02d}"


def episode_for_tts(part: dict) -> dict:
    pieces = part["segments"]
    segments = []
    for i, item in enumerate(pieces):
        question = "?" in item["spoken_text"]
        pause = float(item["pause_after_s"])
        if question:
            pause = max(1.8, pause)
        segments.append({
            "scene": segment_scene(i, len(pieces)),
            "text": item["spoken_text"],
            "pause_after_s": pause,
            "cue": f"p{part['part']:02d}-b{i+1:02d}" + ("-question" if question else ""),
            "headline": "Emanuelly e seus Amigos",
        })
    scenes = []
    for index in range(5):
        joined = [s["text"] for s in segments if s["scene"] == f"{index+1:02d}"]
        if not joined:
            raise ValueError("Cena sem fala")
        scenes.append({
            "id": f"{index+1:02d}",
            "on_screen_text": "Emanuelly e seus Amigos",
            "visual": " / ".join(joined),
            "narration": " ".join(joined),
        })
    return {
        "id": part["id"],
        "script": part["narration"],
        "scenes": scenes,
        "kids_pacing": {
            "schema": "mini-mundo/narracao-acolhedora/v1",
            "target_seconds": {"min": 45, "max": 55},
            "segments": segments,
        },
    }


def reference_hash(path: Path = REFERENCE) -> str:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(
            "Foto de referencia ausente. Extraia o pacote privado na raiz do "
            "projeto, em assets/referencias-privadas/emanuelly-elenco.png "
            "ou use -Referencia para instalar localmente."
        )
    if path.stat().st_size > 18_000_000:
        raise ValueError("Foto acima de 18MB: endpoint do proxy nao aceita")
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        if im.format != "PNG" or min(im.size) < 640:
            raise ValueError("Referencia deve ser PNG nitido (minimo 640px)")
    return sha(path.read_bytes())


def install_reference(source: Path, destination: Path = REFERENCE,
                      *, replace: bool = False) -> dict:
    from PIL import Image
    if not source.is_file():
        raise FileNotFoundError("Arquivo de imagem nao encontrado: " + str(source))
    if source.resolve() == destination.resolve():
        return {"status": "ja_instalada", "sha256": reference_hash(destination)}
    with Image.open(source) as im:
        im.load()
        if min(im.size) < 640:
            raise ValueError("Referencia com resolucao insuficiente")
        output = io.BytesIO()
        im.convert("RGBA").save(output, format="PNG")
        data = output.getvalue()
    if len(data) > 18_000_000:
        raise ValueError("Referencia convertida maior que 18MB")
    fingerprint = sha(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        previous = reference_hash(destination)
        if previous == fingerprint:
            return {"status": "ja_instalada", "sha256": fingerprint}
        if not replace:
            raise ValueError("Referencia diferente ja instalada; usar -SubstituirReferencia explicitamente")
        history = destination.parent / "historico"
        history.mkdir(exist_ok=True)
        old = history / f"emanuelly-elenco-{previous[:12]}.png"
        if not old.exists():
            shutil.copy2(destination, old)
    temp = destination.with_name(destination.name + ".partial")
    temp.write_bytes(data)
    temp.replace(destination)
    return {"status": "instalada_localmente", "sha256": fingerprint,
            "destination": str(destination), "github_upload": False}


def frame_prompt(part: dict, beat: dict, position: int) -> str:
    return scene_prompt(part, beat)


def image_cache(part: dict, beat: dict, model: str, ref_digest: str) -> str:
    return sha((model + "\n" + ref_digest + "\n" + frame_prompt(
        part, beat, beat["index"])).encode("utf-8"))


def frame_paths(part: dict, beat: dict, *, root: Path = ROOT) -> tuple[Path, Path]:
    parent = output_for(part, root) / "quadros"
    stem = f"quadro-{beat['index']:02d}"
    return parent / (stem + ".png"), parent / (stem + ".json")


def valid_frame(part: dict, beat: dict, model: str, ref_digest: str,
                *, root: Path = ROOT) -> bool:
    frame, marker = frame_paths(part, beat, root=root)
    if not frame.is_file() or not marker.is_file() or frame.is_symlink():
        return False
    try:
        saved = json.loads(marker.read_text(encoding="utf-8"))
        role = role_for(part, beat)
        try:
            _isolated, isolated_sha = check_isolated_ref(
                root / "assets" / "referencias-privadas" / "emanuelly-elenco.png", role
            )
        except (FileNotFoundError, ValueError, OSError):
            return False
        if (saved.get("schema") != "kids-emanuelly/image-qa/v2"
                or saved.get("continuity_policy") != POLICY
                or saved.get("allowed_characters") != list(allowed_characters(part, beat))
                or saved.get("reference_role") != role
                or saved.get("isolated_reference_sha256") != isolated_sha
                or saved.get("model") != MODEL
                or saved["signature"] != image_cache(part, beat, model, ref_digest)
                or saved["reference_sha256"] != ref_digest
                or saved["image_sha256"] != sha(frame.read_bytes())):
            return False
        from PIL import Image
        with Image.open(frame) as image:
            image.verify()
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def image_plan(parts: list[dict], reference: Path, model: str, root: Path = ROOT) -> tuple[list[tuple[dict, dict]], str]:
    ref_digest = reference_hash(reference)
    missing = []
    for part in parts:
        for beat in part["segments"]:
            if not valid_frame(part, beat, model, ref_digest, root=root):
                missing.append((part, beat))
    return missing, ref_digest


def make_images(parts: list[dict], *, reference: Path = REFERENCE,
                model: str = MODEL, budget: int = 0,
                root: Path = ROOT, regenerate: bool = False,
                editor=None, key_provider=None) -> dict:
    for part in parts:
        ensure_approved_script(part, root)
    if model != MODEL:
        raise ValueError("Referencias Kids exigem gpt-image-2; nunca gpt-image-1.5")
    if budget < 0:
        raise ValueError("Numero de chamadas nao pode ser negativo")
    missing, ref_digest = image_plan(parts, reference, model, root)
    if not regenerate and any(
        frame_paths(part, beat, root=root)[0].exists()
        and not valid_frame(part, beat, model, ref_digest, root=root)
        for part, beat in missing
    ):
        raise ValueError("Ha imagem em cache de outro roteiro/referencia. Use -Refazer explicitamente.")
    requested = sum(len(part["segments"]) for part in parts) if regenerate else len(missing)
    if budget < requested:
        raise ValueError(
            f"Orcamento de imagens insuficiente: {requested} chamadas novas necessarias, "
            f"maximo permitido {budget}. NENHUMA chamada de IA foi enviada. "
            "Execute -Acao Planejar para revisar o total."
        )
    if requested == 0:
        return {"generated": 0, "cached": sum(len(p["segments"]) for p in parts),
                "reference_sha256": ref_digest, "uploads": 0}
    # Prevent any paid request while an isolated character reference is absent.
    for part, beat in missing:
        check_isolated_ref(reference, role_for(part, beat))
    if editor is None:
        from master_scenes import request_edit
        editor = request_edit
    if key_provider is None:
        from gerar_video_codex import proxy_key
        key_provider = proxy_key
    key = key_provider()
    generated = 0
    for part in parts:
        for beat in part["segments"]:
            if not regenerate and valid_frame(part, beat, model, ref_digest, root=root):
                continue
            out, marker = frame_paths(part, beat, root=root)
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                isolated, isolated_sha = check_isolated_ref(
                    reference, role_for(part, beat)
                )
                raw = editor(
                    isolated, frame_prompt(part, beat, beat["index"]),
                    model, key, transparent=False,
                )
                from master_scenes import normalize_image, validate_image
                result = normalize_image(raw, alpha=False, stage=f"kids/{part['id']}/beat-{beat['index']:02d}")
                validate_image(result, alpha=False)
                # Preserve stale source before user-authorized regeneration.
                if out.is_file():
                    history = out.parent.parent / "historico-imagens"
                    history.mkdir(exist_ok=True)
                    original = history / (out.stem + "-" + sha(out.read_bytes())[:12] + ".png")
                    if not original.exists():
                        shutil.copy2(out, original)
                temp = out.with_suffix(".partial.png")
                temp.write_bytes(result)
                temp.replace(out)
                dump(marker, {
                    "schema": "kids-emanuelly/image-qa/v2",
                    "continuity_policy": POLICY,
                    "part": part["id"], "beat": beat["index"],
                    "allowed_characters": list(allowed_characters(part, beat)),
                    "reference_role": role_for(part, beat),
                    "isolated_reference_sha256": isolated_sha,
                    "signature": image_cache(part, beat, model, ref_digest),
                    "reference_sha256": ref_digest,
                    "image_sha256": sha(result), "model": model,
                    "source": "image_edit_with_isolated_character_reference",
                    "human_character_fidelity_review": "pending",
                    "upload": False,
                })
                generated += 1
                print(f"[IMAGEM COM REFERENCIA] {part['id']} | quadro-{beat['index']:02d} | OK", flush=True)
            except (ValueError, RuntimeError, OSError) as exc:
                print(f"[BLOQUEADO] Imagem {part['id']} quadro {beat['index']:02d}: {exc}", file=sys.stderr)
                raise
    return {"generated": generated, "cached": requested - generated,
            "reference_sha256": ref_digest, "uploads": 0}


def read_voice(part: dict, root: Path = ROOT) -> tuple[Path, dict]:
    ensure_approved_script(part, root)
    directory = output_for(part, root)
    audio = directory / "narracao.mp3"
    marker = directory / "marcacoes-voz.json"
    if not audio.is_file() or not marker.is_file():
        raise FileNotFoundError("Narração ausente. Execute -Acao Voz (PT-BR).")
    value = json.loads(marker.read_text(encoding="utf-8"))
    ep = episode_for_tts(part)
    if (value.get("pacing_sha256") != pacing_signature(ep["kids_pacing"])
            or value.get("script_sha256") != sha(part["narration"].encode("utf-8"))
            or value.get("voice") != VOICE or value.get("rate") != RATE
            or value.get("mp3_sha256") != sha(audio.read_bytes())):
        raise ValueError("Cache de voz pertence a outra versao da historia ou foi alterado")
    if not value.get("words") or not value.get("segments"):
        raise ValueError("Locucao sem alinhamento real")
    return audio, value


def make_voice(part: dict, root: Path = ROOT, *, regenerate: bool = False,
               synthesizer=None, assembler=None) -> dict:
    ensure_approved_script(part, root)
    folder = output_for(part, root)
    if not regenerate:
        try:
            audio, marker = read_voice(part, root)
            return {"status": "cache", "audio": str(audio),
                    "seconds": marker["duration_s"], "parts": 1}
        except FileNotFoundError:
            pass
    async def default_synth(text, voice, rate):
        return await _synthesize(text, voice, rate, minimum_words=1)
    ep = episode_for_tts(part)
    folder.mkdir(parents=True, exist_ok=True)
    completed = asyncio.run((assembler or assemble_paced_voice)(
        ep, VOICE, RATE, folder, synthesizer=synthesizer or default_synth,
    ))
    commit_voice(folder, completed)
    audio, marker = read_voice(part, root)
    return {"status": "nova_narracao", "seconds": marker["duration_s"],
            "pause_seconds": marker["pause_total_s"],
            "voice": VOICE, "audio": str(audio), "published": False}


def build_props(part: dict, *, model: str = MODEL,
                reference: Path = REFERENCE, root: Path = ROOT) -> tuple[dict, Path]:
    ensure_approved_script(part, root)
    ref_digest = reference_hash(reference)
    missing, _ = image_plan([part], reference, model, root)
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} imagens de referencia ausentes ou desatualizadas. "
            "Execute -Acao Imagens antes de renderizar."
        )
    voice, marker = read_voice(part, root)
    duration = audio_seconds(voice)
    total_frames = math.ceil((duration + .45) * FPS)
    if duration > MAX_AUDIO or total_frames > 1800:
        raise ValueError("Narração Kids ou vídeo previsto ultrapassa 60 segundos")
    ep = episode_for_tts(part)
    scenes, captions, beats = scene_props(ep, marker, total_frames)
    if len(beats) != len(part["segments"]):
        raise ValueError("A quantidade de quadros difere da narracao")
    dest = root / "motion-remotion" / "public" / "generated" / "kids-emanuelly" / part["id"]
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(voice, dest / "narracao.mp3")
    music = prepare_kids_music(root, part["id"])
    frames = []
    for segment, beat in zip(part["segments"], beats):
        file, _ = frame_paths(part, segment, root=root)
        target = dest / f"quadro-{segment['index']:02d}.png"
        shutil.copy2(file, target)
        frames.append({
            "startFrame": beat["startFrame"],
            "endFrame": beat["endFrame"],
            "image": f"generated/kids-emanuelly/{part['id']}/{target.name}",
            "cue": segment["visual_cue"], "index": segment["index"],
        })
    props = {
        "episodeId": part["id"], "title": part["title"],
        "brand": "Emanuelly e seus Amigos de Pelúcia",
        "chapter": f"EP 1 · PARTE {part['part']}/4",
        "durationFrames": total_frames,
        "frames": frames,
        "captions": captions,
        "audio": f"generated/kids-emanuelly/{part['id']}/narracao.mp3",
        "referenceSha": ref_digest,
        "madeForKids": True,
        "music": music,
    }
    path = root / "motion-remotion" / f"props-emanuelly-{part['id']}.json"
    dump(path, props)
    return props, path


def render(part: dict, *, model: str = MODEL,
           reference: Path = REFERENCE, root: Path = ROOT,
           regenerate: bool = False) -> dict:
    ensure_approved_script(part, root)
    directory = output_for(part, root)
    video = directory / "final.mp4"
    qa_file = directory / "qa-local.json"
    ref_digest = reference_hash(reference)
    if video.is_file() and not regenerate:
        if not qa_file.is_file():
            raise ValueError("MP4 existente sem QA: usar -Refazer")
        qa = json.loads(qa_file.read_text(encoding="utf-8"))
        # A new image or voice invalidates a cached MP4 even if the script
        # and source photo are unchanged. Never silently reuse stale footage.
        image_hashes = [
            sha(frame_paths(part, b, root=root)[0].read_bytes())
            for b in part["segments"]
            if frame_paths(part, b, root=root)[0].is_file()
        ]
        current_voice = output_for(part, root) / "narracao.mp3"
        voice_hash = sha(current_voice.read_bytes()) if current_voice.is_file() else None
        if (qa.get("video_sha256") == sha(video.read_bytes())
                and qa.get("reference_sha256") == ref_digest
                and qa.get("script_sha256") == sha(part["narration"].encode("utf-8"))
                and qa.get("model") == model
                and qa.get("continuity_policy") == POLICY
                and qa.get("music_policy") == MUSIC_POLICY
                and qa.get("music_sha256") == music_signature(root, part["id"])
                and qa.get("image_sha256") == image_hashes
                and qa.get("voice_sha256") == voice_hash
                and len(image_hashes) == len(part["segments"])):
            return {"status": "render_em_cache", "mp4": str(video), "uploaded": False}
        raise ValueError("MP4 pertence a outro roteiro ou referencia: usar -Refazer")
    props, path = build_props(part, model=model, reference=reference, root=root)
    motion = root / "motion-remotion"
    if not (motion / "node_modules").is_dir():
        raise RuntimeError("Remotion nao instalado; execute npm.cmd install em motion-remotion")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise RuntimeError("Node/npm ausente")
    directory.mkdir(parents=True, exist_ok=True)
    temp = directory / "render-temp.mp4"
    temp.unlink(missing_ok=True)
    subprocess.run(
        [npm, "run", "render:emanuelly", "--", str(temp.resolve()),
         "--props", str(path.resolve()), "--concurrency", "2"],
        cwd=motion, check=True, timeout=3000,
    )
    technical = verify_video(temp)
    if technical.get("technical_status") != "passed":
        raise ValueError("Video de Emanuelly reprovado em FFprobe: " + str(technical))
    if video.is_file():
        history = directory / "historico-renders"
        history.mkdir(exist_ok=True)
        past = history / ("final-" + sha(video.read_bytes())[:12] + ".mp4")
        if not past.exists():
            shutil.copy2(video, past)
        if qa_file.is_file():
            old_qa = history / ("qa-" + sha(video.read_bytes())[:12] + ".json")
            if not old_qa.exists():
                shutil.copy2(qa_file, old_qa)
    temp.replace(video)
    report = {
        "schema": "kids-emanuelly/render-qa/v1",
        "episode_id": part["id"], "channel": "Kids", "language": "pt-BR",
        "video_sha256": sha(video.read_bytes()),
        "script_sha256": sha(part["narration"].encode("utf-8")),
        "voice_sha256": sha((output_for(part, root) / "narracao.mp3").read_bytes()),
        "reference_sha256": ref_digest, "model": model,
        "continuity_policy": POLICY,
        "music_policy": MUSIC_POLICY,
        "music_sha256": music_signature(root, part["id"]),
        "music_source": choose_track(part["id"])[1],
        "music_rights_review": "pending_before_publication",
        "image_sha256": [
            sha(frame_paths(part, b, root=root)[0].read_bytes()) for b in part["segments"]
        ],
        "technical": technical, "image_character_consistency_review": "pending",
        "visual_motion_type": "AI-keyframed illustrated scenes plus animated independent particles; not articulated character rigging",
        "human_audiovisual_review": "pending",
        "made_for_kids": True, "published": False, "upload_approved": False,
    }
    dump(qa_file, report)
    try:
        from organizar_videos_por_canal import refresh_library_after_render
        refresh_library_after_render(root)
    except (OSError, ValueError) as exc:
        print("[BIBLIOTECA AVISO] Original preservado: " + str(exc), flush=True)
    return {"status": "renderizado", "mp4": str(video),
            "duration_seconds": technical["duration"],
            "sha256": report["video_sha256"], "uploaded": False}


def inspect(part: dict, reference: Path = REFERENCE, model: str = MODEL,
            root: Path = ROOT) -> dict:
    reference_present = reference.is_file()
    digest = reference_hash(reference) if reference_present else None
    cached = 0
    for beat in part["segments"]:
        if digest and valid_frame(part, beat, model, digest, root=root):
            cached += 1
    voice_present = (output_for(part, root) / "narracao.mp3").is_file()
    final = output_for(part, root) / "final.mp4"
    roles = sorted({role_for(part, beat) for beat in part["segments"]})
    isolated = {}
    for role in roles:
        try:
            check_isolated_ref(reference, role)
            isolated[role] = True
        except (FileNotFoundError, ValueError, OSError):
            isolated[role] = False
    music_track = choose_track(part["id"])[1]
    return {
        "episode": part["id"], "part": part["part"],
        "music_track": music_track,
        "music_present": (root / music_track).is_file(),
        "music_rights_review": "pending_before_publication",
        "continuity_policy": POLICY, "isolated_references_ready": isolated,
        "reference_present": reference_present,
        "frames_required": len(part["segments"]),
        "frames_cached_and_verified": cached,
        "frames_missing": len(part["segments"]) - cached,
        "voice_present": voice_present,
        "final_mp4_present": final.is_file(),
        "video_path": str(final),
        "note": "Imagem privada nunca entra no GitHub. Geração via proxy images/edits.",
        "uploaded": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Criar Shorts Emanuelly PT-BR com referencia real e pausas")
    parser.add_argument("--acao", choices=("planejar", "instalar-referencia",
                                           "preparar-referencias", "imagens",
                                           "voz", "renderizar", "testar", "verificar"),
                        default="planejar")
    parser.add_argument("--parte", type=int, choices=(1, 2, 3, 4))
    parser.add_argument("--referencia", type=Path, default=REFERENCE)
    parser.add_argument("--modelo", choices=(MODEL,), default=MODEL)
    parser.add_argument("--max-chamadas", type=int, default=0)
    parser.add_argument("--refazer", action="store_true")
    args = parser.parse_args(argv)
    if args.max_chamadas < 0:
        parser.error("--max-chamadas deve ser positivo")
    if args.refazer and args.acao not in ("instalar-referencia", "preparar-referencias", "imagens", "voz", "renderizar", "testar"):
        parser.error("--refazer nao se aplica a acao escolhida")
    if args.acao == "instalar-referencia":
        result = install_reference(args.referencia, replace=args.refazer)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.acao == "preparar-referencias":
        result = prepare_isolated_references(
            REFERENCE, budget=args.max_chamadas, replace=args.refazer
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    parts = select(load_parts(), args.parte)
    # O compositor antigo gera apenas uma imagem por fala; para a Parte 2
    # isso descartaria planos visuais e faria um render incorreto.
    if args.acao in ("imagens","renderizar","testar") and any(
        p["part"]==2 for p in parts
    ):
        raise ValueError(
            "Parte 2 agora usa planos visuais SEM LIMITE FIXO. "
            "Use animar-emanuelly.ps1 -Acao Planejar/Renderizar -Parte 2; "
            "para narracao, este programa ainda aceita -Acao Voz -Parte 2."
        )
    if args.acao in ("planejar", "verificar"):
        result = {
            "schema": "kids-emanuelly/preflight/v1",
            "mode": args.acao, "parts": [inspect(p, REFERENCE, args.modelo) for p in parts],
            "language": "pt-BR", "audience": "Made for Kids",
            "story_status": "four editorial episodes", "uploads": 0,
        }
    else:
        if args.acao in ("imagens", "testar"):
            missing, _ = image_plan(parts, REFERENCE, args.modelo)
            required = sum(len(p["segments"]) for p in parts) if args.refazer else len(missing)
            if required > args.max_chamadas:
                raise ValueError(
                    f"Orcamento {args.max_chamadas} menor que {required} imagens "
                    "necessarias; nenhuma IA chamada. Use --max-chamadas "
                    "e defina o limite antes de gerar."
                )
        rows = []
        for part in parts:
            if args.acao in ("imagens", "testar"):
                rows.append({"part": part["part"], "images": make_images(
                    [part], budget=args.max_chamadas, model=args.modelo,
                    regenerate=args.refazer,
                )})
            if args.acao in ("voz", "testar"):
                rows.append({"part": part["part"], "voice": make_voice(
                    part, regenerate=args.refazer if args.acao == "voz" else False,
                )})
            if args.acao in ("renderizar", "testar"):
                rows.append({"part": part["part"], "render": render(
                    part, model=args.modelo,
                    regenerate=args.refazer,
                )})
        result = {"status": "local_only", "parts": rows, "uploaded": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, KeyError,
            subprocess.SubprocessError) as exc:
        print("[BLOQUEADO SERIE KIDS] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
