"""Four-short Fofinho origin: immutable scene and asset library.

Everything here is a PLAN. No assets are generated, assumed present, or
uploaded by importing this module. The characters debut when the story says
they debut, never when they are present on a reference sheet.
"""
from __future__ import annotations

import json
from pathlib import Path

SCHEMA = "kids/emanuelly/storyboard-fixed-assets/v2"
CANON_OLD = tuple(f"jardim-{i:02d}" for i in range(1, 5)) + tuple(
    f"quarto-{i:02d}" for i in range(1, 5)
) + ("ovo-azul",)

# Transparent objects are ALWAYS built and stored independently. It is
# forbidden to place a kitty or the egg in a full background PNG.
ASSETS = {
    "caminha-ovo": {
        "label": "Caminha de Fofinho: cesto, almofada e mantinha",
        "parent": "quarto-01", "transparent": True, "first_part": 1,
        "prompt": (
            "Create a SINGLE clean isolated children's storybook 3D prop: "
            "small cozy wicker oval nest with soft neutral pillow and pale blue "
            "blanket, following the exact art style, materials and lighting of "
            "this room. The nest should appear empty, no child, no egg, no "
            "animal, no scenery. Perspective three-quarter front view, "
            "whole object shown, generous margins, REAL transparent PNG."
        ),
    },
    "ovo-rachado": {
        "label": "O MESMO ovo azul com pequenas rachaduras",
        "parent": "ovo-azul", "transparent": True, "first_part": 2,
        "prompt": (
            "EDIT THE EXACT SAME BLUE DRAGON EGG from the source. Preserve "
            "the same teardrop drawings, dimensions, color, glossy surface "
            "and silhouette. Add ONLY two delicate faint cracks in its shell. "
            "The egg is NOT open, no creature visible. Exactly ONE egg with "
            "real transparent background, same centered object scale."
        ),
    },
    "ovo-aberto": {
        "label": "O MESMO ovo azul abrindo a casca, ainda sem Fofinho",
        "parent": "ovo-azul", "transparent": True, "first_part": 2,
        "prompt": (
            "EDIT THE SAME blue dragon egg from the source: exact color, "
            "water droplet pattern, thickness, scale. Its top shell has JUST "
            "opened gently, revealing a soft interior glow but ABSOLUTELY "
            "NO animal, kitten or character inside. Keep shell halves as "
            "ONE isolated asset, true transparent PNG, no text or backdrop."
        ),
    },
    "fofinho-azul": {
        "label": "Fofinho: gatinho de pelúcia AZUL oficial isolado",
        "parent": "referencia-dupla", "transparent": True, "first_part": 2,
        "prompt": (
            "The source contains Emanuelly and her blue plush kitten FOFINHO. "
            "Extract ONLY the SAME little BLUE PLUSH KITTEN FOFINHO as ONE "
            "full-body isolated 3D storybook character, preserving his exact "
            "face, fabric, ears, eyes, paws and blue color. Remove Emanuelly "
            "entirely. No other cats, no rainbow or pink kittens, no wildcat, "
            "no hedgehog. No floor, egg, room, text, second subject or props. "
            "True transparent background with generous margins."
        ),
    },
    "fofinho-miando": {
        "label": "Fofinho original com boquinha de miau",
        "parent": "fofinho-azul", "transparent": True, "first_part": 2,
        "prompt": (
            "EDIT this EXACT same blue plush kitten, without changing his "
            "identity, color, fabric, size or hairstyle. One delighted small "
            "MEOW expression with mouth slightly open; natural ears, soft paws, "
            "same full body and original style. One subject on a transparent "
            "PNG, no other character, no text, no background."
        ),
    },
    "fofinho-patinhas": {
        "label": "Fofinho mexendo as patinhas (pose)",
        "parent": "fofinho-azul", "transparent": True, "first_part": 2,
        "prompt": (
            "EDIT this EXACT same blue plush kitten in a playful position "
            "with both soft little front paws raised as if gently clapping, "
            "still one full-body character. Preserve his face, blue plush "
            "texture, proportions and child-friendly gentle expression. "
            "Transparent PNG, no extra limbs or characters."
        ),
    },
    "fofinho-aconchegado": {
        "label": "Fofinho descansando, mesmo personagem de pelúcia",
        "parent": "fofinho-azul", "transparent": True, "first_part": 4,
        "prompt": (
            "EDIT this EXACT same blue plush kitten curled up softly and "
            "sleepily, as if resting on a small invisible pillow. Preserve "
            "face and blue fabric, no pillow actually drawn, no person, "
            "transparent background, entire silhouette visible."
        ),
    },
    "gotinha-agua": {
        "label": "Uma gotinha azul mágica isolada",
        "parent": "ovo-azul", "transparent": True, "first_part": 2,
        "prompt": (
            "Using the blue and water-droplet motif of the same egg, create "
            "ONE single charming transparent glowing blue WATER DROPLET, "
            "not an egg, not a character, not a face, no text, "
            "on genuine transparent PNG. No multiple droplets."
        ),
    },
}

