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
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MOTION=ROOT/'motion-remotion'
OUT=ROOT/'assets'/'gerados'/'shorts-animados'
FPS=30
sys.path.insert(0,str(ROOT/'scripts'))
from master_scenes import read_storyboard,scene_dir,validate_image,production_storyboard
from roteiro_para_storyboard import select_episode, save_plan
from narracao_shorts import ensure_voice
from renderizar_com_remotion import audio_duration,captions_from_ass
from capa_cinematografica import cover_options, render_cover
from qa_foreground_fidelity import foreground_fidelity


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
        # Recheck even old QA files: a previously cached scene may have been
        # produced before the source-consistency test existed.
        source=folder/'foreground-normalized.png'
        if not source.is_file():
            source=folder/'foreground-raw.png'
        if not source.is_file():
            source=paths['foreground']
        fidelity=foreground_fidelity(paths['master'],source)
        safe_2d=bool(fidelity.get('review_required') or fidelity['redrawn'])
        if report.get('warnings'):
            print(f"[QA AVISO] Cena {scene['id']}: {', '.join(report['warnings'])}. "
                  'Confira o background antes de publicar.')
        if safe_2d:
            print(f"[QA PROTECAO] Cena {scene['id']}: foreground redesenhado ou "
                  'inconclusivo. Renderizando a master original como imagem '
                  'inteira, sem recompor corpo/tabuleiro. Nenhuma IA usada.')
        verified.append({'scene':scene,'folder':folder,'files':paths,
                         'qa':report,'fidelity':fidelity,
                         'render_mode':'master_static' if safe_2d else '2_5d'})
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
        if entry['render_mode']=='master_static':
            # A wrongly redrawn alpha layer may cover furniture and chess
            # pieces. Use the ORIGINAL master as a single still image.
            shutil.copy2(entry['files']['master'],target/f'{stem}-background.png')
            with Image.open(entry['files']['master']) as source:
                canvas=source.size
            Image.new('RGBA',canvas,(0,0,0,0)).save(
                target/f'{stem}-foreground.png',format='PNG')
        else:
            for kind in ('foreground','background'):
                shutil.copy2(entry['files'][kind],target/f'{stem}-{kind}.png')
        scenes.append({'id':scene['id'],'subject':scene['subject'],
                       'renderMode':entry['render_mode'],
                       'foregroundQA':entry['fidelity'],
                       'startFrame':start,'endFrame':end,
                       'background':f'generated/{ep["id"]}/{stem}-background.png',
                       'foreground':f'generated/{ep["id"]}/{stem}-foreground.png',
                       'shotType':scene.get('shot_type','legacy'),
                       'cameraAngle':scene.get('camera_angle',''),
                       'focusSubject':scene.get('focus_subject',''),
                       'action':scene.get('action','')})
    shutil.copy2(voice,target/'voz.mp3')
    parent=select_episode(ep['id'])
    return {'id':ep['id'],'durationFrames':bounds[-1][1],
            'audio':f'generated/{ep["id"]}/voz.mp3',
            'scenes':scenes,'captions':captions,'hook':parent.get('cover','')}


