"""Offline compositing and geometric safety checks for semantic scene layers."""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageStat

from scene_layer_profiles import Layer

SIZE=(1024,1536)
MAX_MEAN_DIFFERENCE=32.0
OVERLAP_REVIEW_PREFIX="personagem_atras_sobre_tabuleiro:"


def classify_qa_alerts(qa:dict)->tuple[list[str],list[str]]:
    """Split blocking image defects from ambiguous mask collisions.

    Previous versions stored ALL alerts in qa.warnings. Do not alter paid
    cache manifests just to reclassify a mask overlap; approvals are tied to
    the manifest hash. Unknown warnings fail closed.
    """
    blocking=[]
    review=list(qa.get("review_warnings",[]))
    for warning in qa.get("warnings",[]):
        if warning.startswith(OVERLAP_REVIEW_PREFIX):
            if warning not in review:
                review.append(warning)
        elif warning not in blocking:
            blocking.append(warning)
    return blocking,review


def exact_layer(master:Path,mask_raw:bytes)->bytes:
    """Discard AI-painted RGB. Only alpha from segmentation is trustworthy."""
    with Image.open(master) as src, Image.open(io.BytesIO(mask_raw)) as proposal:
        if src.size!=SIZE or proposal.size!=SIZE:
            raise ValueError("Dimensoes das camadas devem ser exatamente 1024x1536")
        if "A" not in proposal.getbands():
            raise ValueError("A edicao nao retornou PNG com transparencia real")
        alpha=proposal.getchannel("A")
        extrema=alpha.getextrema()
        if not extrema or extrema[1]<50:
            raise ValueError("Mascara vazia; nenhuma chamada adicional automatica")
        # Guard against an opaque all-scene generation.
        hist=alpha.histogram()
        coverage=sum(hist[128:])/float(SIZE[0]*SIZE[1])
        if coverage>.88:
            raise ValueError("Mascara cobre mais de 88% da imagem; rejeitar extracao")
        image=src.convert("RGBA")
        image.putalpha(alpha)
        buf=io.BytesIO()
        image.save(buf,format="PNG",optimize=True)
        return buf.getvalue()


def union_inpaint_mask(layers:list[Path])->bytes:
    """OpenAI edit mask: transparent where filling is required."""
    union=Image.new("L",SIZE,0)
    for file in layers:
        with Image.open(file) as im:
            if im.size!=SIZE or "A" not in im.getbands():
                raise ValueError("Camada nao e RGBA valida: "+str(file))
            union=ImageChops.lighter(union,im.getchannel("A"))
    # Only modest padding: preserve table/board perspective in unmasked pixels.
    union=union.filter(ImageFilter.MaxFilter(11))
    mask=Image.new("RGBA",SIZE,(255,255,255,255))
    from PIL import ImageOps
    mask.putalpha(ImageOps.invert(union))
    out=io.BytesIO()
    mask.save(out,format="PNG",optimize=True)
    if out.tell()>4_000_000:
        raise ValueError("Mascara de inpainting acima de 4 MB")
    return out.getvalue()


def normalize_clean_plate(master:Path,edit_raw:bytes,mask:bytes)->bytes:
    """Preserve untouched image pixels; inpaint only removed objects."""
    with Image.open(master) as src, Image.open(io.BytesIO(edit_raw)) as replacement, Image.open(io.BytesIO(mask)) as mp:
        if replacement.size!=SIZE or src.size!=SIZE:
            raise ValueError("Clean plate com resolucao invalida")
        import PIL.ImageOps
        to_replace=PIL.ImageOps.invert(mp.getchannel("A"))
        result=Image.composite(replacement.convert("RGB"),src.convert("RGB"),to_replace)
        result.save(out:=io.BytesIO(),format="PNG",optimize=True)
    return out.getvalue()


def compose(background:Path,ordered:list[tuple[Layer,Path]])->Image.Image:
    with Image.open(background) as bg:
        if bg.size!=SIZE:raise ValueError("Fundo com dimensoes invalidas")
        target=bg.convert("RGBA")
    for layer,file in sorted(ordered,key=lambda x:x[0].z):
        with Image.open(file) as src:
            if src.size!=SIZE or "A" not in src.getbands():
                raise ValueError("Camada incompatível: "+str(file))
            target=Image.alpha_composite(target,src.convert("RGBA"))
    return target.convert("RGB")


def qa_multilayer_geometry(master:Path,background:Path,ordered:list[tuple[Layer,Path]])->dict:
    if not ordered:raise ValueError("Nenhuma camada para verificar")
    if len({layer.z for layer,_ in ordered})!=len(ordered):
        raise ValueError("Camadas com a mesma ordem Z")
    by_id={layer.id:(layer,file) for layer,file in ordered}
    if "board" in by_id and "table" in by_id:
        if by_id["board"][0].z<=by_id["table"][0].z:
            raise ValueError("O tabuleiro precisa estar a frente da mesa na pilha Z")
    with Image.open(master) as original:
        if original.size!=SIZE:raise ValueError("Master invalida")
        base=original.convert("RGB")
    composed=compose(background,ordered)
    diff=ImageChops.difference(base,composed)
    mean=round(sum(ImageStat.Stat(diff.resize((256,384))).mean)/3,2)
    warnings=[]
    review_warnings=[]
    if mean>MAX_MEAN_DIFFERENCE:
        warnings.append("recomposicao_distante_da_master")
    # Masks overlapping the board do not automatically imply penetration:
    # a player's hand may legally be touching a chess piece. Expose the
    # conflicting area for visual review rather than guessing anatomy.
    overlaps=[]
    if "board" in by_id:
        with Image.open(by_id["board"][1]) as board:
            board_alpha=board.getchannel("A").point(lambda a:255 if a>128 else 0)
            board_area=sum(board_alpha.histogram()[128:])
        for layer,file in ordered:
            if layer.role!="back_character":continue
            with Image.open(file) as fg:
                back_alpha=fg.getchannel("A").point(lambda a:255 if a>128 else 0)
            crossing=ImageChops.darker(board_alpha,back_alpha)
            fraction=round(sum(crossing.histogram()[128:])/max(1,board_area),4)
            overlaps.append({"character":layer.id,"board_fraction":fraction})
            if fraction>.025:
                # A back-character mask can include a hand over the board or
                # hidden torso pixels. The board has a HIGHER Z and masks
                # this overlap in the actual render. A mask collision is not
                # proof of a visible anatomical error. Flag it for human
                # review instead of automatically rejecting a good preview.
                review_warnings.append(OVERLAP_REVIEW_PREFIX+layer.id)
    return {
        "status":"revisao_obrigatoria",
        "master_composite_mean_difference":mean,
        "overlap_with_board":overlaps,
        "warnings":warnings,
        "review_warnings":review_warnings,
        "manual_approval_required":True,
        "notes":"Comparacao geometrica nao detecta todas as poses impossiveis; revisar visualmente master, camadas e preview",
    }