# Deferred ensemble assets, not needed for Fofinho EP01.
FUTURE_CAST = {
    "fofinha-arco-iris": {
        "label": "Fofinha Arco-Íris, irmã gêmea nascida UM ANO após Fofinho",
        "earliest": "episodio_futuro",
    },
    "fofinha-rosa": {
        "label": "Fofinha Rosa, irmã gêmea da Arco-Íris",
        "earliest": "episodio_futuro",
    },
    "raposo": {
        "label": "Raposo, onça de pelúcia, apresentação em episódio futuro",
        "earliest": "episodio_futuro",
    },
    "porco-espinho": {
        "label": "Porco-espinho de pelúcia, estreia em episódio futuro",
        "earliest": "episodio_futuro",
    },
}


def shot(index: int, backdrop: str, pose: str | None = None,
         *, egg: str = "none", kitty: str | None = None,
         nest: bool = False, drops: int = 0, magic: bool = False,
         night: bool = False, future_glow: bool = False,
         movement: str = "still", kitten_motion: str = "idle") -> dict:
    return {
        "index": index, "backdrop": backdrop, "pose": pose, "egg_phase": egg,
        "kitty": kitty, "nest": nest, "drops": drops, "magic": magic,
        "night": night, "future_glow": future_glow,
        "movement": movement, "kitten_motion": kitten_motion,
    }


# O episodio 2 nao limita a quantidade de cenas visuais. Elas sao
# independentes dos blocos da narracao e podem ser ampliadas por direcao.
PART2_DIRECTION=Path(__file__).resolve().parents[1]/"conteudos/fofinhos-ep01-parte02-direcao-v2.json"
MANIFEST=Path(__file__).resolve().parents[1]/"conteudos/kids-emanuelly-ep01-shortserie-v1.json"


def dynamic_birth_storyboard() -> tuple[dict, ...]:
    data=json.loads(PART2_DIRECTION.read_text(encoding="utf-8"))
    if data.get("schema")!="fofinhos/parte02-direcao-visual/v2":
        raise ValueError("Direcao visual do nascimento nao reconhecida")
    raw=data.get("shots",[])
    if not isinstance(raw,list) or not raw:
        raise ValueError("Episodio 2 sem planos visuais")
    output=[]
    previous_beat=0
    for number,item in enumerate(raw,1):
        beat=item.get("beat")
        if item.get("index")!=number or not isinstance(beat,int) or beat<previous_beat or beat<1:
            raise ValueError("Planos do nascimento fora de ordem")
        previous_beat=beat
        view=shot(number,item["backdrop"],item.get("pose"),
                  egg=item.get("egg_phase","none"),kitty=item.get("kitty"),
                  nest=item.get("nest",False),drops=item.get("drops",0),
                  magic=item.get("magic",False),night=item.get("night",False),
                  future_glow=item.get("future_glow",False),
                  movement=item.get("movement","still"),
                  kitten_motion=item.get("kitten_motion","idle"))
        weight=float(item.get("shot_weight",1))
        if not 0<weight<=10:
            raise ValueError("Duracao relativa invalida no plano "+str(number))
        view.update(beat=beat,shot_weight=weight,
                    visual_cue=item["visual_cue"],
                    sfx_cue=item.get("sfx_cue",""),
                    framing=item.get("framing","two-shot"),
                    camera_motion=item.get("camera_motion","still"))
        output.append(view)
    return tuple(output)


