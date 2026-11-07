#!/usr/bin/env python3
"""Render the five English Shorts using APPROVED original scene layers.

Different voice, narration, subtitles, cover and output folder.
Never requests new AI images and never uploads to YouTube.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from narracao_shorts import ensure_voice
from master_scenes import read_storyboard, production_storyboard
from renderizar_com_remotion import audio_duration, captions_from_ass
from shorts_duration import validate_planned_audio, validate_video
import renderizar_master_remotion as master
from otaku_reframe_direction import ensure_english_plan
from english_caption_design import grouped_captions
from qa_automatico_reframe_en import prepare_qa_storyboard
from otaku_reframe_production import validate_english_production
from metadata_shorts import load_episodes

# Identidades verificadas por consulta dos canais conectados em 2026-11-04.
BR_CHANNEL_V3 = "UCXGYTuBYn-0Ziqin5ajKhOw"
EN_CHANNEL_V3 = "UCBoNbQjaMYdpJqPLRZAFkvQ"
BR_SNAPSHOT_V3 = ROOT / "conteudos" / "otaku-br-publicados-snapshot-20261104.json"


def validate_reused_br_manifest(data: dict, items: list[dict]) -> None:
    """Rejeita mapeamento incorreto de videos e fontes PT (sem chamada remota)."""
    if not any(e.get("source_br_video_id") for e in items):
        return
    if data.get("target_channel_id") != EN_CHANNEL_V3 or data.get("source_br_channel_id") != BR_CHANNEL_V3:
        raise ValueError("Destino Otaku Reframe ou origem Otaku Multicena invalido")
    snapshot = json.loads(BR_SNAPSHOT_V3.read_text(encoding="utf-8-sig"))
    ready = {r["episode_id"]: r["video_id"] for r in snapshot["videos"]
             if r.get("status") == "ready"}
    originals = load_episodes(include_recaps=True)
    seen = set()
    for ep in items:
        original = originals.get(ep["id"])
        vid = ep.get("source_br_video_id", "")
        if not original or ready.get(ep["id"]) != vid or ep["id"] in seen:
            raise ValueError("Fonte BR nao confirmada ou duplicada: " + ep["id"])
        seen.add(ep["id"])
        digest = hashlib.sha256(original["script"].encode("utf-8")).hexdigest()
        if ep.get("source_pt_script_sha256") != digest or ep.get("source_pt_episode_id") != ep["id"]:
            raise ValueError("Fonte PT foi alterada; revalidar adaptacao EN: " + ep["id"])
        if ep.get("channel") != "Otaku Reframe" or ep.get("source_visual_check") != "requires_full_english_video_review":
            raise ValueError("Identidade EN ou revisao obrigatoria ausente: " + ep["id"])
        if not isinstance(ep.get("hook_options"), list) or len(ep["hook_options"]) != 5:
            raise ValueError("Roteiro EN sem cinco propostas de gancho: " + ep["id"])
        if not ep["script"].startswith(ep.get("selected_hook", "")):
            raise ValueError("A abertura EN diverge do gancho escolhido: " + ep["id"])


LANG = ROOT / "conteudos" / "testes-animados-5-en.json"
OUT = ROOT / "assets" / "gerados" / "shorts-animados"
MOTION = ROOT / "motion-remotion"
VOICE = "en-US-GuyNeural"


def load_english(path: Path = LANG) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "arquivo-otaku/shorts-english/v1":
        raise ValueError("Manifesto ingles nao reconhecido")
    items = data.get("episodes", [])
    if not items or len(set(ep["id"] for ep in items)) != len(items):
        raise ValueError("Manifesto ingles sem episodios ou com IDs duplicados")
    if path == LANG and len(items) != 5:
        raise ValueError("O lote original em ingles deve conservar exatamente cinco episodios")
    validate_reused_br_manifest(data, items)
    for item in items:
        item.setdefault("channel", data.get("channel", "Otaku Reframe"))
        if item.get("scenes"):
            item.setdefault("production", data.get("production"))
        validate_english_production(item, item.get("production"))
    for item in items:
        if len(item["script"].split()) < 50 or not item["cover"].strip():
            raise ValueError("Episodio ingles precisa de roteiro e capa: " + item["id"])
        if not 1 <= len(item["title"]) <= 100:
            raise ValueError("Titulo fora do limite YouTube: " + item["id"])
    return items


def english_metadata(item: dict) -> dict:
    brand = item.get("channel", "Otaku Reframe")
    hashtag = "".join(ch for ch in brand if ch.isalnum())
    authored = str(item.get("description", "")).strip()
    description = authored or (
        f"An original English commentary on {item['series']}.\n\n"
        f"{item['script']}\n\n"
        "English narration and original editorial adaptation with AI-generated illustrations. "
        "The anime and its characters belong to their respective rights holders.\n\n"
        f"#DeathNote #Anime #AnimeAnalysis #{hashtag} #Shorts"
    )
    tags = item.get("tags") or [
        "Death Note", "Anime", "Anime Analysis", brand, "English Anime Shorts"
    ]
    if not isinstance(tags, list) or not tags or any(
            not isinstance(tag, str) or not tag.strip() for tag in tags):
        raise ValueError("Tags EN devem ser uma lista de termos relevantes")
    return {
        "titulo": item["title"],
        "descricao": description,
        "tags": tags,
        "categoria": "1",  # Film & Animation
        "idioma": "en",
        "feito_para_criancas": False,
    }

def audio_for(item: dict, folder: Path, *, create: bool) -> tuple[Path, Path]:
    digest = hashlib.sha256(
        (item["script"] + "\n" + VOICE).encode("utf-8")
    ).hexdigest()
    stamp = folder / "voice-script-sha256.txt"
    mp3 = folder / "voz-master.mp3"
    ass = folder / "legendas.ass"
    if stamp.is_file() and stamp.read_text(encoding="utf-8").strip() != digest:
        if not create:
            raise RuntimeError("Roteiro ingles mudou; gere a nova voz com -CriarVoz")
        for file in (mp3, ass, folder / "marcacoes-voz.json", stamp):
            file.unlink(missing_ok=True)
    if mp3.is_file() and ass.is_file() and not stamp.is_file():
        if not create:
            raise RuntimeError("Cache de voz sem assinatura do roteiro; use -CriarVoz")
        for file in (mp3, ass, folder / "marcacoes-voz.json"):
            file.unlink(missing_ok=True)
    voice, captions = ensure_voice(item, folder, create=create, voice=VOICE)
    stamp.write_text(digest + "\n", encoding="utf-8")
    return voice, captions


def prepare_cover(ep: dict, item: dict, folder: Path, model: str) -> Path:
    cover = folder / f"{item['id']}-en-US-master-capa.jpg"
    report = master.cover_from_master(ep, model, cover, title_override=item["cover"])
    (folder / "qa-en-cover.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return cover


def assess_character_motion(props: dict, *, strict: bool = False) -> dict:
    """Medir capacidade de camada por cena, sem chamar zoom de animacao."""
    character = [s for s in props.get("scenes", []) if s.get("subject") == "personagens"]
    movable = [s for s in character if s.get("motionCapability") == "character-layer"
               and s.get("movableCharacterLayers", 0) > 0]
    facial = [s for s in character if s.get("motionCapability") == "face-performance"]
    camera_only = [str(s.get("id", "?")) for s in character if s not in movable and s not in facial]
    if strict and camera_only:
        raise ValueError(
            "EN sem movimento independente dos personagens nas cenas: "
            + ", ".join(camera_only)
            + ". Zoom de camera nao substitui animacao; melhorar camadas antes de renderizar."
        )
    return {
        "character_scenes": len(character),
        "character_layer_scenes": len(movable),
        "face_performance_scenes": len(facial),
        "camera_only_character_scene_ids": camera_only,
        "character_motion_verified": not camera_only and bool(character),
        "note": "Camada movel nao garante rigging articulado; verificar video inteiro",
    }


def process(item: dict, action: str, *, profile: str, model: str, overwrite: bool,
            qa_mode: str = "automatico", require_character_motion: bool = False) -> dict:
    episode_id = item["id"]
    # Render ONLY through the local AutoEditorVideo + Remotion engine.
    # External cloud previews are not an acceptable source for this pipeline.
    production = validate_english_production(item, item.get("production"))
    folder = OUT / episode_id / "en-US"
    folder.mkdir(parents=True, exist_ok=True)
    folder.joinpath("metadata-en.json").write_text(
        json.dumps(english_metadata(item), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if action == "planejar":
        if item.get("scenes"):
            plan = ensure_english_plan(item, folder)
            print(f"[EN STORYBOARD] {plan} — cenas e continuidade especificas do roteiro.")
        print(f"[PLANO EN] {episode_id}: {item['title']}; sem IA ou upload.")
        return {"id": episode_id, "status": "planejado"}
    # Generating English voice does not require image assets or a completed storyboard.
    if action == "voz":
        voice, ass = audio_for(item, folder, create=True)
        validate_planned_audio(audio_duration(voice), stage=f"Voz EN {episode_id}")
        print(f"[EN VOZ] {voice} | {ass}")
        return {"id": episode_id, "status": "voz_pronta"}
    # New editorial episodes have their OWN immutable EN storyboard.
    # Older translations continue to reuse approved PT imagery.
    path = (ensure_english_plan(item, folder)
            if item.get("scenes") else production_storyboard(episode_id, 6))
    ep = read_storyboard(path)
    if ep["id"] != episode_id:
        raise ValueError("Storyboard divergente do episodio em ingles")
    review = {"mode": "legacy", "auto_checked": 0, "explicitly_approved": 0}
    if item.get("scenes"):
        ep, review = prepare_qa_storyboard(ep, model, qa_mode)
    if action == "capa":
        cover = prepare_cover(ep, item, folder, model)
        print(f"[EN CAPA] {cover}")
        return {"id": episode_id, "status": "capa_pronta", "cover": str(cover)}
    suffix = ("retention-v2" if item.get("scenes")
              else f"master-multicenas-personagens-v3-{profile}")
    output = folder / f"{episode_id}-en-US-{suffix}.mp4"
    if output.is_file() and not overwrite:
        validate_video(output,stage=f'Cache EN {episode_id}')
        report_file = folder / "qa-en-US.json"
        if item.get("source_br_video_id"):
            if not report_file.is_file():
                raise ValueError("MP4 EN reaproveitado sem QA assinado; use -Refazer.")
            previous = json.loads(report_file.read_text(encoding="utf-8"))
            if (previous.get("video_sha256") != hashlib.sha256(output.read_bytes()).hexdigest()
                    or previous.get("render_origin") != "AutoEditorVideo/local/remotion"
                    or previous.get("language") != "en-US"
                    or previous.get("source_br_video_id") != item["source_br_video_id"]
                    or previous.get("source_pt_script_sha256") != item["source_pt_script_sha256"]):
                raise ValueError("MP4 EN em cache nao corresponde a fonte BR/QA; use -Refazer.")
        if item.get("scenes"):
            if not report_file.is_file():
                raise ValueError("MP4 em cache sem QA EN; use -Refazer.")
            previous = json.loads(report_file.read_text(encoding="utf-8"))
            if previous.get("video_sha256") != hashlib.sha256(output.read_bytes()).hexdigest():
                raise ValueError("MP4 em cache sem assinatura QA correspondente. Use -Refazer.")
        if require_character_motion:
            if not report_file.is_file():
                raise ValueError("MP4 EN em cache sem diagnostico de movimento: use -Refazer.")
            checked = json.loads(report_file.read_text(encoding="utf-8"))
            if not checked.get("character_motion_qa", {}).get("character_motion_verified"):
                raise ValueError("MP4 EN em cache nao passou no modo estrito de personagens; use -Refazer.")
        print(f"[EN CACHE] Ja renderizado: {output} (use -Refazer para substituir)")
        return {"id": episode_id, "status": "cache", "mp4": str(output)}
    # Audio MUST be English and fresh before rendering English subtitles.
    voice, ass = audio_for(item, folder, create=True)
    confirmed = master.validate_scenes(ep, model=model)
    seconds = validate_planned_audio(audio_duration(voice),stage=f'Pre-render EN {episode_id}')
    # Consistent readable word groups for every English render, whether
    # translated from an older episode or built with the new visual storyboard.
    captions = grouped_captions(captions_from_ass(ass, seconds))
    if not captions:
        raise ValueError("Faltam legendas sincronizadas inglesas")
    props = master.build_props(
        ep, voice, captions, seconds, model=model, output=OUT,
        public=MOTION / "public", animation_mode="cinematica",
        character_preset=profile,
        asset_namespace=f"{episode_id}-en-us",
        hook_override=item["cover"],
    )
    motion_qa = assess_character_motion(props, strict=require_character_motion)
    if motion_qa["camera_only_character_scene_ids"]:
        print("[AVISO EN MOVIMENTO] Cenas apenas com camera: " +
              ", ".join(motion_qa["camera_only_character_scene_ids"]) +
              "; nao confundir com animacao do personagem.", flush=True)
    props["language"] = "en-US"
    props["editorialProfile"] = "retention-v2" if item.get("scenes") else "legacy"
    propfile = MOTION / f"props-master-{episode_id}-en-US.json"
    propfile.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not (MOTION / "node_modules").is_dir():
        raise RuntimeError("Instale Remotion: cd motion-remotion; npm.cmd install")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise RuntimeError("Node.js/npm nao encontrado no PATH")
    command = [npm, "run", "render:master", "--", str(output.resolve()),
               "--props", str(propfile.resolve()), "--concurrency", "2"]
    subprocess.run(command, cwd=MOTION, check=True, timeout=1800)
    if not output.is_file() or output.stat().st_size < 100000:
        raise RuntimeError("Remotion finalizou mas nao produziu um MP4 valido")
    actual_seconds = validate_video(output,stage=f'Export EN {episode_id}')
    cover = prepare_cover(ep, item, folder, model)
    report = {
        "id": episode_id,
        "status": ("renderizado_qa_automatico"
                   if item.get("scenes") and qa_mode == "automatico"
                   else "renderizado_aguardando_revisao"),
        "language": "en-US", "voice": VOICE, "video": str(output),
        "cover": str(cover), "duration_s": actual_seconds, "scenes": len(confirmed),
        "captions": len(captions), "published": False,
        "uses_cached_images": True,
        "visual_qa_mode": review["mode"],
        "automatic_technical_qa": review["mode"] == "automatico",
        "manual_approvals_forged": False,
        "manual_approvals": review["explicitly_approved"],
        "video_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "video_qa_description": "Auto technical checks; artistic quality reviewed by creator after upload",
        "production_pipeline": production,
        "render_origin": "AutoEditorVideo/local/remotion",
        "editorial_profile": props["editorialProfile"],
        "source_br_video_id": item.get("source_br_video_id"),
        "source_pt_script_sha256": item.get("source_pt_script_sha256"),
        "english_visual_review_required": bool(item.get("source_br_video_id")),
        "character_motion_qa": motion_qa,
        "require_character_motion": require_character_motion,
        "visual_continuity": "ryuk-reveal-after-beat-9" if item.get("scenes") else "legacy",
    }
    report["visual_review_stage"] = "post_upload_youtube_studio"
    report["visual_review_status"] = "pending"
    (folder / "qa-en-US.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        from organizar_videos_por_canal import refresh_library_after_render
        archive = refresh_library_after_render(ROOT)
        if archive["status"] == "updated":
            print("[BIBLIOTECA EN] Videos sincronizados por canal: " + str(archive["videos"]))
    except (OSError, ValueError) as exc:
        print("[BIBLIOTECA AVISO] MP4 preservado; organize manualmente: " + str(exc))
    print(f"[EN PRONTO] MP4 tecnico criado: {output}. "
          "Avaliacao artistica somente apos upload PRIVADO ao YouTube Studio.")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Renderiza Shorts EN sem novas imagens nem upload")
    parser.add_argument("--acao", choices=("planejar", "voz", "capa", "renderizar"), default="planejar")
    parser.add_argument("--manifesto", default=str(LANG), help="JSON de Shorts EN; padrao: cinco originais")
    parser.add_argument("--id", default="")
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"), default="gpt-image-1.5")
    parser.add_argument("--perfil", choices=("equilibrado", "vivo", "ultrassutil"), default="equilibrado")
    parser.add_argument("--refazer", action="store_true")
    parser.add_argument("--exigir-movimento-personagem", action="store_true",
                        help="Bloqueia cenas com personagens sem camadas moveis reais")
    parser.add_argument("--modo-qa", choices=("automatico","manual"), default="automatico")
    args = parser.parse_args(argv)
    entries = load_english(Path(args.manifesto))
    if args.id:
        entries = [item for item in entries if item["id"] == args.id]
        if not entries:
            parser.error("ID nao encontrado")
    problems = []
    for item in entries:
        try:
            process(item, args.acao, profile=args.perfil, model=args.modelo,
                    overwrite=args.refazer, qa_mode=args.modo_qa,
                    require_character_motion=args.exigir_movimento_personagem)
        except Exception as exc:
            problems.append((item["id"], str(exc)))
            print(f"[EN FALHOU] {item['id']}: {exc}", file=sys.stderr, flush=True)
    print(f"[RESUMO EN] {len(entries) - len(problems)}/{len(entries)} concluidos. "
          "PT intocado; nenhum upload.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
