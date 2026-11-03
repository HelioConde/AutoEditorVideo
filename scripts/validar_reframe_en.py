#!/usr/bin/env python3
"""Offline quality gate before any English AutoEditorVideo/Remotion render.

Reads ONLY local EN storyboard, generated PNGs, visual-review files, and Edge
TTS audio/subtitles. No image generation, external rendering, or YouTube upload.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from master_scenes import read_storyboard, scene_dir
from revisao_visual_cenas import read_review
import renderizar_master_remotion as master
from renderizar_com_remotion import audio_duration, captions_from_ass
from renderizar_shorts_en import audio_for, load_english
from english_caption_design import grouped_captions
from otaku_reframe_direction import ensure_english_plan
from shorts_duration import validate_planned_audio
from qa_automatico_reframe_en import prepare_qa_storyboard


def require_approved_scenes(plan: dict, model: str) -> int:
    count = 0
    for scene in plan["scenes"]:
        path = scene_dir(plan, scene, model)
        review = read_review(path)
        if not review or review.get("status") != "aprovado":
            raise ValueError(
                "Cena " + str(scene["id"]) + " ainda nao aprovada manualmente. "
                "Confira master.png, comparacao.jpg, foreground/background. "
                "Use .\\gerar-otaku-reframe.ps1 -Acao Revisar -Id " + plan["id"] +
                " -Manifesto <manifesto-EN> para analisar e decidir uma cena "
                "de cada vez; a aprovacao nunca e automatica."
            )
        count += 1
    return count


def validate_item(item: dict, model: str, *, mode: str = 'automatico', out: Path | None = None) -> dict:
    if not item.get("scenes"):
        raise ValueError("Esta validacao estrita exige storyboard EN original.")
    folder = (out or ROOT / "assets" / "gerados" / "shorts-animados") / item["id"] / "en-US"
    path = ensure_english_plan(item, folder)
    plan = read_storyboard(path)
    if plan["id"] != item["id"]:
        raise ValueError("Storyboard EN divergente.")
    if mode == "manual":
        require_approved_scenes(plan, model)
    checked, review = prepare_qa_storyboard(plan, model, mode)
    qa_results = master.validate_scenes(checked, model=model)
    if len(qa_results) != len(plan["scenes"]):
        raise ValueError("QA de imagem nao conferiu todos os planos.")
    voice, ass = audio_for(item, folder, create=False)
    seconds = validate_planned_audio(audio_duration(voice), stage="Voice EN preflight")
    captions = grouped_captions(captions_from_ass(ass, seconds))
    if not captions:
        raise ValueError("Legendas WordBoundary EN ausentes.")
    return {
        "id": item["id"],
        "status": "pronto_para_render_local",
        "verified_visual_shots": len(qa_results),
        "manual_approvals": review["explicitly_approved"],
        "automatic_technical_qa": mode == "automatico",
        "manual_approvals_forged": False,
        "visual_qa_mode": mode,
        "captions": len(captions),
        "audio_duration_s": round(seconds, 3),
        "renderer": "AutoEditorVideo/Remotion",
        "youtube_published": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA EN local; nao gera nem publica")
    parser.add_argument("--manifesto", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--modo-qa", choices=("automatico","manual"), default="automatico")
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"),
                        default="gpt-image-1.5")
    args = parser.parse_args(argv)
    chosen = [ep for ep in load_english(args.manifesto) if ep["id"] == args.id]
    if len(chosen) != 1:
        raise ValueError("Episodio EN nao encontrado no manifesto.")
    result = validate_item(chosen[0], args.modelo, mode=args.modo_qa)
    print(
        "[EN QA TECNICO] {verified_visual_shots} cenas verificadas, {captions} legendas, "
        "voz {audio_duration_s:.2f}s. Modo {visual_qa_mode}. "
        "Nao certifica a qualidade artistica; render via {renderer}.".format(**result),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, FileNotFoundError) as exc:
        print("[EN QA BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