STORYBOARDS: dict[int, tuple[dict, ...]] = {
    1: (
        shot(1, "jardim-01", egg="closed", magic=True),
        shot(2, "jardim-02", "caminhando", egg="closed", movement="walk"),
        shot(3, "jardim-03", "observando", egg="closed", magic=True),
        shot(4, "jardim-04", "estendendo-mao", egg="closed", movement="approach"),
        shot(5, "jardim-01", "segurando-ovo", egg="closed", movement="lift"),
        shot(6, "quarto-01", "preparando-caminha", egg="closed",
             nest=True, movement="prepare"),
        shot(7, "quarto-02", "prometendo-cuidar", egg="closed", nest=True,
             movement="promise"),
        shot(8, "quarto-03", "surpresa", egg="closed", nest=True,
             night=True, movement="rock"),
        shot(9, "quarto-04", "estendendo-mao", egg="closed", nest=True,
             night=True, movement="wonder"),
    ),
    2: dynamic_birth_storyboard(),
    3: (
        shot(1, "quarto-04", "encantada", kitty="fofinho-patinhas", drops=1),
        shot(2, "quarto-03", "observando", kitty="fofinho-patinhas",
             drops=1, kitten_motion="paws"),
        shot(3, "quarto-02", "surpresa", kitty="fofinho-azul",
             drops=3, magic=True),
        shot(4, "quarto-01", "observando", kitty="fofinho-azul",
             drops=3, magic=True),
        shot(5, "jardim-01", "encantada", kitty="fofinho-azul",
             drops=3, magic=True),
        shot(6, "jardim-02", "rindo", kitty="fofinho-patinhas",
             drops=1, magic=True),
        shot(7, "jardim-03", "rindo", kitty="fofinho-azul", drops=3),
        shot(8, "jardim-04", "brincando-jardim", kitty="fofinho-patinhas",
             kitten_motion="hop"),
        shot(9, "jardim-02", "fazendo-carinho", kitty="fofinho-azul",
             kitten_motion="snuggle"),
    ),
    4: (
        shot(1, "jardim-01", "triste", kitty="fofinho-azul",
             kitten_motion="approach"),
        shot(2, "jardim-02", "sentada-carinho", kitty="fofinho-azul",
             kitten_motion="snuggle"),
        shot(3, "jardim-03", "surpresa", kitty="fofinho-patinhas",
             drops=1, kitten_motion="paws"),
        shot(4, "jardim-04", "sorrindo", kitty="fofinho-azul",
             kitten_motion="hop"),
        shot(5, "quarto-01", "abracando-pelucia", kitty="fofinho-azul",
             night=True, kitten_motion="snuggle"),
        shot(6, "quarto-02", "fazendo-carinho", kitty="fofinho-azul",
             night=True, kitten_motion="snuggle"),
        shot(7, "quarto-03", "observando", kitty="fofinho-aconchegado",
             nest=True, night=True),
        shot(8, "quarto-04", "sorrindo", kitty="fofinho-azul",
             night=True, magic=True),
        shot(9, "quarto-04", future_glow=True, magic=True, night=True),
    ),
}


