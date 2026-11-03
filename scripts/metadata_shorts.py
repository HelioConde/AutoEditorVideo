#!/usr/bin/env python3
"""Metadados UTF-8 por Short: fonte única para uploads e reparos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conteudos" / "testes-animados-5.json"
RECAPS_MANIFEST = ROOT / "conteudos" / "death-note-recaps-60s.json"


def load_episodes(path: Path = MANIFEST) -> dict[str, dict]:
    sources = [path]
    if path == MANIFEST and RECAPS_MANIFEST.is_file():
        sources.append(RECAPS_MANIFEST)
    items = []
    for source in sources:
        data = json.loads(source.read_text(encoding="utf-8-sig"))
        items.extend(data["episodes"])
    result = {ep["id"]: ep for ep in items}
    if len(result) != len(items):
        raise ValueError("IDs duplicados no catálogo")
    return result


def description_for(episode: dict) -> str:
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
    title = str(episode["title"]).strip()
    if not 1 <= len(title) <= 100:
        raise ValueError("Título inválido para YouTube")
    return {
        "serie": episode["series"],
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
    episodes = load_episodes()
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
