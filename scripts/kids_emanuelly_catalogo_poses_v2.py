"""Pose catalog v2: reusable solo Emanuelly animation assets for Kids.

Keep the original eight pose prompts in the legacy generator unchanged:
their signatures protect already-paid approved images. New catalog prompts
show only Emanuelly and NEVER another character, egg, scenery, or prop.
"""
from __future__ import annotations

# New slugs only. Tuple = (English image-edit direction, PT-BR label).
EXTRA_POSES: dict[str, tuple[str, str]] = {
    # EP 01: magical blue egg, garden, bedroom. NO prop is rendered here.
    "brincando-jardim": (
        "Standing playful on tiptoe as if enjoying a garden, reaching one hand "
        "toward an INVISIBLE flower at hip height; no flowers or scenery.",
        "Brincando no jardim (sem flores no PNG)"),
    "abaixando": (
        "Mid-motion bending her knees to lower into a crouch, leaning forward "
        "with one arm naturally balancing; not already kneeling.",
        "Abaixando para investigar"),
    "pegando-ovo-chao": (
        "Squatting low with both hands cupped just above the ground to lift "
        "an INVISIBLE medium-sized egg; hands must not touch a drawn object.",
        "Pegando o ovo no chão (sem ovo)"),
    "andando-com-ovo": (
        "Walking carefully forward carrying one INVISIBLE medium-sized egg "
        "in both cupped hands close to her torso, steady head and legs in stride.",
        "Caminhando com o ovo invisível"),
    "colocando-ovo": (
        "Leaning toward an invisible low soft basket, gradually opening both "
        "hands to set down an INVISIBLE egg with care, knees slightly bent.",
        "Colocando o ovo na caminha"),
    "olhando-ovo-cesta": (
        "Kneeling beside an INVISIBLE little basket to her right, eyes angled "
        "down toward an unseen egg, hands relaxed and away from the basket.",
        "Observando o ovo na caminha"),
    "escutando-ovo": (
        "Kneeling with one hand gently near her ear as if listening to a "
        "quiet ticking from an INVISIBLE egg, alert kind face.",
        "Ouvindo as batidinhas do ovo"),
    "prometendo-cuidar": (
        "Standing with one hand resting on her heart and the other open "
        "toward an INVISIBLE egg, making a gentle caring promise.",
        "Prometendo cuidar"),
    # Carinho: toys/animals remain separate animation layers.
    "fazendo-carinho": (
        "Sitting comfortably and stroking the top of an INVISIBLE small plush "
        "friend at her knee height with one OPEN palm, one gentle continuous gesture.",
        "Fazendo carinho na cabeça de um amigo invisível"),
    "acariciando-cabeca": (
        "Kneeling with right palm gently stroking an INVISIBLE kitten's head "
        "at ankle-to-knee level, looking down affectionately, no kitten visible.",
        "Acariciando a cabeça de Fofinho sem desenhá-lo"),
    "abracando-pelucia": (
        "Sitting upright and wrapping both arms in a soft hug around an "
        "INVISIBLE small plush toy held at chest level, no visible object.",
        "Abraçando um bichinho de pelúcia invisível"),
    "abracando-de-lado": (
        "Standing and leaning slightly sideways for a friendly side hug "
        "toward an INVISIBLE friend, one arm curled protectively.",
        "Abraçando um amigo de lado"),
    "dando-beijinho": (
        "Sitting with lips gently puckered as if kissing the forehead of "
        "an INVISIBLE plush friend held just below her face, warm and child-safe.",
        "Dando um beijinho de carinho"),
    "consolando": (
        "Kneeling and offering one hand and an empathetic small smile to "
        "an INVISIBLE sad friend at her side, body language gently comforting.",
        "Consolando um amiguinho"),
    "ninando": (
        "Sitting with arms cradled around an INVISIBLE sleepy plush friend, "
        "gently rocking its unseen body in a soothing manner.",
        "Ninando um bichinho de pelúcia"),
    "sentada-carinho": (
        "Seated on an INVISIBLE low cushion, shoulders relaxed, leaning forward "
        "with both hands ready to lovingly pet a small unseen friend.",
        "Sentada oferecendo carinho"),
    # Faces and emotions; keep full-body reference and wardrobe unchanged.
    "sorrindo": (
        "Standing with a sweet small smile, relaxed shoulders and open posture, "
        "eyes bright but no huge exaggerated grin.",
        "Sorrindo delicadamente"),
    "rindo": (
        "Standing with a natural cheerful laugh, shoulders relaxed, one hand "
        "lightly touching the chest, expressive face without exaggerated features.",
        "Rindo de alegria"),
    "curiosa": (
        "Standing with a curious head tilt and slightly raised eyebrows, one "
        "hand near the chin while inspecting an INVISIBLE discovery.",
        "Curiosa e interessada"),
    "encantada": (
        "Standing with wide joyful eyes and open hands facing an INVISIBLE "
        "magical discovery, showing wonder but not fear.",
        "Encantada com a magia"),
    "preocupada": (
        "Standing quietly concerned, brow gently furrowed and hands held close "
        "to the chest, reassuring rather than frightened expression.",
        "Preocupada de leve"),
    "aliviada": (
        "Standing with shoulders settling after relief, a soft smile and both "
        "hands relaxed down, eyes peaceful.",
        "Aliviada e tranquila"),
    "triste": (
        "Sitting in a gentle, slightly slouched pose, downturned eyes and "
        "subtle sadness without tears or distressing body language.",
        "Tristinha, precisando de carinho"),
    "bocejando": (
        "Standing and covering a sleepy yawn with one palm, eyelids half "
        "closed, relaxed cozy bedtime expression.",
        "Bocejando com sono"),
    # Body mechanics / future animation keyframes.
    "correndo": (
        "Running with one knee raised and opposite arm forward, one foot off "
        "the ground; clear full-body mid-run silhouette, no speed-line background.",
        "Correndo alegremente"),
    "passinho-lateral": (
        "Mid-step moving sideways to the right, legs separated and both arms "
        "slightly extended for balance; a clear lateral silhouette.",
        "Dando um passo lateral"),
    "virando": (
        "Body rotating three-quarter toward her left while feet pivot, looking "
        "over her shoulder; NOT a duplicated front-facing standing pose.",
        "Virando para olhar atrás"),
    "agachando": (
        "Squatting low balanced on both feet with knees bent and palms near "
        "the thighs, a compact stable full-body silhouette.",
        "Agachando"),
    "levantando": (
        "Rising from a crouch with knees partly bent, torso upward and one "
        "hand balancing by her side, an intermediate stand-up pose.",
        "Levantando-se"),
    "pulando": (
        "Small joyful hop with both feet barely above an INVISIBLE floor, "
        "knees soft and arms raised, entire body visible with margins.",
        "Dando um pulinho"),
    "sentando": (
        "Mid-motion bending into an INVISIBLE low seat with knees bent "
        "and palms moving beside her hips, no chair drawn.",
        "Sentando-se"),
    "levantando-do-chao": (
        "Half-kneeling and pushing up carefully from the ground, one palm "
        "supporting, head raised, clear transitioning posture.",
        "Levantando do chão"),
    # Future play activities, still NO toy/flower/bubble rendered in PNG.
    "batendo-palmas": (
        "Standing with both palms meeting at chest level in a cheerful "
        "clap, fingers correctly positioned, face smiling.",
        "Batendo palminhas"),
    "dancando": (
        "Playful dance step with one knee bent and both arms gracefully "
        "lifted in different directions, lively but child-safe pose.",
        "Dançando"),
    "apontando": (
        "Standing with one arm extended to point toward an INVISIBLE object "
        "at her side, the other arm relaxed, interested smile.",
        "Apontando uma descoberta"),
    "soprando-bolha": (
        "Lips gently pursed as if blowing at an INVISIBLE soap bubble in "
        "front of her face, empty hands, no wand or bubble drawn.",
        "Soprando uma bolhinha invisível"),
    "esconde-esconde": (
        "Playfully covering her own eyes with both hands as though counting "
        "in hide-and-seek, gentle smile, no other character visible.",
        "Brincando de esconde-esconde"),
    "comemorando": (
        "Standing with both arms raised and a delighted smile celebrating "
        "a happy discovery, no confetti or objects.",
        "Comemorando uma conquista"),
    # Everyday actions with empty space for composited props.
    "dormindo": (
        "Lying peacefully on her side in a curled sleepy pose with eyes "
        "closed and hands tucked near the face; no bed or pillow drawn, "
        "same official clothes and hair.",
        "Dormindo tranquilamente"),
    "acordando": (
        "Sitting up after a nap, gently stretching both arms with a soft "
        "smile and sleepy eyes, no bed drawn.",
        "Acordando e se espreguiçando"),
    "lendo": (
        "Sitting upright with both hands separated as if supporting an "
        "INVISIBLE open book, eyes angled down toward the empty space.",
        "Lendo um livro invisível"),
    "regando-planta": (
        "Standing and tipping an INVISIBLE watering can with both hands "
        "toward an unseen plant near her feet, no water or can rendered.",
        "Regando uma plantinha invisível"),
    "cuidando-flores": (
        "Kneeling to inspect an INVISIBLE flower at ground level, one hand "
        "carefully reaching for the stem, no real flower drawn.",
        "Cuidando das flores"),
    "abrindo-porta": (
        "Standing in a three-quarter view, one hand gripping an INVISIBLE "
        "door handle and other arm balancing, no door drawn.",
        "Abrindo uma porta invisível"),
    "oferecendo-objeto": (
        "Standing with both hands open toward an INVISIBLE recipient, "
        "offering a small unseen gift at chest height, friendly expression.",
        "Oferecendo um presente invisível"),
    "ouvindo-atenta": (
        "Sitting still and leaning forward attentively, one hand cupped "
        "gently behind the ear, curious and welcoming expression.",
        "Escutando com atenção"),
}

