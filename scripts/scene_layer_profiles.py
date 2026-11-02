"""Per-scene semantic layer profiles with an explicit physical Z order.

A profile describes desired extractions; it does NOT claim that an AI already
detected a person or verified anatomy. Human review remains mandatory.
"""
from __future__ import annotations

from dataclasses import dataclass

SCHEMA="arquivo-otaku/scene-layers/v1"
PROFILES="arquivo-otaku/table-occlusion/v1"


@dataclass(frozen=True)
class Layer:
    id: str
    role: str
    z: int
    prompt: str


def is_chess(ep:dict,scene:dict)->bool:
    return ep.get("effect")=="chess" or scene.get("shot_type") in {
        "wide_duel","ots_light","ots_l","light_moves_king","l_moves_king",
        "l_reaction","light_reaction","final_checkmate","top_board",
        "king_hand_macro","close_reaction_l","close_reaction_kira",
    }


def layer_profile(ep:dict,scene:dict)->list[Layer]:
    """Return distinct object/character masks in a stable, explicit order."""
    if not is_chess(ep,scene):
        return [Layer("subject","front_character",40,
                      "Extract ONLY the main visible subject of this scene; "
                      "do not include furniture or other people.")]
    shot=scene.get("shot_type","")
    if shot in ("ots_light","wide_duel","final_checkmate"):
        characters=[("l","back_character",10),("light","front_character",40)]
    elif shot in ("ots_l","l_moves_king"):
        characters=[("light","back_character",10),("l","front_character",40)]
    elif shot in ("l_reaction","close_reaction_l"):
        characters=[("l","back_character",10)]
    elif shot in ("light_moves_king","light_reaction","close_reaction_kira",
                  "king_hand_macro"):
        characters=[("light","front_character",40)]
    elif shot=="top_board":
        characters=[]
    else:
        characters=[("l","back_character",10),("light","front_character",40)]
    layers=[
        Layer("table","occluder",20,
              "Isolate ONLY the physical chess table: tabletop, front rim, "
              "table legs and structural wood. Do not include the chessboard, "
              "chess pieces, clothing, faces, hands, hair or chairs."),
        Layer("board","object",30,
              "Isolate ONLY the rectangular chessboard and its 64 squares. "
              "Do not include the table, people, hands, pieces or room."),
    ]
    for name,role,z in characters:
        who="Light Yagami (brown hair, dark jacket)" if name=="light" else (
            "L Lawliet (shaggy black hair, white long-sleeve shirt)")
        layers.append(Layer(name,role,z,
            f"Extract ONLY the visible pixels of {who}. "
            "Do not include the other person, furniture, chessboard or "
            "chess pieces. Never hallucinate anatomy hidden behind the table."))
    if shot in ("light_moves_king","l_moves_king","king_hand_macro"):
        who="Light" if shot=="light_moves_king" else "L"
        layers.append(Layer("king_hand","hero_prop",50,
            f"Extract the exact hand of {who} while it touches the chess KING "
            "and the complete chess king itself as one foreground action. "
            "Do NOT include the board, table, other person or background. "
            "Preserve the entire piece including crown and base."))
    return sorted(layers,key=lambda x:x.z)


def mask_prompt(layer:Layer)->str:
    return (
        "PRECISION ALPHA SEGMENTATION, never an illustration or a new pose. "
        "Input is the scene MASTER image. Preserve the EXACT same canvas "
        "1024x1536 and original XY coordinates. Return PNG RGBA with all "
        "non-target pixels transparent and ONLY target pixels opaque. "
        +layer.prompt+" "
        "Do not add body parts, move any objects, create shadows or extend "
        "occluded surfaces. An object behind a table must stay behind it. "
        "IMPORTANT: Output pixels are used ONLY as an alpha mask; their color "
        "will be discarded and original MASTER pixels restored. "
        "Use smooth precise borders with no halos or table fragments."
    )


def background_prompt()->str:
    return (
        "Create an EMPTY clean plate of the SAME room and exact same camera "
        "angle as the input photo. Inpaint ONLY the masked foreground people, "
        "table, chessboard, hands and chess pieces, leaving unmasked walls, "
        "lights, furniture and architecture unchanged. Remove every fragment. "
        "No people, no extra furniture, no split screen, no text. Return the "
        "original 1024x1536 canvas."
    )
