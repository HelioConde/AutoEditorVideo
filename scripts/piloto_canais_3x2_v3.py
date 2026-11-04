#!/usr/bin/env python3
"""Piloto de dois novos canais: 3 Shorts games + 3 Kids.

Validador e preparador 100% offline. NAO gera MP4, imagens ou voz,
NAO executa login/upload e NAO considera storyboard um video pronto.
Os IDs e nomes dos novos canais ainda nao foram configurados.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conteudos" / "piloto-games-kids-3x2-v3.json"
OUTPUT = ROOT / "assets" / "gerados" / "piloto-canais-v3" / "preparacao"
VALID_TYPES = ("curiosity", "contradiction", "decision", "mystery", "consequence")
KIDS_BLOCKED = (
    "comente", "comentário", "comentarios", "inscreva", "se inscreva",
    "curta o vídeo", "deixa o like", "compartilhe", "sininho",
    "clique no link", "compre", "promoção", "me siga",
)
CHANNEL_IDS = ("games", "kids")
ID_PATTERN = re.compile(r"^(game|kids)-[0-9]{3}-[a-z0-9-]+$")
SAFE_PATH = re.compile(r"^[a-zA-Z0-9_/-]+(?:[.]mp4)?$")
REQUIRED_SCENE = (
    "id", "start_s", "end_s", "narration", "visual", "physical_action",
    "on_screen_text", "character_motion", "camera_motion", "continuity",
    "transition", "sound", "asset_source", "required_asset",
)


def load_manifest(path: Path = MANIFEST) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    validate(data)
    return data


def validate(data: dict) -> None:
    """Checks objective invariants, not artistic quality or growth forecasts."""
    if data.get("schema") != "piloto-canais/games-kids/shorts-v3.0":
        raise ValueError("Manifesto de canais 3x2 nao reconhecido")
    if data.get("upload_enabled") is not False or data.get("no_automatic_publication") is not True:
        raise ValueError("Upload deve permanecer desativado no piloto")
    if data.get("language") != "pt-BR":
        raise ValueError("Os seis roteiros devem estar em portugues brasileiro")
    channels = data.get("channels")
    if not isinstance(channels, list) or [c.get("id") for c in channels] != list(CHANNEL_IDS):
        raise ValueError("Exigir exatamente os canais games e kids, separados")
    all_ids = set()
    for channel in channels:
        channel_id = channel["id"]
        children = channel_id == "kids"
        if channel.get("youtube_channel_id") is not None:
            raise ValueError("IDs dos novos canais ainda nao foram verificados; nao usar conta existente")
        if channel.get("directed_to_children") is not children:
            raise ValueError("Configuracao do publico invalida: " + channel_id)
        if channel.get("default_made_for_kids") is not children:
            raise ValueError("Kids deve ser Made for Kids; games nao e por padrao")
        if channel.get("privacy_default") != "private":
            raise ValueError("Piloto deve permanecer privado ate aprovacao")
        if channel.get("name_status") != "provisorio":
            raise ValueError("Nomes ainda sao provisórios, nao perfis criados")
        episodes = channel.get("episodes")
        if not isinstance(episodes, list) or len(episodes) != 3:
            raise ValueError("Exatamente tres Shorts por canal")
        for ep in episodes:
            ep_id = ep.get("id", "")
            if not ID_PATTERN.fullmatch(ep_id) or not ep_id.startswith("kids-" if children else "game-"):
                raise ValueError("ID de Short fora do seu canal: " + str(ep_id))
            if ep_id in all_ids:
                raise ValueError("IDs repetidos entre os canais")
            all_ids.add(ep_id)
            if not 1 <= len(ep.get("title", "")) <= 100:
                raise ValueError("Titulo fora do limite YouTube: " + ep_id)
            if not ep.get("cover") or not ep.get("description_youtube") or not ep.get("tags"):
                raise ValueError("Metadados incompletos: " + ep_id)
            variants = ep.get("hook_options")
            if not isinstance(variants, dict) or set(variants) != set(VALID_TYPES):
                raise ValueError("Cinco estilos de gancho necessarios: " + ep_id)
            if len(set(variants.values())) != 5:
                raise ValueError("As cinco opcoes de gancho nao podem ser repetidas: " + ep_id)
            hook, script = ep.get("hook", ""), ep.get("script", "")
            if hook != ep.get("narration_beats", [""])[0] or not script.startswith(hook):
                raise ValueError("Hook precisa ser a primeira fala: " + ep_id)
            beats = ep.get("narration_beats")
            if not isinstance(beats, list) or len(beats) != 5 or " ".join(beats) != script:
                raise ValueError("Roteiro narrativo nao coincide com cinco cenas: " + ep_id)
            scenes = ep.get("scenes")
            if not isinstance(scenes, list) or len(scenes) != 5:
                raise ValueError("Storyboard deve ter cinco cenas: " + ep_id)
            expected_duration = 28 if children else 38
            if ep.get("planned_duration_seconds") != expected_duration:
                raise ValueError("Duracao planejada invalida: " + ep_id)
            if children:
                all_text = " ".join((ep["script"], ep["description_youtube"], ep["title"])).casefold()
                if any(word in all_text for word in KIDS_BLOCKED):
                    raise ValueError("Kids nao deve pedir comentarios, likes ou inscricoes: " + ep_id)
                if ep.get("footage_origin") != "original_vector_animation" or not ep.get("intended_learning"):
                    raise ValueError("Kids precisa de conteudo educativo original: " + ep_id)
            elif ep.get("footage_origin") != "recorded_gameplay_required":
                raise ValueError("Gameplay precisa de captura real: " + ep_id)
            previous = 0
            for idx, scene in enumerate(scenes):
                missing = [x for x in REQUIRED_SCENE if x not in scene]
                if missing:
                    raise ValueError("Campos de cena ausentes: " + ep_id + " " + ",".join(missing))
                if scene["id"] != f"{idx+1:02d}" or scene["narration"] != beats[idx]:
                    raise ValueError("Sequencia e narracao devem coincidir: " + ep_id)
                start, end = scene["start_s"], scene["end_s"]
                if start != previous or not start < end:
                    raise ValueError("Cenas precisam de tempos continuos: " + ep_id)
                previous = end
                if idx == 0 and end > 3:
                    raise ValueError("Primeiro hook precisa comecar nos primeiros 3s: " + ep_id)
                if children:
                    if scene["asset_source"] != "original_procedural_vector" or scene["required_asset"] is not None:
                        raise ValueError("Kids requer composicao original, nao gameplay: " + ep_id)
                    if scene["camera_motion"].casefold().strip() not in ("fixa", "câmera fixa", "camera fixa"):
                        raise ValueError("Camera Kids deve ser estavel e confortavel: " + ep_id)
                else:
                    if scene["asset_source"] != "captured_real_gameplay":
                        raise ValueError("Jogo sem gameplay verificado: " + ep_id)
                    relative = scene["required_asset"]
                    expected = (
                        f"assets/gerados/piloto-canais-v3/capturas/{ep_id}/"
                        f"cena-{scene['id']}.mp4"
                    )
                    if relative != expected:
                        raise ValueError("Caminho da captura nao confere com episodio: " + ep_id)
            if previous != expected_duration:
                raise ValueError("Storyboard nao fecha na duracao planejada: " + ep_id)
    if len(all_ids) != 6:
        raise ValueError("O piloto deve ter exatamente seis roteiros")


def selected(data: dict, *, channel_name: str = "ambos", episode_id: str = "") -> list[tuple[dict, dict]]:
    rows = [
        (c, ep) for c in data["channels"] if channel_name in ("ambos", c["id"])
        for ep in c["episodes"] if not episode_id or ep["id"] == episode_id
    ]
    if not rows:
        raise ValueError("Nenhum Short corresponde a selecao")
    return rows


def export_metadata(channel: dict, ep: dict) -> dict:
    kids = channel["id"] == "kids"
    return {
        "title": ep["title"],
        "description": ep["description_youtube"],
        "tags": ep["tags"],
        "category": "27" if kids else "20",  # Education / Gaming
        "defaultLanguage": "pt-BR",
        "defaultAudioLanguage": "pt-BR",
        "selfDeclaredMadeForKids": kids,
        "privacyStatus": "private",
        "channel_id": None,  # Target must be configured and verified separately.
        "channel_name_provisional": channel["name"],
        "status": "rascunho_nao_aprovado",
    }


def inspect_episode(channel: dict, ep: dict, root: Path = ROOT) -> dict:
    """Only checks what exists on disk; no capture, render or upload."""
    base = root / "assets" / "gerados" / "piloto-canais-v3" / channel["id"] / ep["id"]
    clips = []
    if channel["id"] == "games":
        for scene in ep["scenes"]:
            path = root / scene["required_asset"]
            clips.append({"scene": scene["id"], "found": path.is_file(), "path": str(path)})
    mp4 = base / "final.mp4"
    voice = base / "narracao.mp3"  # Mesmo formato produzido por produzir_piloto_canais_v3.py
    review = base / "revisao-manual.json"
    return {
        "episode": ep["id"],
        "channel": channel["id"],
        "source_captures": clips,
        "sources_available": all(c["found"] for c in clips) if clips else False,
        "voice_file_present": voice.is_file(),
        "final_video_present": mp4.is_file(),
        "final_video": str(mp4),
        "manual_review_present": review.is_file(),
        "youtube_channel_id_verified": False,
        "upload_ready": False,
        "blockers": [
            "Canal YouTube ainda nao configurado/verificado",
            "Revisao audiovisual e direitos exigida antes de publicar",
            *(
                ["Gameplay real ausente em ao menos uma cena"]
                if channel["id"] == "games" and not all(c["found"] for c in clips)
                else []
            ),
            *(
                ["Animacao original Kids ainda nao exportada"]
                if channel["id"] == "kids" and not mp4.is_file()
                else []
            ),
        ],
    }


def verify_video(video: Path) -> dict:
    if not video.is_file() or video.stat().st_size < 100_000:
        return {"technical_status": "missing_or_incomplete"}
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height", "-of", "json", str(video)],
            capture_output=True, text=True, timeout=30, check=True,
        )
        info = json.loads(p.stdout)
        v = next((stream for stream in info["streams"] if stream["codec_type"] == "video"), None)
        a = any(stream["codec_type"] == "audio" for stream in info["streams"])
        duration = float(info.get("format", {}).get("duration", 0))
        width, height = int(v["width"]), int(v["height"])
        problems = []
        if not 0 < duration <= 60:
            problems.append("duracao_fora_de_60s")
        if not a:
            problems.append("sem_audio")
        if abs(width / height - (9 / 16)) > .02:
            problems.append("nao_vertical_9_por_16")
        return {
            "technical_status": "failed" if problems else "passed",
            "duration": duration, "resolution": [width, height], "problems": problems,
            "artistic_and_rights_review": "not_verified",
        }
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError, StopIteration, ZeroDivisionError):
        return {"technical_status": "unverified", "problems": ["ffprobe_invalid_or_missing"]}


def prepare(data: dict, rows: list[tuple[dict, dict]], output: Path) -> dict:
    prepared = []
    for channel, ep in rows:
        package = output / channel["id"] / ep["id"]
        package.mkdir(parents=True, exist_ok=True)
        metadata = export_metadata(channel, ep)
        item = {
            "schema": "piloto-canais/production-ticket/v3",
            "episode_id": ep["id"],
            "channel": channel["id"],
            "expected_channel_id": None,
            "made_for_kids": channel["default_made_for_kids"],
            "title": ep["title"],
            "five_hooks": ep["hook_options"],
            "script": ep["script"],
            "storyboard": ep["scenes"],
            "provisional_timing": True,
            "production_status": "awaiting_real_gameplay_and_render" if channel["id"] == "games"
                                 else "awaiting_original_animation_and_render",
            "manual_gates": data["mandatory_gates"],
            "metadata": metadata,
            "upload_authorized": False,
        }
        (package / "pacote.json").write_text(
            json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        prepared.append({"id": ep["id"], "package": str(package / "pacote.json")})
    return {"packages_prepared": len(prepared), "files": prepared, "videos_rendered": 0, "uploads": 0}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Piloto 3x2: roteiro e QA offline de Games e Kids")
    p.add_argument("--acao", choices=("validar", "preparar", "inspecionar", "verificar-video"),
                   default="validar")
    p.add_argument("--canal", choices=("ambos", "games", "kids"), default="ambos")
    p.add_argument("--id", default="")
    p.add_argument("--manifesto", type=Path, default=MANIFEST)
    p.add_argument("--saida", type=Path, default=OUTPUT)
    args = p.parse_args(argv)
    data = load_manifest(args.manifesto)
    rows = selected(data, channel_name=args.canal, episode_id=args.id)
    base = {
        "schema": "piloto-canais/preflight/v3", "channels": sorted({c["id"] for c, _ in rows}),
        "episodes": [ep["id"] for _, ep in rows],
        "made_for_kids": {c["id"]: c["default_made_for_kids"] for c, _ in rows},
        "channel_accounts_configured": False,
        "uploads": 0,
    }
    if args.acao == "preparar":
        base.update(prepare(data, rows, args.saida))
    elif args.acao in ("inspecionar", "verificar-video"):
        base["media"] = [inspect_episode(c, ep) for c, ep in rows]
        if args.acao == "verificar-video":
            for media in base["media"]:
                media["ffprobe"] = verify_video(Path(media["final_video"]))
    else:
        base["validation"] = "passed_objective_checks_only"
    print(json.dumps(base, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as err:
        print("[BLOQUEADO] " + str(err), file=sys.stderr)
        raise SystemExit(1)
