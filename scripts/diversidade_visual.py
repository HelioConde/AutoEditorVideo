#!/usr/bin/env python3
"""Direção de fotografia variável para Shorts: offline, determinística e sem IA.

As ações de xadrez são metáforas ilustrativas; não afirmam que o anime
mostrou uma partida literal. Os prompts não devem manter as mesmas poses
frontais por seis imagens consecutivas.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

VERSION = "arquivo-otaku/visual-diversity/v1"

# Plano, ângulo, distância, assunto, ação, instrução, emoção.
CHESS_SHOTS = [
    ("wide_duel", "frontal low wide shot", "wide", "Light e L", "estabelecer o confronto",
     "Both rivals across the chessboard, full heads and hands visible. Dramatic staging, no overlapping silhouettes.", "tensão"),
    ("ots_light", "over-the-shoulder from behind Light", "medium", "L", "L observa as intenções do rival",
     "Camera BEHIND Light's shoulder, looking toward L; show an intentional three-quarter view. NOT a symmetric front-facing duel.", "suspeita"),
    ("light_moves_king", "low 3/4 angle at chessboard height", "detail", "mão de Light e o rei",
     "Light move o rei preto",
     "Tight cinematic detail: Light's complete hand gently moves a single BLACK KING across the chessboard, king clearly readable, with blurred rival farther back. Hands anatomically complete. NOT two men staring across a table.", "decisão"),
    ("l_reaction", "close-up three-quarter side angle", "close", "L", "L percebe uma possibilidade",
     "Strong close-up on L's eyes and thoughtful fingers, shallow background depth, character expression dominates; chessboard only hinted in background.", "revelação"),
    ("l_moves_king", "over-the-shoulder from behind L", "medium_close", "L e sua mão",
     "L move o rei branco",
     "Camera from L's SIDE and slightly above shoulder, L moves a WHITE KING with a full anatomically correct hand; Light is soft in the distance. Avoid symmetrical table confrontation.", "contra-ataque"),
    ("final_checkmate", "dramatic diagonal overhead 3/4 angle", "dramatic", "reis de xadrez e os dois rivais",
     "xeque-mate mental",
     "Climactic diagonal perspective looking across kings and faces, visual tension and strong depth, both rivals in contrasting positions. Chess is a SYMBOLIC metaphor, not canon footage.", "clímax"),
    ("top_board", "high angle over chessboard", "detail", "tabuleiro", "uma peça ameaça o rei",
     "Top-down macro of the chessboard, one piece threatening the king, dramatic hands at edges; preserve chess geometry and piece shapes. No familiar frontal two-person composition.", "ameaça"),
    ("light_reaction", "side-profile tight close-up", "close", "Light", "Light esconde sua reação",
     "Sharp side-profile close on Light's eyes and tense mouth; L appears only as subtle blurred silhouette, not a repeated wide shot.", "segredo"),
    ("ots_l", "over-the-shoulder from behind L", "medium", "Light", "Light analisa o adversário",
     "Camera BEHIND L looking at Light from a new position; show full head/hair and intentional asymmetry.", "confronto"),
    ("king_hand_macro", "extreme macro lateral angle", "macro", "mão sobre o tabuleiro",
     "um dedo interrompe uma jogada",
     "Extreme detail of fingertips above a king chess piece, dramatic shadows, no whole room or frontal duo. Complete fingers, stable anatomy, legible piece.", "suspense"),
]
GENERAL_SHOTS = [
    ("establishing", "three-quarter wide shot", "wide", "personagens", "estabelecer o ambiente",
     "Establish the location and key visual conflict from a spacious three-quarter view.", "curiosidade"),
    ("over_shoulder", "over-the-shoulder angle", "medium", "personagem oposto", "observação",
     "Foreground shoulder framing another character or the story's object. New camera axis, no repeated frontal posing.", "mistério"),
    ("object_detail", "low macro angle", "detail", "objeto central", "ação no objeto",
     "One hand interacting with the story's important object in detail; do not generate an unrelated item.", "decisão"),
    ("face_reaction", "three-quarter face close-up", "close", "personagem principal", "reação emocional",
     "Expressive eyes and facial emotion, completely visible hairstyle, shallow depth of field.", "reação"),
    ("low_angle", "low side angle", "medium", "personagem principal", "consequência",
     "Strong silhouette seen from below/side, not the same camera position as preceding frame.", "tensão"),
    ("final_reveal", "diagonal dramatic close-up", "dramatic", "assunto principal", "clímax visual",
     "New reveal perspective with readable face and object; cinematic final frame.", "clímax"),
    ("top_detail", "high-angle close-up", "detail", "objeto central", "detalhe significativo",
     "Overhead object detail with meaningful relationship to the spoken phrase.", "curiosidade"),
    ("profile_reaction", "side-profile close-up", "close", "personagem principal", "reação reveladora",
     "Dramatic side profile, subject and lighting visually different from last frame.", "surpresa"),
    ("reverse_angle", "reverse over-the-shoulder shot", "medium", "outro personagem", "ponto de vista oposto",
     "Reverse camera viewpoint, meaningful background separation.", "suspeita"),
    ("macro_action", "extreme lateral macro", "macro", "mão e objeto", "gesto decisivo",
     "Close-up of a purposeful gesture, complete hands and distinct composition.", "decisão"),
]


def direction(episode: dict, index: int, speech: str, role: str,
              previous: list[dict] | None = None, *, last: bool = False) -> dict:
    """Choose a distinct shot deterministically; no online model calls."""
    if index < 0:
        raise ValueError("Índice de enquadramento inválido")
    chess = episode.get("effect") == "chess"
    profiles = CHESS_SHOTS if chess else GENERAL_SHOTS
    choice = (5 if chess else 5) if last and index > 0 else index % len(profiles)
    seen = Counter(s["shot_type"] for s in (previous or []))
    # Never repeat the shot directly; never exceed 2 occurrences unless the
    # episode needs more images than the library can provide.
    previous_type = (previous or [{}])[-1].get("shot_type")
    for attempt in range(len(profiles)):
        candidate = profiles[(choice + attempt) % len(profiles)]
        if candidate[0] != previous_type and (seen[candidate[0]] < 2 or
                    len(previous or []) >= 2 * len(profiles)):
            break
    else:
        raise ValueError("Não foi possível selecionar um plano distinto")
    shot, angle, distance, focus, action, instruction, emotion = candidate
    if not chess:
        focus = episode.get("character", "personagem principal") if focus in (
            "personagens", "personagem principal", "personagem oposto",
            "outro personagem") else episode.get("object", "objeto importante")
        if shot in ("object_detail", "top_detail", "macro_action"):
            focus = episode.get("object", "objeto importante")
        action += ": " + speech[:125]
    # The user requested a king-move metaphor, NOT a claim that this literal
    # chess exchange occurs in the source anime.
    return {
        "shot_type": shot,
        "camera_angle": angle,
        "camera_distance": distance,
        "focus_subject": focus,
        "action": action,
        "emotion": emotion,
        "visual_instruction": instruction,
        "must_differ_from_previous": True,
        "avoid_repeating": [s["shot_type"] for s in (previous or [])[-2:]],
        "visual_direction_version": VERSION,
    }


def direction_prompt(episode: dict, selected: dict, *, previous: dict | None = None) -> str:
    """Put photographic direction FIRST so it cannot be lost in the generic prompt."""
    context = (f"VISUAL SHOT ID: {selected['shot_type']}. Camera: {selected['camera_angle']}; "
               f"distance: {selected['camera_distance']}; focal point: {selected['focus_subject']}; "
               f"visible ACTION: {selected['action']}; emotion: {selected['emotion']}. "
               f"{selected['visual_instruction']} ")
    if previous:
        context += (f"CRITICAL: Do NOT repeat the previous {previous['shot_type']} shot "
                    f"({previous['camera_angle']}). Change camera perspective, subject "
                    "scale, pose and dominant visual action. ")
    if episode.get("effect") == "chess":
        context += ("The chess moves are a cinematic METAPHOR for the intellectual conflict "
                    "in Death Note, not a factual claim of a literal televised chess game. "
                    "Show a single clear king and realistic chessboard perspective. ")
    return context


def storyboard_warnings(scenes: list[dict]) -> list[dict]:
    """Metadata-only QA: no automatic regeneration or credit use."""
    errors: list[dict] = []
    counts: Counter = Counter()
    for index, scene in enumerate(scenes):
        shot = scene.get("shot_type")
        if not shot:
            continue  # old production storyboards remain readable
        counts[shot] += 1
        prev = scenes[index-1] if index else None
        if prev and prev.get("shot_type") == shot:
            errors.append({"scene": scene["id"], "code": "plano_repetido_consecutivo",
                           "with_scene": prev["id"]})
        if prev and all(prev.get(k) == scene.get(k) for k in
                       ("camera_angle", "focus_subject", "action")):
            errors.append({"scene": scene["id"], "code": "direcao_visual_duplicada",
                           "with_scene": prev["id"]})
        if counts[shot] > 2 and len(scenes) <= 2 * max(1,len(CHESS_SHOTS)):
            errors.append({"scene": scene["id"], "code": "plano_usado_mais_de_duas_vezes",
                           "with_scene": None})
    return errors


def image_fingerprint(image: Path) -> tuple[int, list[int]]:
    """Lightweight grayscale perceptual fingerprint, computed offline."""
    # The storyboard planner needs no third-party packages; import PIL only
    # when evaluating an image in the generation/QA pipeline.
    from PIL import Image, ImageOps
    with Image.open(image) as source:
        gray=ImageOps.grayscale(source.convert("RGB"))
        small=list(gray.resize((9,8),Image.Resampling.BILINEAR).getdata())
        pixels=list(gray.resize((32,32),Image.Resampling.BILINEAR).getdata())
    bits=0
    for y in range(8):
        for x in range(8):
            bits=(bits << 1) | int(small[y*9+x] > small[y*9+x+1])
    return bits,pixels


def similar_masters(current: Path, previous: list[tuple[str,Path]],
                    *,max_hamming: int=7, max_mean_delta: float=13.0) -> list[dict]:
    """Conservative duplicate detector. Flag likely near-identical masters.

    This cannot prove different body poses are present; humans approve the QA.
    It never deletes files or requests paid retries.
    """
    if not current.is_file():
        return []
    current_hash, current_pixels=image_fingerprint(current)
    found=[]
    for scene_id, image in previous[-6:]:
        if not image.is_file():
            continue
        other_hash, other_pixels=image_fingerprint(image)
        distance=(current_hash^other_hash).bit_count()
        mean_delta=sum(abs(a-b) for a,b in zip(current_pixels,other_pixels))/len(current_pixels)
        if distance<=max_hamming and mean_delta<=max_mean_delta:
            found.append({"scene":scene_id,"hamming":distance,
                          "mean_luma_delta":round(mean_delta,2),
                          "code":"composicao_repetitiva"})
    return found
