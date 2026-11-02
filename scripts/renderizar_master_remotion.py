#!/usr/bin/env python3
"""Monta qualquer quantidade de imagens-mãe em um Short Remotion 9:16.

Tempos proporcionais à voz real; legendas ASS obtidas do TTS.
Nenhum upload e nenhuma geração de imagens ocorrem neste módulo.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MOTION=ROOT/'motion-remotion'
OUT=ROOT/'assets'/'gerados'/'shorts-animados'
FPS=30
sys.path.insert(0,str(ROOT/'scripts'))
from master_scenes import read_storyboard,scene_dir,validate_image,production_storyboard
from roteiro_para_storyboard import select_episode, save_plan
from narracao_shorts import ensure_voice
from renderizar_com_remotion import audio_duration,captions_from_ass


def validate_scenes(ep:dict,model:str,output:Path=OUT)->list[dict]:
    verified=[]
    for scene in ep['scenes']:
        folder=scene_dir(ep,scene,model,output)
        paths={k:folder/(k+'.png') for k in ('master','foreground','background')}
        for kind,path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(f'Enquadramento {scene["id"]}: falta {path}. Gere as camadas antes.')
            validate_image(path.read_bytes(),alpha=kind=='foreground')
        qa=folder/'qa.json'
        if not qa.is_file():
            raise ValueError(f'Enquadramento {scene["id"]}: falta QA da composição')
        report=json.loads(qa.read_text(encoding='utf-8'))
        if report.get('status')!='aguardando_revisao_visual':
            raise ValueError('Enquadramento sem relatório de extração válido')
        if report.get('warnings'):
            print(f"[QA AVISO] Cena {scene['id']}: {', '.join(report['warnings'])}. "
                  'Confira o background antes de publicar.')
        verified.append({'scene':scene,'folder':folder,'files':paths,'qa':report})
    return verified


def assign_frames(scenes:list[dict],seconds:float)->list[tuple[int,int]]:
    if not scenes:raise ValueError('Vídeo sem cenas')
    frames=math.ceil(seconds*FPS)
    sizes=[max(1,len(s.get('trecho_roteiro','').split())) for s in scenes]
    total=sum(sizes)
    marks=[0]
    for i in range(1,len(sizes)):
        marks.append(round(frames*sum(sizes[:i])/total))
    marks.append(frames)
    bounds=list(zip(marks[:-1],marks[1:]))
    if any(end<=start for start,end in bounds):
        raise ValueError('Duração muito curta para o número de planos')
    return bounds


def build_props(ep:dict,voice:Path,captions:list[dict],seconds:float,
                *,model:str='gpt-image-1.5',output:Path=OUT,public:Path|None=None)->dict:
    entries=validate_scenes(ep,model,output)
    target=(public or MOTION/'public')/'generated'/ep['id']
    target.mkdir(parents=True,exist_ok=True)
    bounds=assign_frames([e['scene'] for e in entries],seconds)
    scenes=[]
    for entry,(start,end) in zip(entries,bounds):
        scene=entry['scene']
        stem='scene-'+scene['id']
        for kind in ('foreground','background'):
            shutil.copy2(entry['files'][kind],target/f'{stem}-{kind}.png')
        scenes.append({'id':scene['id'],'subject':scene['subject'],
                       'startFrame':start,'endFrame':end,
                       'background':f'generated/{ep["id"]}/{stem}-background.png',
                       'foreground':f'generated/{ep["id"]}/{stem}-foreground.png'})
    shutil.copy2(voice,target/'voz.mp3')
    parent=select_episode(ep['id'])
    return {'id':ep['id'],'durationFrames':bounds[-1][1],
            'audio':f'generated/{ep["id"]}/voz.mp3',
            'scenes':scenes,'captions':captions,'hook':parent.get('cover','')}


def cover_from_master(ep:dict,model:str,destination:Path)->None:
    first=scene_dir(ep,ep['scenes'][0],model)/'master.png'
    with Image.open(first) as im:
        canvas=im.convert('RGB').resize((1080,1620),Image.Resampling.LANCZOS)
    frame=Image.new('RGB',(1080,1920),'#0a0b14')
    frame.paste(canvas,(0,145))
    layer=Image.new('RGBA',frame.size,(0,0,0,0))
    drawer=ImageDraw.Draw(layer)
    drawer.rounded_rectangle((60,120,1020,310),radius=24,fill=(5,7,14,215))
    label=select_episode(ep['id']).get('cover','ARQUIVO OTAKU')
    try:
        family='C:/Windows/Fonts/arialbd.ttf'
        if not Path(family).exists():family='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        font=ImageFont.truetype(family,64)
    except OSError:
        font=ImageFont.load_default()
    drawer.multiline_text((90,160),str(label)[:45],font=font,fill='white',
                          stroke_width=3,stroke_fill='#14141a')
    frame=Image.alpha_composite(frame.convert('RGBA'),layer).convert('RGB')
    destination.parent.mkdir(parents=True,exist_ok=True)
    frame.save(destination,'JPEG',quality=90,optimize=True)


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='Renderiza Short com múltiplas imagens originais; não publica')
    ap.add_argument('--id',default='003-death-note-xadrez')
    ap.add_argument('--plano',type=Path)
    ap.add_argument('--modelo',default='gpt-image-1.5')
    ap.add_argument('--max-segundos-por-plano',type=float,default=6)
    ap.add_argument('--criar-voz',action='store_true')
    ap.add_argument('--renderizar',action='store_true')
    ap.add_argument('--motor',type=Path,default=MOTION)
    args=ap.parse_args(argv)
    path=production_storyboard(args.id,args.max_segundos_por_plano,selected=args.plano)
    ep=read_storyboard(path)
    if ep['id']!=args.id:raise ValueError('ID de episódio divergente')
    validated=validate_scenes(ep,args.modelo)
    print(f'[QA] {len(validated)} enquadramentos com PNG alfa e cenário correspondente.')
    folder=OUT/args.id
    voice,ass=ensure_voice(select_episode(args.id),folder,create=args.criar_voz)
    seconds=audio_duration(voice)+.4
    captions=captions_from_ass(ass,seconds)
    if not captions:raise RuntimeError('Narração sem legendas')
    props=build_props(ep,voice,captions,seconds,model=args.modelo,public=args.motor/'public')
    propfile=args.motor/f"props-master-{ep['id']}.json"
    propfile.write_text(json.dumps(props,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"[PREPARADO] {len(props['scenes'])} planos, {seconds:.1f}s e {len(captions)} legendas: {propfile}")
    if not args.renderizar:
        print('[INFO] Rode novamente com --renderizar para exportar MP4. Nada foi publicado.')
        return 0
    if not (args.motor/'node_modules').is_dir():
        raise RuntimeError('Execute npm.cmd install em motion-remotion antes de renderizar')
    npm=shutil.which('npm.cmd' if sys.platform=='win32' else 'npm')
    if not npm:raise RuntimeError('Node/npm não encontrado')
    output=folder/f"{ep['id']}-master-multicenas.mp4"
    command=[npm,'run','render:master','--',str(output.resolve()),'--props',
             str(propfile.resolve()),'--concurrency','2']
    subprocess.run(command,cwd=args.motor,check=True,timeout=1800)
    cover=folder/f"{ep['id']}-master-capa.jpg"
    cover_from_master(ep,args.modelo,cover)
    manifest={'id':ep['id'],'status':'renderizado-aguardando-revisao',
              'mp4':str(output),'cover':str(cover),'duration_s':seconds,
              'narrative_beats':ep.get('narrative_beats'),
              'visual_shots':len(props['scenes']),'captions':len(captions),
              'published':False,
              'visual_alerts':[{'scene':e['scene']['id'],
                  'margins':e['qa']['alpha'].get('margin_warning'),
                  'alignment':e['qa']['composition'].get('alignment_warning'),
                  'background_source':e['qa'].get('background_source','desconhecido'),
                  'background_warnings':e['qa'].get('warnings',[])}
                  for e in validated]}
    (folder/'qa-master-multicenas.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'[OK] Short pronto para revisão (NÃO publicado): {output}')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,FileNotFoundError,OSError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