# The core eight are kept as an unchanged backward-compatible group.
ESSENCIAIS = (
    "em-pe", "caminhando", "observando", "ajoelhada",
    "estendendo-mao", "segurando-ovo", "preparando-caminha", "surpresa",
)

EP01_EXTRAS = (
    "brincando-jardim", "abaixando", "pegando-ovo-chao",
    "andando-com-ovo", "colocando-ovo", "olhando-ovo-cesta",
    "escutando-ovo", "prometendo-cuidar",
)
CARINHO = (
    "fazendo-carinho", "acariciando-cabeca", "abracando-pelucia",
    "abracando-de-lado", "dando-beijinho", "consolando",
    "ninando", "sentada-carinho",
)
EMOCOES = (
    "sorrindo", "rindo", "curiosa", "encantada", "preocupada",
    "aliviada", "triste", "bocejando",
)
MOVIMENTO = (
    "correndo", "passinho-lateral", "virando", "agachando",
    "levantando", "pulando", "sentando", "levantando-do-chao",
)
BRINCADEIRAS = (
    "batendo-palmas", "dancando", "apontando", "soprando-bolha",
    "esconde-esconde", "comemorando",
)
COTIDIANO = (
    "dormindo", "acordando", "lendo", "regando-planta",
    "cuidando-flores", "abrindo-porta", "oferecendo-objeto",
    "ouvindo-atenta",
)

