"""Quality-mode policy for original English AutoEditorVideo storyboards.

Automatic mode never forges manual approvals. It preserves scene and cache
identity, rejects any explicitly rejected cache, and relies on the project's
PNG/layer/composition checks before render. It does *not* claim subjective
artistic quality certification; creators may review the completed video.
"""
from __future__ import annotations

from copy import deepcopy

from master_scenes import scene_dir
from revisao_visual_cenas import read_review

MODES = ("automatico", "manual")


def prepare_qa_storyboard(plan: dict, model: str, mode: str = "automatico") -> tuple[dict, dict]:
    if mode not in MODES:
        raise ValueError("Modo de QA EN invalido")
    if plan.get("language") != "en-US" or not plan.get("source_script_sha256"):
        raise ValueError("QA automatico restrito a storyboards EN originais assinados.")
    scenes = plan.get("scenes", [])
    if not scenes:
        raise ValueError("Storyboard EN sem cenas.")
    checked = deepcopy(plan)
    explicit_approved = 0
    pending = 0
    for scene in checked["scenes"]:
        folder = scene_dir(plan, scene, model)
        review = read_review(folder)
        if review and review["status"] == "reprovado":
            raise ValueError(
                f"Cena {scene['id']} reprovada no cache {folder.name}; "
                "corrija/regere esta cena antes do render automatico."
            )
        if review and review["status"] == "aprovado":
            explicit_approved += 1
        else:
            pending += 1
            if mode == "manual":
                raise ValueError(
                    f"Cena {scene['id']} aguarda revisao visual manual. "
                    "Use -Acao Revisar ou selecione -ModoQA automatico."
                )
        if mode == "automatico":
            scene.setdefault("correcao_visual", {})["requires_manual_approval"] = False
            scene["correcao_visual"]["automatic_technical_qa"] = True
    return checked, {
        "mode": mode,
        "total_scenes": len(scenes),
        "explicitly_approved": explicit_approved,
        "auto_checked": pending if mode == "automatico" else 0,
        "manual_approvals_forged": False,
    }