def cover_from_master(ep:dict,model:str,destination:Path)->dict:
    """Create a premium cover from cached scene layers; never request new images."""
    options=cover_options(ROOT,ep['id'])
    chosen=options.get('scene',ep['scenes'][0]['id'])
    scene=next((s for s in ep['scenes'] if s['id']==chosen),None)
    if scene is None:
        raise ValueError(f'Cena de capa {chosen} ausente no storyboard atual')
    folder=scene_dir(ep,scene,model)
    foreground=folder/'foreground.png'
    background=folder/'background.png'
    master=folder/'master.png'
    if background.is_file() and foreground.is_file():
        validate_image(background.read_bytes(),alpha=False)
        validate_image(foreground.read_bytes(),alpha=True)
        unshifted=folder/'foreground-normalized.png'
        if not unshifted.is_file():
            unshifted=folder/'foreground-raw.png'
        if not unshifted.is_file():
            unshifted=foreground
        fidelity=foreground_fidelity(master,unshifted)
        if fidelity.get('review_required') or fidelity['redrawn']:
            with Image.open(master) as im:
                source=im.convert('RGB')
            source_type='master-static-qa'
            print(f'[CAPA PROTECAO] Cena {chosen}: extração redesenhada; '
                  'usando imagem original completa.',flush=True)
        else:
            with Image.open(background) as bg, Image.open(foreground) as fg:
                source=Image.alpha_composite(bg.convert('RGBA'),fg.convert('RGBA')).convert('RGB')
            source_type='background+foreground'
    elif master.is_file():
        validate_image(master.read_bytes(),alpha=False)
        with Image.open(master) as im:
            source=im.convert('RGB')
        source_type='master'
        print(f'[CAPA AVISO] Cena {chosen}: camadas finais ausentes; '
              'usando a master original.',flush=True)
    else:
        raise FileNotFoundError(
            f'Nao ha imagens da cena {chosen} para gerar capa offline em {folder}. '
            'Gere ou recupere o cache dessa cena.')
    label=options.get('title') or select_episode(ep['id']).get('cover') or ep.get('title') or 'ARQUIVO OTAKU'
    report=render_cover(source,str(label),destination,
                        zoom=options.get('zoom',1.07),
                        focus_x=options.get('focus_x',.5),
                        focus_y=options.get('focus_y',.38))
    report.update(scene=chosen,source=source_type,model=model,output=str(destination))
    print(f'[CAPA] {report["style"]} | cena {chosen} | fonte: {source_type} | '
          f'{destination}',flush=True)
    return report


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='Renderiza Short com múltiplas imagens originais; não publica')
    ap.add_argument('--id',default='003-death-note-xadrez')
    ap.add_argument('--plano',type=Path)
    ap.add_argument('--modelo',default='gpt-image-1.5')
    ap.add_argument('--max-segundos-por-plano',type=float,default=6)
    ap.add_argument('--criar-voz',action='store_true')
    ap.add_argument('--renderizar',action='store_true')
    ap.add_argument('--somente-capa',action='store_true',help='Gera so a capa premium com imagens em cache; sem voz/Remotion/IA')
    ap.add_argument('--motor',type=Path,default=MOTION)
    args=ap.parse_args(argv)
    path=production_storyboard(args.id,args.max_segundos_por_plano,selected=args.plano)
    ep=read_storyboard(path)
    if ep['id']!=args.id:raise ValueError('ID de episódio divergente')
    folder=OUT/args.id
    if args.somente_capa:
        if args.renderizar or args.criar_voz:
            raise ValueError('--somente-capa nao combina com --renderizar/--criar-voz')
        cover=folder/f'{ep["id"]}-master-capa.jpg'
        report=cover_from_master(ep,args.modelo,cover)
        (folder/'qa-capa.json').write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('[PRONTO] Capa criada offline; nenhum video ou imagem IA gerada.')
        return 0
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
    cover_report=cover_from_master(ep,args.modelo,cover)
    manifest={'id':ep['id'],'status':'renderizado-aguardando-revisao',
              'cover_design':cover_report,
              'mp4':str(output),'cover':str(cover),'duration_s':seconds,
              'narrative_beats':ep.get('narrative_beats'),
              'visual_shots':len(props['scenes']),'captions':len(captions),
              'published':False,
              'visual_alerts':[{'scene':e['scene']['id'],
                  'margins':e['qa']['alpha'].get('margin_warning'),
                  'alignment':e['qa']['composition'].get('alignment_warning'),
                  'background_source':e['qa'].get('background_source','desconhecido'),
                  'background_warnings':e['qa'].get('warnings',[]),
                  'render_mode':e['render_mode'],
                  'foreground_source_consistency':e['fidelity']}
                  for e in validated]}
    (folder/'qa-master-multicenas.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'[OK] Short pronto para revisão (NÃO publicado): {output}')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,FileNotFoundError,OSError,RuntimeError,KeyError,subprocess.SubprocessError) as exc:
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
