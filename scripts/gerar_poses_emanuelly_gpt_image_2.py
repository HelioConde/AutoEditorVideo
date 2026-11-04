#!/usr/bin/env python3
"""Emanuelly: a photo-guided, strictly GPT Image 2, local pose asset library.

Never uploads to GitHub or YouTube. The user's private visual reference is
transmitted to the configured image-edit proxy ONLY for an explicit Gerar run.
Does not change the existing video renderer, narration, or approved images.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

from kids_poses_enquadramento_v1 import fit_transparent_pose

ROOT = Path(__file__).resolve().parents[1]
MODEL = "gpt-image-2"
SCHEMA = "kids/emanuelly/identity-poses/v1"
REFERENCE_REL = Path("assets/referencias-privadas/emanuelly-personagem-oficial.png")
OUTPUT_REL = Path("assets/gerados/kids-emanuelly/biblioteca-personagens/emanuelly/poses")

# Distinct ACTIONS, not eight variants of "girl kneeling and looking".
POSES = {
    "em-pe": ("Standing upright, full-body, relaxed and friendly, arms at sides.",
              "Estar em pé"),
    "caminhando": ("Walking forward with one foot clearly ahead, natural arm swing.",
                  "Caminhar"),
    "observando": ("Standing in place and noticing something magical in the distance, "
                  "head gently turned and eyes curious; no kneeling.",
                  "Observar"),
    "ajoelhada": ("Kneeling on ONE knee, full-body side three-quarter view, both "
                 "hands resting naturally; a clearly different silhouette.",
                 "Ajoelhar"),
    "estendendo-mao": ("Kneeling and extending ONE open hand gently forward toward "
                      "an invisible object, other hand near the chest.",
                      "Estender a mão"),
    "segurando-ovo": ("Standing upright with BOTH hands cupped together as if holding "
                     "an invisible medium-sized egg near the waist. DO NOT draw an egg "
                     "or any other prop. No duplicate hands.",
                     "Segurar o ovo (sem desenhar o objeto)"),
    "preparando-caminha": ("Bending gently forward and arranging an INVISIBLE soft "
                          "blanket on a low surface, hands open in a clear caring "
                          "gesture; no actual pillow or basket.",
                          "Arrumar a caminha"),
    "surpresa": ("Standing upright with a soft, delighted expression and hands "
                "near the cheeks, reacting to a gentle magical discovery.",
                "Surpresa acolhedora"),
}

def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def private_ref(root: Path = ROOT) -> Path:
    return root / REFERENCE_REL


def pose_dir(root: Path = ROOT) -> Path:
    return root / OUTPUT_REL


def image_check(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Referencia visual privada ausente: " + str(path))
    if path.stat().st_size > 18_000_000:
        raise ValueError("Referencia acima do limite de 18 MB do proxy")
    from PIL import Image
    with Image.open(path) as im:
        im.load()
        if min(im.size) < 640:
            raise ValueError("Referencia visual com resolucao insuficiente (minimo 640px)")
    return digest(path.read_bytes())


def install(source: Path, *, root: Path = ROOT, replace: bool = False) -> dict:
    from PIL import Image
    if not source.is_file():
        raise FileNotFoundError("Imagem fornecida nao encontrada: " + str(source))
    dest = private_ref(root)
    # Normalize reference format locally; never send the source to GitHub.
    with Image.open(source) as im:
        im.load()
        if min(im.size) < 640:
            raise ValueError("Referencia abaixo de 640px")
        stream = io.BytesIO()
        im.convert("RGB").save(stream, "PNG")
        png = stream.getvalue()
    if len(png) > 18_000_000:
        raise ValueError("Referencia convertida acima de 18 MB")
    sha = digest(png)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        old_hash = image_check(dest)
        if old_hash == sha:
            return {"status": "ja_instalada", "sha256": sha,
                    "caminho": str(dest), "upload": False}
        if not replace:
            raise ValueError(
                "Ja existe referencia diferente. Para substituir com backup, "
                "use -Refazer na acao InstalarReferencia."
            )
        archive = dest.parent / "historico"
        archive.mkdir(exist_ok=True)
        old_path = archive / f"emanuelly-personagem-{old_hash[:12]}.png"
        if not old_path.exists():
            shutil.copy2(dest, old_path)
    temp = dest.with_suffix(".partial.png")
    temp.write_bytes(png)
    temp.replace(dest)
    return {"status": "instalada", "sha256": sha,
            "caminho": str(dest), "upload": False}


def prompt(pose: str) -> str:
    if pose not in POSES:
        raise ValueError("Pose nao reconhecida: " + pose)
    action = POSES[pose][0]
    return (
        "REFERENCE-LOCKED 3D CARTOON CHARACTER POSE EDIT. "
        "Use the supplied PRIVATE image as the SOLE visual identity reference "
        "for Emanuelly. This is THE SAME CHILD CHARACTER in a different pose, "
        "not a new character. Preserve her recognizable face, eye shapes, "
        "facial proportions, hairstyle, hair texture and color, skin appearance, "
        "clothing colors, accessories and original 3D storybook rendering style "
        "EXACTLY as they appear in the uploaded reference. Do not invent or "
        "change freckles, bows, bangs, makeup, outfits, shoe style, age or "
        "accessories. If an accessory is not visible in the source, do NOT add it. "
        "Make ONE single coherent FULL BODY of Emanuelly, with both feet visible "
        "unless naturally occluded, and room around her silhouette. "
        f"SPECIFIC ACTION TO DRAW: {action} "
        "Use a 1024x1536 upright PNG canvas with TRUE TRANSPARENT ALPHA "
        "background (not checkerboard, white, colored, blurred or photographed "
        "background). No floor, scenery, shadows on the background, furniture, "
        "props, flowers, trees, eggs, plush toys, second character, duplicate "
        "girl, contact sheet, panels, labels, lettering or logos. "
        "NO future characters: Fofinho, Fofinha Rainbow, Fofinha Pink, Raposo "
        "or Hedgehog. Keep the exact same character scale as other pose files. "
        "Keep the ENTIRE silhouette within the center 80 percent of the canvas, "
        "at least 12 percent free transparent space on LEFT and RIGHT, and at "
        "least 9 percent free transparent space above the hair and below the feet. "
        "Do not place even hands, shoes, hair, bows or accessories on image edges. "
        "NO zoomed-in character, NO clipped feet or fingers. "
        "A distinct believable body action, five fingers per hand, natural "
        "arms and anatomy, no cropped limbs, no excess fingers."
    )


# Previously generated 'em-pe' poses remain valid under their original
# identity and image hashes; updating framing instructions must not force
# wasting a new paid request for an already successful image.
MARGIN_PROMPT = (
    "Keep the ENTIRE silhouette within the center 80 percent of the canvas, "
    "at least 12 percent free transparent space on LEFT and RIGHT, and at "
    "least 9 percent free transparent space above the hair and below the feet. "
    "Do not place even hands, shoes, hair, bows or accessories on image edges. "
    "NO zoomed-in character, NO clipped feet or fingers. "
)


def paths(pose: str, root: Path = ROOT) -> tuple[Path, Path]:
    if pose not in POSES:
        raise ValueError("Pose invalida: " + pose)
    base = pose_dir(root) / f"emanuelly-{pose}"
    return base.with_suffix(".png"), base.with_suffix(".json")


def expected(ref_sha: str, pose: str) -> str:
    return digest((SCHEMA + "\n" + MODEL + "\n" + ref_sha + "\n" +
                   prompt(pose)).encode("utf-8"))


def expected_before_margin_fix(ref_sha: str, pose: str) -> str:
    earlier = prompt(pose).replace(MARGIN_PROMPT, "")
    return digest((SCHEMA + "\n" + MODEL + "\n" + ref_sha + "\n"
                   + earlier).encode("utf-8"))


def valid(pose: str, root: Path = ROOT) -> bool:
    art, manifest = paths(pose, root)
    if not art.is_file() or not manifest.is_file() or art.is_symlink():
        return False
    try:
        ref_sha = image_check(private_ref(root))
        details = json.loads(manifest.read_text(encoding="utf-8"))
        if not (
            details.get("schema") == SCHEMA and details.get("model") == MODEL
            and details.get("pose") == pose
            and details.get("reference_sha256") == ref_sha
            and details.get("signature") in (
                expected(ref_sha, pose), expected_before_margin_fix(ref_sha, pose)
            )
            and details.get("image_sha256") == digest(art.read_bytes())
            and details.get("qa", {}).get("transparent_fraction", 0) >= 0.08
        ):
            return False
        from PIL import Image
        with Image.open(art) as img:
            img.load()
            if img.mode != "RGBA" or img.size != (1024, 1536):
                return False
            return img.getchannel("A").getextrema()[0] < 200
    except (KeyError, ValueError, OSError, TypeError):
        return False
    return True


def plan(poses: list[str], *, root: Path = ROOT) -> dict:
    ref = private_ref(root)
    ref_exists = ref.is_file()
    ref_sha = image_check(ref) if ref_exists else None
    rows = []
    for slug in poses:
        finished = valid(slug, root)
        recoverable = (
            not finished and ref_sha is not None and raw_valid(slug, ref_sha, root)
        )
        png, _meta = paths(slug, root)
        raw, _raw_meta = raw_paths(slug, root)
        if finished:
            status = "em_cache"
        elif recoverable:
            status = "bruto_recuperavel_sem_ia"
        elif png.exists() or raw.exists():
            status = "desatualizada"
        else:
            status = "pendente"
        rows.append({
            "pose": slug, "descricao": POSES[slug][1],
            "status": status, "chamadas_novas": int(
                not finished and not recoverable
            ),
        })
    return {
        "schema": SCHEMA, "model": MODEL,
        "referencia_instalada": ref_exists,
        "referencia": str(ref),
        "poses": rows,
        "chamadas_necessarias": sum(r["chamadas_novas"] for r in rows),
        "brutos_recuperaveis": sum(r["status"] == "bruto_recuperavel_sem_ia"
                                  for r in rows),
        "revisao_identidade": "necessaria_antes_de_uso_na_animacao",
        "publicacoes": 0,
    }


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".partial")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    tmp.replace(path)


def raw_paths(pose: str, root: Path = ROOT) -> tuple[Path, Path]:
    if pose not in POSES:
        raise ValueError("Pose bruta desconhecida")
    base = pose_dir(root) / "brutos" / f"emanuelly-{pose}"
    return base.with_suffix(".png"), base.with_suffix(".json")


def raw_valid(pose: str, ref_sha: str, root: Path = ROOT) -> bool:
    art, marker = raw_paths(pose, root)
    if not art.is_file() or not marker.is_file() or art.is_symlink():
        return False
    try:
        meta = json.loads(marker.read_text(encoding="utf-8"))
        return (meta.get("schema") == SCHEMA
                and meta.get("model") == MODEL
                and meta.get("pose") == pose
                and meta.get("reference_sha256") == ref_sha
                and meta.get("signature") == expected(ref_sha, pose)
                and meta.get("raw_sha256") == digest(art.read_bytes()))
    except (OSError, KeyError, ValueError, TypeError):
        return False


def cache_raw(pose: str, blob: bytes, ref_sha: str,
              root: Path = ROOT) -> None:
    """Write the PAID API response before validation, even if it fails QA."""
    path, metadata = raw_paths(pose, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        previous = path.read_bytes()
        backup = path.parent / "historico" / (
            f"emanuelly-{pose}-{digest(previous)[:12]}.png"
        )
        backup.parent.mkdir(exist_ok=True)
        if not backup.exists():
            shutil.copy2(path, backup)
    tmp = path.with_suffix(".partial.png")
    tmp.write_bytes(blob)
    tmp.replace(path)
    save_json(metadata, {
        "schema": SCHEMA, "model": MODEL, "pose": pose,
        "reference_sha256": ref_sha,
        "signature": expected(ref_sha, pose),
        "raw_sha256": digest(blob),
        "status": "paid_response_saved_before_qa",
        "upload": False,
    })


def generate(poses: list[str], *, root: Path = ROOT,
             budget: int = 0, replace: bool = False,
             editor=None, key_provider=None) -> dict:
    if budget < 0:
        raise ValueError("Orcamento negativo")
    original = private_ref(root)
    ref_sha = image_check(original)
    pending = poses if replace else [p for p in poses if not valid(p, root)]
    # Reject changed references/corrupt files until the user explicitly asks
    # to regenerate: never overwrite earlier pictures invisibly.
    if not replace:
        stale = [p for p in pending if paths(p, root)[0].exists()]
        stale += [p for p in pending if raw_paths(p, root)[0].exists()
                  and not raw_valid(p, ref_sha, root) and p not in stale]
        if stale:
            raise ValueError(
                "Poses com referencia alterada ou QA invalido: " + ", ".join(stale) +
                ". Use -Refazer para guardar as versoes anteriores."
            )
    # A paid image which failed margins is RECOVERABLE at zero new calls.
    # The API budget must count requests, not poses pending local QA.
    to_call = [p for p in pending if replace or not raw_valid(p, ref_sha, root)]
    if len(to_call) > budget:
        raise ValueError(
            f"Orcamento insuficiente: {len(to_call)} novas chamadas necessarias "
            f"(inclui {len(pending) - len(to_call)} respostas recuperaveis "
            f"do cache bruto); -MaxChamadas {budget}. "
            "NENHUMA chamada de IA realizada."
        )
    if not pending:
        return {"status": "cache", "geradas": 0, "reutilizadas": len(poses),
                "modelo": MODEL, "publicadas": 0}
    if to_call:
        if editor is None:
            from master_scenes import request_edit
            editor = request_edit
        if key_provider is None:
            from gerar_video_codex import proxy_key
            key_provider = proxy_key
        key = key_provider()
    from master_scenes import normalize_image, validate_image
    finished = []
    reframed = []
    rescued = []
    for slug in pending:
        if raw_valid(slug, ref_sha, root) and not replace:
            raw = raw_paths(slug, root)[0].read_bytes()
            rescued.append(slug)
            print(f"[CACHE BRUTO] Recuperando a pose {slug} sem nova chamada", flush=True)
        else:
            # Use the SAME supplied private reference for every pose.
            print(f"[GPT IMAGE 2] Gerando pose isolada: {slug}", flush=True)
            raw = editor(original, prompt(slug), MODEL, key, transparent=True)
            # CRITICAL: save exact paid bytes BEFORE any possible QA failure.
            cache_raw(slug, raw, ref_sha, root)
        png = normalize_image(raw, alpha=True, stage="kids/emanuelly/" + slug)
        pre_qa = validate_image(png, alpha=True)
        png, frame_qa = fit_transparent_pose(png)
        qa = validate_image(png, alpha=True)
        if qa.get("margin_warning"):
            raise ValueError(
                "Falha de margens mesmo apos reenquadrar localmente: " + slug
                + ". Resposta bruta salva em brutos/ para recuperacao."
            )
        if frame_qa["reframed"]:
            reframed.append(slug)
            print(f"[REENQUADRAMENTO LOCAL] {slug}: margens corrigidas, zero IA extra", flush=True)
        if frame_qa["source_may_already_be_cropped"]:
            print(f"[AVISO DE REVISAO] {slug}: imagem original encosta na borda; "
                  "confira se nenhum membro ja estava cortado.", flush=True)
        target, metadata = paths(slug, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            history = pose_dir(root) / "historico"
            history.mkdir(exist_ok=True)
            backup = history / f"{target.stem}-{digest(target.read_bytes())[:12]}.png"
            if not backup.exists():
                shutil.copy2(target, backup)
            if metadata.is_file():
                oldmeta = history / f"{target.stem}-{digest(target.read_bytes())[:12]}.json"
                if not oldmeta.exists():
                    shutil.copy2(metadata, oldmeta)
        tmp = target.with_suffix(".partial.png")
        tmp.write_bytes(png)
        tmp.replace(target)
        save_json(metadata, {
            "schema": SCHEMA, "model": MODEL,
            "pose": slug, "reference_sha256": ref_sha,
            "signature": expected(ref_sha, slug),
            "image_sha256": digest(png), "qa": qa,
            "source_qa": pre_qa, "reframe": frame_qa,
            "raw_sha256": digest(raw),
            "reference_sent_to": "configured_local_codex_proxy_image_edits",
            "identity_approved_by_human": False,
            "status": "pending_visual_review",
            "youtube_upload": False,
        })
        finished.append(slug)
    return {"status": "gerado_para_revisao", "geradas": len(finished),
            "poses": finished, "modelo": MODEL, "publicadas": 0,
            "novas_chamadas": len(to_call),
            "recuperadas_cache_bruto": rescued,
            "reenquadradas_sem_ia": reframed,
            "saida": str(pose_dir(root))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gerar poses transparentes da Emanuelly com GPT Image 2")
    parser.add_argument("--acao", default="planejar",
                        choices=("planejar", "instalar-referencia", "gerar", "verificar", "abrir"))
    parser.add_argument("--pose", default="Todas",
                        choices=["Todas", *POSES])
    parser.add_argument("--referencia", type=Path)
    parser.add_argument("--max-chamadas", type=int, default=0)
    parser.add_argument("--refazer", action="store_true")
    args = parser.parse_args(argv)
    if args.max_chamadas < 0:
        parser.error("--max-chamadas deve ser >= 0")
    if args.acao == "instalar-referencia":
        if args.referencia is None:
            parser.error("InstalarReferencia exige --referencia")
        response = install(args.referencia, replace=args.refazer)
    else:
        if args.referencia is not None:
            parser.error("Use a referencia somente com InstalarReferencia")
        poses = list(POSES) if args.pose == "Todas" else [args.pose]
        if args.acao in ("planejar", "verificar"):
            if args.refazer:
                parser.error("Refazer nao e permitido em Planejar/Verificar")
            response = plan(poses)
        elif args.acao == "abrir":
            folder = pose_dir()
            if not folder.is_dir():
                raise FileNotFoundError("Pasta de poses ausente; primeiro execute Gerar")
            import os
            if os.name == "nt":
                os.startfile(str(folder))  # only local, from explicit action
            response = {"pasta": str(folder), "publicacoes": 0}
        else:
            response = generate(poses, budget=args.max_chamadas,
                                replace=args.refazer)
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError) as exc:
        print("[POSES KIDS BLOQUEADAS] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
