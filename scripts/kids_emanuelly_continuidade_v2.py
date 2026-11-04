"""Canon-aware image reference gates for Emanuelly EP01.

The CAST SHEET is NEVER used directly to render a story beat.
Create isolated private references via GPT Image 2; each beat receives
only the characters that have been introduced up to that exact moment.
This reduces unwanted cast leakage; no automated pixel-level identity
recognition is claimed, so artistic review of rendered video is still needed.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

MODEL = "gpt-image-2"
POLICY = "emanuelly/character-continuity/v2"
SOLO = "emanuelly-solo.png"
DUO = "emanuelly-fofinho.png"
REFERENCE_ROLES = ("emanuelly-solo", "emanuelly-fofinho")
BIRTH_BEAT = 6

# Future protagonists cannot be visually introduced in the origin episode.
CAST_LOCK = {
    "fofinha-arco-iris": "future episode, a year after Fofinho",
    "fofinha-rosa": "future episode, a year after Fofinho",
    "raposo": "future introduction",
    "porco-espinho": "future introduction",
}


def role_for(part: dict, beat: dict) -> str:
    chapter = part["part"]
    position = beat["index"]
    if chapter not in (1, 2, 3, 4) or position < 1:
        raise ValueError("Parte/quadro nao autorizado")
    if chapter == 1 or (chapter == 2 and position < BIRTH_BEAT):
        return "emanuelly-solo"
    return "emanuelly-fofinho"


def allowed_characters(part: dict, beat: dict) -> tuple[str, ...]:
    if role_for(part, beat) == "emanuelly-solo":
        return ("Emanuelly",)
    return ("Emanuelly", "Fofinho")


def isolated_reference(full_reference: Path, role: str) -> Path:
    if role not in REFERENCE_ROLES:
        raise ValueError("Papel de referencia nao reconhecido")
    return full_reference.parent / (SOLO if role == "emanuelly-solo" else DUO)


def isolation_prompt(role: str) -> str:
    if role == "emanuelly-solo":
        return (
            "SOURCE CAST SHEET IS ONLY AN IDENTITY GUIDE, NOT A SCENE. "
            "Create ONE ISOLATED clean full-body character reference portrait "
            "of the exact GIRL EMANUELLY present in the supplied cast sheet. "
            "Keep her original face, hairstyle, clothing, skin appearance, "
            "proportions and 3D storybook aesthetic. Only ONE child in the output. "
            "Completely remove every plush toy, animal, kitten, person, prop "
            "and dragon egg. Plain light neutral background. Do not generate a "
            "collage, contact sheet, extra character or text. Keep generous margins."
        )
    if role == "emanuelly-fofinho":
        return (
            "SOURCE CAST SHEET IS ONLY AN IDENTITY GUIDE, NOT A SCENE. "
            "Create a clean character reference showing EXACTLY TWO subjects: "
            "(1) GIRL EMANUELLY and (2) BLUE PLUSH KITTEN FOFINHO, who has already "
            "hatched in the story. Preserve their exact approved proportions, "
            "clothing, facial appearance, blue plush texture and matching "
            "3D children's storybook style from the supplied image. "
            "Do NOT include ANY other plushies, rainbow kitten, pink kitten, "
            "wildcat, hedgehog, people, costumes or accessories. "
            "Plain light neutral background, both full-body and separated "
            "with enough room to see their silhouettes. Single reference image, "
            "not a collage, no typography."
        )
    raise ValueError("Isolamento de elenco nao reconhecido")


def scene_prompt(part: dict, beat: dict) -> str:
    role = role_for(part, beat)
    visual = beat["visual_cue"]
    # Beat 03 previously tempted the generator to reveal future plush friends.
    if part["part"] == 1 and beat["index"] == 3:
        visual = ("Uma luz suave e magica ilumina brinquedos GUARDADOS, "
                  "fora do enquadramento; somente Emanuelly aparece, "
                  "sem outros personagens ou bichinhos de pelucia visiveis")
    if part["part"] == 1 and beat["index"] == 8:
        visual = ("SOZINHA, Emanuelly observa o OVO AZUL INTACTO, "
                  "sobre a mesma mantinha e almofada de seu quarto a noite. "
                  "O ovo comeca a balancar devagar; ninguem mais esta no quarto.")
    if part["part"] == 1 and beat["index"] == 9:
        visual = ("Emanuelly sozinha se aproxima do MESMO ovo azul ainda "
                  "inteiro e fechado; misterio carinhoso. Nao mostrar o interior.")

    if role == "emanuelly-solo":
        cast_rules = (
            "VISIBLE CAST: EXACTLY ONE CHARACTER, GIRL EMANUELLY. "
            "NO kittens, cats, animals, plush friends, toy figures, "
            "dragons, imaginary silhouettes, reflections of other beings, "
            "or other people. Any magical life is still INSIDE the closed egg. "
            "Absolutely no blue plush kitten before the birth scene. "
        )
    else:
        cast_rules = (
            "VISIBLE CAST: EXACTLY EMANUELLY and her BLUE PLUSH KITTEN FOFINHO. "
            "NO extra cats, rainbow-colored plush, pink plush, wildcats, "
            "hedgehogs, other plush friends, other children, or crowds. "
            "The attached isolated TWO-SUBJECT reference is the complete cast. "
        )
    if part["part"] == 1:
        egg = (
            "The SAME blue DRAGON EGG, medium-sized, closed, intact, with "
            "identical blue shade, teardrop patterns and subtle soft glow "
            "through all 9 frames. No cracks until the chapter after this one. "
            "Garden for discovery; then a cozy bedroom with one same pillow "
            "and one same blanket. Emanuelly keeps one consistent outfit. "
            "Scene 08 must NOT show ANY second character. "
        )
    elif part["part"] == 2 and beat["index"] < BIRTH_BEAT:
        egg = (
            "One same blue egg on the same pillow in the same moonlit room. "
            "Do not show the kitten until spoken birth beat 06. "
        )
    else:
        egg = (
            "Fofinho is a SMALL BLUE PLUSH KITTEN with soft fabric texture; "
            "never a real cat, never a dragon, never a second kitten. "
        )
    effect = ("No floating magical water powers yet. "
              if (part["part"] == 1 or (part["part"] == 2 and beat["index"] < 10))
              else "Water magic must match ONLY this spoken beat; no premature spoilers. ")
    return (
        f"CONTINUITY AND CAST LOCK {POLICY}; GPT Image 2 reference editing. "
        "Create ONE original vertical 9:16 illustration for a children's "
        "storybook. The attached PRIVATE ISOLATED REFERENCE contains ONLY "
        "the permitted subject(s); copy their exact face, outfit, hair, "
        "proportions, plush appearance and art style. "
        + cast_rules + egg + effect +
        f"EP 1, Part {part['part']}/4, FRAME {beat['index']}/{len(part['segments'])}. "
        f"REQUIRED VISUAL ACTION: {visual}. "
        f"Spoken sentence for timing only (do not draw letters): {beat['spoken_text']}. "
        "Natural scale, consistent camera height and environment, warm gentle "
        "lighting. Show the ACTION distinctly instead of simply posing beside "
        "the egg. NO reference sheet, split panels, logo, subtitles, letters, "
        "horror, extra limbs, flash effects or new characters. "
        "If the isolated source has only Emanuelly, it is forbidden to "
        "invent or add any other being or plush. Output one coherent frame."
    )


def fingerprint(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def reference_signature(full_source: bytes, role: str) -> str:
    return fingerprint(
        (MODEL + "\n" + POLICY + "\n" + role + "\n" + isolation_prompt(role)).encode("utf-8")
        + fingerprint(full_source).encode()
    )


def check_isolated_ref(full: Path, role: str) -> tuple[Path, str]:
    path = isolated_reference(full, role)
    metadata = path.with_suffix(".json")
    if not path.is_file() or not metadata.is_file():
        raise FileNotFoundError(
            f"Referencia isolada {role} ausente. Execute "
            r".\gerar-historia-kids.ps1 -Acao PrepararReferencias -MaxChamadas 2"
        )
    source_hash = fingerprint(full.read_bytes())
    current_hash = fingerprint(path.read_bytes())
    data = json.loads(metadata.read_text(encoding="utf-8"))
    if not (data.get("schema") == POLICY
            and data.get("model") == MODEL
            and data.get("reference_role") == role
            and data.get("source_sha256") == source_hash
            and data.get("derived_sha256") == current_hash
            and data.get("prompt_signature") == reference_signature(full.read_bytes(), role)):
        raise ValueError(
            f"Referencia {role} desatualizada ou alterada. "
            "Recrie as referencias isoladas antes de gerar quadros."
        )
    from PIL import Image
    with Image.open(path) as im:
        im.verify()
    return path, current_hash


def prepare_isolated_references(
    full: Path, *, budget: int, editor=None, key_provider=None,
    replace: bool = False,
) -> dict:
    if not full.is_file():
        raise FileNotFoundError("Foto original privada nao encontrada")
    if budget < 0:
        raise ValueError("Orcamento invalido")
    missing = []
    for role in REFERENCE_ROLES:
        try:
            check_isolated_ref(full, role)
        except (FileNotFoundError, ValueError, OSError):
            missing.append(role)
    targets = list(REFERENCE_ROLES) if replace else missing
    if len(targets) > budget:
        raise ValueError(
            f"Precisamos de {len(targets)} imagens de isolamento e o limite "
            f"e {budget}; nenhuma chamada foi enviada."
        )
    if not targets:
        return {"status": "cache", "new_calls": 0, "roles": REFERENCE_ROLES}
    if editor is None:
        from master_scenes import request_edit
        editor = request_edit
    if key_provider is None:
        from gerar_video_codex import proxy_key
        key_provider = proxy_key
    from master_scenes import normalize_image, validate_image
    key = key_provider()
    saved = []
    for role in targets:
        raw = editor(full, isolation_prompt(role), MODEL, key, transparent=False)
        result = normalize_image(raw, alpha=False, stage="kids/isolamento/" + role)
        validate_image(result, alpha=False)
        target = isolated_reference(full, role)
        meta = target.with_suffix(".json")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            history = target.parent / "historico"
            history.mkdir(exist_ok=True)
            old = history / (target.stem + "-" + fingerprint(target.read_bytes())[:12] + ".png")
            if not old.exists():
                shutil.copy2(target, old)
        temporary = target.with_suffix(".partial.png")
        temporary.write_bytes(result)
        temporary.replace(target)
        info = {
            "schema": POLICY, "model": MODEL,
            "reference_role": role,
            "source_sha256": fingerprint(full.read_bytes()),
            "derived_sha256": fingerprint(result),
            "prompt_signature": reference_signature(full.read_bytes(), role),
            "automated_content_verification": "not_available",
            "manual_visual_review": "pending_after_render",
        }
        meta.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        saved.append(role)
    return {"status": "isolated", "new_calls": len(saved), "roles": list(REFERENCE_ROLES),
            "review_note": "Isolamento reduz aparicoes indevidas, mas exige conferencia visual."}
