#!/usr/bin/env python3
"""Otaku Multicena: plano offline de distribuicao multiplataforma.

Nao envia videos, nao consulta redes sociais, nao troca trilhas e nao executa IA.
Gera propostas editoriais para revisao humana e verifica MP4 apenas sob demanda.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata

from otaku_growth_v3 import DEFAULT_CATALOGS, audit_episode, read_catalogs, WINDOWS_HOURS

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("ultrassutil", "equilibrado", "vivo")
DISTRIBUTION_PLATFORMS = ("youtube", "instagram", "tiktok", "kwai")
HOOK_APPROACHES = {
    "curiosidade": "Qual detalhe especifico e verificavel chama atencao antes da explicacao?",
    "contradicao": "Que contraste verdadeiro entre expectativa e realidade move a historia?",
    "decisao": "Qual escolha concreta de um personagem mudou as consequencias?",
    "misterio": "Que pergunta o proprio roteiro consegue responder ate o final?",
    "consequencia": "Que resultado inesperado pode ser explicado sem exagero?",
}


def _clean(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _hashtag(series: str) -> str:
    normalized = unicodedata.normalize("NFKD", series)
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = re.sub(r"[^A-Za-z0-9]", "", normalized)
    return "#" + normalized[:45] if normalized else "#Anime"


def _preview_sentence(episode: dict) -> str:
    script = _clean(episode.get("script"))
    hook = _clean(episode.get("hook"))
    cta = _clean(episode.get("cta"))
    if hook and script.casefold().startswith(hook.casefold()):
        script = script[len(hook):].lstrip()
    if cta and script.endswith(cta):
        script = script[:-len(cta)].strip()
    # Parar em uma frase real, nao truncar a narração no meio da palavra.
    first_sentence = re.split(r"(?<=[.!?])\s+", script)[0].strip()
    return first_sentence if first_sentence and len(first_sentence) < 230 else ""


def _render_path(episode_id: str, profile: str, root: Path) -> Path:
    # IDs so podem vir do catalogo, mas nunca aceitar path traversal no output.
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,110}", episode_id):
        raise ValueError("ID invalido para caminho de video")
    return (
        root / "assets" / "gerados" / "shorts-animados" / episode_id /
        f"{episode_id}-master-multicenas-personagens-v3-{profile}.mp4"
    )


def inspect_video(video: Path) -> dict:
    """Somente ffprobe read-only. Duracao 60s e requisito do projeto."""
    result = {"status": "missing", "file": str(video), "issues": []}
    if not video.is_file():
        result["issues"].append("MP4 local ainda nao encontrado")
        return result
    try:
        call = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height",
             "-of", "json", str(video)],
            capture_output=True, text=True, check=True, timeout=20,
        )
        info = json.loads(call.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError, json.JSONDecodeError):
        result["status"] = "unverified"
        result["issues"].append("FFprobe indisponivel, expirou ou retornou dados invalidos")
        return result
    streams = info.get("streams", [])
    vids = [s for s in streams if s.get("codec_type") == "video"]
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    try:
        duration = float(info.get("format", {}).get("duration", 0))
    except (TypeError, ValueError):
        duration = 0
    size = vids[0] if vids else {}
    w, h = int(size.get("width") or 0), int(size.get("height") or 0)
    issues = []
    if not duration or duration > 60:
        issues.append("Duracao invalida: MP4 deve ter no maximo 60 segundos")
    if not w or not h or abs(w / h - 9 / 16) > 0.02:
        issues.append("Video nao esta em formato vertical 9:16")
    if not audio:
        issues.append("Nenhuma faixa de audio detectada")
    result.update({
        "status": "pass" if not issues else "failed",
        "duration_seconds": round(duration, 3),
        "resolution": [w, h],
        "audio_stream_present": bool(audio),
        "issues": issues,
    })
    return result


def make_plan(
    episode: dict, *,
    profile: str = "equilibrado",
    root: Path = ROOT,
    verify_mp4: bool = False,
    tiktok_audio_removed: bool = False,
) -> dict:
    if profile not in PROFILES:
        raise ValueError("Perfil de render invalido")
    audit = audit_episode(episode)
    episode_id = audit["id"]
    if not episode_id:
        raise ValueError("Episodio sem ID")
    series = _clean(episode.get("series"))
    hook = _clean(episode.get("hook"))
    caption_context = _preview_sentence(episode)
    short_context = "\n\n" + caption_context if caption_context else ""
    topic_tag = _hashtag(series)
    tags = f"{topic_tag} #AnimeBrasil #OtakuMulticena"
    video_path = _render_path(episode_id, profile, root)
    media = inspect_video(video_path) if verify_mp4 else {
        "status": "not_checked", "file": str(video_path),
        "issues": ["Executar checagem de MP4 no computador com --verificar-mp4"],
    }
    common_review = [
        "Conferir fidelidade factual e originalidade editorial",
        "Conferir direitos de imagens, personagens, trilha e voz",
        "Verificar movimento de personagens e qualidade do MP4 final",
        "Conferir legenda, volume e pronuncia",
        "Confirmar publicacao apenas com autorizacao explicita",
    ]
    platforms = {
        "youtube": {
            "publication": "no_action",
            "review_status": "metadata_existing_only",
            "title": _clean(episode.get("title")),
            "description": _clean(episode.get("description_youtube")),
            "checks": ["Nao sobrescrever titulo ou descricao de video ja publicado sem aprovacao"],
        },
        "instagram": {
            "publication": "manual_after_review",
            "review_status": "pending",
            "caption_draft": f"{hook}{short_context}\n\n{tags} #Reels",
            "checks": ["Verificar Reels e a elegibilidade do Trial Reels", 
                       "Rever o enquadramento na area segura do aplicativo"],
        },
        "tiktok": {
            "publication": "blocked" if tiktok_audio_removed else "manual_after_review",
            "review_status": "sound_removed" if tiktok_audio_removed else "audio_rights_unverified",
            "caption_draft": f"{hook}\n\n{tags} #TikTokAnime",
            "checks": (
                ["Som removido informado: consultar decisao/recurso no app; NAO reenviar como tentativa de contorno"]
                if tiktok_audio_removed else
                ["Conferir licenca e direitos do audio; verificar avisos oficiais antes de publicar",
                 "Nao presumir que palavras especificas causaram silenciamento"]
            ),
        },
        "kwai": {
            "publication": "manual_after_review",
            "review_status": "integration_not_configured",
            "caption_draft": f"{hook}{short_context}\n\n{tags}",
            "checks": ["Confirmar a identidade da conta e as diretrizes vigentes no Kwai",
                       "Nao afirmar que existe automacao oficial configurada"],
        },
    }
    return {
        "id": episode_id,
        "series": series,
        "schema": "otaku-multicena/multiplatform-plan/v3",
        "mode": "offline_proposal_only",
        "automated_publications": 0,
        "story": {"hook": hook, "retention_promise": "Entregar a curiosidade ou conflito anunciado",
                  "hook_review_prompts": HOOK_APPROACHES},
        "editorial_blocking_issues": [i for i in audit["issues"] if i["severity"] == "blocking"],
        "media": media,
        "requires_manual_review": common_review,
        "metrics_collection_hours": list(WINDOWS_HOURS),
        "platforms": platforms,
        "notes": ["Nao confundir numero de visualizacoes com retencao",
                  "Planos de distribuicao nao autorizam publicacao nem mudanca de audio",
                  "Caption e proposta editorial, nao texto ja aprovado"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Otaku Multicena 3.0: plano multiplataforma offline")
    ap.add_argument("--id", action="append", required=True, help="ID do episodio (repetivel)")
    ap.add_argument("--perfil", choices=PROFILES, default="equilibrado")
    ap.add_argument("--verificar-mp4", action="store_true", help="Somente inspecionar MP4 por FFprobe")
    ap.add_argument("--tiktok-som-removido", action="store_true",
                    help="Marcar TikTok bloqueado por remocao de audio ja informada")
    ap.add_argument("--saida", type=Path, help="Salvar proposta JSON local")
    args = ap.parse_args(argv)
    episodes = read_catalogs(list(DEFAULT_CATALOGS))
    selected = {ep["id"]: ep for ep in episodes if ep.get("id") in args.id}
    missing = set(args.id) - set(selected)
    if missing:
        ap.error("IDs nao encontrados: " + ", ".join(sorted(missing)))
    results = [
        make_plan(selected[ep_id], profile=args.perfil, verify_mp4=args.verificar_mp4,
                  tiktok_audio_removed=args.tiktok_som_removido)
        for ep_id in dict.fromkeys(args.id)
    ]
    report = {
        "schema": "otaku-multicena/multiplatform-campaign/v3",
        "mode": "offline_proposal_only",
        "automated_publications": 0,
        "episodes": results,
        "summary": {"episodes": len(results), "platforms": list(DISTRIBUTION_PLATFORMS),
                    "tiktok_blocked": sum(
                        p["platforms"]["tiktok"]["publication"] == "blocked" for p in results
                    )},
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(output, encoding="utf-8")
        print("[OFFLINE] Plano salvo em " + str(args.saida))
    else:
        print(output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print("[BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
