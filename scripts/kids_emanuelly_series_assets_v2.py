#!/usr/bin/env python3
"""All four Fofinho EP01 Shorts: source-locked assets, no recycled full frames.

Strict preflight. Save official imagery once, reuse between videos, and
explicitly authorize optional GPT Image 2 edits with a per-run call budget.
No upload to GitHub/YouTube and no modification of original final.mp4.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image

import kids_emanuelly_cenarios_camadas_v1 as v1
import kids_fofinho_storyboards_v2 as bible
import serie_kids_emanuelly_v1 as story
import gerar_poses_emanuelly_gpt_image_2 as poses
from kids_musicas_fundo_v1 import prepare_kids_music, music_signature

ROOT=Path(__file__).resolve().parents[1]
LIBRARY=Path("assets/gerados/kids-emanuelly/biblioteca-oficial")
POLICY=bible.SCHEMA
RELEASE_ROOT=Path("motion-remotion/public/generated/kids-emanuelly")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reference(name: str, root: Path=ROOT) -> Path:
    if name in bible.CANON_OLD:
        return v1.official(name, root)
    if name == "referencia-dupla":
        return root/"assets/referencias-privadas/emanuelly-fofinho.png"
    if name in bible.ASSETS:
        return root/LIBRARY/(name+".png")
    raise ValueError("Recurso nao permitido: "+name)


def marker(name: str, root: Path=ROOT) -> Path:
    if name in bible.CANON_OLD:
        return v1.metadata(name, root)
    if name not in bible.ASSETS:
        raise ValueError("Recurso nao registrado: "+name)
    return reference(name, root).with_suffix(".json")


def good_png(data: bytes, *, transparent: bool) -> bytes:
    with Image.open(io.BytesIO(data)) as im:
        im.load()
        if min(im.size)<640:
            raise ValueError("Imagem abaixo de 640px")
        if transparent and "A" not in im.getbands():
            raise ValueError("Imagem de personagem/objeto precisa de alfa verdadeiro")
        rgba=im.convert("RGBA")
        alpha=rgba.getchannel("A")
        histogram=alpha.histogram()
        if transparent and (min(alpha.getextrema())>=200 or
                            sum(histogram[:60]) < rgba.width*rgba.height*.03):
            raise ValueError("Fundo transparente ausente; nao aceitar xadrez desenhado")
        if not transparent and sum(histogram[:180])>rgba.width*rgba.height*.1:
            raise ValueError("Cenario nao pode ter grandes areas vazadas")
        output=io.BytesIO()
        rgba.save(output,format="PNG")
        return output.getvalue()


def parent_source(name: str, root: Path=ROOT) -> Path:
    parent=bible.ASSETS[name]["parent"]
    source=reference(parent,root)
    if parent=="referencia-dupla":
        if not source.is_file():
            raise FileNotFoundError("Referencia privada Manu + Fofinho ausente. "
              "Execute gerar-historia-kids.ps1 -Acao PrepararReferencias -MaxChamadas 2")
    elif not valid(parent,root):
        raise FileNotFoundError("Recurso oficial anterior ausente ou modificado: "+parent)
    return source


def valid(name: str, root: Path=ROOT) -> bool:
    if name in bible.CANON_OLD:
        return v1.installed(name,root)
    if name not in bible.ASSETS:
        return False
    file=reference(name,root)
    meta=marker(name,root)
    if not file.is_file() or not meta.is_file():
        return False
    try:
        info=json.loads(meta.read_text(encoding="utf8"))
        source=parent_source(name,root)
        if info.get("schema")!=POLICY or info.get("asset")!=name:
            return False
        if info.get("model") not in ("gpt-image-2","importado-pelo-criador"):
            return False
        if info.get("file_sha256")!=digest(file.read_bytes()):
            return False
        if info.get("parent_sha256")!=digest(source.read_bytes()):
            return False
        with Image.open(file) as im:
            im.verify()
        return True
    except (OSError,ValueError,KeyError,TypeError,RecursionError):
        return False


def install(name: str, file: Path, *, root: Path=ROOT,
            replace: bool=False, model: str="importado-pelo-criador") -> dict:
    if name in bible.CANON_OLD:
        return v1.install(name,file,root=root,replace=replace)
    if name not in bible.ASSETS:
        raise ValueError("Recurso nao oficial. Veja -Acao Catalogo: "+name)
    if not file.is_file() or file.is_symlink():
        raise FileNotFoundError("Imagem ausente ou link nao permitido: "+str(file))
    src=parent_source(name,root)
    data=good_png(file.read_bytes(),transparent=True)
    dst=reference(name,root)
    meta=marker(name,root)
    new_hash=digest(data)
    parent_hash=digest(src.read_bytes())
    if dst.is_file():
        if (new_hash==digest(dst.read_bytes()) and valid(name,root)):
            return {"asset":name,"status":"ja_instalado","uploads":0}
        if not replace:
            raise ValueError("Recurso existente, alterado ou desatualizado: "+name+
                             ". Use -Refazer para preservar historico.")
        hist=dst.parent/"historico"
        hist.mkdir(parents=True,exist_ok=True)
        old_hash=digest(dst.read_bytes())[:12]
        old=hist/(name+"-"+old_hash+".png")
        if not old.exists():shutil.copy2(dst,old)
        if meta.exists():
            oldmeta=hist/(name+"-"+old_hash+".json")
            if not oldmeta.exists():shutil.copy2(meta,oldmeta)
    dst.parent.mkdir(parents=True,exist_ok=True)
    temporary=dst.with_suffix(".partial.png")
    temporary.write_bytes(data)
    temporary.replace(dst)
    story.dump(meta,{
        "schema":POLICY,"asset":name,"file_sha256":new_hash,
        "parent":bible.ASSETS[name]["parent"],"parent_sha256":parent_hash,
        "model":model,"identity_visual_approval":"pending_video_review",
        "published":False,"uploaded":False,
    })
    return {"asset":name,"status":"instalado","sha256":new_hash,"uploads":0}


def names(parts: list[int]) -> tuple[list[str],list[str]]:
    images=set()
    poses_required=set()
    for p in parts:
        a,b=bible.resource_names(p)
        images.update(a);poses_required.update(b)
    # Folder import order: canonical room/egg first, then dependent images.
    ordered=[*bible.CANON_OLD,*bible.ASSETS]
    return [n for n in ordered if n in images], sorted(poses_required)


def parts_from(value: str) -> list[int]:
    if value=="Todas":
        return [1,2,3,4]
    i=int(value)
    if i not in bible.STORYBOARDS:
        raise ValueError("Parte deve ser 1, 2, 3, 4 ou Todas")
    return [i]


def plan(parts: list[int], *,root:Path=ROOT) -> dict:
    bible.validate_storyboard()
    episodes=[]
    all_missing=[]
    for number in parts:
        p=story.load_parts()[number-1]
        scenes=bible.STORYBOARDS[number]
        if len(scenes)!=len(p["segments"]):
            raise ValueError("Storyboard incompatível com roteiro: Parte "+str(number))
        images, characters=bible.resource_names(number)
        missing=[n for n in images if not valid(n,root)]
        missing_pose=[n for n in characters if not poses.valid(n,root)]
        try:
            story.read_voice(p,root)
            voice_ok=True
        except (OSError,ValueError):
            voice_ok=False
        song=(root/("Wondertrail _Main Theme_.mp3" if number%2 else
                    "Wondertrail _Main Theme_2.mp3")).is_file()
        block=[*["imagem:"+n for n in missing],
               *["pose:"+n for n in missing_pose]]
        if not voice_ok:block.append("narracao:"+str(number))
        if not song:block.append("musica:"+str(number))
        all_missing.extend(block)
        episodes.append({
            "part":number,"episode_id":p["id"],
            "scene_count":len(scenes),"images":images,
            "poses":characters,"missing":block,
            "ready":not block,"no_upload":True,
        })
    return {
        "schema":POLICY,"episodes":episodes,"ready":not all_missing,
        "missing":list(dict.fromkeys(all_missing)),
        "future_characters":bible.FUTURE_CAST,
        "uploads":0,"automatic_generation":False,
    }


def install_folder(folder:Path,*,root:Path=ROOT,replace:bool=False)->dict:
    if not folder.is_dir():
        raise FileNotFoundError("Pasta de imagens ausente: "+str(folder))
    ordered=[*bible.CANON_OLD,*bible.ASSETS]
    pending=[n for n in ordered if (folder/(n+".png")).is_file()]
    if not pending:
        raise FileNotFoundError("Nenhum PNG com nome oficial encontrado na pasta")
    # Before installing anything, validate all image bytes and known
    # replacement conflicts. Parent dependencies are checked per resource.
    for name in pending:
        data=(folder/(name+".png")).read_bytes()
        good_png(data,transparent=name not in bible.CANON_OLD[:-1])
        dst=reference(name,root)
        if dst.exists() and not replace:
            with Image.open(io.BytesIO(data)) as im:
                b=io.BytesIO();im.convert("RGBA").save(b,"PNG")
            if digest(b.getvalue())!=digest(dst.read_bytes()):
                raise ValueError("Recurso oficial existente diferente: "+name+
                                 ". Use -Refazer com historico.")
    return {"imported":[install(n,folder/(n+".png"),root=root,replace=replace)
                         for n in pending],
            "uploads":0}


def _signature(name:str,root:Path)->str:
    src=parent_source(name,root)
    prompt=bible.ASSETS[name]["prompt"]
    return digest(("gpt-image-2|"+name+"|"+prompt+"|"+
                   digest(src.read_bytes())).encode("utf8"))


def raw_path(name:str,root:Path=ROOT)->Path:
    if name not in bible.ASSETS:raise ValueError("Recurso invalido")
    return root/LIBRARY/"brutos"/(name+".png")


def raw_usable(name:str,root:Path=ROOT)->bool:
    file=raw_path(name,root)
    meta=file.with_suffix(".json")
    if not file.is_file() or not meta.is_file():
        return False
    try:
        info=json.loads(meta.read_text(encoding="utf8"))
        return info["signature"]==_signature(name,root) and (
            info["sha256"]==digest(file.read_bytes())
        )
    except (KeyError,OSError,ValueError):
        return False


def generate(name:str,*,root:Path=ROOT,budget:int=0,
             replace:bool=False,editor=None,key_provider=None)->dict:
    """One intentional GPT Image 2 request at most, reusing paid raw responses."""
    if name not in bible.ASSETS:
        raise ValueError("Somente novos recursos da biblioteca podem ser gerados: "+name)
    if valid(name,root) and not replace:
        return {"asset":name,"status":"ja_em_cache","new_calls":0}
    output=reference(name,root)
    if output.exists() and not replace:
        raise ValueError("Imagem existente mas invalida: "+name+
                         "; use -Refazer antes de substituir")
    original=parent_source(name,root)
    from master_scenes import normalize_image,validate_image
    if raw_usable(name,root) and not replace:
        raw=raw_path(name,root).read_bytes()
        calls=0
    else:
        if budget<1:
            raise ValueError("Gerar "+name+" precisa de 1 chamada GPT Image 2, "
                             "mas -MaxChamadas 0. Nenhuma IA foi chamada.")
        if editor is None:
            from master_scenes import request_edit
            editor=request_edit
        if key_provider is None:
            from gerar_video_codex import proxy_key
            key_provider=proxy_key
        raw=editor(original,bible.ASSETS[name]["prompt"],"gpt-image-2",
                   key_provider(),transparent=True)
        # Paid response is saved BEFORE any QA step, so retries cost zero.
        cache=raw_path(name,root)
        cache.parent.mkdir(parents=True,exist_ok=True)
        temp=cache.with_suffix(".partial.png")
        temp.write_bytes(raw)
        temp.replace(cache)
        story.dump(cache.with_suffix(".json"),{
            "signature":_signature(name,root),"sha256":digest(raw),
            "model":"gpt-image-2","status":"received_before_qa",
        })
        calls=1
    normalized=normalize_image(raw,alpha=True,stage="kids/fofinho/"+name)
    validate_image(normalized,alpha=True)
    # Apply same local safe-fit as the Emanuelly pose library.
    from kids_poses_enquadramento_v1 import fit_transparent_pose
    framed,_qa=fit_transparent_pose(normalized)
    output.parent.mkdir(parents=True,exist_ok=True)
    intermediate=output.parent/(name+".staged.png")
    intermediate.write_bytes(framed)
    try:
        result=install(name,intermediate,root=root,replace=replace,model="gpt-image-2")
    finally:
        intermediate.unlink(missing_ok=True)
    result["new_calls"]=calls
    result["reused_paid_raw"]=calls==0
    return result


def generate_list(parts:list[int],*,root:Path=ROOT,budget:int=0,
                  only:str|None=None,replace:bool=False,
                  editor=None,key_provider=None)->dict:
    if budget<0:raise ValueError("Orcamento invalido")
    names_needed,_=names(parts)
    missing=[n for n in names_needed if n in bible.ASSETS and (
        replace or not valid(n,root))]
    if only:
        if only not in bible.ASSETS:raise ValueError("Recurso nao geravel: "+only)
        missing=[only] if replace or not valid(only,root) else []
    # Budget preflight, including parent->child generation within same run.
    estimated=sum(1 for n in missing if replace or not raw_usable(n,root)
                  if _parent_available_or_pending(n,missing,root))
    # If a parent is pending, its raw signature cannot yet be computed;
    # conservatively count one new model call for that child.
    estimated+=sum(1 for n in missing if not _parent_available_or_pending(n,missing,root))
    if estimated>budget:
        raise ValueError(f"Plano exige ate {estimated} chamadas gpt-image-2; "
                         f"MaxChamadas={budget}. NENHUMA IA acionada.")
    # Ensure every parent exists or will be generated earlier in THIS list.
    for i,name in enumerate(missing):
        parent=bible.ASSETS[name]["parent"]
        if parent in bible.ASSETS and not valid(parent,root) and parent not in missing[:i]:
            raise ValueError("Gere primeiro o recurso pai "+parent+" de "+name)
        if parent=="referencia-dupla" and not reference(parent,root).is_file():
            raise FileNotFoundError("Referência dupla Manu/Fofinho ainda não preparada")
        if parent in bible.CANON_OLD and not valid(parent,root):
            raise FileNotFoundError("Falta referencia oficial "+parent)
    outputs=[]
    left=budget
    for name in missing:
        result=generate(name,root=root,budget=left,replace=replace,
                        editor=editor,key_provider=key_provider)
        left-=result["new_calls"]
        outputs.append(result)
    return {"generated_assets":outputs,"new_calls":budget-left,"uploads":0}


def _parent_available_or_pending(name:str,pending:list[str],root:Path)->bool:
    parent=bible.ASSETS[name]["parent"]
    return parent not in bible.ASSETS or valid(parent,root)
