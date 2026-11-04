"""Safe offline reframe of GPT Image 2 character cutouts.

A warning about a near-edge alpha silhouette is not proof of clipping.
Recompose the SAME RGBA pixels at a smaller scale with safe margins.
Never invent missing limbs; flag source edge contact for human review.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image

SIZE = (1024, 1536)
MARGIN_X, MARGIN_Y = 88, 100
THRESHOLD = 75


def fit_transparent_pose(blob: bytes) -> tuple[bytes, dict]:
    """Return RGBA PNG and objective crop/reframe metadata (no AI calls).

    Only downscale/recenter if actual body pixels lie too close to an edge.
    The original bytes should remain cached separately, unchanged.
    """
    with Image.open(BytesIO(blob)) as input_image:
        input_image.load()
        if input_image.format != "PNG" or input_image.size != SIZE:
            raise ValueError("Enquadramento espera PNG RGBA 1024x1536")
        if "A" not in input_image.getbands():
            raise ValueError("Enquadramento exige transparência real")
        image = input_image.convert("RGBA")
    a = image.getchannel("A")
    # A tiny isolated anti-alias pixel must not trigger a full reframe.
    mask = a.point(lambda v: 255 if v >= THRESHOLD else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("Pose vazia: nenhum personagem visivel")
    left, top, right, bottom = bbox
    if (right - left) < 80 or (bottom - top) < 120:
        raise ValueError("Personagem pequeno ou incompleto para reposicionar")
    touches = (
        left <= 1 or top <= 1 or right >= SIZE[0] - 1 or bottom >= SIZE[1] - 1
    )
    near_margin = (
        left < MARGIN_X or right > SIZE[0] - MARGIN_X
        or top < MARGIN_Y or bottom > SIZE[1] - MARGIN_Y
    )
    details = {
        "strategy": "alpha_bbox_fit_no_new_pixels",
        "source_bounds": [left, top, right, bottom],
        "source_touches_canvas_edge": bool(touches),
        "source_may_already_be_cropped": bool(touches),
        "reframed": bool(near_margin),
    }
    if not near_margin:
        return blob, details
    # Never crop the subject: move only the alpha-containing region onto a
    # larger transparent margin, preserving its appearance and proportions.
    # Include faint anti-aliasing pixels around the visible silhouette.
    cropbox = (
        max(0, left - 7), max(0, top - 7),
        min(SIZE[0], right + 7), min(SIZE[1], bottom + 7),
    )
    cropped = image.crop(cropbox)
    max_width = SIZE[0] - 2 * MARGIN_X
    max_height = SIZE[1] - 2 * MARGIN_Y
    factor = min(1.0, max_width / cropped.width, max_height / cropped.height)
    new_dims = (max(1, round(cropped.width * factor)),
                max(1, round(cropped.height * factor)))
    if factor < 1.0:
        cropped = cropped.resize(new_dims, Image.Resampling.LANCZOS)
    # Consistent standing baseline / center alignment for character layers.
    x = round((SIZE[0] - cropped.width) / 2)
    y = min(SIZE[1] - MARGIN_Y - cropped.height,
            max(MARGIN_Y, round((SIZE[1] - cropped.height) / 2)))
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(cropped, (x, y))
    output = BytesIO()
    canvas.save(output, format="PNG")
    details["output_bounds"] = [x, y, x + cropped.width, y + cropped.height]
    details["scale"] = round(factor, 4)
    return output.getvalue(), details
