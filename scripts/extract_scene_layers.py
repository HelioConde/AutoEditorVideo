#!/usr/bin/env python3
"""One command for multi-layer scene extraction; multiple *budgeted* image edits.

Uses the existing 1024x1536 master and extracts distinct semantic RGBA masks
using the connected image-edit API. Each final layer copies actual master RGB,
not the model's redrawn pixels. Source masks and paid bytes remain on disk.
Never publishes anything. Always requires manual approval for multi-layer render.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image

import master_scenes as core
from revisao_visual_cenas import read_review
from scene_layer_profiles import (
    Layer, SCHEMA, PROFILES, layer_profile, mask_prompt, background_prompt,
)
from qa_multilayer_geometry import (
    SIZE, exact_layer, union_inpaint_mask, normalize_clean_plate, compose,
    qa_multilayer_geometry,
)

REVIEW="review.json"


def paths(folder:Path,layer:Layer)->tuple[Path,Path]:
    dest=folder/"multilayer"
    return dest/f"{layer.id}-raw.png",dest/f"{layer.id}.png"


def pending_calls(ep:dict,scene:dict,model:str)->list[str]:
    folder=core.scene_dir(ep,scene,model)
    # A new multicamadas scene can begin with NO generated image. Count
    # the master as one distinct paid image only if neither the normalized
    # master nor its paid raw response already exists.
    missing_master=not (folder/"master.png").is_file()
    if missing_master and core.cache_pin(ep,scene,model):
        raise ValueError(
            f"Cena {scene['id']} tem cache fixado e master ausente: {folder}. "
            "Restaure o cache aprovado ou retire o pin conscientemente. "
            "Nunca sobrescrever uma versao fixada sem autorizacao.")
    if (review:=read_review(folder)) and review["status"]=="reprovado":
        raise ValueError(
            f"Cena {scene['id']} MASTER reprovada: {review['reason']}. "
            "Uma separacao de camadas nao conserta anatomia na imagem-mae. "
            "Crie um novo take da master primeiro.")
    wanted=layer_profile(ep,scene)
    pending=[]
    if missing_master and not (folder/"master-raw.png").is_file():
        pending.append(scene["id"]+"/master")
    pending.extend(scene["id"]+"/"+layer.id for layer in wanted
                   if not paths(folder,layer)[0].is_file())
    if not (folder/"multilayer"/"background-raw.png").is_file():
        pending.append(scene["id"]+"/background-clean")
    return pending


def _read_manifest(folder:Path)->dict|None:
    file=folder/"scene-layers.json"
    if not file.is_file():return None
    document=json.loads(file.read_text(encoding="utf-8"))
    if document.get("schema")!=SCHEMA:raise ValueError("Manifesto multicamadas invalido")
    return document


def validate_multilayer(ep:dict,scene:dict,model:str,folder:Path,
                        *,approval:bool=True)->dict|None:
    document=_read_manifest(folder)
    if document is None:return None
    master=folder/"master.png"
    if not master.is_file():raise ValueError("Master removida depois da extracao")
    identity=hashlib.sha256(master.read_bytes()).hexdigest()
    if document.get("master_sha256")!=identity or document.get("model")!=model:
        raise ValueError("Multicamadas invalidas: master/modelo mudou. Refaça os recortes.")
    expected=layer_profile(ep,scene)
    expected_ids=[l.id for l in expected]
    layer_info=document.get("layers",[])
    if [row.get("id") for row in layer_info]!=expected_ids:
        raise ValueError("Manifesto nao corresponde ao perfil de camadas")
    files=[]
    for expected_layer,row in zip(expected,layer_info):
        if row.get("z")!=expected_layer.z or row.get("role")!=expected_layer.role:
            raise ValueError("Ordem Z incoerente para "+expected_layer.id)
        path=folder/"multilayer"/(expected_layer.id+".png")
        if row.get("sha256")!=hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Camada alterada sem revisao: "+expected_layer.id)
        with Image.open(path) as img:
            if img.size!=SIZE or "A" not in img.getbands():
                raise ValueError("Camada ausente/invalida: "+str(path))
        files.append((expected_layer,path))
    bg=folder/"multilayer"/"background.png"
    if not bg.is_file():raise FileNotFoundError("Background multicamadas ausente")
    if document.get("background_sha256")!=hashlib.sha256(bg.read_bytes()).hexdigest():
        raise ValueError("Fundo multicamadas alterado apos a revisao; gere novo QA")
    with Image.open(bg) as img:
        if img.size!=SIZE:raise ValueError("Fundo multicamadas invalido")
    qa=document.get("qa",{})
    if qa.get("warnings"):
        raise ValueError("Multicamadas com alertas: "+", ".join(qa["warnings"])+
                         ". Corrija as camadas antes de liberar o render.")
    if approval:
        reviewfile=folder/"multilayer"/REVIEW
        if not reviewfile.is_file():
            raise ValueError(f"Cena {scene['id']} multicamadas aguardando revisao. "
                             "Confira preview-composicao.png e use -AprovarMulticamadas.")
        review=json.loads(reviewfile.read_text(encoding="utf-8"))
        if review.get("status")!="aprovado" or review.get("manifest_sha256")!=(
            hashlib.sha256((folder/"scene-layers.json").read_bytes()).hexdigest()):
            raise ValueError("Aprovacao multicamadas ausente/desatualizada.")
    return {"manifest":document,"layers":files,"background":bg,"qa":qa}


def approve_multilayer(ep:dict,scene:dict,model:str,reason:str)->dict:
    folder=core.scene_dir(ep,scene,model)
    result=validate_multilayer(ep,scene,model,folder,approval=False)
    if result is None:raise FileNotFoundError("Nao ha camadas prontas para aprovar")
    base=read_review(folder)
    if base and base.get("status")=="reprovado":
        raise ValueError("Master reprovada; nao e possivel aprovar apenas as camadas")
    if not reason.strip():
        raise ValueError("Informe motivo/nota de aprovacao apos revisao visual")
    file=folder/"scene-layers.json"
    report={"status":"aprovado","reason":reason.strip(),
            "manifest_sha256":hashlib.sha256(file.read_bytes()).hexdigest()}
    core.atomic(folder/"multilayer"/REVIEW,
                (json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
    return report


def ensure_master(ep:dict,scene:dict,model:str,*,generate=None,
                  offline:bool=False)->Path:
    """Reuse existing PNG/raw first; generate exactly one paid master if needed.

    Raw responses survive normalization failures. This deliberately does NOT
    invoke the legacy foreground/background pipeline (three extra edits).
    """
    folder=core.scene_dir(ep,scene,model)
    master=folder/"master.png"
    if master.is_file():
        core.validate_image(master.read_bytes(),alpha=False)
        return master
    if core.cache_pin(ep,scene,model):
        raise ValueError("Master de cache fixado ausente: "+str(master))
    raw=folder/"master-raw.png"
    if not raw.is_file():
        if offline or generate is None:
            raise RuntimeError(
                f"Cena {scene['id']}: master faltando. "
                "Rode sem -Offline e com orcamento suficiente "
                "ou restaure master-raw.png do cache.")
        content=generate(core.master_prompt(ep,scene),model)
        folder.mkdir(parents=True,exist_ok=True)
        core.atomic(raw,content)
    normalized=core.normalize_image(raw.read_bytes(),alpha=False,
                                     stage=f"{scene['id']}/master")
    core.validate_image(normalized,alpha=False)
    core.atomic(master,normalized)
    print(f"[MASTER] Cena {scene['id']}: " +
          ("normalizada do raw existente." if generate is None else
           "reconstruida/gerada no cache."),flush=True)
    return master


def process_multilayer(ep:dict,scene:dict,model:str,*,edit=None,
                       generate=None,offline:bool=False)->dict:
    folder=core.scene_dir(ep,scene,model)
    pending=pending_calls(ep,scene,model)
    if pending and offline:
        raise RuntimeError("Imagens faltando em modo offline: "+", ".join(pending))
    if pending and edit is None:
        # Generating just a master without masks would leave partial work.
        raise RuntimeError("Edicoes faltando sem autorizacao: "+", ".join(pending))
    master=ensure_master(ep,scene,model,generate=generate,offline=offline)
    dest=folder/"multilayer"
    dest.mkdir(parents=True,exist_ok=True)
    layers=layer_profile(ep,scene)
    for layer in layers:
        raw,working=paths(folder,layer)
        if not raw.is_file():
            paid=edit(master,mask_prompt(layer),model,transparent=True)
            core.atomic(raw,paid)  # Save paid image exactly, before any validation.
        original=core.normalize_image(raw.read_bytes(),alpha=True,
                                      stage=f"{scene['id']}/multilayer/{layer.id}")
        # Copy pixels from the master; edit's RGB (including invented legs) dies here.
        core.atomic(working,exact_layer(master,original))
        print(f"[CAMADA] {scene['id']}/{layer.id} z={layer.z}: master RGB preservado.",
              flush=True)
    raw_bg=dest/"background-raw.png"
    mask=union_inpaint_mask([paths(folder,l)[1] for l in layers])
    if not raw_bg.is_file():
        # Never pay for a background if a validated edit mask is missing.
        maskfile=dest/"background-mask.png"
        core.atomic(maskfile,mask)
        paid=edit(master,background_prompt(),model,transparent=False,mask=maskfile)
        core.atomic(raw_bg,paid)
    normalized=core.normalize_image(raw_bg.read_bytes(),alpha=False,
                                    stage=f"{scene['id']}/multilayer/background")
    core.atomic(dest/"background.png",normalize_clean_plate(master,normalized,mask))
    ordered=[(l,paths(folder,l)[1]) for l in layers]
    preview=compose(dest/"background.png",ordered)
    buffer=io.BytesIO()
    preview.save(buffer,format="PNG",optimize=True)
    core.atomic(dest/"preview-composicao.png",buffer.getvalue())
    qa=qa_multilayer_geometry(master,dest/"background.png",ordered)
    document={
        "schema":SCHEMA,"profile":PROFILES,"scene":scene["id"],
        "model":model,
        "master_sha256":hashlib.sha256(master.read_bytes()).hexdigest(),
        "background":"multilayer/background.png",
        "background_sha256":hashlib.sha256((dest/"background.png").read_bytes()).hexdigest(),
        "preview":"multilayer/preview-composicao.png",
        "layers":[{"id":l.id,"role":l.role,"z":l.z,
                   "file":"multilayer/"+l.id+".png",
                   "sha256":hashlib.sha256(paths(folder,l)[1].read_bytes()).hexdigest(),
                   "raw":"multilayer/"+l.id+"-raw.png"}
                  for l in layers],
        "qa":qa,
    }
    atomic_json= (json.dumps(document,ensure_ascii=False,indent=2)+"\n").encode()
    core.atomic(folder/"scene-layers.json",atomic_json)
    print(f"[MULTICAMADAS] Cena {scene['id']}: {len(layers)+1} camadas; "
          f"QA diferenca media={qa['master_composite_mean_difference']}; "
          f"avisos={qa['warnings']}. Pendente de aprovacao visual.",flush=True)
    return document


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description="Extracao multicamadas em um comando, orcamento explicito")
    ap.add_argument("--id",required=True)
    ap.add_argument("--modelo",default="gpt-image-1.5",
                    choices=["gpt-image-1.5","gpt-image-2"])
    ap.add_argument("--cena",type=int,default=1)
    ap.add_argument("--todas-cenas",action="store_true")
    ap.add_argument("--max-chamadas",type=int,default=0)
    ap.add_argument("--offline",action="store_true")
    ap.add_argument("--diagnosticar-cache",action="store_true")
    ap.add_argument("--verificar-aprovacoes",action="store_true",help="Checa se todas as cenas estao liberadas para render, sem gerar imagens")
    ap.add_argument("--aprovar",action="store_true")
    ap.add_argument("--motivo",default="")
    ap.add_argument("--max-segundos-por-plano",type=float,default=6)
    ap.add_argument("--plano",type=Path)
    args=ap.parse_args(argv)
    if not 0<=args.max_chamadas<=180:raise ValueError("Orcamento invalido")
    ep=core.read_storyboard(core.production_storyboard(
        args.id,args.max_segundos_por_plano,selected=args.plano))
    scenes=ep["scenes"] if args.todas_cenas else [
        next((s for s in ep["scenes"] if int(s["id"])==args.cena),None)]
    if scenes[0] is None:raise ValueError("Cena inexistente")
    if args.verificar_aprovacoes:
        # The renderer owns this check for both legacy scenes and semantic
        # layers. Keep image generation disconnected from the approval check.
        from renderizar_master_remotion import validate_scenes
        try:
            validated=validate_scenes(ep,args.modelo)
        except (OSError,RuntimeError,ValueError,KeyError) as exc:
            print("[RENDER AGUARDA REVISAO] "+str(exc),flush=True)
            return 2
        print(f"[RENDER LIBERADO] {len(validated)} cenas aprovadas e prontas.",flush=True)
        return 0
    if args.aprovar:
        if args.todas_cenas:raise ValueError("Aprovacao deve ser individual")
        report=approve_multilayer(ep,scenes[0],args.modelo,args.motivo)
        print(f"[APROVADO] Cena {scenes[0]['id']} | {report['reason']}")
        return 0
    preflight=[]
    for scene in scenes:
        preflight.extend(pending_calls(ep,scene,args.modelo))
    print(f"[MULTICAMADAS] {len(scenes)} cenas | {len(preflight)} "
          f"chamadas previstas | limite {args.max_chamadas}.")
    for item in preflight:
        print("  [PENDENTE] "+item)
    if args.diagnosticar_cache:
        return 0
    if len(preflight)>args.max_chamadas:
        raise RuntimeError("Orcamento insuficiente; nenhuma chamada enviada. "
                           "Aumente -MaxChamadas apenas se desejar pagar pelas edicoes.")
    if args.offline and preflight:
        raise RuntimeError("Modo offline: mascaras/fundos faltando; sem chamadas enviadas.")
    edit=generate=None
    if preflight:
        from gerar_video_codex import proxy_key,check_proxy_accounts,request_image
        key=(proxy_key(Path(os.environ["ARQUIVO_OTAKU_PROXY_ENV"]))
             if os.environ.get("ARQUIVO_OTAKU_PROXY_ENV") else proxy_key())
        check_proxy_accounts(key)
        edit=lambda source,prompt,model,*,transparent,mask=None:core.request_edit(
            source,prompt,model,key,transparent=transparent,mask=mask)
        generate=lambda prompt,model:request_image(
            prompt,model,key,size="1024x1536",output_format="png")
    for scene in scenes:
        process_multilayer(ep,scene,args.modelo,edit=edit,
                           generate=generate,offline=args.offline)
    print("[PRONTO] Previews e manifestos no cache local. Nao publicado.")
    return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (OSError,RuntimeError,ValueError,KeyError,Image.UnidentifiedImageError) as exc:
        print("[ERRO] "+str(exc),file=sys.stderr)
        raise SystemExit(1)
