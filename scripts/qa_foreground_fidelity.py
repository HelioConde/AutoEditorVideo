"""Conservative QA: verify that the extracted character matches source pixels.

An alpha-extraction must not invent new arms, faces, clothes or chessboards.
Compare before any intentional foreground shift or scale. No AI calls.
"""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image


def foreground_fidelity(master:Path,foreground:Path|bytes)->dict:
    import numpy as np
    with Image.open(master) as im:
        reference=np.asarray(
            im.convert('RGB').resize((256,384),Image.Resampling.BILINEAR),dtype=np.int16)
    source=io.BytesIO(foreground) if isinstance(foreground,bytes) else foreground
    with Image.open(source) as im:
        layer=np.asarray(
            im.convert('RGBA').resize((256,384),Image.Resampling.BILINEAR),dtype=np.int16)
    opaque=layer[:,:,3]>=180
    if not opaque.any():
        return {'status':'inconclusivo','redrawn':False,
                'render_recommendation':'master_static','review_required':True}
    delta=np.abs(reference-layer[:,:,:3]).mean(axis=2)
    mean=float(delta[opaque].mean())
    fraction=float((delta[opaque]>50).mean())
    lower=opaque[192:,:]
    below=delta[192:,:]
    lower_mean=float(below[lower].mean()) if lower.any() else 0.
    lower_fraction=float((below[lower]>50).mean()) if lower.any() else 0.
    # Conservative: tolerate modest color grading / compression variation.
    # A severe mismatch in the lower half often indicates invented torso/table.
    redrawn=(mean>=45 and fraction>=.32) or (
        lower_mean>=70 and lower_fraction>=.52 and float(lower.mean())>=.15)
    return {
        'status':'redesenho_detectado' if redrawn else 'sem_redesenho_significativo_detectado',
        'redrawn':bool(redrawn),
        'opaque_fraction':round(float(opaque.mean()),3),
        'mean_difference':round(mean,2),
        'fraction_above_50':round(fraction,3),
        'lower_half_mean_difference':round(lower_mean,2),
        'lower_half_fraction_above_50':round(lower_fraction,3),
        'render_recommendation':'master_static' if redrawn else '2_5d_layers',
        'review_required':bool(redrawn),
        'method':'unshifted_foreground_vs_original_master_pixels',
        'limitation':'Heuristica conservadora; exige inspecao visual e nao detecta todos os erros anatomicos',
    }
