#!/usr/bin/env python3
"""Monta qualquer quantidade de imagens-mãe em um Short Remotion 9:16.

Tempos proporcionais à voz real; legendas ASS obtidas do TTS.
Nenhum upload e nenhuma geração de imagens ocorrem neste módulo.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from PIL import Image, ImageChops, ImageFilter

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
from chess_composition_safety import master_static_for_chess_action
from revisao_visual_cenas import read_review
from extract_scene_layers import validate_multilayer
from rigby2d_bridge import approved_frames
from qa_multilayer_geometry import compose as compose_semantic_layers


def validate_scenes(ep:dict,model:str,output:Path=OUT)->list[dict]:
    verified=[]
    for scene in ep['scenes']:
        folder=scene_dir(ep,scene,model,output)
        if (folder/'scene-layers.json').is_file():
            # Once opted into semantic layers, never silently fall back to an
            # unapproved two-layer render on a failing QA/review.
            base_review=read_review(folder)
            if base_review and base_review['status']=='reprovado':
                raise ValueError(f"Cena {scene['id']}: master reprovada; "
                                 'multicamadas nao consertam anatomia ruim.')
            validated=validate_multilayer(ep,scene,model,folder)
            report={'status':'aguardando_revisao_visual',
                    'alpha':{'margin_warning':False},
                    'composition':{'alignment_warning':False},
                    'warnings':validated['qa'].get('warnings',[]),
                    'background_source':'semantic_multilayer'}
            verified.append({'scene':scene,'folder':folder,
                             'files':{'master':folder/'master.png'},
                             'multi':validated,'qa':report,
                             'fidelity':{'status':'source_master_pixels'},
                             'render_mode':'multilayer'})
            continue
        paths={k:folder/(k+'.png') for k in ('master','foreground','background')}
        for kind,path in paths.items():
            if not path.is_file():
                raise FileNotFoundError(f'Enquadramento {scene["id"]}: falta {path}. Gere as camadas antes.')
            validate_image(path.read_bytes(),alpha=kind=='foreground')
        manual=read_review(folder)
        if manual and manual['status']=='reprovado':
            raise ValueError(f"Cena {scene['id']} REPROVADA manualmente: "
                             f"{manual['reason']}. Corrija/regenere a imagem e "
                             'revise a nova versão antes de renderizar.')
        if scene.get('correcao_visual',{}).get('requires_manual_approval') and (
                not manual or manual['status']!='aprovado'):
            raise ValueError(f"Cena {scene['id']}: nova versao requer APROVACAO "
                             'visual explicita antes de entrar no Short. '
                             'Use -AprovarCena so apos conferir master e comparacao.')
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
        hero_master=master_static_for_chess_action(scene)
        safe_2d=bool(hero_master or fidelity.get('review_required') or fidelity['redrawn'])
        if report.get('warnings'):
            print(f"[QA AVISO] Cena {scene['id']}: {', '.join(report['warnings'])}. "
                  'Confira o background antes de publicar.')
        if safe_2d:
            reason='rei/tabuleiro preservados' if hero_master else 'foreground inseguro'
            print(f"[QA PROTECAO] Cena {scene['id']}: {reason}. "
                  'Renderizando master intacta (camera global, sem parallax 2.5D). '
                  'Nenhuma chamada de IA.')
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


def layer_animation_metrics(image:Path)->dict:
    """Read metadata from approved RGBA layer; never change cached PNG bytes."""
    with Image.open(image) as layer:
        alpha=layer.getchannel('A')
        histogram=alpha.histogram()
        fraction=round(sum(histogram[128:]) / float(layer.width*layer.height),5)
        bounding=alpha.point(lambda a:255 if a>127 else 0).getbbox()
        if bounding is None:
            return {'alphaCoverage':0.,'anchorX':50.,'anchorY':80.}
        # Breathing pivot near the character's lowest visible body pixel.
        x0,y0,x1,y1=bounding
        return {
            'alphaCoverage':fraction,
            'anchorX':round((x0+x1)/2/layer.width*100,2),
            'anchorY':round((y0*.10+y1*.90)/layer.height*100,2),
        }


def layer_motion_safety(layer,source:Path,ordered:list,ep_id:str,scene_id:str)->dict:
    """Inspect already-approved RGBA only. Never rewrite source or pay for AI.

    Non-character masks define objects/furniture. Their proximity identifies
    places where the character should move less, including the upper body
    contacting a table. A hero/hand overlap blocks only the attached person,
    never another independently separated character.
    """
    with Image.open(source) as image:
        if 'A' not in image.getbands():
            raise ValueError('Animacao precisa de PNG RGBA aprovado')
        alpha=image.getchannel('A')
        original_box=alpha.getbbox()
        if original_box is None:
            return {'contactRisk':1.0,'heroRisk':1.0,
                    'heightFraction':0.0,'motionSeed':0}
        source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
        height_fraction=round((original_box[3]-original_box[1])/image.height,4)
        # Thumbnail-sized mask statistics avoid per-frame GPU/image processing.
        size=(160,240)
        subject=alpha.resize(size,Image.Resampling.NEAREST).point(
            lambda v:255 if v>=128 else 0)
    area=sum(subject.histogram()[128:])
    near=None
    hero=None
    for other,path in ordered:
        if other is layer or path==source:
            continue
        if other.role not in ('occluder','object','hero_prop'):
            continue
        with Image.open(path) as item:
            if item.size != image.size or 'A' not in item.getbands():
                raise ValueError('Mascara de objeto incompatível para movimento')
            mask=item.getchannel('A').resize(size,Image.Resampling.NEAREST).point(
                lambda v:255 if v>=128 else 0)
        if other.role=='hero_prop':
            hero=mask if hero is None else ImageChops.lighter(hero,mask)
        else:
            # ~12px source-image halo around rigid scene furniture.
            mask=mask.filter(ImageFilter.MaxFilter(5))
            near=mask if near is None else ImageChops.lighter(near,mask)
    def overlap_fraction(probe):
        if probe is None or not area:return 0.
        shared=ImageChops.darker(subject,probe)
        return round(min(1.,sum(shared.histogram()[128:])/area),4)
    return {
        'contactRisk':overlap_fraction(near),
        'heroRisk':overlap_fraction(hero),
        'heightFraction':height_fraction,
        'motionSeed':int(hashlib.sha256(
            (ep_id+'/'+scene_id+'/'+layer.id+'/'+source_sha).encode('utf-8')
        ).hexdigest()[:8],16),
    }


def build_props(ep:dict,voice:Path,captions:list[dict],seconds:float,
                *,model:str='gpt-image-1.5',output:Path=OUT,
                public:Path|None=None,animation_mode:str='cinematica',
                character_preset:str='equilibrado')->dict:
    entries=validate_scenes(ep,model,output)
    target=(public or MOTION/'public')/'generated'/ep['id']
    target.mkdir(parents=True,exist_ok=True)
    bounds=assign_frames([e['scene'] for e in entries],seconds)
    scenes=[]
    rigs_found=0
    for entry,(start,end) in zip(entries,bounds):
        scene=entry['scene']
        stem='scene-'+scene['id']
        if entry['render_mode']=='multilayer':
            multi=entry['multi']
            shutil.copy2(multi['background'],target/f'{stem}-background.png')
            with Image.open(entry['files']['master']) as original:
                transparent=Image.new('RGBA',original.size,(0,0,0,0))
            transparent.save(target/f'{stem}-foreground.png')
            semantic=[]
            has_hero_prop=any(layer.role=='hero_prop' for layer,_ in multi['layers'])
            for layer,path in multi['layers']:
                dest=target/f'{stem}-layer-{layer.id}.png'
                shutil.copy2(path,dest)
                record={'id':layer.id,'role':layer.role,'z':layer.z,
                    'src':f'generated/{ep["id"]}/{dest.name}',
                    **layer_animation_metrics(path)}
                if layer.role in ('back_character','front_character'):
                    record.update(layer_motion_safety(
                        layer,path,multi['layers'],ep['id'],scene['id']))
                if (animation_mode=='esqueleto2d' and
                        layer.id in ('l','light') and not has_hero_prop):
                    rig=approved_frames(entry['folder'],layer.id)
                    if rig is not None:
                        images=[]
                        for index,asset in enumerate(rig['files']):
                            rig_dest=target/f'{stem}-layer-{layer.id}-rig-{index:04d}.png'
                            shutil.copy2(asset,rig_dest)
                            images.append(f'generated/{ep["id"]}/{rig_dest.name}')
                        record['rigFrames']={'fps':rig['fps'],'frames':images}
                        rigs_found+=1
                semantic.append(record)
        elif entry['render_mode']=='master_static':
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
                       'layers':semantic if entry['render_mode']=='multilayer' else [],
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
    if animation_mode not in ('cinematica','desligada','esqueleto2d'):
        raise ValueError('Modo de animacao desconhecido')
    if animation_mode=='esqueleto2d' and rigs_found==0:
        raise ValueError(
            'Nenhuma sequencia Rigby2D aprovada em cena segura. '
            'Cenas com king_hand/rei estao protegidas contra movimento de '
            'personagens que desalinhe a peca. Prepare um rig para uma '
            'cena sem rei, como a 04, usando rigby2d_bridge.py. '
            'MP4 anterior preservado; nenhuma imagem IA consumida.')
    if animation_mode=='esqueleto2d':
        print(f"[RIGBY2D] {rigs_found} sequencias articuladas aprovadas. "
              "Outras camadas continuam estaticas, sem movimento enganoso.",
              flush=True)
    if character_preset not in ('ultrassutil','equilibrado','vivo'):
        raise ValueError('Preset de personagens desconhecido')
    return {'id':ep['id'],'durationFrames':bounds[-1][1],
            'animationMode':animation_mode,
            'characterPreset':character_preset,
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
    if (folder/'scene-layers.json').is_file():
        multi=validate_multilayer(ep,scene,model,folder)
        source=compose_semantic_layers(multi['background'],multi['layers'])
        label=options.get('title') or select_episode(ep['id']).get('cover') or ep.get('title') or 'ARQUIVO OTAKU'
        report=render_cover(source,str(label),destination,
                            zoom=options.get('zoom',1.07),
                            focus_x=options.get('focus_x',.5),
                            focus_y=options.get('focus_y',.38))
        report.update(scene=chosen,source='multilayer-approved',
                      model=model,output=str(destination))
        print(f'[CAPA] multicamadas aprovadas | cena {chosen} | {destination}',flush=True)
        return report
    foreground=folder/'foreground.png'
    background=folder/'background.png'
    master=folder/'master.png'
    manual=read_review(folder)
    if manual and manual['status']=='reprovado':
        raise ValueError(f"Capa bloqueada: cena {chosen} reprovada: "
                         f"{manual['reason']}. Escolha cena aprovada no JSON.")
    if scene.get('correcao_visual',{}).get('requires_manual_approval') and (
            not manual or manual['status']!='aprovado'):
        raise ValueError(f"Capa bloqueada: nova cena {chosen} ainda nao foi aprovada.")
    if background.is_file() and foreground.is_file():
        validate_image(background.read_bytes(),alpha=False)
        validate_image(foreground.read_bytes(),alpha=True)
        unshifted=folder/'foreground-normalized.png'
        if not unshifted.is_file():
            unshifted=folder/'foreground-raw.png'
        if not unshifted.is_file():
            unshifted=foreground
        fidelity=foreground_fidelity(master,unshifted)
        if (master_static_for_chess_action(scene) or
                fidelity.get('review_required') or fidelity['redrawn']):
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
    ap.add_argument('--animacao',choices=['cinematica','desligada','esqueleto2d'],
                    default='cinematica',
                    help='Movimentos originais de camera, respiracao segura e luz')
    ap.add_argument('--perfil-personagens',
                    choices=['ultrassutil','equilibrado','vivo'],
                    default='equilibrado',
                    help='Intensidade dos movimentos sutis de Light e L')
    ap.add_argument('--somente-voz',action='store_true',help='Gerar voz e legendas sem validar ou renderizar imagens')
    ap.add_argument('--renderizar',action='store_true')
    ap.add_argument('--somente-capa',action='store_true',help='Gera so a capa premium com imagens em cache; sem voz/Remotion/IA')
    ap.add_argument('--motor',type=Path,default=MOTION)
    args=ap.parse_args(argv)
    path=production_storyboard(args.id,args.max_segundos_por_plano,selected=args.plano)
    ep=read_storyboard(path)
    if ep['id']!=args.id:raise ValueError('ID de episódio divergente')
    folder=OUT/args.id
    if args.somente_voz:
        if args.somente_capa or args.renderizar:
            raise ValueError('--somente-voz nao pode renderizar video ou capa')
        voice,subtitles=ensure_voice(select_episode(args.id),folder,create=args.criar_voz)
        print(f'[VOZ PRONTA] Audio: {voice} | legendas: {subtitles}. '
              'Nenhum render executado; aguardando aprovacao visual das imagens.')
        return 0
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
    props=build_props(ep,voice,captions,seconds,model=args.modelo,
                      public=args.motor/'public',animation_mode=args.animacao,
                      character_preset=args.perfil_personagens)
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
    # Never overwrite the previous still-image MP4 while introducing motion.
    # Never overwrite the previous originals or existing cinematic version.
    suffix=(f'-master-multicenas-personagens-v3-{args.perfil_personagens}.mp4'
            if args.animacao=='cinematica' else
            '-master-multicenas-esqueleto2d.mp4'
            if args.animacao=='esqueleto2d'
            else '-master-multicenas-referencia-estatica.mp4')
    output=folder/f"{ep['id']}{suffix}"
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
              'animation_mode':args.animacao,
              'character_preset':args.perfil_personagens,
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
