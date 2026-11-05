#!/usr/bin/env python3
"""Valida MP4 BR de um Short da grade 50, sem gerar imagens nem publicar.

Chamado por lote2-otaku-3br-3en.ps1 via caminho de arquivo para evitar
problemas de aspas do PowerShell 5.1 com 'python -c'.
"""
from __future__ import annotations

import argparse
import sys

from grade_50_shorts import ensure_ready, load_queue


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA local BR para upload privado do lote 2")
    parser.add_argument("--id", required=True)
    parser.add_argument("--perfil", choices=("equilibrado", "vivo", "ultrassutil"),
                        default="equilibrado")
    parser.add_argument("--exigir-movimento-personagem", action="store_true")
    args = parser.parse_args(argv)

    matching = [episode for episode in load_queue() if episode["id"] == args.id]
    if len(matching) != 1:
        parser.error("Episodio nao existe ou esta duplicado na grade: " + args.id)
    video = ensure_ready(
        matching[0],
        args.perfil,
        require_character_motion=args.exigir_movimento_personagem,
    )
    print(f"[QA BR APROVADO] {args.id} | MP4: {video}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print("[QA BR BLOQUEADO] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
