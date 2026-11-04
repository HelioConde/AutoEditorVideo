#!/usr/bin/env python3
"""Metadados UTF-8 por Short: fonte única para uploads e reparos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conteudos" / "testes-animados-5.json"
RECAPS_MANIFEST = ROOT / "conteudos" / "death-note-recaps-60s.json"
FORMATS_MANIFEST = ROOT / "conteudos" / "death-note-formatos-60s.json"
JUJUTSU_MANIFEST = ROOT / "conteudos" / "jujutsu-kaisen-recaps-60s.json"
GRADE_50_MANIFESTS = (ROOT / "conteudos" / "otaku-multicena-grade-50-a.json",
                      ROOT / "conteudos" / "otaku-multicena-grade-50-b.json")


def load_episodes(path: Path = MANIFEST, *, include_recaps: bool = False) -> dict[str, dict]:
    """Original five by default; opt in to the new recap catalog explicitly.

    The already-published repair workflow must never accidentally treat new
    recaps as part of its fixed five-video historical upload batch.
    """
    sources = [path]
    if include_recaps and path == MANIFEST:
        sources.extend(extra for extra in (RECAPS_MANIFEST, FORMATS_MANIFEST, JUJUTSU_MANIFEST, *GRADE_50_MANIFESTS)
                       if extra.is_file())
    items = []
    for source in sources:
        data = json.loads(source.read_text(encoding="utf-8-sig"))
        for ep in data["episodes"]:
            normalized = dict(ep)
            if not normalized.get("series") and data.get("series"):
                normalized["series"] = data["series"]
            items.append(normalized)
    result = {ep["id"]: ep for ep in items}
    if len(result) != len(items):
        raise ValueError("IDs duplicados no catálogo")
    return result

def description_for(episode: dict) -> str:
    explicit = str(episode.get('description_youtube') or '').strip()
    if explicit:
        if len(explicit) > 5000 or any(marker in explicit for marker in ('Ã¡', 'Ã©', 'Ã§', 'Ã£', '\ufffd')):
            raise ValueError('Descrição explícita inválida ou com caracteres corrompidos')
        return explicit
    series = str(episode["series"]).strip()
    script = str(episode["script"]).strip()
    if not series or not script:
        raise ValueError("Série ou roteiro ausente")
    if episode.get("episode_number"):
        description = (
            f"{series} — episódio {episode['episode_number']} recontado em até 60 segundos. "
            "Uma recapitulação narrativa com spoilers, ilustrações geradas por IA, "
            "narração e edição originais.\n\n"
            f"{script}\n\n"
            "Curtiu a história? Inscreva-se para acompanhar a continuação!\n\n"
            "Análise e adaptação editorial independente, não oficial. "
            "Obra e personagens pertencem aos respectivos titulares.\n\n"
            "#DeathNote #Anime #ResumoDeAnime #Shorts #ArquivoOtaku"
        )
    elif episode.get("format_type") in ("curiosidade", "voce-lembra"):
        category = episode["format_type"]
        opening = ("Curiosidade de anime: um detalhe de Death Note que muda tudo."
                   if category == "curiosidade"
                   else "Você lembra? Vamos reviver Death Note com uma nova narrativa.")
        hashtags = ("#DeathNote #CuriosidadesAnime #Anime #Shorts #ArquivoOtaku"
                    if category == "curiosidade"
                    else "#DeathNote #VoceLembra #NostalgiaAnime #Shorts #ArquivoOtaku")
        description = (
            f"{opening}\n\n{script}\n\n"
            "Comente sua opinião ou lembrança e inscreva-se para mais histórias!\n\n"
            "Imagens geradas por IA, narração, roteiro e edição autorais. "
            "Conteúdo não oficial; obra e personagens pertencem aos respectivos titulares.\n\n"
            + hashtags
        )
    else:
        description = (
            f"Análise e comentário sobre {series}.\n\n"
            f"{script}\n\n"
            "Ilustrações geradas por IA e edição autoral. "
            "A obra e os personagens pertencem aos respectivos titulares.\n\n"
            "#DeathNote #Anime #Shorts #ArquivoOtaku"
        )
    if any(marker in description for marker in ("Ã¡", "Ã©", "Ã§", "Ã£", "\ufffd")):
        raise ValueError("Descrição contém caracteres corrompidos")
    if len(description) > 5000:
        raise ValueError("Descrição muito longa para o YouTube")
    return description


def publisher_episode(episode: dict) -> dict:
    series = str(episode.get("series") or episode.get("serie") or "").strip()
    if not series:
        raise ValueError(
            f"Episódio {episode.get('id', '<sem id>')} sem série: informe "
            "'series' no episódio ou no manifesto."
        )
    title = str(episode["title"]).strip()
    if not 1 <= len(title) <= 100:
        raise ValueError("Título inválido para YouTube")
    return {
        "serie": series,
        "titulo": title,
        "titulo_youtube": title,
        "descricao_youtube": description_for(episode),
        "capa_texto": episode.get("cover", ""),
        "roteiro": episode["script"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Exporta JSON UTF-8 para o publicador")
    parser.add_argument("--id", required=True)
    parser.add_argument("--destino", required=True, type=Path)
    args = parser.parse_args()
    episodes = load_episodes(include_recaps=True)
    if args.id not in episodes:
        parser.error("Episódio não encontrado no manifesto")
    args.destino.parent.mkdir(parents=True, exist_ok=True)
    args.destino.write_text(
        json.dumps(publisher_episode(episodes[args.id]), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[UTF-8] Metadados preparados: {args.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