def validate_storyboard() -> None:
    if len(STORYBOARDS) != 4:
        raise ValueError("A origem de Fofinho deve ter quatro Partes")
    for part, scenes in STORYBOARDS.items():
        if [s["index"] for s in scenes] != list(range(1, len(scenes) + 1)):
            raise ValueError("Quadros fora de ordem: parte " + str(part))
        for s in scenes:
            if s["backdrop"] not in CANON_OLD[:-1]:
                raise ValueError("Cenario nao oficial: " + s["backdrop"])
            if s["egg_phase"] not in ("closed", "cracked", "open", "none"):
                raise ValueError("Estado do ovo desconhecido")
            if part == 1 and s["kitty"]:
                raise ValueError("Fofinho NAO existe visivelmente na Parte 1")
            if part == 2 and s["beat"] < 6 and s["kitty"]:
                raise ValueError("Fofinho so aparece apos o ovo abrir, no beat 06")
            if part == 2 and s["beat"] > 6 and s["egg_phase"] != "none":
                raise ValueError("O ovo nao pode continuar em cena apos a revelacao")
            if part == 2 and s["beat"] < 8 and s["drops"]:
                raise ValueError("A primeira gotinha nao pode aparecer antes do primeiro miau")
            if part >= 3 and s["egg_phase"] != "none":
                raise ValueError("Ovo original nao reaparece depois do nascimento")
            if s["kitty"] and s["kitty"] not in ASSETS:
                raise ValueError("Referencia de Fofinho nao conhecida")
            if s["drops"] < 0 or (part == 1 and s["drops"]):
                raise ValueError("Poder da agua nao aparece antes do nascimento")
    # Plano e fala NAO sao sinonimos: a Parte 2 aceita N planos para cada fala.
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8"))
    beats_count=len(manifest["parts"][1]["segments"])
    birth=STORYBOARDS[2]
    if set(s["beat"] for s in birth)!=set(range(1,beats_count+1)):
        raise ValueError("Toda fala da Parte 2 deve receber pelo menos um plano visual")
    if not any(s["beat"]==6 and s["kitty"] for s in birth):
        raise ValueError("Nascimento do Fofinho nao esta visivel no beat 06")
    if not any(s["beat"]==8 and s["drops"]==1 for s in birth):
        raise ValueError("O primeiro poder de agua deve surgir antes de receber o nome")
    if STORYBOARDS[1][0]["pose"] is not None:
        raise ValueError("O PRIMEIRO quadro e somente ovo e jardim")
    if STORYBOARDS[4][-1]["kitty"] is not None:
        raise ValueError("Nao revelar filhotes ou Fofinho na visao do futuro")


def resource_names(part: int) -> tuple[list[str], list[str]]:
    if part not in STORYBOARDS:
        raise ValueError("Parte invalida")
    scenes=STORYBOARDS[part]
    assets=set()
    poses=set()
    for s in scenes:
        assets.add(s["backdrop"])
        if s["egg_phase"]=="closed":assets.add("ovo-azul")
        if s["egg_phase"]=="cracked":assets.add("ovo-rachado")
        if s["egg_phase"]=="open":assets.add("ovo-aberto")
        if s["nest"]:assets.add("caminha-ovo")
        if s["kitty"]:assets.add(s["kitty"])
        if s["drops"]:assets.add("gotinha-agua")
        if s["pose"]:poses.add(s["pose"])
    return sorted(assets), sorted(poses)


def inventory() -> dict:
    validate_storyboard()
    chapters={}
    for number,scenes in STORYBOARDS.items():
        assets,poses=resource_names(number)
        chapters[str(number)]={
            "part":number,"beats":len(scenes),
            "images":assets,"emanuelly_poses":poses,
            "characters_after_birth":number>=2,
            "storyboard":list(scenes),
        }
    return {
        "schema":SCHEMA,
        "parts":chapters,
        "official_scenery":list(CANON_OLD),
        "additional_assets":ASSETS,
        "future_characters_deferred":FUTURE_CAST,
        "future_characters_allowed_in_EP01":False,
        "image_model_if_generation_explicit":"gpt-image-2",
        "no_automatic_generation":True,
        "no_upload":True,
    }
