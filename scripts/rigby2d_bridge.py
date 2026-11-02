#!/usr/bin/env python3
"""Bridge approved scene RGBA cutouts to externally rigged Rigby2D animation.

Rigby2D requires anatomically separated body parts, not just 'person.png'.
We DO NOT pretend its AutoRig works on one flattened character. Users can
prepare parts and export a full-canvas transparent PNG sequence from Rigby2D.
No paid APIs, automatic scene approvals, asset uploads, or raw overwrites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from PIL import Image, ImageChops, ImageStat

import master_scenes as core
from extract_scene_layers import validate_multilayer

SCHEMA="arquivo-otaku/rigby2d-frames/v1"
PARTS=("head","torso","upperarm_left","forearm_left","hand_left",
       "upperarm_right","forearm_right","hand_right")
CHARACTERS={"l","light"}
SIZE=(1024,1536)
MAX_FRAMES=240

def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def rig_folder(scene_folder:Path,character:str)->Path:
    if character not in CHARACTERS:
        raise ValueError("Personagem nao suportado: "+character)
    return scene_folder/"multilayer"/"rigby2d"/character

def source_for(scene_folder:Path,character:str)->Path:
    path=scene_folder/"multilayer"/(character+".png")
    if not path.is_file():
        raise FileNotFoundError(f"Camada {character} nao existe no cache: {path}")
    return path

def validate_source(source:Path):
    with Image.open(source) as im:
        if im.size!=SIZE or 'A' not in im.getbands():
            raise ValueError("Camada original deve ser RGBA 1024x1536")

def prepare(scene_folder:Path,character:str)->Path:
    source=source_for(scene_folder,character)
    validate_source(source)
    folder=rig_folder(scene_folder,character)
    folder.mkdir(parents=True,exist_ok=True)
    # Preserve the local-only approved RGBA under the prep folder.
    dst=folder/"character-reference.png"
    if dst.is_file() and sha(dst)!=sha(source):
        raise ValueError("Referencia mudou; revise o rig anterior antes de sobrescrever")
    if not dst.is_file():
        shutil.copy2(source,dst)
    guide=folder/"rigby2d-guide.json"
    if not guide.exists():
        guide.write_text(json.dumps({
            "schema":"arquivo-otaku/rigby2d-guide/v1",
            "character":character,
            "canvas":{"width":1024,"height":1536},
            "source_sha256":sha(source),
            "status":"PARTES_ANATOMICAS_NAO_SEPARADAS",
            "parts_to_prepare":list(PARTS),
            "instructions":"Rigby2D AutoRig precisa de head/torso/bracos/maos como partes RGBA individuais. "
                           "Importe partes em PSD com posicao preservada; confira ossos, IK, "
                           "juntas e sobreposicao de manga. Exporte frames RGBA 1024x1536 "
                           "alinhados ao original e o frame de repouso no inicio. "
                           "Nao use apenas character-reference.png como um falso esqueleto."
        },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return folder

def _frame_paths(folder:Path)->list[Path]:
    frames=sorted((folder/"frames").glob("frame-*.png"))
    if not frames:return []
    if len(frames)>MAX_FRAMES:
        raise ValueError("Sequencia excede limite de 240 quadros")
    for i,path in enumerate(frames):
        if path.name!=f"frame-{i:04d}.png":
            raise ValueError("Quadros com lacunas ou nome invalido: "+path.name)
    return frames

def validate_frames(scene_folder:Path,character:str)->dict:
    folder=rig_folder(scene_folder,character)
    src=source_for(scene_folder,character)
    validate_source(src)
    frames=_frame_paths(folder)
    if len(frames)<3:
        raise ValueError("Rigby2D requer pelo menos 3 frames exportados; "
                         "nenhuma animacao esquelética foi importada")
    original=Image.open(src).convert('RGBA')
    src_alpha=original.getchannel("A")
    bad=[]
    hashes=[]
    # Sampling first/middle/last + every 12th image for safety, while
    # checking all PNG dimensions/hashes for cache invalidation.
    sample_indices={0,len(frames)-1,len(frames)//2,*range(0,len(frames),12)}
    for index,path in enumerate(frames):
        with Image.open(path) as im:
            if im.size!=SIZE or 'A' not in im.getbands():
                raise ValueError("Frame fora do canvas RGBA: "+path.name)
            if index in sample_indices:
                image=im.convert("RGBA")
                alpha=image.getchannel("A")
                coverage=sum(alpha.histogram()[128:])/(SIZE[0]*SIZE[1])
                if coverage<.008 or coverage>.70:
                    bad.append(f"alpha fora do intervalo: {path.name}")
                if index==0:
                    # Color underneath alpha=0 is undefined for PNGs:
                    # the master may retain RGB while Rigby2D exports
                    # transparent black. Compare only visible pixels.
                    blank=Image.new("RGBA",SIZE,(0,0,0,255))
                    original_visible=Image.alpha_composite(blank,original)
                    rig_visible=Image.alpha_composite(blank,image)
                    d=ImageChops.difference(original_visible,rig_visible)
                    mean=sum(ImageStat.Stat(d.convert("RGB").resize((256,384))).mean)/3
                    if mean>7:
                        bad.append(f"frame inicial nao corresponde ao personagem aprovado (MAE={mean:.1f})")
        hashes.append(sha(path))
    if bad:
        raise ValueError("; ".join(bad))
    manifest=folder/"rigby2d-frames.json"
    fps=30
    if manifest.is_file():
        saved=json.loads(manifest.read_text(encoding="utf-8"))
        if saved.get("schema")==SCHEMA:fps=saved.get("fps",30)
    if not isinstance(fps,int) or not 8<=fps<=60:
        raise ValueError("FPS de rig inválido; intervalo 8..60")
    return {
        "schema":SCHEMA,
        "character":character,"fps":fps,
        "master_layer_sha256":sha(src),
        "frames":[{"file":f"frames/{p.name}","sha256":digest}
                  for p,digest in zip(frames,hashes)],
    }

def write_manifest(scene_folder:Path,character:str,fps:int)->Path:
    if not 8<=fps<=60:raise ValueError("FPS 8..60")
    folder=rig_folder(scene_folder,character)
    m=folder/"rigby2d-frames.json"
    # validate first, then write. A changed animation invalidates the approval.
    report=validate_frames(scene_folder,character)
    report["fps"]=fps
    content=(json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode()
    core.atomic(m,content)
    return m

def approve(scene_folder:Path,character:str,reason:str)->Path:
    if not reason.strip():raise ValueError("Aprovacao visual exige justificativa")
    folder=rig_folder(scene_folder,character)
    m=folder/"rigby2d-frames.json"
    if not m.is_file():raise FileNotFoundError("Importe frames e crie manifesto antes de aprovar")
    expected=validate_frames(scene_folder,character)
    saved=json.loads(m.read_text(encoding="utf-8"))
    if saved!=expected:raise ValueError("Frames alterados desde o manifesto; reimporte")
    review={"status":"aprovado","motivo":reason.strip(),"manifest_sha256":sha(m)}
    path=folder/"rigby2d-review.json"
    core.atomic(path,(json.dumps(review,ensure_ascii=False,indent=2)+"\n").encode())
    return path

def approved_frames(scene_folder:Path,character:str)->dict|None:
    folder=rig_folder(scene_folder,character)
    m=folder/"rigby2d-frames.json"
    if not m.is_file():return None
    expected=validate_frames(scene_folder,character)
    saved=json.loads(m.read_text(encoding="utf-8"))
    if saved!=expected:raise ValueError("Rigby2D editado depois da manifestacao; reimporte e aprove")
    review=folder/"rigby2d-review.json"
    if not review.is_file():
        raise ValueError(f"Rig esquelético de {character} aguardando revisao; use --aprovar")
    record=json.loads(review.read_text(encoding="utf-8"))
    if record.get("status")!="aprovado" or record.get("manifest_sha256")!=sha(m):
        raise ValueError("Aprovacao Rigby2D desatualizada")
    return {"fps":saved["fps"],"files":[folder/r["file"] for r in saved["frames"]]}

def import_sequence(scene_folder:Path,character:str,sequence:Path,fps:int)->Path:
    """Accept full-canvas PNGs exported by the real skeletal editor."""
    source=source_for(scene_folder,character)
    validate_source(source)
    srcs=sorted(sequence.glob("*.png"))
    if not 3<=len(srcs)<=MAX_FRAMES:
        raise ValueError("Forneca 3 a 240 PNGs RGBA exportados pelo Rigby2D")
    folder=prepare(scene_folder,character)
    dest=folder/"frames"
    # Validate everything before changing the working cache.
    for file in srcs:
        with Image.open(file) as im:
            if im.size!=SIZE or 'A' not in im.getbands():
                raise ValueError("Frame nao e RGBA 1024x1536: "+file.name)
    dest.mkdir(exist_ok=True)
    # Do not allow silent partial overwrites or a stale approval.
    if list(dest.glob("frame-*.png")):
        raise ValueError("Frames existentes. Preserve o cache; use outro take/manual backup.")
    for i,file in enumerate(srcs):
        shutil.copy2(file,dest/f"frame-{i:04d}.png")
    return write_manifest(scene_folder,character,fps)

def _scene_folder(ep_id:str,model:str,scene_num:int)->tuple[dict,Path]:
    storyboard=core.read_storyboard(core.production_storyboard(ep_id,6))
    scene=next((s for s in storyboard["scenes"] if int(s["id"])==scene_num),None)
    if scene is None:raise ValueError("Cena inexistente")
    folder=core.scene_dir(storyboard,scene,model)
    # Do not allow rigging disapproved or unvalidated source images.
    validate_multilayer(storyboard,scene,model,folder,approval=True)
    return scene,folder

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description="Preparar, importar e revisar rig Rigby2D, sem IA")
    ap.add_argument("--id",required=True)
    ap.add_argument("--modelo",default="gpt-image-1.5")
    ap.add_argument("--cena",type=int,required=True)
    ap.add_argument("--personagem",choices=sorted(CHARACTERS),required=True)
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--preparar",action="store_true")
    group.add_argument("--importar-quadros",type=Path)
    group.add_argument("--aprovar",action="store_true")
    group.add_argument("--diagnosticar",action="store_true")
    ap.add_argument("--fps",type=int,default=30)
    ap.add_argument("--motivo",default="")
    args=ap.parse_args(argv)
    scene,folder=_scene_folder(args.id,args.modelo,args.cena)
    if args.preparar:
        dest=prepare(folder,args.personagem)
        print("[RIG PREPARADO] "+str(dest))
        print("[NECESSARIO] Separe cabeca/tronco/bracos antes do AutoRig; nenhuma IA chamada.")
    elif args.importar_quadros:
        dest=import_sequence(folder,args.personagem,args.importar_quadros,args.fps)
        print("[RIG IMPORTADO] "+str(dest))
        print("[PENDENTE] Revise os frames e aprove antes de renderizar.")
    elif args.aprovar:
        print("[RIG APROVADO] "+str(approve(folder,args.personagem,args.motivo)))
    else:
        print("[RIG STATUS] "+str(approved_frames(folder,args.personagem)))
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError) as exc:
        print("[ERRO] "+str(exc),file=sys.stderr);raise SystemExit(1)
