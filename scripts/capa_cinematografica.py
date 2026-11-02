#!/usr/bin/env python3
"""Reusable, offline cinematic 9:16 covers for Arquivo Otaku.

The reference style is a high-impact anime duel: enlarged main subjects,
blue/red edge light, chess-like visual tension and large two-line white titles.
This generator never invents new character poses and never calls an image API.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

SIZE = (1080, 1920)
SCHEMA = 'arquivo-otaku/cover-design/v1'
STYLE = 'duelo-cinematografico'


def cover_options(root: Path, episode_id: str) -> dict:
    path = root / 'configs' / 'cover-design.json'
    if not path.is_file():
        return {'style': STYLE, 'zoom': 1.07, 'focus_x': .5, 'focus_y': .4}
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schema') != SCHEMA:
        raise ValueError('Config de capa: schema nao reconhecido')
    values = {**data.get('default', {}), **data.get('episodes', {}).get(episode_id, {})}
    if values.get('style') != STYLE:
        raise ValueError('Estilo de capa nao suportado')
    if (type(values.get('zoom', 1.07)) not in (int, float)
            or not 1.0 <= values.get('zoom', 1.07) <= 1.4):
        raise ValueError('Zoom da capa precisa estar entre 1.0 e 1.4')
    for key in ('focus_x', 'focus_y'):
        if type(values.get(key, .5)) not in (int, float) or not 0 <= values.get(key, .5) <= 1:
            raise ValueError('Foco da capa precisa estar entre 0 e 1')
    scene = values.get('scene')
    if scene is not None and (not isinstance(scene, str) or
                              not re.fullmatch(r'\d{2}', scene)):
        raise ValueError('Cena da capa deve ter ID de dois digitos')
    return values


def font_path() -> str | None:
    """Try real editorial display faces on Windows and Linux CI."""
    paths = [
        'C:/Windows/Fonts/georgiab.ttf',
        'C:/Windows/Fonts/Georgia.ttf',
        'C:/Windows/Fonts/impact.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf',
        '/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    ]
    return next((p for p in paths if Path(p).is_file()), None)


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    face = font_path()
    if face:
        return ImageFont.truetype(face, size)
    return ImageFont.load_default(size=size)


def text_lines(title: str, draw: ImageDraw.ImageDraw, size: int,
               width: int = 970) -> list[str]:
    words = title.split()
    if not words:
        raise ValueError('A capa precisa de um titulo')
    font = load_font(size)
    if len(words) == 1:
        return words
    # Keep a short hook impactful in TWO centred rows, like the reference.
    # For longer hooks, preserve every word in at most three rows.
    rows = min(3, max(2, math.ceil(len(title) / 22)))
    if rows == 2:
        splits = range(1, len(words))
        options = [[ ' '.join(words[:s]), ' '.join(words[s:]) ] for s in splits]
        valid = [ls for ls in options if all(draw.textbbox((0,0), ln, font=font,
                   stroke_width=0)[2] <= width for ln in ls)]
        if valid:
            return min(valid, key=lambda ls:
                       max(draw.textbbox((0,0), ln, font=font)[2] for ln in ls) -
                       min(draw.textbbox((0,0), ln, font=font)[2] for ln in ls))
    lines: list[str] = []
    for word in words:
        proposed = (lines[-1] + ' ' + word) if lines else word
        if lines and draw.textbbox((0,0), proposed, font=font)[2] > width:
            lines.append(word)
        elif lines:
            lines[-1] = proposed
        else:
            lines.append(word)
    return lines


def title_layout(draw: ImageDraw.ImageDraw, title: str) -> tuple[list[str], ImageFont.ImageFont, int]:
    for size in range(142, 53, -2):
        font = load_font(size)
        lines = text_lines(title, draw, size)
        heights = [draw.textbbox((0,0), row, font=font, stroke_width=2)[3] -
                   draw.textbbox((0,0), row, font=font, stroke_width=2)[1] for row in lines]
        if (len(lines) <= 3 and max(draw.textbbox((0,0), row, font=font,
            stroke_width=2)[2] for row in lines) <= 960
                and sum(heights) + (len(lines)-1)*12 <= 330):
            return lines, font, size
    raise ValueError('Titulo da capa longo demais para o layout seguro')


def zoom_cover(im: Image.Image, zoom: float, center_x: float, center_y: float) -> Image.Image:
    base = ImageOps.fit(im.convert('RGB'), SIZE, method=Image.Resampling.LANCZOS,
                        centering=(center_x, center_y))
    if zoom == 1:
        return base
    bigger = base.resize((round(SIZE[0]*zoom),round(SIZE[1]*zoom)),
                         Image.Resampling.LANCZOS)
    x = round((bigger.width-SIZE[0]) * center_x)
    y = round((bigger.height-SIZE[1]) * center_y)
    return bigger.crop((x,y,x+SIZE[0],y+SIZE[1]))


def add_cinematic_grade(image: Image.Image) -> Image.Image:
    result = ImageEnhance.Contrast(image).enhance(1.12)
    result = ImageEnhance.Color(result).enhance(1.17)
    # Blue vs red lighting is part of the reusable identity, not a baked image.
    tint=Image.new('RGBA',SIZE,(0,0,0,0))
    painter=ImageDraw.Draw(tint)
    for x in range(SIZE[0]):
        d=abs(x-(SIZE[0]-1)/2)/((SIZE[0]-1)/2)
        alpha=round(24*(d*d))
        painter.line((x,0,x,SIZE[1]),
                     fill=(12,88,190,alpha) if x<SIZE[0]/2 else (215,19,32,alpha))
    result=Image.alpha_composite(result.convert('RGBA'),tint)
    # Gentle vignette makes faces and the chessboard the focal point.
    darkness=Image.new('RGBA',SIZE,(0,0,0,0))
    d=ImageDraw.Draw(darkness)
    d.rectangle((0,0,SIZE[0],160),fill=(1,3,10,55))
    shadow=Image.new('RGBA',SIZE,(0,0,0,0))
    ds=ImageDraw.Draw(shadow)
    ds.rounded_rectangle((-210,160,1290,1880),radius=320,
                         outline=(0,0,0,110),width=180)
    shadow=shadow.filter(ImageFilter.GaussianBlur(110))
    return Image.alpha_composite(Image.alpha_composite(result,shadow),darkness)


def draw_title(canvas: Image.Image, text: str) -> Image.Image:
    if len(text.strip()) > 90:
        raise ValueError('Titulo da capa excede 90 caracteres')
    panel=Image.new('RGBA',SIZE,(0,0,0,0))
    painter=ImageDraw.Draw(panel)
    rows,font,font_size=title_layout(painter,text.strip().upper())
    # Soft black gradient instead of the old opaque rounded rectangle.
    top=118
    bottom=565 if len(rows)==3 else 510
    for y in range(top,bottom):
        frac=(y-top)/max(1,bottom-top)
        a=round(219*(1-frac**2.2)) if frac>0.28 else 219
        painter.line((0,y,1080,y),fill=(4,5,12,a))
    title_heights=[]
    for row in rows:
        box=painter.textbbox((0,0),row,font=font,stroke_width=2)
        title_heights.append(box[3]-box[1])
    leading=12
    total=sum(title_heights)+leading*(len(rows)-1)
    y=190 if len(rows)==2 else 169
    if len(rows)==1:
        y=229
    for row,height in zip(rows,title_heights):
        box=painter.textbbox((0,0),row,font=font,stroke_width=2)
        width=box[2]-box[0]
        # textbbox offset can be non-zero for serif glyphs.
        x=round((SIZE[0]-width)/2-box[0])
        text_y=y-box[1]
        painter.text((x+3,text_y+6),row,font=font,fill=(0,0,0,205),
                     stroke_width=5,stroke_fill=(0,0,0,180))
        painter.text((x,text_y),row,font=font,fill='#FFF9F0',
                     stroke_width=2,stroke_fill='#1A1520')
        y+=height+leading
    # Fine luminous rules are inspired by the reference, not a heavy banner.
    rule_top=177
    rule_bottom=min(bottom-45, y+25)
    flare=Image.new('RGBA',SIZE,(0,0,0,0))
    g=ImageDraw.Draw(flare)
    for pos in (rule_top,rule_bottom):
        g.line((58,pos,1022,pos),fill=(248,62,53,170),width=3)
    glow=flare.filter(ImageFilter.GaussianBlur(10))
    return Image.alpha_composite(Image.alpha_composite(canvas,glow),
                                 Image.alpha_composite(panel,flare))


def render_cover(source: Image.Image, title: str, destination: Path,
                 *,zoom: float=1.07, focus_x: float=.5, focus_y: float=.4) -> dict:
    """Render deterministic high-impact cover from cached pixels only."""
    if not 1.0<=zoom<=1.4 or not 0<=focus_x<=1 or not 0<=focus_y<=1:
        raise ValueError('Zoom/foco da capa invalido')
    image=zoom_cover(source,zoom,focus_x,focus_y)
    result=draw_title(add_cinematic_grade(image),title).convert('RGB')
    destination.parent.mkdir(parents=True,exist_ok=True)
    result.save(destination,'JPEG',quality=94,subsampling=0,optimize=True)
    return {'size':list(SIZE),'style':STYLE,'title':title.upper(),
            'zoom':zoom,'focus_x':focus_x,'focus_y':focus_y}