GROUPS: dict[str, tuple[str, ...]] = {
    "Essenciais": ESSENCIAIS,
    "Ep01": ESSENCIAIS + EP01_EXTRAS,
    "Carinho": CARINHO,
    "Emocoes": EMOCOES,
    "Movimento": MOVIMENTO,
    "Brincadeiras": BRINCADEIRAS,
    "Cotidiano": COTIDIANO,
    "Futuras": CARINHO + EMOCOES + MOVIMENTO + BRINCADEIRAS + COTIDIANO,
    "Todas": ESSENCIAIS + EP01_EXTRAS + CARINHO + EMOCOES
              + MOVIMENTO + BRINCADEIRAS + COTIDIANO,
}

# Sequence markers are metadata for future animation; still frames alone
# do NOT constitute rigging, tweening, or articulated character movement.
ANIMATION_SEQUENCES: dict[str, tuple[str, ...]] = {
    "encontrar-ovo": (
        "brincando-jardim", "observando", "curiosa", "abaixando",
        "ajoelhada", "estendendo-mao", "pegando-ovo-chao",
        "andando-com-ovo"),
    "acolher-ovo": (
        "preparando-caminha", "colocando-ovo", "olhando-ovo-cesta",
        "prometendo-cuidar", "escutando-ovo", "surpresa"),
    "carinho-fofinho": (
        "sentada-carinho", "fazendo-carinho", "acariciando-cabeca",
        "abracando-pelucia", "dando-beijinho", "ninando"),
    "brincadeira": (
        "em-pe", "caminhando", "correndo", "pulando",
        "batendo-palmas", "dancando", "comemorando"),
}


def choose(group: str, specific_pose: str = "Todas") -> list[str]:
    """Choose a safe ordered subset; a specific pose overrides group."""
    if specific_pose != "Todas":
        if specific_pose not in ESSENCIAIS and specific_pose not in EXTRA_POSES:
            raise ValueError("Pose desconhecida: " + specific_pose)
        return [specific_pose]
    if group not in GROUPS:
        raise ValueError("Grupo de poses desconhecido: " + group)
    return list(dict.fromkeys(GROUPS[group]))


def inventory() -> dict:
    return {
        "schema": "kids/emanuelly/pose-catalog/v2",
        "model": "gpt-image-2",
        "groups": {
            label: {
                "total": len(slugs),
                "poses": list(slugs),
            } for label, slugs in GROUPS.items()
        },
        "sequences_for_future_animation": {
            k: list(v) for k, v in ANIMATION_SEQUENCES.items()
        },
        "no_automatic_generation": True,
        "no_youtube_upload": True,
    }
