#!/usr/bin/env python3
"""Prepare/render all four Emanuelly/Fofinho Shorts with fixed PNG references.

Narration and music stay untouched; all generated scene props reuse cached
approved images. Produces final-camadas.mp4 in each episode directory; no
publishing functions exist in this entrypoint.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import kids_fofinho_storyboards_v2 as bible
import kids_emanuelly_series_assets_v2 as store
import serie_kids_emanuelly_v1 as story
import gerar_poses_emanuelly_gpt_image_2 as poses
from kids_musicas_fundo_v1 import prepare_kids_music, music_signature

ROOT=Path(__file__).resolve().parents[1]
POLICY=bible.SCHEMA
FPS=30


def _episode(part:int)->dict:
    p=story.load_parts()[part-1]
    if len(p["segments"])!=len(bible.STORYBOARDS[part]):
        raise ValueError("Roteiro e storyboard divergentes: Parte "+str(part))
    return p


def _shot_layout(scene:dict, part:int) ->dict:
    # Initial placement is deterministic and may be tuned after watching MP4.
    i=scene["index"]
    garden=scene["backdrop"].startswith("jardim")
    pose_x=.33 if i%2==0 else .38
    if not scene["pose"]:pose_x=.0
    kitty_x=.68 if garden else .66
    egg_x=.66 if not garden else .63
    if part==1 and i==1:egg_x=.53
    return {
        "index":i,"poseX":pose_x,"poseY":.13,
        "poseSize":.70 if garden else .72,
        "eggX":egg_x,"eggY":.72 if garden else .76,
        "eggSize":.23 if garden else .20,
        "kittyX":kitty_x,"kittyY":.75 if garden else .78,
        "kittySize":.23,"nestX":.69,"nestY":.82,"nestSize":.36,
        "waterX":kitty_x-.09,"waterY":.60 if garden else .62,
        "waterSize":.07,
    }


def _public_path(part:dict,name:str)->str:
    return ("generated/kids-emanuelly/"+part["id"]+"/layers-v2/"+name)


def build(part:int,*,root:Path=ROOT)->tuple[dict,Path,dict]:
    status=store.plan([part],root=root)
    if not status["ready"]:
        raise ValueError("Parte "+str(part)+" bloqueada. Faltam: "+
                         ", ".join(status["missing"])+
                         ". Execute -Acao Planejar para ver a biblioteca.")
    chapter=_episode(part)
    voice,marker=story.read_voice(chapter,root)
    duration=story.audio_seconds(voice)
    duration_frames=math.ceil((duration+.45)*FPS)
    if duration>story.MAX_AUDIO or duration_frames>1800:
        raise ValueError("Video Kids ultrapassaria 60s: Parte "+str(part))
    _scenes,captions,timing=story.scene_props(
        story.episode_for_tts(chapter),marker,duration_frames
    )
    expected=bible.STORYBOARDS[part]
    if len(timing)!=len(expected):
        raise ValueError("Tempos da narracao nao correspondem aos beats da parte")
    dest=root/"motion-remotion/public/generated/kids-emanuelly"/chapter["id"]/"layers-v2"
    dest.mkdir(parents=True,exist_ok=True)
    copied=set()
    signatures=[]
    def use(src:Path)->str:
        if not src.is_file():
            raise FileNotFoundError("Referencia ausente: "+str(src))
        h=store.digest(src.read_bytes())
        signatures.append(h)
        dst=dest/src.name
        if dst.name not in copied:
            shutil.copy2(src,dst)
            copied.add(dst.name)
        return _public_path(chapter,dst.name)
    audio=use(voice)
    shots=[]
    for shot,t in zip(expected,timing):
        layer=_shot_layout(shot,part)
        layer["startFrame"]=t["startFrame"]
        layer["endFrame"]=t["endFrame"]
        layer["animation"]=shot["movement"]
        layer["magic"]=shot["magic"]
        layer["night"]=shot["night"]
        layer["futureGlow"]=shot["future_glow"]
        layer["kittenMotion"]=shot["kitten_motion"]
        layer["background"]=use(store.reference(shot["backdrop"],root))
        layer["pose"]=(use(poses.paths(shot["pose"],root)[0])
                       if shot["pose"] else None)
        layer["egg"]=(use(store.reference({
            "closed":"ovo-azul","cracked":"ovo-rachado",
            "open":"ovo-aberto",
        }[shot["egg_phase"]],root))
                      if shot["egg_phase"]!="none" else "")
        layer["showEgg"]=shot["egg_phase"]!="none"
        layer["nest"]=(use(store.reference("caminha-ovo",root))
                       if shot["nest"] else None)
        layer["kitty"]=(use(store.reference(shot["kitty"],root))
                        if shot["kitty"] else None)
        layer["water"]=(use(store.reference("gotinha-agua",root))
                        if shot["drops"] else None)
        layer["waterCount"]=shot["drops"]
        if part==1 and shot["index"]==1 and (layer["pose"] or layer["kitty"]):
            raise ValueError("Primeira cena nao pode mostrar Emanuelly/Fofinho")
        if part==2 and shot["index"]<6 and layer["kitty"]:
            raise ValueError("Fofinho visivel antes do nascimento")
        if part==1 and layer["kitty"]:
            raise ValueError("Spoiler: personagem futuro na Parte 1")
        shots.append(layer)
    music=prepare_kids_music(root,chapter["id"])
    signatures.extend([
        music_signature(root,chapter["id"]),
        store.digest(chapter["narration"].encode("utf8")),
        store.digest(json.dumps(expected,sort_keys=True).encode("utf8")),
    ])
    signature=store.digest((POLICY+"|"+
                            "|".join(signatures)).encode("utf8"))
    props={
        "episodeId":chapter["id"],"title":chapter["title"],
        "brand":"Emanuelly e seus Amigos de Pelúcia",
        "chapter":f"EP 1 · PARTE {part}/4",
        "durationFrames":duration_frames,
        "frames":[],"layeredScenes":shots,
        "captions":captions,"audio":audio,
        "referenceSha":signature,"madeForKids":True,"music":music,
    }
    file=root/"motion-remotion"/f"props-emanuelly-camadas-parte{part}.json"
    story.dump(file,props)
    return props,file,{"signature":signature,"images_sha256":signatures}


def render(part:int,*,root:Path=ROOT,replace:bool=False)->dict:
    chapter=_episode(part)
    props,props_path,fingerprint=build(part,root=root)
    folder=story.output_for(chapter,root)
    video=folder/"final-camadas.mp4"
    metadata=folder/"qa-camadas.json"
    if video.exists() and not replace:
        if metadata.exists():
            saved=json.loads(metadata.read_text(encoding="utf8"))
            if saved.get("schema")==POLICY and (
                saved.get("signature")==fingerprint["signature"]
                and saved.get("video_sha256")==store.digest(video.read_bytes())
            ):
                return {"part":part,"status":"cache","mp4":str(video),"uploads":0}
        raise ValueError("Previa anterior pertence a outros assets; use -Refazer "
                         "para preservar em historico.")
    motion=root/"motion-remotion"
    if not (motion/"node_modules").is_dir():
        raise RuntimeError("Remotion nao instalado: npm.cmd install dentro de motion-remotion")
    npm=shutil.which("npm.cmd" if sys.platform=="win32" else "npm")
    if not npm:raise FileNotFoundError("npm nao encontrado no Windows")
    folder.mkdir(parents=True,exist_ok=True)
    temp=folder/"camadas-v2-temporario.mp4"
    temp.unlink(missing_ok=True)
    subprocess.run([npm,"run","render:emanuelly","--",str(temp.resolve()),
                    "--props",str(props_path.resolve()),"--concurrency","2"],
                   cwd=motion,check=True,timeout=3000)
    technical=story.verify_video(temp)
    if technical.get("technical_status")!="passed":
        raise ValueError("MP4 reprovado no FFprobe: "+str(technical))
    if video.is_file():
        hist=folder/"historico-renders"
        hist.mkdir(exist_ok=True)
        old_hash=store.digest(video.read_bytes())[:12]
        backup=hist/("final-camadas-"+old_hash+".mp4")
        if not backup.exists():shutil.copy2(video,backup)
        if metadata.exists():
            previous=hist/("qa-camadas-"+old_hash+".json")
            if not previous.exists():shutil.copy2(metadata,previous)
    temp.replace(video)
    story.dump(metadata,{
        "schema":POLICY,"part":part,"episode_id":chapter["id"],
        "signature":fingerprint["signature"],
        "images_sha256":fingerprint["images_sha256"],
        "video_sha256":store.digest(video.read_bytes()),
        "technical":technical,
        "quality_review":"pending_after_watching_youtube_private_video",
        "music_rights_review":"pending_before_publication",
        "made_for_kids":True,"uploads":0,"image_ai_calls":0,
    })
    return {"part":part,"status":"render_local_para_revisao",
            "mp4":str(video),"uploads":0}


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description="Serie Kids Fofinho - recursos de TODAS as partes")
    ap.add_argument("--acao",choices=("catalogo","planejar","verificar","instalar",
                                      "instalar-lote","gerar-imagens","preparar",
                                      "renderizar"),default="planejar")
    ap.add_argument("--parte",choices=("1","2","3","4","Todas"),default="1")
    ap.add_argument("--recurso",default="")
    ap.add_argument("--tipo",choices=("Jardim","Quarto","Ovo"),default="Jardim")
    ap.add_argument("--indice",type=int,default=1)
    ap.add_argument("--arquivo",type=Path)
    ap.add_argument("--pasta",type=Path)
    ap.add_argument("--max-chamadas",type=int,default=0)
    ap.add_argument("--refazer",action="store_true")
    args=ap.parse_args(argv)
    if args.max_chamadas<0:ap.error("Orcamento de IA nao pode ser negativo")
    if args.refazer and args.acao not in (
        "instalar","instalar-lote","gerar-imagens","renderizar"
    ):ap.error("Refazer nao se aplica a esta acao")
    parts=store.parts_from(args.parte)
    if args.acao=="catalogo":
        result=bible.inventory()
    elif args.acao in ("planejar","verificar"):
        result=store.plan(parts)
    elif args.acao=="instalar":
        if not args.arquivo:ap.error("Instalar exige --arquivo")
        if args.recurso:
            name=args.recurso
        elif args.tipo=="Ovo":
            name="ovo-azul"
        else:
            if not 1<=args.indice<=4:ap.error("Indice deve ser de 1 a 4")
            name=f"{args.tipo.lower()}-{args.indice:02d}"
        result=store.install(name,args.arquivo,replace=args.refazer)
    elif args.acao=="instalar-lote":
        if not args.pasta:ap.error("InstalarLote exige --pasta")
        result=store.install_folder(args.pasta,replace=args.refazer)
    elif args.acao=="gerar-imagens":
        result=store.generate_list(parts,budget=args.max_chamadas,
            only=args.recurso or None,replace=args.refazer)
    elif args.acao=="preparar":
        rows=[]
        for part in parts:
            props,path,meta=build(part)
            rows.append({"part":part,"file":str(path),"scenes":len(props["layeredScenes"]),
                         "signature":meta["signature"],"uploads":0})
        result={"prepared":rows,"uploads":0}
    elif args.acao=="renderizar":
        status=store.plan(parts)
        if not status["ready"]:
            raise ValueError("Nenhum MP4 sera criado antes do preflight completo: "+
                             ", ".join(status["missing"]))
        result={"rendered":[render(part,replace=args.refazer) for part in parts],
                "uploads":0}
    else:raise ValueError("Acao desconhecida")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,RuntimeError,KeyError,
            subprocess.SubprocessError) as e:
        print("[KIDS SERIES V2 BLOQUEADO] "+str(e),file=sys.stderr)
        raise SystemExit(1)
