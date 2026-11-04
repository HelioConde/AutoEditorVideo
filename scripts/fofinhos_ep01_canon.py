#!/usr/bin/env python3
"""Read-only continuity audit and guard for the approved Fofinhos EP01 Part 1.

The original 9-beat/under-60s short remains an archival draft. It is not the
creator-approved 15-scene narration. Never silently synthesize or render it.
No private files, image generation, uploads or external services.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANON = Path("conteudos/fofinhos-ep01-parte01-narracao-aprovada-v1.json")
MANIFEST = Path("conteudos/kids-emanuelly-ep01-shortserie-v1.json")


def normalize(text: str) -> str:
    return " ".join(text.split())


def read_canon(root: Path = ROOT) -> dict:
    data = json.loads((root / CANON).read_text(encoding="utf-8"))
    if data.get("schema") != "fofinhos/approved-narration-visual-v1":
        raise ValueError("Documento de narracao Fofinhos nao reconhecido")
    if data.get("series") != "Fofinhos":
        raise ValueError("Marca Fofinhos incorreta")
    scenes = data.get("scenes", [])
    if len(scenes) != 15 or [s.get("index") for s in scenes] != list(range(1, 16)):
        raise ValueError("Parte 1 aprovada exige 15 cenas na ordem")
    for scene in scenes:
        if not normalize(scene.get("spoken_text", "")):
            raise ValueError("Cena aprovada sem fala")
        if scene.get("background", "").split("-")[0] not in ("jardim", "quarto"):
            raise ValueError("Cenario inexistente")
        if not scene.get("visual_cue") or not scene.get("forbidden"):
            raise ValueError("Cena sem contrato de continuidade")
    expected_pauses = {4: 1.0, 6: .8, 14: 1.8}
    if {p["after_scene"]: p["seconds"] for p in data.get("pauses", [])} != expected_pauses:
        raise ValueError("Pausas aprovadas foram modificadas")
    for index in range(2, 10):
        scene = scenes[index]
        if scene["egg_location"] != "entre_flores":
            raise ValueError(f"Ovo deve ficar entre flores na cena {index+1}")
        if not scene["background"].startswith("jardim"):
            raise ValueError(f"Cena {index+1}: ovo saiu do jardim antes de ser pego")
    if scenes[6]["spoken_text"] != "E viu aquele lindo ovo azul brilhando entre as flores.":
        raise ValueError("Fala fundamental das flores foi alterada")
    if not scenes[6]["forbidden"].startswith("PROIBIDO ovo no caminho"):
        raise ValueError("Bloqueio de ovo no caminho removido")
    if any(s["night"] for s in scenes[:12]) or not all(s["night"] for s in scenes[12:]):
        raise ValueError("Dia/noite incoerentes com narração")
    if any(s["background"].startswith("quarto") for s in scenes[:10]):
        raise ValueError("Emanuelly nao vai para o quarto antes de levar o ovo")
    if not all(s["background"].startswith("quarto") for s in scenes[10:]):
        raise ValueError("Cenas finais devem ocorrer no mesmo quarto")
    if scenes[14]["egg_location"] != "caminha_quarto":
        raise ValueError("Final deve mostrar ovo fechado na caminha")
    return data


def approved_text(root: Path = ROOT) -> str:
    return normalize(" ".join(s["spoken_text"] for s in read_canon(root)["scenes"]))


def compare_short_draft(root: Path = ROOT) -> dict:
    canon = read_canon(root)
    shorts = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    part = shorts["parts"][0]
    aligned = normalize(part["narration"]) == approved_text(root)
    return {
        "schema": "fofinhos/continuity-audit-v1",
        "official_series": "Fofinhos",
        "approved_scene_count": len(canon["scenes"]),
        "legacy_short_scene_count": len(part["segments"]),
        "legacy_script_matches_approved": aligned,
        "legacy_part1_render_authorized": aligned,
        "egg_required_location": "entre_flores_fora_do_caminho",
        "human_approval_required": True,
        "approved_source": str(CANON),
        "instructions": (
            "Nao gerar ou renderizar a Parte 1 antiga. Adaptar a narracao integral "
            "para duracao real; se exceder 60s, dividir editorialmente sem cortar "
            "falas nem revelar Fofinho antes da Parte 2."
            if not aligned else "Conferir montagem visual e duracao da narracao."
        ),
        "uploads": 0,
    }


def ensure_approved_script(part: dict, root: Path = ROOT) -> None:
    """Block accidental voice/image/render production from obsolete Part 1.

    Temporary isolated fixtures lacking the canonical file are exempt; these
    tests never use the creator's private Windows directory or approved media.
    """
    if part.get("part") != 1 or not (root / CANON).is_file():
        return
    if normalize(part.get("narration", "")) != approved_text(root):
        raise ValueError(
            "FOFINHOS: Parte 1 ainda usa a narracao ANTIGA de 9 trechos. "
            "A versao aprovada tem 15 cenas e esta em " + str(CANON) + ". "
            "NAO gerar voz, imagens de cena nem renderizar o roteiro antigo. "
            "Adaptar primeiro a historia integral aos limites de duracao e revisar "
            "o ovo ENTRE AS FLORES, nunca no caminho."
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditar narracao canônica Fofinhos EP01")
    parser.add_argument("--acao", choices=("revisar", "validar"), default="revisar")
    args = parser.parse_args()
    report = compare_short_draft()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.acao == "validar" and not report["legacy_short_scene_count"] == 15:
        # A validation failure is intentional until editorial recut.
        raise ValueError("Antigo Short ainda nao foi adaptado para a narracao aprovada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
