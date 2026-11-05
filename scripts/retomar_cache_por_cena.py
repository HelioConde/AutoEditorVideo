#!/usr/bin/env python3
"""Retoma caches de um Short cena por cena, com teto total de IA.

Nao faz upload e nunca associa automaticamente caches de hashes ou modelos diferentes.
Com --max-chamadas 0: diagnostico somente leitura.
Com N > 0: avanca somente em cenas que cabem no limite restante,
reconstroi artefatos derivados das respostas ja em cache e interrompe ao
esgotar o teto, preservando os trabalhos ja concluidos.

Status 0 = completo; 2 = pendente; 1 = falha de uma cena.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from master_scenes import (
    estimate,
    production_storyboard,
    read_storyboard,
    scene_dir,
    validate_cache_pin,
)

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts" / "master_scenes.py"
DERIVED = ("master.png", "foreground.png", "background.png", "qa.json")


def describe_scene(plan: dict, scene: dict, model: str) -> tuple[list[str], list[str]]:
    pending = estimate(plan, [scene], model)
    directory = scene_dir(plan, scene, model)
    derived_missing = [filename for filename in DERIVED
                       if not (directory / filename).is_file()]
    return pending, derived_missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retoma imagens por cena, com limite TOTAL")
    parser.add_argument("--id", required=True)
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"),
                        default="gpt-image-2")
    parser.add_argument("--max-chamadas", type=int, default=0)
    args = parser.parse_args(argv)
    if not 0 <= args.max_chamadas <= 180:
        parser.error("Maximo de 0 a 180 chamadas")

    pinned = production_storyboard(args.id, 6.0)
    plan = read_storyboard(pinned)
    if plan["id"] != args.id:
        raise ValueError("O storyboard pertence a outro episodio")
    scenes = plan["scenes"]
    pending_total = sum(len(estimate(plan, [s], args.modelo)) for s in scenes)
    print(f"[ORCAMENTO] {args.id}: {pending_total} chamadas de imagem estimadas "
          f"para {len(scenes)} cenas; limite desta execucao: "
          f"{args.max_chamadas}.", flush=True)
    for scene in scenes:
        pending, derived = describe_scene(plan, scene, args.modelo)
        if pending or derived:
            print(f"[CENA {scene['id']}] IA pendente: {len(pending)}; "
                  f"arquivos derivados pendentes: {', '.join(derived) or 'nenhum'}",
                  flush=True)
            for stage in pending:
                print(f"  [PENDENTE] {stage}", flush=True)

    if args.max_chamadas == 0:
        print("[DIAGNOSTICO] Nenhuma imagem gerada, nenhum upload realizado.",
              flush=True)
        return 0 if pending_total == 0 and all(
            not describe_scene(plan, s, args.modelo)[1] for s in scenes
        ) else 2

    # Validar pins antes de qualquer pedido de IA.
    for scene in scenes:
        validate_cache_pin(plan, scene, args.modelo)

    remaining = args.max_chamadas
    for scene in scenes:
        pending, derived = describe_scene(plan, scene, args.modelo)
        count = len(pending)
        if count == 0 and not derived:
            continue
        if count > remaining:
            print(f"[ADIADA] Cena {scene['id']}: precisa {count} chamada(s), "
                  f"sobram {remaining} no limite. Nenhuma chamada para esta cena.",
                  flush=True)
            continue
        print(f"[RETOMANDO] Cena {scene['id']} | chamadas previstas {count} "
              f"| saldo autorizado {remaining}.", flush=True)
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--id", args.id,
             "--modelo", args.modelo, "--cena", str(int(scene["id"])),
             "--max-chamadas", str(count)],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            print(f"[INTERROMPIDO] Falha na cena {scene['id']}. "
                  "Arquivos anteriores preservados. Nenhum upload.",
                  file=sys.stderr, flush=True)
            return 1
        remaining -= count
        # Nao continuar se uma cena nao produziu os artefatos esperados.
        still_pending, still_derived = describe_scene(plan, scene, args.modelo)
        if still_pending or still_derived:
            print(f"[QA PENDENTE] Cena {scene['id']} continua incompleta. "
                  "Inspecione o diagnostico antes de tentar novamente.",
                  file=sys.stderr, flush=True)
            return 1

    missing = sum(len(estimate(plan, [s], args.modelo)) for s in scenes)
    unbuilt = [(s["id"], describe_scene(plan, s, args.modelo)[1])
               for s in scenes
               if describe_scene(plan, s, args.modelo)[1]]
    print(f"[RESUMO CACHE] chamadas autorizadas nao utilizadas: {remaining}; "
          f"etapas de IA pendentes: {missing}; "
          f"cenas com artefatos incompletos: {len(unbuilt)}.", flush=True)
    if missing or unbuilt:
        print("[PARCIAL] Pode retomar executando novamente com novo limite "
              "autorizado; cache ja produzido permanece salvo. Sem upload.",
              flush=True)
        return 2
    print("[CACHE COMPLETO] As cenas estao prontas para validacao e render EN.",
          flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print("[ERRO CACHE] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
