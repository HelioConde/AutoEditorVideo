#!/usr/bin/env python3
"""EP01/Part01: compositor Kids com camadas persistentes, sem imagens de IA.

Uses previously generated approved assets on the USER's computer. It never
uploads files, alters earlier clips/voice/music or invents a replacement asset.
Only the first part is supported until later chapters have their own storyboards.
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

import serie_kids_emanuelly_v1 as story
import gerar_poses_emanuelly_gpt_image_2 as poses
from kids_musicas_fundo_v1 import prepare_kids_music, music_signature

ROOT = Path(__file__).resolve().parents[1]
POLICY = "kids/emanuelly/fixed-scenery-layers/v1"
CANON = Path("assets/gerados/kids-emanuelly/cenarios-oficiais")
SLOTS = tuple([f"jardim-{i:02d}" for i in range(1, 5)] +
              [f"quarto-{i:02d}" for i in range(1, 5)] + ["ovo-azul"])
EPISODE = "kids-emanuelly-ep01-p01-ovo-azul"

# Deliberate camera decisions, not random complete-scene illustrations.
# Scene 01: no Emanuelly; all scenes use the ONE immutable egg file.
SHOTS = (
    dict(index=1, backdrop="jardim-01", pose=None,          eggX=.53, eggY=.70, eggSize=.26, poseX=.0, poseY=.0, poseSize=.0, movement="still",    showEgg=True),
    dict(index=2, backdrop="jardim-02", pose="caminhando",  eggX=.66, eggY=.71, eggSize=.20, poseX=.39, poseY=.13, poseSize=.72, movement="walk",   showEgg=True),
    dict(index=3, backdrop="jardim-03", pose="observando",  eggX=.68, eggY=.72, eggSize=.18, poseX=.34, poseY=.13, poseSize=.72, movement="still",  showEgg=True, magic=True),
    dict(index=4, backdrop="jardim-04", pose="estendendo-mao",eggX=.63,eggY=.74,eggSize=.30,poseX=.35,poseY=.12,poseSize=.72,movement="approach",showEgg=True),
    dict(index=5, backdrop="jardim-01", pose="segurando-ovo", eggX=.50,eggY=.62,eggSize=.19,poseX=.47,poseY=.10,poseSize=.78,movement="lift",showEgg=True),
    dict(index=6, backdrop="quarto-01", pose="preparando-caminha",eggX=.72,eggY=.76,eggSize=.20,poseX=.36,poseY=.14,poseSize=.70,movement="prepare",showEgg=True),
    dict(index=7, backdrop="quarto-02", pose="observando", eggX=.68, eggY=.77, eggSize=.20, poseX=.38, poseY=.12, poseSize=.73, movement="promise", showEgg=True),
    dict(index=8, backdrop="quarto-03", pose="surpresa",   eggX=.66, eggY=.78, eggSize=.21, poseX=.36, poseY=.14, poseSize=.72, movement="rock", showEgg=True, night=True),
    dict(index=9, backdrop="quarto-04", pose="estendendo-mao",eggX=.62,eggY=.72,eggSize=.28,poseX=.36,poseY=.12,poseSize=.71,movement="wonder", showEgg=True, night=True),
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def official(slot: str, root: Path = ROOT) -> Path:
    if slot not in SLOTS:
        raise ValueError("Referencia oficial desconhecida: " + slot)
    return root / CANON / f"{slot}.png"


def metadata(slot: str, root: Path = ROOT) -> Path:
    return official(slot, root).with_suffix(".json")


def install(slot: str, file: Path, *, root: Path = ROOT, replace: bool = False) -> dict:
    if slot not in SLOTS:
        raise ValueError("Slot desconhecido: " + slot)
    if not file.is_file() or file.is_symlink():
        raise FileNotFoundError("Imagem não encontrada ou link não autorizado: " + str(file))
    with Image.open(file) as im:
        im.load()
        if min(im.size) < 640:
            raise ValueError("Resolução do recurso inferior a 640px")
        image = im.convert("RGBA")
        alpha = image.getchannel("A")
        extrema = alpha.getextrema()
        if slot == "ovo-azul":
            # The egg must be cut out and use REAL transparency.
            if extrema[0] >= 200 or sum(v for v in alpha.histogram()[:10]) < image.width * image.height * .025:
                raise ValueError("Ovo precisa de fundo realmente transparente; não usar PNG com fundo desenhado")
        elif extrema[0] < 255 and sum(alpha.histogram()[:180]) > image.width * image.height * .10:
            raise ValueError("Cenário precisa de imagem preenchida, sem grandes buracos transparentes")
        output = io.BytesIO()
        image.save(output, "PNG")
        content = output.getvalue()
    target = official(slot, root)
    digest = sha(content)
    meta = metadata(slot, root)
    if target.exists():
        if sha(target.read_bytes()) == digest:
            return {"slot":slot,"status":"ja_instalado","sha256":digest,"uploaded":False}
        if not replace:
            raise ValueError("Referência diferente já registrada para "+slot+". Use -Refazer para substituir com histórico")
        history = target.parent / "historico"
        history.mkdir(exist_ok=True, parents=True)
        backup = history / f"{slot}-{sha(target.read_bytes())[:12]}.png"
        if not backup.exists():
            shutil.copy2(target, backup)
        if meta.exists():
            back_meta = history / f"{slot}-{sha(target.read_bytes())[:12]}.json"
            if not back_meta.exists():
                shutil.copy2(meta, back_meta)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + ".partial")
    temp.write_bytes(content)
    temp.replace(target)
    story.dump(meta, {"schema": POLICY, "slot":slot, "sha256":digest,
                      "source":"installed_by_creator", "needs_visual_approval":True,
                      "no_youtube_upload":True})
    return {"slot":slot,"status":"instalado","sha256":digest,"uploaded":False}


def installed(slot: str, root: Path = ROOT) -> bool:
    target=official(slot, root)
    meta=metadata(slot, root)
    if not target.is_file() or not meta.is_file():
        return False
    try:
        info=json.loads(meta.read_text(encoding="utf8"))
        if info.get("schema") != POLICY or info.get("slot") != slot or info.get("sha256") != sha(target.read_bytes()):
            return False
        with Image.open(target) as im:
            im.verify()
        return True
    except (OSError, ValueError, TypeError, KeyError):
        return False


def install_directory(folder: Path, *, root: Path = ROOT, replace: bool = False) -> dict:
    if not folder.is_dir():
        raise FileNotFoundError("Pasta com cenários não encontrada: "+str(folder))
    # Validate all nine BEFORE writing anything, to avoid partial imports.
    missing=[slot for slot in SLOTS if not (folder / f"{slot}.png").is_file()]
    if missing:
        raise FileNotFoundError("Faltam imagens na pasta: "+", ".join(missing))
    # Preflight identity change without touching other saved files.
    for slot in SLOTS:
        target=official(slot, root)
        if target.exists() and not replace:
            with Image.open(folder / f"{slot}.png") as im:
                stream=io.BytesIO();im.convert("RGBA").save(stream,"PNG")
            if sha(stream.getvalue()) != sha(target.read_bytes()):
                raise ValueError("Já existe imagem oficial diferente: "+slot+"; use -Refazer com histórico")
    results=[install(slot, folder / f"{slot}.png", root=root, replace=replace)
             for slot in SLOTS]
    return {"installed":results,"uploads":0}


def part1() -> dict:
    part=story.load_parts()[0]
    if part["id"] != EPISODE or len(part["segments"]) != len(SHOTS):
        raise ValueError("Storyboard por camadas não corresponde aos 9 trechos do EP 1 Parte 1")
    return part


def required_poses() -> list[str]:
    return list(dict.fromkeys(s["pose"] for s in SHOTS if s["pose"]))


def preflight(*, root: Path = ROOT) -> dict:
    sources={slot:installed(slot, root) for slot in SLOTS}
    characters={name:poses.valid(name, root) for name in required_poses()}
    folder=story.output_for(part1(), root)
    sound=folder/"narracao.mp3"
    try:
        story.read_voice(part1(), root)
        voice_ready=True
    except (OSError, ValueError):
        voice_ready=False
    music= root/"Wondertrail _Main Theme_.mp3"
    missing=[*["cenario:"+p for p,v in sources.items() if not v],
             *["pose:"+p for p,v in characters.items() if not v]]
    if not voice_ready:missing.append("narracao_original")
    if not music.is_file():missing.append("musica_original")
    return {
        "schema":POLICY,"episode":EPISODE,
        "storyboard": [
            {"beat":s["index"],"background":s["backdrop"],"pose":s["pose"],
             "animation":s["movement"],"show_egg":s["showEgg"]} for s in SHOTS
        ],
        "first_scene_no_emanuelly": SHOTS[0]["pose"] is None,
        "same_egg_entire_episode": len({str(official("ovo-azul",root))})==1,
        "assets_official":sources,"poses_ready":characters,
        "voice_ready":voice_ready,"music_ready":music.is_file(),
        "missing":missing,"ready":not missing,"uploads":0,
    }


def build_props(*, root: Path = ROOT) -> tuple[dict,Path,dict]:
    status=preflight(root=root)
    if not status["ready"]:
        raise ValueError("Materiais em falta: "+", ".join(status["missing"])+
                         ". Instale cenários/ovo e gere poses; não criar novas imagens de cena.")
    part=part1()
    voice, marker=story.read_voice(part, root)
    duration=story.audio_seconds(voice)
    frames=math.ceil((duration+.45)*story.FPS)
    if duration>story.MAX_AUDIO or frames>1800:
        raise ValueError("Narração excede o limite de 60s para Shorts Kids")
    _scenes,captions,beats=story.scene_props(
        story.episode_for_tts(part), marker, frames
    )
    if len(beats)!=len(SHOTS):
        raise ValueError("Número de beats diferente do storyboard")
    publish=root/"motion-remotion/public/generated/kids-emanuelly"/part["id"]/"layers"
    publish.mkdir(parents=True,exist_ok=True)
    shutil.copy2(voice,publish/"narracao.mp3")
    music=prepare_kids_music(root, part["id"])
    all_hashes=[]
    render_scenes=[]
    for shot,beat in zip(SHOTS,beats):
        if shot["index"]==1 and shot["pose"] is not None:
            raise ValueError("A primeira cena do ovo NÃO pode ter Emanuelly")
        background=official(shot["backdrop"],root)
        egg=official("ovo-azul",root)
        back_dest=publish/background.name
        egg_dest=publish/egg.name
        shutil.copy2(background,back_dest)
        shutil.copy2(egg,egg_dest)
        if shot["pose"]:
            source=poses.paths(shot["pose"],root)[0]
            pose_dest=publish/("emanuelly-"+shot["pose"]+".png")
            shutil.copy2(source,pose_dest)
            pose_path=(
                "generated/kids-emanuelly/"+part["id"]+"/layers/"+pose_dest.name
            )
            all_hashes.append(sha(source.read_bytes()))
        else:
            pose_path=None
        all_hashes.append(sha(background.read_bytes()))
        layer={
            "index":shot["index"],
            "startFrame":beat["startFrame"],"endFrame":beat["endFrame"],
            "background":"generated/kids-emanuelly/"+part["id"]+"/layers/"+back_dest.name,
            "pose":pose_path,
            "egg":"generated/kids-emanuelly/"+part["id"]+"/layers/"+egg_dest.name,
            "showEgg":shot["showEgg"],"poseX":shot["poseX"],"poseY":shot["poseY"],
            "poseSize":shot["poseSize"],"eggX":shot["eggX"],
            "eggY":shot["eggY"],"eggSize":shot["eggSize"],
            "animation":shot["movement"],"magic":shot.get("magic",False),
            "night":shot.get("night",False),
        }
        render_scenes.append(layer)
    all_hashes.append(sha(official("ovo-azul",root).read_bytes()))
    all_hashes.append(sha(voice.read_bytes()))
    all_hashes.append(music_signature(root,part["id"]))
    all_hashes.append(sha(part["narration"].encode("utf8")))
    signature=sha((POLICY+"|"+"|".join(all_hashes)).encode("utf8"))
    props={
        "episodeId":part["id"],"title":part["title"],
        "brand":"Emanuelly e seus Amigos de Pelúcia",
        "chapter":"EP 1 · PARTE 1/4","durationFrames":frames,
        "frames":[],"layeredScenes":render_scenes,"captions":captions,
        "audio":"generated/kids-emanuelly/"+part["id"]+"/layers/narracao.mp3",
        "referenceSha":signature,"madeForKids":True,"music":music,
    }
    file=root/"motion-remotion"/"props-emanuelly-camadas-parte1.json"
    story.dump(file, props)
    return props,file,{"signature":signature,"assets_sha256":all_hashes}


def render(*, root: Path = ROOT, regenerate: bool = False) -> dict:
    part=part1()
    folder=story.output_for(part,root)
    video=folder/"final-camadas.mp4"
    qa_path=folder/"qa-camadas.json"
    props,params,qa=build_props(root=root)
    if video.exists() and not regenerate:
        if qa_path.is_file():
            previous=json.loads(qa_path.read_text(encoding="utf8"))
            if previous.get("signature")==qa["signature"] and previous.get("video_sha256")==sha(video.read_bytes()):
                return {"status":"cache","video":str(video),"uploads":0}
        raise ValueError("Prévia anterior existe com outros recursos. Use -Refazer; histórico preservado.")
    motion=root/"motion-remotion"
    if not (motion/"node_modules").is_dir():
        raise RuntimeError("Remotion não instalado. Execute npm.cmd install dentro de motion-remotion")
    npm=shutil.which("npm.cmd" if sys.platform=="win32" else "npm")
    if not npm:
        raise FileNotFoundError("npm ausente")
    folder.mkdir(parents=True,exist_ok=True)
    target=folder/"preview-camadas-temp.mp4"
    target.unlink(missing_ok=True)
    subprocess.run(
        [npm,"run","render:emanuelly","--",str(target.resolve()),
         "--props",str(params.resolve()),"--concurrency","2"],
        cwd=motion,check=True,timeout=3000,
    )
    technical=story.verify_video(target)
    if technical.get("technical_status")!="passed":
        raise ValueError("QA técnico do MP4 reprovado: "+str(technical))
    if video.exists():
        history=folder/"historico-renders"
        history.mkdir(exist_ok=True)
        old=history/("final-camadas-"+sha(video.read_bytes())[:12]+".mp4")
        if not old.exists():shutil.copy2(video,old)
        if qa_path.exists():
            oldqa=history/("qa-camadas-"+sha(video.read_bytes())[:12]+".json")
            if not oldqa.exists():shutil.copy2(qa_path,oldqa)
    target.replace(video)
    story.dump(qa_path,{
        "schema":POLICY,"episode":part["id"],"signature":qa["signature"],
        "assets_sha256":qa["assets_sha256"],
        "video_sha256":sha(video.read_bytes()),
        "technical":technical,"status":"needs_visual_review",
        "made_for_kids":True,"uploads":0,
        "music_rights_review":"pending_before_publication",
        "no_new_image_ai_calls":True,
    })
    return {"status":"render_local_para_revisao","video":str(video),
            "qa":str(qa_path),"uploads":0}


def main(argv=None):
    ap=argparse.ArgumentParser(description="EP01 Parte 1 camadas Kids")
    ap.add_argument("--acao",choices=("planejar","instalar","instalar-lote",
                                       "props","renderizar","verificar"),
                    default="planejar")
    ap.add_argument("--tipo",choices=("Jardim","Quarto","Ovo"))
    ap.add_argument("--indice",type=int,default=1)
    ap.add_argument("--arquivo",type=Path)
    ap.add_argument("--pasta",type=Path)
    ap.add_argument("--refazer",action="store_true")
    args=ap.parse_args(argv)
    if args.refazer and args.acao not in ("instalar","instalar-lote","renderizar"):
        ap.error("-Refazer permitido apenas ao substituir ou renderizar")
    if args.acao=="instalar":
        if not args.tipo or not args.arquivo:
            ap.error("Instalar exige -Tipo e -Arquivo")
        if args.tipo=="Ovo":
            slot="ovo-azul"
        else:
            if not 1 <= args.indice <= 4:
                ap.error("Indice deve ser de 1 a 4")
            slot=f"{args.tipo.lower()}-{args.indice:02d}"
        result=install(slot,args.arquivo,replace=args.refazer)
    elif args.acao=="instalar-lote":
        if not args.pasta:ap.error("InstalarLote exige -Pasta")
        result=install_directory(args.pasta,replace=args.refazer)
    elif args.acao in ("planejar","verificar"):
        result=preflight()
    elif args.acao=="props":
        props,path,qa=build_props()
        result={"props":str(path),"frames":props["durationFrames"],
                "scenes":len(props["layeredScenes"]),
                "signature":qa["signature"],"uploaded":False}
    elif args.acao=="renderizar":
        result=render(regenerate=args.refazer)
    else:
        raise ValueError("Ação desconhecida")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=="__main__":
    try:raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,subprocess.SubprocessError) as error:
        print("[KIDS CAMADAS BLOQUEADO] "+str(error),file=sys.stderr)
        raise SystemExit(1)
