#!/usr/bin/env python3
"""Review English AutoEditorVideo shots interactively, one exact cache at a time.

Opens the already-generated local comparacao.jpg/master.png with the Windows
default image viewer. Explicit keyboard confirmation for EVERY shot is required;
never mass-approves and never generates images, renders, or uploads.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from master_scenes import read_storyboard, scene_dir
from revisao_visual_cenas import read_review, write_review


def review_rows(plan: dict, model: str) -> list[dict]:
    result = []
    for scene in plan["scenes"]:
        folder = scene_dir(plan, scene, model)
        comparison = folder / "comparacao.jpg"
        master = folder / "master.png"
        current = read_review(folder)
        result.append({
            "id": str(scene["id"]),
            "status": current["status"] if current else "pendente",
            "folder": folder,
            "comparison": comparison,
            "master": master,
            "missing": [p.name for p in (master, comparison) if not p.is_file()],
            "scene": scene,
        })
    return result


def perform_review(row: dict, *, opener=None, input_func=input) -> str:
    """Requires a displayed comparison, then typed case-specific confirmation."""
    if row["missing"]:
        raise FileNotFoundError(
            f"Cena {row['id']}: faltam {', '.join(row['missing'])}. "
            "Confira -Acao Diagnosticar; nao aprove um cache incompleto."
        )
    opener = opener or (os.startfile if os.name == "nt" else None)
    if opener is None:
        raise RuntimeError("Revisao com abertura automatica requer Windows.")
    opener(str(row["comparison"]))
    opener(str(row["master"]))
    print(f"[REVISAO] Cena {row['id']} — confira composicao, mãos, rostos, "
          "texto, personagens e fundo.", flush=True)
    print(f"[IMAGENS] {row['comparison']} | {row['master']}", flush=True)
    print("Digite APROVAR " + row["id"] + " ou REPROVAR " + row["id"] +
          " somente APOS olhar as imagens. PULAR ou SAIR nao muda o cache.", flush=True)
    command = input_func("> ").strip().upper()
    if command in ("SAIR", "Q"):
        return "sair"
    if command in ("PULAR", "P", ""):
        return "pular"
    if command == "APROVAR " + row["id"]:
        reason = input_func("Descreva brevemente o que verificou: ").strip()
        if len(reason) < 6:
            print("[PENDENTE] Justificativa insuficiente; nenhuma aprovacao registrada.")
            return "pular"
        write_review(row["folder"], status="aprovado", reason=reason)
        print("[APROVADO] " + row["id"])
        return "aprovado"
    if command == "REPROVAR " + row["id"]:
        reason = input_func("Qual defeito visual deve ser corrigido? ").strip()
        if len(reason) < 6:
            print("[PENDENTE] Especifique o defeito; nenhuma reprovacao registrada.")
            return "pular"
        write_review(row["folder"], status="reprovado", reason=reason)
        print("[REPROVADO] " + row["id"] + " — cache preservado.")
        return "reprovado"
    print("[PENDENTE] Comando nao reconhecido: nenhuma cena aprovada.")
    return "pular"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Revisar imagens EN locais; nao faz upload")
    parser.add_argument("--plano", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"),
                        default="gpt-image-1.5")
    parser.add_argument("--acao", choices=("listar", "revisar"), default="revisar")
    parser.add_argument("--incluir-aprovadas", action="store_true")
    args = parser.parse_args(argv)
    plan = read_storyboard(args.plano)
    if plan["id"] != args.id or plan.get("language") != "en-US":
        raise ValueError("Plano nao corresponde ao Short EN solicitado.")
    rows = review_rows(plan, args.modelo)
    print(f"[EN REVISAO] {len(rows)} cenas no storyboard; nenhuma geracao de IA ou upload.")
    for row in rows:
        print(f"  {row['id']}: {row['status']}" +
              (f" [AUSENTE: {', '.join(row['missing'])}]" if row["missing"] else ""))
    if args.acao == "listar":
        return 0
    if os.name != "nt":
        raise RuntimeError("Revisao interativa precisa do visualizador de imagens do Windows.")
    for row in rows:
        if row["status"] == "aprovado" and not args.incluir_aprovadas:
            continue
        response = perform_review(row)
        if response == "sair":
            break
    refreshed = review_rows(plan, args.modelo)
    approved = sum(r["status"] == "aprovado" for r in refreshed)
    rejected = sum(r["status"] == "reprovado" for r in refreshed)
    print(f"[EN RESUMO] {approved}/{len(refreshed)} aprovadas, {rejected} reprovadas, "
          f"{len(refreshed)-approved-rejected} pendentes. Sem render/upload.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
        print("[EN REVISAO BLOQUEADA] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
