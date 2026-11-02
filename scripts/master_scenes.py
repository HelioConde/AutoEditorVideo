#!/usr/bin/env python3
"""Imagem-mãe -> PNG transparente -> cenário inpaint -> QA.

Não publica. Mantém respostas da IA em cache por prompt/modelo para evitar
reuso de artes erradas; funciona com endpoint JSON de edição se o proxy suportar.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys

from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat
from roteiro_para_storyboard import select_episode, save_plan

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'gerados'/'shorts-animados'
SIZE=(1024,1536)
SAFE=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
EDIT_URL='http://127.0.0.1:8080/v1/images/edits'


def sha(value:str)->str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:14]


def master_prompt(ep:dict, scene:dict)->str:
    return (scene['prompt']+' '
        'Use natural scale and consistent cinematic lighting. '
        'Keep all important human anatomy fully inside frame, at least 12 percent '
        'margin left/right and 10 percent above heads. Keep lower 20 percent '
        'clean for YouTube Shorts captions. Flat coherent 2D Japanese anime, '
        'one image, not a split screen, no typography or green screen.')


def scene_dir(ep:dict,scene:dict,model:str,output:Path=OUT)->Path:
    ident=sha(model+'\n'+master_prompt(ep,scene))
    return output/ep['id']/'master-scenes'/f"{scene['id']}-{ident}"


def read_storyboard(path:Path)->dict:
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schema')!='arquivo-otaku/master-storyboards/v2':
        raise ValueError('Storyboard v2 necessário; execute planejar-cenas.ps1')
    ep_id=data.get('id','')
    if not SAFE.fullmatch(ep_id):raise ValueError('ID de episódio inválido')
    scenes=data.get('scenes')
    if not isinstance(scenes,list) or not 1<=len(scenes)<=60:
        raise ValueError('O storyboard precisa de 1 a 60 enquadramentos')
    if [s.get('id') for s in scenes]!=[f'{i:02d}' for i in range(1,len(scenes)+1)]:
        raise ValueError('IDs dos enquadramentos não sequenciais')
    if any(len(s.get('prompt',''))<40 or s.get('subject') not in ('personagens','objeto') for s in scenes):
        raise ValueError('Prompt ou objeto inválido em enquadramento')
    return data


def validate_image(blob:bytes,*,alpha:bool)->dict:
    import numpy as np
    with Image.open(io.BytesIO(blob)) as im:
        im.load()
        if im.format!='PNG' or im.size!=SIZE:raise ValueError('Imagem deve ser PNG 1024x1536, sem redimensionar as camadas')
        if alpha and 'A' not in im.getbands():raise ValueError('Personagem/objeto veio sem canal alpha real')
        pixels=np.asarray(im.convert('RGBA').resize((256,384)),dtype=np.uint8)
    a=pixels[:,:,3]
    clear=float((a<35).mean())
    solid=a>150
    occupancy=float(solid.mean())
    if alpha and (clear<.08 or occupancy<.03 or occupancy>.9):
        raise ValueError(f'PNG alpha inválido: transparente={clear:.0%}, opaco={occupancy:.0%}')
    spill=0.
    bounds=[0,0,SIZE[0],SIZE[1]]
    warning=False
    if alpha:
        rgb=pixels[:,:,:3].astype('int16')
        green=(rgb[:,:,1]>145)&(rgb[:,:,1]>rgb[:,:,0]*1.65)&(rgb[:,:,1]>rgb[:,:,2]*1.65)
        spill=float((green&solid).sum())/max(1,int(solid.sum()))
        if spill>.015:raise ValueError(f'Verde residual {spill:.1%}. Não usar fundo verde como alternativa.')
        ys,xs=np.where(a>75)
        bounds=[int(xs.min()*4),int(ys.min()*4),int((xs.max()+1)*4),int((ys.max()+1)*4)]
        warning=bounds[0]<36 or bounds[2]>SIZE[0]-36 or bounds[1]<36
    return {'transparent_fraction':round(clear,3),'opaque_fraction':round(occupancy,3),
            'green_ratio':round(spill,4),'bounds':bounds,'margin_warning':bool(warning)}


def normalize_image(blob:bytes, *, alpha:bool, stage:str)->bytes:
    """Normalize proxy output to the shared portrait canvas without stretching.

    Keep raw paid responses untouched; normalize only the working copies.
    A single contain-and-pad transform preserves the complete frame and alpha.
    """
    try:
        with Image.open(io.BytesIO(blob)) as source:
            source.load()
            if source.format != 'PNG':
                raise ValueError(f'{stage}: proxy retornou {source.format}, esperado PNG')
            if alpha and 'A' not in source.getbands():
                raise ValueError(f'{stage}: camada sem alpha real')
            if source.size == SIZE:
                return blob
            original_size = source.size
            canvas = ImageOps.pad(
                source.convert('RGBA' if alpha else 'RGB'), SIZE,
                method=Image.Resampling.LANCZOS, color=(0, 0, 0, 0) if alpha else (0, 0, 0),
            )
            buffer = io.BytesIO()
            canvas.save(buffer, format='PNG', optimize=True)
            print(f'[AJUSTE] {stage}: {original_size[0]}x{original_size[1]} -> '
                  '1024x1536, proporcional e sem cortar (original em cache).',
                  flush=True)
            return buffer.getvalue()
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError(f'{stage}: imagem PNG inválida: {exc}') from exc


def image_url(image:Path)->str:
    data=image.read_bytes()
    if not data or len(data)>18_000_000:raise ValueError('Imagem de referência vazia ou acima de 18 MB')
    return 'data:image/png;base64,'+base64.b64encode(data).decode('ascii')


def request_edit(master:Path,prompt:str,model:str,key:str,*,transparent:bool,
                 mask:Path|None=None,post=None)->bytes:
    if not master.is_file() or (mask is not None and not mask.is_file()):
        raise FileNotFoundError('Imagem ou máscara de referência ausente')
    payload={'model':model,'images':[{'image_url':image_url(master)}],
             'prompt':prompt,'n':1,'size':'1024x1536',
             'background':'transparent' if transparent else 'opaque',
             'output_format':'png'}
    if model=='gpt-image-1.5':payload['input_fidelity']='high'
    if mask is not None:payload['mask']={'image_url':image_url(mask)}
    if post is None:
        import requests
        post=requests.post
    r=post(EDIT_URL,json=payload,headers={'Authorization':'Bearer '+key,
          'Content-Type':'application/json'},timeout=(15,360))
    if not r.ok:
        raise RuntimeError(f'Proxy recusou images/edits (HTTP {r.status_code}): {str(r.text)[:180]}. '
                           'Sem gerar nova cena de forma independente.')
    data=r.json().get('data') or []
    if not data:raise RuntimeError('O proxy não retornou imagem editada')
    value=data[0].get('b64_json') or data[0].get('url','')
    if value.startswith('data:image/'):value=value.split(',',1)[1]
    if not value or value.startswith('http'):raise RuntimeError('Edits sem base64 local; URL remota não aceita')
    try:blob=base64.b64decode(value,validate=True)
    except Exception as exc:raise RuntimeError('Base64 inválido na resposta de edição') from exc
    if len(blob)>25_000_000:raise RuntimeError('Resposta PNG maior que 25 MB')
    return blob


def foreground_prompt(scene:dict)->str:
    thing='personagens, seus cabelos, roupas, mãos e acessórios visíveis' if scene['subject']=='personagens' else 'objeto de primeiro plano que é o foco'
    return ('Edit the ATTACHED scene, keeping exact original 1024x1536 canvas and X/Y '
            'placement. Isolate ONLY the '+thing+' and turn every other pixel '
            'TRANSPARENT with real PNG alpha. No green, no scene elements, '
            'do not create or redraw new poses, do not move the subject.')


def background_prompt()->str:
    return ('Edit ONLY the masked region in the attached original image. '
            'Completely remove the foreground subject, including every loose hair tip, '
            'hand, finger, sleeve, arm and clothing fragment. Reconstruct the EMPTY '
            'room and table behind the subject. Absolutely no floating hair, '
            'disconnected silhouettes, remaining limbs or dark cutout remnants. '
            'Keep the chessboard, furniture, walls, camera angle, reflections and '
            'lighting consistent. Preserve all unmasked pixels and the exact '
            'original 1024x1536 canvas.')


def make_mask(fg:Path,target:Path)->None:
    with Image.open(fg) as im:
        alpha=im.getchannel('A')
    # Binary closure catches narrow holes between strands/fingers before a wider dilation.
    solid=alpha.point(lambda v:255 if v>20 else 0)
    closed=solid.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(11))
    dilated=closed.filter(ImageFilter.MaxFilter(61))
    inv=ImageOps.invert(dilated.filter(ImageFilter.GaussianBlur(2)))
    im=Image.new('RGBA',SIZE,(0,0,0,0));im.putalpha(inv)
    im.save(target,'PNG',optimize=True)
    if target.stat().st_size>=4_000_000:raise ValueError('Máscara de fundo acima do limite de 4MB')


def find_clean_background(master:Path,mask:Path,directory:Path)->Path|None:
    """Reuse only same-camera clean plates: never substitute a merely similar room.

    Explicit background-clean.png has priority. Other scenes are candidates only
    when their unchanged, nonblack background pixels align closely with master.
    """
    import numpy as np
    sample=(128,192)
    with Image.open(master) as original, Image.open(mask) as mask_image:
        base=np.asarray(original.convert('RGB').resize(sample),dtype=np.int16)
        keep=np.asarray(mask_image.getchannel('A').resize(sample),dtype=np.uint8)>245
    # Exclude letterbox black: matching empty margins proves nothing about geometry.
    valid=keep & (base.mean(axis=2)>40)
    if int(valid.sum())<2000:
        return None
    candidates=[directory/'background-clean.png']
    if directory.parent.is_dir():
        for sibling in sorted(directory.parent.iterdir()):
            if sibling.is_dir() and sibling!=directory:
                candidates.extend((sibling/'background-clean.png',sibling/'background.png'))
    best=None
    best_score=float('inf')
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            with Image.open(candidate) as image:
                if image.size!=SIZE or image.format!='PNG':
                    continue
                rgb=np.asarray(image.convert('RGB').resize(sample),dtype=np.int16)
        except (OSError,ValueError):
            continue
        difference=np.abs(rgb-base).mean(axis=2)[valid]
        mean=float(difference.mean())
        q75=float(np.percentile(difference,75))
        if mean<12 and q75<19 and mean<best_score:
            best,best_score=candidate,mean
    if best:
        print(f'[FUNDO LIMPO] Referencia alinhada: {best} (erro {best_score:.1f})',flush=True)
    return best


def reconstruct(master:Path,edited:Path,mask:Path,out:Path)->None:
    with Image.open(master) as a, Image.open(edited) as b, Image.open(mask) as m:
        erase=ImageOps.invert(m.getchannel('A'))
        merged=Image.composite(b.convert('RGB'),a.convert('RGB'),erase)
        merged.save(out,'PNG',optimize=True)


def compare(master:Path,bg:Path,fg:Path,output:Path)->dict:
    with Image.open(master) as original,Image.open(bg) as background,Image.open(fg) as foreground:
        main=original.convert('RGB')
        merged=Image.alpha_composite(background.convert('RGBA'),foreground.convert('RGBA')).convert('RGB')
        difference=ImageChops.difference(main,merged)
        error=round(sum(ImageStat.Stat(difference.resize((256,384))).mean)/3,2)
        preview=Image.new('RGB',(1024,768))
        preview.paste(main.resize((512,768)),(0,0))
        preview.paste(merged.resize((512,768)),(512,0))
        preview.save(output,'JPEG',quality=90)
    return {'mean_rgb_difference':error,'alignment_warning':error>50,
            'visual_approval':'pendente','comparison':str(output)}


def atomic(path:Path,bytes_:bytes)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name('.'+path.name+'.partial')
    tmp.write_bytes(bytes_);tmp.replace(path)


def estimate(ep:dict,scenes:list[dict],model:str,*,existing_master:Path|None=None,
             repair_background:bool=False)->list[str]:
    pending=[]
    for s in scenes:
        d=scene_dir(ep,s,model)
        if not (d/'master.png').is_file() and not (d/'master-raw.png').is_file() and existing_master is None:pending.append(s['id']+'/master')
        if not (d/'foreground-raw.png').is_file():pending.append(s['id']+'/foreground')
        if repair_background and (d/'background-raw.png').is_file():
            pending.append(s['id']+'/background-repair')
        elif not (d/'background-raw.png').is_file():
            pending.append(s['id']+'/background')
    return pending


def execute_scene(ep:dict,scene:dict,model:str,*,directory:Path|None=None,
                  supplied_master:Path|None=None,generate=None,edit=None,offline:bool=False,
                  repair_background:bool=False)->dict:
    d=directory or scene_dir(ep,scene,model)
    d.mkdir(parents=True,exist_ok=True)
    master=d/'master.png'
    fg_raw=d/'foreground-raw.png'
    fg=d/'foreground.png'
    bg_raw=d/'background-raw.png'
    bg=d/'background.png'
    mask=d/'background-mask.png'
    if not master.exists():
        if supplied_master:
            with Image.open(supplied_master) as im:
                if im.size!=SIZE:raise ValueError('Master importada precisa ter 1024x1536')
                im.convert('RGB').save(master,'PNG')
        else:
            raw_master=d/'master-raw.png'
            if raw_master.is_file():
                content=raw_master.read_bytes()
            else:
                if offline or generate is None:raise RuntimeError('Master não existe e geração por IA não está autorizada')
                content=generate(master_prompt(ep,scene),model)
                atomic(raw_master,content)  # Preservar resposta paga mesmo se o formato estiver errado.
            normalized=normalize_image(content,alpha=False,stage=f"{scene['id']}/master")
            validate_image(normalized,alpha=False)
            atomic(master,normalized)
    validate_image(master.read_bytes(),alpha=False)
    if not fg_raw.exists():
        if offline or edit is None:raise RuntimeError('Foreground ausente no cache; não gerar em offline')
        content=edit(master,foreground_prompt(scene),model,transparent=True)
        atomic(fg_raw,content)
    normalized_fg=normalize_image(fg_raw.read_bytes(),alpha=True,stage=f"{scene['id']}/foreground")
    report=validate_image(normalized_fg,alpha=True)
    atomic(fg,normalized_fg)
    make_mask(fg,mask)
    if repair_background or not bg_raw.exists():
        if offline or edit is None:
            raise RuntimeError('Background ausente ou reparo solicitado em modo offline')
        content=edit(master,background_prompt(),model,transparent=False,mask=mask)
        # Validate the new paid result BEFORE replacing any cached source.
        normalized_new=normalize_image(content,alpha=False,stage=f"{scene['id']}/background")
        validate_image(normalized_new,alpha=False)
        if bg_raw.is_file():
            previous=bg_raw.read_bytes()
            backup=d/('background-raw-backup-'+hashlib.sha256(previous).hexdigest()[:12]+'.png')
            if not backup.exists():
                atomic(backup,previous)
        atomic(bg_raw,content)
    normalized_bg=normalize_image(bg_raw.read_bytes(),alpha=False,stage=f"{scene['id']}/background")
    validate_image(normalized_bg,alpha=False)
    working_bg=d/'background-normalized.png'
    atomic(working_bg,normalized_bg)
    clean_reference=find_clean_background(master,mask,d)
    source=clean_reference or working_bg
    reconstruct(master,source,mask,bg)
    comp=compare(master,bg,fg,d/'comparacao.jpg')
    result={'version':'master-derived-v2','episode':ep['id'],'scene':scene['id'],
            'background_source':str(clean_reference) if clean_reference else 'inpainting',
            'subject':scene['subject'],'alpha':report,'composition':comp,
            'status':'aguardando_revisao_visual','files':{
              name:str(d/name) for name in ('master.png','foreground.png','background.png','comparacao.jpg')}}
    atomic(d/'qa.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return result


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='Gera master, recorta foreground e reconstrói cenário; não publica')
    ap.add_argument('--id',default='003-death-note-xadrez')
    ap.add_argument('--plano',type=Path)
    ap.add_argument('--cena',type=int,default=1)
    ap.add_argument('--todas-cenas',action='store_true')
    ap.add_argument('--modelo',default='gpt-image-1.5',choices=['gpt-image-1.5','gpt-image-2'])
    ap.add_argument('--max-chamadas',type=int,default=3)
    ap.add_argument('--max-segundos-por-plano',type=float,default=6)
    ap.add_argument('--master-existente',type=Path)
    ap.add_argument('--planejar',action='store_true')
    ap.add_argument('--offline',action='store_true')
    ap.add_argument('--validar',action='store_true')
    ap.add_argument('--reparar-fundo',action='store_true',help='Refaz somente o background via IA; faz backup do raw anterior')
    args=ap.parse_args(argv)
    if not 0<=args.max_chamadas<=180:raise ValueError('Limite permitido: 0 a 180 chamadas')
    if args.master_existente and args.todas_cenas:raise ValueError('Master existente funciona somente com uma cena')
    plan_path=args.plano or save_plan(select_episode(args.id),max_hold=args.max_segundos_por_plano)
    ep=read_storyboard(plan_path)
    if ep['id']!=args.id:raise ValueError('ID no storyboard diferente do solicitado')
    scenes=ep['scenes'] if args.todas_cenas else [next((s for s in ep['scenes'] if int(s['id'])==args.cena),None)]
    if scenes[0] is None:raise ValueError('Cena solicitada não existe')
    missing=estimate(ep,scenes,args.modelo,existing_master=args.master_existente,
                     repair_background=args.reparar_fundo and not args.validar)
    print(f"[PLANO] {len(scenes)} de {len(ep['scenes'])} enquadramentos; "
          f"{len(missing)} chamadas adicionais previstas; orçamento {args.max_chamadas}.")
    for stage in missing:print('  [PENDENTE] '+stage)
    if args.planejar:return 0
    if args.validar:
        for scene in scenes:
            d=scene_dir(ep,scene,args.modelo)
            for name,alpha in [('master.png',False),('foreground.png',True),('background.png',False)]:
                validate_image((d/name).read_bytes(),alpha=alpha)
            print(f'[QA] {d}/comparacao.jpg')
        return 0
    if args.offline and missing:raise RuntimeError('Imagens faltando, mas foi solicitado modo offline')
    if len(missing)>args.max_chamadas:raise RuntimeError('Orçamento de IA insuficiente; nenhum pedido enviado')
    generate=edit=None
    if missing:
        sys.path.insert(0,str(ROOT/'scripts'))
        from gerar_video_codex import proxy_key,check_proxy_accounts,request_image
        key=proxy_key(Path(os.environ['ARQUIVO_OTAKU_PROXY_ENV'])) if os.environ.get('ARQUIVO_OTAKU_PROXY_ENV') else proxy_key()
        check_proxy_accounts(key)
        generate=lambda prompt,model:request_image(prompt,model,key,size='1024x1536',output_format='png')
        edit=lambda image,prompt,model,*,transparent,mask=None:request_edit(
            image,prompt,model,key,transparent=transparent,mask=mask)
    for idx,scene in enumerate(scenes,1):
        result=execute_scene(ep,scene,args.modelo,supplied_master=args.master_existente,
                             generate=generate,edit=edit,offline=args.offline,
                             repair_background=args.reparar_fundo)
        print(f"[OK] {idx}/{len(scenes)} cena {scene['id']} | diferença média: "
              f"{result['composition']['mean_rgb_difference']} | margens: "
              f"{'REVER' if result['alpha']['margin_warning'] else 'OK'}")
    print('[PRONTO] Cenas em cache para revisão. Nenhum upload foi executado.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError,RuntimeError,KeyError) as exc:
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
