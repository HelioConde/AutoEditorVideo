"""Direcao visual e QA local do Arquivo Otaku. Nao chama APIs.

A imagem final usada pelo MoneyPrinterTurbo deve ser inspecionada/corrigida
ANTES de virar clipe, portanto este modulo trabalha no arquivo original.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Any

STYLE = (
    "Faithful hand drawn 2D Japanese television anime from the mid 2000s. "
    "Recognizable established Death Note character proportions and hairstyles. "
    "Crisp dark ink line art with smooth traditional cel shading. "
    "Vertical portrait 9:16 with the main subject clearly framed. "
    "Dark suspenseful midnight blue atmosphere with gentle muted red accents. "
    "IMPORTANT the face and eyes must be readable on a small phone screen: "
    "use a soft key light and clear separation from background, controlled shadows not crushed blacks. "
    "Include readable light on important foreground objects; cinematic not underexposed. "
    "Anime screenshot composition with precise anatomy. "
    "NOT photorealistic NOT realistic skin NOT CGI NOT 3D NOT cosplay. "
    "No written words no watermarks no logos no captions no graphical frames."
)

def load_plan(path: Path) -> dict:
    obj=json.loads(Path(path).read_text(encoding="utf-8-sig"))
    scenes=obj.get("cenas")
    if not isinstance(scenes,list) or not (3<=len(scenes)<=12):
        raise ValueError("Plano precisa de 3 a 12 cenas")
    for s in scenes:
        if not s.get("id") or len(s.get("descricao", ""))<20:
            raise ValueError("Cena sem identificador ou descricao suficiente")
        if ',' in str(s.get('id')):
            raise ValueError("ID de cena invalido")
    if len({str(s['id']) for s in scenes}) != len(scenes):
        raise ValueError("IDs de cena repetidos")
    if len(obj.get("roteiro_melhorado", "").strip())<70:
        raise ValueError("Roteiro melhorado ausente ou curto")
    return obj

def scene_prompt(scene: dict, plan: dict) -> str:
    return (STYLE + " Scene subject: " + scene["descricao"] +
        ". This exact shot is different from other shots and should avoid repetitive generic portraits. "
        "Keep important content within the middle 70 percent of the frame; lower quarter must remain subtitle friendly.")

def scene_digest(prompt: str, model: str) -> str:
    return hashlib.sha256((model+'\n'+prompt).encode('utf-8')).hexdigest()[:14]

def _sample_stats(image):
    from PIL import ImageStat
    scaled=image.convert('RGB').resize((128,192))
    gray=scaled.convert('L')
    values=list(gray.get_flattened_data() if hasattr(gray, "get_flattened_data") else gray.getdata()); values.sort()
    # Centrally weighted region measures the subject, not just the dark border.
    center=gray.crop((32,38,96,154))
    return {
        "p10":int(values[len(values)//10]),
        "mediana":int(values[len(values)//2]),
        "media_centro":round(ImageStat.Stat(center).mean[0],1),
        "percentual_escuro":round(sum(v < 70 for v in values)/len(values)*100,1),
    }

def visual_signature(image) -> int:
    from PIL import Image
    small=image.convert('L').resize((9,8),Image.Resampling.LANCZOS)
    pixels=list(small.get_flattened_data() if hasattr(small, "get_flattened_data") else small.getdata())
    h=0
    for y in range(8):
        for x in range(8):
            h=(h<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
    return h

def quality_adjust_image(image) -> tuple[Any,dict]:
    """Lift shadows moderately, never bleach the entire noir aesthetic."""
    from PIL import Image,ImageEnhance
    image=image.convert('RGB')
    before=_sample_stats(image)
    # Only apply controlled lifting when very dark; gamma >1 would darken.
    if before['mediana'] < 42:
        gamma=.76
    elif before['mediana'] < 64:
        gamma=.84
    elif before['mediana'] < 81:
        gamma=.92
    else:
        gamma=1.0
    if gamma < 1.0:
        lut=[min(255,int(255*(v/255.0)**gamma)) for v in range(256)]
        image=image.point(lut*3)
    if gamma < .9:
        image=ImageEnhance.Contrast(image).enhance(1.035)
    after=_sample_stats(image)
    return image,{"antes":before,"depois":after,"gamma":gamma,
                  "alertas":(["Cena permanece muito escura para tela pequena"] if after['media_centro']<48 else [])}

def process_file(raw: Path, final: Path, scene: dict, prompt: str, model: str) -> dict:
    """Persist approved/adjusted JPEG; never mutate the remote response itself."""
    from PIL import Image
    with Image.open(raw) as image:
        if min(image.size)<640: raise ValueError(f"Imagem muito pequena: {image.size}")
        fixed,qa=quality_adjust_image(image)
        signature=visual_signature(fixed)
        final.parent.mkdir(parents=True,exist_ok=True)
        temporary=final.with_suffix('.tmp.jpg')
        fixed.save(temporary,'JPEG',quality=94,subsampling=0,optimize=True)
        temporary.replace(final)
    qa.update({"id":scene['id'],"tipo":scene.get('tipo'),"papel":scene.get('papel'),
               "arquivo":str(final),"assinatura":f"{signature:016x}",
               "prompt_sha":scene_digest(prompt,model)})
    return qa

def duplicate_warnings(rows: list[dict], max_distance:int=5) -> list[str]:
    found=[]
    for i in range(len(rows)):
        for j in range(i):
            distance=(int(rows[i]['assinatura'],16)^int(rows[j]['assinatura'],16)).bit_count()
            if distance <= max_distance:
                found.append(f"Cenas {rows[j]['id']} e {rows[i]['id']} muito parecidas (distancia={distance})")
    return found
