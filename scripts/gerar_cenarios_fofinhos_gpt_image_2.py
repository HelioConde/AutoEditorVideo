#!/usr/bin/env python3
"""Fofinhos: nine canonical assets made with GPT Image 2, using two scene masters.

The first garden is grounded in the locally approved Emanuelly style image.
Room, egg and all alternate camera angles derive from approved scene masters.
All assets and original paid responses remain on the user's Windows machine.
No GitHub/YouTube upload and no automatic image calls.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

from PIL import Image

import kids_emanuelly_cenarios_camadas_v1 as canon

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-image-2"
SCHEMA = "kids/fofinhos/consistent-scenery/v1"
PRIVATE_STYLE = Path("assets/referencias-privadas/emanuelly-solo.png")
BASES = ("jardim-01", "quarto-01", "ovo-azul")
ANGLES = ("jardim-02", "jardim-03", "jardim-04",
          "quarto-02", "quarto-03", "quarto-04")
ALL = BASES + ANGLES

GARDEN_IDENTITY = (
    "Location identity: a single cozy magical garden, bright daytime, "
    "storybook 3D animation style, soft colorful lighting. "
    "Permanent landmarks: a curved tan stone path, ONE leafy flowering tree "
    "on the left, a low cream picket fence with ONE little wooden gate at "
    "the back right, a small wooden bench near the fence, and beds of "
    "blue/yellow flowers along the path. Identical species, fence design, "
    "path material, flowers, colors and relative landmark locations. "
    "Garden floor and sky fill the entire upright frame. "
)
ROOM_IDENTITY = (
    "Location identity: the exact SAME cozy child's bedroom in all shots. "
    "Permanent landmarks: pale mint walls, ONE arched window on the left "
    "with light cream curtains, low wooden bed on the right with the SAME "
    "sky-blue quilt, round cream rug at center, small white dresser on "
    "the back wall, a wooden toy shelf and ONE closed cream door at back right. "
    "Preserve wall color, floor planks, furniture design and relative positions. "
    "Daylight is soft and warm in ALL base backgrounds; the video compositor "
    "will create night-time lighting separately. "
)
NO_CAST = (
    "EMPTY clean background only. Absolutely NO children, people, animals, "
    "plush toys, dragon eggs, text, logos, watermark, picture frames depicting "
    "characters, or character shadows. No collage, multiple scenes, split "
    "screen, or inset pictures. Portrait 1024x1536, edge-to-edge opaque image. "
)
GARDEN_VIEWS = {
    "jardim-02": "Camera moved three steps LEFT of the first view: three-quarter angle looking diagonally toward the back gate; the SAME tree, bench, fence and curved path remain in their physically consistent positions.",
    "jardim-03": "Camera moved three steps RIGHT of the first view: reverse three-quarter view looking toward the SAME tree and path, with recognizable gate, fence, bench and flowerbeds.",
    "jardim-04": "Camera lowered near the curved path, slightly closer to the SAME tree, for a gentle eye-level discovery framing. The SAME bench and gate are in the correct background positions.",
}
ROOM_VIEWS = {
    "quarto-02": "Camera moved toward the LEFT side of the same bedroom, looking diagonally across the cream rug toward the SAME bed and dresser. Keep the window and door spatially plausible.",
    "quarto-03": "Camera shifted toward the RIGHT side of the exact same bedroom, with the SAME bed, window, dresser, door, rug and shelf recognizable. Daylight only.",
    "quarto-04": "Camera moved to a closer, gentle low viewpoint near the bed, looking across the SAME room. Preserve the exact decorations, furniture and layout. Daylight only.",
}


def prompt(slot: str) -> str:
    if slot == "jardim-01":
        return (
            "Create a new EMPTY establishing background for the FOFINHOS "
            "children's series. Use the supplied character picture ONLY to "
            "match its gentle rounded 3D storybook render style; REMOVE the "
            "character entirely. " + GARDEN_IDENTITY + "A clear wide three-quarter "
            "view, useful for staging a child and a separate egg overlay. " + NO_CAST
        )
    if slot == "quarto-01":
        return (
            "Create an EMPTY indoor bedroom background for the SAME children's "
            "storybook world as this attached OFFICIAL garden image. Borrow "
            "only its materials, lighting quality, colors and render style. "
            "This is a new interior, NOT the garden. " + ROOM_IDENTITY +
            "Wide establishing shot with free floor space for isolated "
            "character, basket and egg layers. " + NO_CAST
        )
    if slot == "ovo-azul":
        return (
            "Use this OFFICIAL garden picture ONLY as a guide to the same "
            "rounded 3D storybook aesthetic. Create exactly ONE mysterious "
            "smooth BLUE dragon egg, with distinctive painted little WATER "
            "DROPLET motifs, gentle cyan highlights and tiny glossy details. "
            "Do NOT include the garden, grass, shadows, scenery or anyone else. "
            "The same intact egg will be reused in every shot. "
            "One upright egg centered with generous clear margins, entire "
            "silhouette visible. TRUE TRANSPARENT RGBA background, 1024x1536. "
            "No checkerboard painted onto the image, no text or watermark."
        )
    if slot in GARDEN_VIEWS:
        return (
            "CAMERA REPOSITION OF THIS EXACT OFFICIAL GARDEN REFERENCE. "
            "This is NOT a different garden and NOT a redesign. Preserve "
            "the same 3D world and geometry. " + GARDEN_IDENTITY +
            GARDEN_VIEWS[slot] + " Do not add/remove or move any landmarks. " +
            NO_CAST
        )
    if slot in ROOM_VIEWS:
        return (
            "CAMERA REPOSITION OF THIS EXACT OFFICIAL BEDROOM REFERENCE. "
            "This is NOT a different room and NOT a redesign. Preserve "
            "the same 3D world and geometry. " + ROOM_IDENTITY +
            ROOM_VIEWS[slot] + " Do not add/remove or relocate furniture. " +
            NO_CAST
        )
    raise ValueError("Cena desconhecida: " + slot)


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def source(slot: str, root: Path = ROOT) -> Path:
    if slot == "jardim-01":
        return root / PRIVATE_STYLE
    if slot in ("quarto-01", "ovo-azul") or slot.startswith("jardim-"):
        return canon.official("jardim-01", root)
    return canon.official("quarto-01", root)


def raw_path(slot: str, root: Path = ROOT) -> Path:
    return root / canon.CANON / "brutos" / (slot + ".png")


def raw_meta(slot: str, root: Path = ROOT) -> Path:
    return raw_path(slot, root).with_suffix(".json")


def generated_meta(slot: str, root: Path = ROOT) -> Path:
    return root / canon.CANON / "origens" / (slot + ".json")


def record(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def source_hash(slot: str, root: Path = ROOT) -> str | None:
    ref = source(slot, root)
    if not ref.is_file() or ref.is_symlink():
        return None
    return sha(ref.read_bytes())


def raw_reusable(slot: str, root: Path = ROOT) -> bool:
    art, meta = raw_path(slot, root), raw_meta(slot, root)
    origin = source_hash(slot, root)
    if not origin or not art.is_file() or not meta.is_file():
        return False
    try:
        data = json.loads(meta.read_text(encoding="utf-8"))
        return (data.get("schema") == SCHEMA and data.get("model") == MODEL
                and data.get("slot") == slot
                and data.get("source_sha256") == origin
                and data.get("prompt_sha256") == sha(prompt(slot).encode("utf-8"))
                and data.get("raw_sha256") == sha(art.read_bytes()))
    except (OSError, ValueError, TypeError):
        return False


def status(slot: str, root: Path = ROOT) -> str:
    asset = canon.official(slot, root)
    meta = generated_meta(slot, root)
    if canon.installed(slot, root):
        if not meta.is_file():
            return "instalado_externamente"
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            if (data.get("schema") == SCHEMA
                    and data.get("model") == MODEL
                    and data.get("slot") == slot
                    and data.get("source_sha256") == source_hash(slot, root)
                    and data.get("prompt_sha256") == sha(prompt(slot).encode("utf-8"))
                    and data.get("image_sha256") == sha(asset.read_bytes())):
                return "em_cache"
        except (OSError, ValueError, TypeError):
            pass
        return "desatualizado"
    if asset.exists():
        return "desatualizado"
    return "bruto_recuperavel" if raw_reusable(slot, root) else "pendente"


def report(root: Path = ROOT) -> dict:
    return {
        "schema": SCHEMA, "model": MODEL,
        "bases": [{"slot": s, "status": status(s, root)} for s in BASES],
        "angulos": [{"slot": s, "status": status(s, root)} for s in ANGLES],
        "resumo": {
            "arquivos_registrados": sum(canon.installed(s, root) for s in ALL),
            "total": 9,
            "chamadas_previstas_bases": sum(
                status(s, root) not in ("em_cache", "instalado_externamente", "bruto_recuperavel")
                for s in BASES),
            "chamadas_previstas_angulos": sum(
                status(s, root) not in ("em_cache", "instalado_externamente", "bruto_recuperavel")
                for s in ANGLES),
        },
        "revisao_visual": "obrigatoria_para_confirmar_consistencia_entre_angulos",
        "publicacoes": 0,
    }


def validate_output(data: bytes, slot: str) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        if im.size != (1024, 1536):
            raise ValueError("Imagem nao veio em 1024x1536: " + slot)
        rgba = im.convert("RGBA")
        alpha = rgba.getchannel("A")
        histogram = alpha.histogram()
        transparent = sum(histogram[:60]) / (rgba.width * rgba.height)
        if slot == "ovo-azul":
            if transparent < .025 or alpha.getextrema()[0] >= 200:
                raise ValueError("Ovo deve ser um PNG com fundo realmente transparente")
        elif transparent > .02 or alpha.getextrema()[0] < 240:
            raise ValueError("Cenario precisa ser opaco e cobrir todo o quadro")
        output = io.BytesIO()
        rgba.save(output, "PNG")
        return output.getvalue()


def generate_batch(slots: tuple[str, ...], *, root: Path = ROOT,
                   budget: int = 0, replace: bool = False,
                   editor=None, key_provider=None) -> dict:
    if budget < 0:
        raise ValueError("MaxChamadas nao pode ser negativo")
    # No charged requests if the plan or dependencies cannot be satisfied.
    pending = [s for s in slots
               if replace or status(s, root) not in ("em_cache", "instalado_externamente")]
    stale = [s for s in pending if status(s, root) == "desatualizado"]
    if stale and not replace:
        raise ValueError("Recursos diferentes/desatualizados: " + ", ".join(stale)
                         + ". Use -Refazer para preservar historico.")
    for i, slot in enumerate(pending):
        ref = source(slot, root)
        if slot == "jardim-01":
            if not ref.is_file() or ref.is_symlink():
                raise FileNotFoundError(
                    "Referencia privada Emanuelly solo ausente: " + str(ref))
        else:
            parent = "quarto-01" if slot.startswith("quarto-") and slot != "quarto-01" else "jardim-01"
            if parent not in pending[:i] and not canon.installed(parent, root):
                raise FileNotFoundError("Gere primeiro a imagem-base " + parent)
    predicted = sum(replace or not raw_reusable(slot, root) for slot in pending)
    if predicted > budget:
        raise ValueError(
            f"O lote exige ate {predicted} chamadas {MODEL}; MaxChamadas={budget}. "
            "NENHUMA IA acionada.")
    results = []
    calls = 0
    key = None
    for slot in pending:
        origin = source(slot, root)
        origin_sha = source_hash(slot, root)
        if origin_sha is None:
            raise FileNotFoundError("Origem desapareceu: " + str(origin))
        if not replace and raw_reusable(slot, root):
            blob = raw_path(slot, root).read_bytes()
            reused = True
        else:
            if editor is None:
                from master_scenes import request_edit
                editor = request_edit
            if key is None:
                if key_provider is None:
                    from gerar_video_codex import proxy_key
                    key_provider = proxy_key
                key = key_provider()
            blob = editor(origin, prompt(slot), MODEL, key,
                          transparent=(slot == "ovo-azul"))
            # Save the paid output before QA. Retrying a bad QA is free.
            raw = raw_path(slot, root)
            raw.parent.mkdir(parents=True, exist_ok=True)
            temp = raw.with_name(raw.name + ".partial")
            temp.write_bytes(blob)
            temp.replace(raw)
            record(raw_meta(slot, root), {
                "schema": SCHEMA, "model": MODEL, "slot": slot,
                "source_sha256": origin_sha,
                "prompt_sha256": sha(prompt(slot).encode("utf-8")),
                "raw_sha256": sha(blob)})
            calls += 1
            reused = False
        converted = validate_output(blob, slot)
        temp_image = root / canon.CANON / "temporarios" / (slot + ".png")
        temp_image.parent.mkdir(parents=True, exist_ok=True)
        temp_image.write_bytes(converted)
        try:
            installed = canon.install(slot, temp_image, root=root, replace=replace)
        finally:
            temp_image.unlink(missing_ok=True)
        record(generated_meta(slot, root), {
            "schema": SCHEMA, "model": MODEL, "slot": slot,
            "source": str(origin.relative_to(root)),
            "source_sha256": origin_sha,
            "prompt_sha256": sha(prompt(slot).encode("utf-8")),
            "image_sha256": sha(canon.official(slot, root).read_bytes()),
            "visual_approval": "pending_creator_review",
            "no_youtube_upload": True})
        results.append({"slot": slot, "status": installed["status"],
                        "raw_reused": reused})
    return {"schema": SCHEMA, "results": results, "new_calls": calls,
            "skipped_cache": [s for s in slots if s not in pending],
            "model": MODEL, "uploads": 0}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fofinhos: jardim/quarto 4 angulos + ovo")
    ap.add_argument("--acao", choices=("planejar", "verificar", "bases", "angulos"),
                    default="planejar")
    ap.add_argument("--max-chamadas", type=int, default=0)
    ap.add_argument("--bases-aprovadas", action="store_true")
    ap.add_argument("--refazer", action="store_true")
    args = ap.parse_args(argv)
    if args.acao in ("planejar", "verificar"):
        if args.refazer or args.bases_aprovadas or args.max_chamadas:
            ap.error("Planejar/Verificar sao somente leitura")
        result = report()
    elif args.acao == "bases":
        if args.bases_aprovadas:
            ap.error("BasesAprovadas e apenas para GerarAngulos")
        result = generate_batch(BASES, budget=args.max_chamadas, replace=args.refazer)
    else:
        if not args.bases_aprovadas:
            ap.error("Revise visualmente jardim-01, quarto-01 e ovo-azul; "
                     "depois use -BasesAprovadas")
        if not all(canon.installed(s) for s in BASES):
            ap.error("As tres imagens-base devem existir antes dos angulos")
        result = generate_batch(ANGLES, budget=args.max_chamadas, replace=args.refazer)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileNotFoundError, OSError, RuntimeError) as exc:
        print("[FOFINHOS CENARIOS BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
