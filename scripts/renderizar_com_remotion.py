#!/usr/bin/env python3
"""Reutiliza PNG, voz e ASS de Shorts existentes no Remotion; sem IA e sem upload."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SPEC=ROOT/'conteudos'/'testes-animados-5.json'
OUT=ROOT/'assets'/'gerados'/'shorts-animados'
MOTION=ROOT/'motion-remotion'
SAFE_ID=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
FPS=30

def select_asset(folder:Path,prefix:str)->Path:
    choices=sorted(folder.glob(prefix+'-*.png'),key=lambda x:x.stat().st_mtime,reverse=True)
    if not choices:raise FileNotFoundError(f'{prefix} ausente em {folder}. Gere primeiro as camadas.')
    return choices[0]

def inspect_alpha(path:Path)->dict:
    import numpy as np
    with Image.open(path) as original:
        if 'A' not in original.getbands():
            raise ValueError(f'{path.name}: sem canal alpha real')
        pixels=np.asarray(original.convert('RGBA'),dtype=np.uint8)
    alpha=pixels[:,:,3]
    transparent=float((alpha<40).mean())
    opaque=alpha>150
    if transparent<.05 or float(opaque.mean())<.04:
        raise ValueError(f'{path.name}: transparencia insuficiente')
    rgb=pixels[:,:,:3].astype('int16')
    green=((rgb[:,:,1]>125)&(rgb[:,:,1]>rgb[:,:,0]*1.5)&(rgb[:,:,1]>rgb[:,:,2]*1.5))
    spill=float((green&opaque).sum())/max(1,int(opaque.sum()))
    if spill>.012:
        raise ValueError(f'{path.name}: {spill:.1%} verde residual; gere novamente com PNG alpha nativo')
    ys,xs=np.where(alpha>32)
    if not len(xs):raise ValueError(f'{path.name}: camada vazia')
    box=(max(0,int(xs.min())-16),max(0,int(ys.min())-16),
         min(pixels.shape[1],int(xs.max())+17),min(pixels.shape[0],int(ys.max())+17))
    return {'green_ratio':round(spill,4),'alpha_fraction':round(transparent,3),'bounds':box}

def copy_asset(source:Path,target:Path,kind:str)->dict:
    target.parent.mkdir(parents=True,exist_ok=True)
    if kind=='background':
        with Image.open(source) as im:
            if min(im.size)<640:raise ValueError('Fundo menor que 640 px')
            im.convert('RGB').save(target,'PNG')
        return {'tipo':'background'}
    stats=inspect_alpha(source)
    with Image.open(source) as im:
        im.convert('RGBA').crop(tuple(stats['bounds'])).save(target,'PNG')
    return stats

def ass_time(text:str)->float:
    h,m,s=text.split(':')
    return int(h)*3600+int(m)*60+float(s)

def captions_from_ass(path:Path,duration:float)->list[dict]:
    captions=[]
    for row in path.read_text(encoding='utf-8-sig').splitlines():
        if not row.startswith('Dialogue:'):continue
        fields=row.split(',',9)
        if len(fields)!=10:continue
        start,end=ass_time(fields[1]),ass_time(fields[2])
        label=re.sub(r'\{.*?\}','',fields[9]).replace(r'\N',' ').strip()
        if label and 0<=start<end<=duration+1:
            captions.append({'startFrame':round(start*FPS),
                             'endFrame':min(round(duration*FPS),round(end*FPS)),
                             'text':label})
    if not captions:raise ValueError(f'Sem legendas ASS validas: {path}')
    return captions

def audio_duration(path:Path)->float:
    cp=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
       '-of','default=nw=1:nk=1',str(path)],capture_output=True,text=True,timeout=20,check=True)
    value=float(cp.stdout.strip())
    if not 8<=value<=180:raise ValueError(f'Audio invalido: {value}s')
    return value

def layer(src:str,motion:str,x:int,y:int,width:int,dx:int=0,dy:int=0,delay:int=0)->dict:
    return {'src':src,'motion':motion,'x':x,'y':y,'width':width,'dx':dx,'dy':dy,'delay':delay}

def build_episode(episode:dict,folder:Path,public:Path,audio_path:Path|None=None)->dict:
    ep_id=episode['id']
    if not SAFE_ID.fullmatch(ep_id):raise ValueError('ID de episodio invalido')
    dest=public/'generated'/ep_id
    kinds=['background','character','object']+(['extra_object'] if episode.get('extra_object') else [])
    found={kind:select_asset(folder,kind) for kind in kinds}
    # Nao desperdiçar tempo em render se houver partes verdes ou sem alpha.
    for kind in found:
        if kind!='background':inspect_alpha(found[kind])
    voices=sorted(folder.glob('voz-*.mp3'),key=lambda p:p.stat().st_mtime,reverse=True)
    voice=audio_path or (voices[0] if voices else None)
    if not voice or not voice.is_file():raise FileNotFoundError('MP3 de voz nao encontrado')
    duration=audio_duration(voice)
    captions=captions_from_ass(folder/'legendas.ass',duration+.4)
    dest.mkdir(parents=True,exist_ok=True)
    for kind,source in found.items():copy_asset(source,dest/f'{kind}.png',kind)
    shutil.copy2(voice,dest/'voz.mp3')
    base=f'generated/{ep_id}/'
    presets={
      'chess':[layer(base+'character.png','breathe',135,300,810),
               layer(base+'object.png','chess-slide',260,1020,185,185,-12,18)],
      'second_kira':[layer(base+'character.png','reveal',125,290,830),
                     layer(base+'object.png','float',485,1060,285)],
      'blood':[layer(base+'character.png','breathe',180,330,750),
               layer(base+'object.png','blood-drop',490,540,140,0,510,20)],
      'ryuk':[layer(base+'character.png','float',80,190,890),
              layer(base+'object.png','feather',560,520,175,0,430,12)],
      'apple':[layer(base+'character.png','breathe',85,240,900),
               layer(base+'object.png','apple-bounce',535,540,175,0,380,20)]
    }
    if episode['effect'] not in presets:raise ValueError('Efeito nao reconhecido')
    layers=presets[episode['effect']]
    if 'extra_object' in found:
        layers.append(layer(base+'extra_object.png','chess-slide',730,1100,185,-190,0,26))
    return {'id':ep_id,'durationFrames':math.ceil((duration+.4)*FPS),
            'background':base+'background.png','layers':layers,
            'audio':base+'voz.mp3','captions':captions,
            'hook':episode.get('cover',''),'title':episode.get('title',''),'effect':episode['effect']}

def main()->int:
    parser=argparse.ArgumentParser(description='Remotion opcional sem chamadas IA, nem upload ao YouTube')
    parser.add_argument('--id',required=True)
    parser.add_argument('--plano',type=Path,default=SPEC)
    parser.add_argument('--assets',type=Path,default=OUT)
    parser.add_argument('--motor',type=Path,default=MOTION)
    parser.add_argument('--renderizar',action='store_true')
    args=parser.parse_args()
    try:
        manifest=json.loads(args.plano.read_text(encoding='utf-8-sig'))
        ep=next((e for e in manifest['episodes'] if e['id']==args.id),None)
        if ep is None:raise ValueError('ID de episodio nao encontrado')
        props=build_episode(ep,args.assets/args.id,args.motor/'public')
        path=args.motor/f'props-{args.id}.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(props,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('[OK] Dados de renderizacao: '+str(path))
        if args.renderizar:
            npm=shutil.which('npm.cmd' if sys.platform=='win32' else 'npm')
            if not npm:raise RuntimeError('npm nao encontrado no PATH')
            if not (args.motor/'node_modules').is_dir():raise RuntimeError('Execute npm install em motion-remotion')
            out=args.assets/args.id/f'{args.id}-remotion.mp4'
            subprocess.run([npm,'run','render','--',str(out.resolve()),
                            '--props',str(path.resolve()),'--concurrency','2'],
                            cwd=str(args.motor),check=True)
            print('[OK] MP4 renderizado: '+str(out))
        else:
            print('[PREPARADO] Rode novamente com --renderizar; nenhum video enviado')
        return 0
    except (ValueError,KeyError,IndexError,OSError,subprocess.SubprocessError) as exc:
        print('[ERRO] '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
