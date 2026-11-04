#!/usr/bin/env python3
"""Dirige enquadramentos diferentes a partir dos acontecimentos do roteiro.

Planejador determinístico, sem cota de IA nem upload.
Bloco narrativo != imagem: um bloco longo pode conter múltiplos enquadramentos.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import re
from diversidade_visual import direction, direction_prompt, storyboard_warnings

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'conteudos'/'testes-animados-5.json'
RECAPS_MANIFEST=ROOT/'conteudos'/'death-note-recaps-60s.json'
FORMATOS_MANIFEST=ROOT/'conteudos'/'death-note-formatos-60s.json'
JUJUTSU_MANIFEST=ROOT/'conteudos'/'jujutsu-kaisen-recaps-60s.json'
GRADE_50_MANIFESTS=(ROOT/'conteudos'/'otaku-multicena-grade-50-a.json',
                    ROOT/'conteudos'/'otaku-multicena-grade-50-b.json')
OUTPUT=ROOT/'assets'/'gerados'/'planos-visuais'
ID=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


def chunks(text: str, count: int) -> list[str]:
    """Separa em partes sequenciais sem descartar nenhuma palavra."""
    words=text.split()
    if not words:raise ValueError('Bloco narrativo vazio')
    count=min(count,len(words))
    return [" ".join(words[round(i*len(words)/count):round((i+1)*len(words)/count)])
            for i in range(count)]


def framing(episode: dict, role: str, index: int, within: int, total: int,
            direction_info: dict | None = None, previous: dict | None = None) -> tuple[str,str,str]:
    """Planos são dependentes da narração e do elenco, não uma lista fixa."""
    effect=episode.get('effect','chess')
    character=episode.get('character','personagem principal do anime')
    obj=episode.get('object','objeto importante')
    background=episode.get('background','cenário coerente com a história')
    focal=(character if within%3!=2 else obj)
    if role=='fechamento':
        focal=character
        shot='Plano final dramático mostrando a reação e a tensão do conflito.'
    elif within%3==2:
        shot='Plano-detalhe do objeto essencial à fala; perspectiva e escala física naturais.'
    elif index==0:
        shot='Plano médio cinematográfico que estabelece a situação e o conflito.'
    elif within%3==1:
        shot='Novo ângulo de reação ou close moderado do personagem; olhos e mãos legíveis.'
    else:
        shot='Plano geral ou médio com contexto visual diferente do enquadramento anterior.'
    subject='objeto' if within%3==2 and role!='fechamento' else 'personagens'
    if effect=='chess' and subject=='objeto':
        focal='Peça de xadrez realista no tabuleiro; a metáfora do duelo intelectual'
    if direction_info is not None:
        shot=direction_info['camera_angle']+' | '+direction_info['shot_type']
        focal=direction_info['focus_subject']
        # Action inserts must be large enough to read and preserve real hands.
        # The only pure-object chess shot is top_board.
        subject='objeto' if direction_info['shot_type'] in ('top_board','top_detail') else 'personagens'
    prompt=(f'{shot} Assunto principal: {focal}. Ambiente: {background}. '
            'Cena inspirada no tema de '+episode.get('series','anime')+'. '
            'Uma imagem vertical 2D anime cel shaded, com um único enquadramento coeso. '
            'Se houver personagem, cabelo, rosto, ombros e mãos inteiros; '
            'margens laterais de 12%, margem superior de 10%, '
            'escala natural e espaço inferior para legenda. '
            'NÃO desenhar texto, interface, mosaico ou telas divididas.')
    if direction_info is not None:
        prompt=(direction_prompt(episode,direction_info,previous=previous)+
                prompt+' Use an intentional single-camera composition unlike the preceding shot. '
                'For a close/detail view, crop naturally but never amputate wrists or hair. ')
    return subject,shot,prompt


def build_storyboard(episode: dict, max_hold: float=6.0,
                     duration: float|None=None) -> dict:
    from planejar_cenas_dinamicas import scene_plan
    if not 2.5<=max_hold<=12:
        raise ValueError('Tempo máximo de permanência entre 2.5 e 12 segundos')
    ep_id=str(episode.get('id',''))
    if not ID.fullmatch(ep_id):raise ValueError('ID inválido')
    base=scene_plan(episode,duration=duration)
    shots=[]
    for beat_idx,beat in enumerate(base['cenas']):
        seconds=beat['duracao_estimada_s']
        # Não gerar cortes só para bater 7 imagens; apenas evitar um plano cansativo.
        slots=max(1,math.ceil(seconds/max_hold))
        snippets=chunks(beat['trecho_roteiro'],slots)
        pos=beat['inicio_estimado_s']
        total_words=sum(len(t.split()) for t in snippets)
        for j,speech in enumerate(snippets):
            proportion=len(speech.split())/total_words
            end=beat['fim_estimado_s'] if j==len(snippets)-1 else pos+seconds*proportion
            visual=direction(episode,len(shots),speech,beat['papel'],
                             previous=shots,
                             last=(beat_idx==len(base['cenas'])-1 and
                                   j==len(snippets)-1))
            subject,angle,prompt=framing(
                episode,beat['papel'],len(shots),j,len(snippets),
                direction_info=visual,previous=shots[-1] if shots else None)
            prompt += (' Narrative moment: '+speech+
                       ' Preserve the narrated meaning; do not invent canonical actions.')
            shots.append({
                'id':f'{len(shots)+1:02d}','bloco_id':beat['id'],
                'papel':beat['papel'],'subject':subject,
                'trecho_roteiro':speech,'tipo_plano':angle,'prompt':prompt,
                **{k:v for k,v in visual.items() if k!='visual_instruction'},
                'inicio_estimado_s':round(pos,3),'fim_estimado_s':round(end,3),
                'duracao_estimada_s':round(end-pos,3),
                'revisao_visual_pendente':True
            })
            pos=end
    if not shots:raise ValueError('Roteiro sem planos')
    if len(shots)>60:raise ValueError('Roteiro exige mais de 60 enquadramentos; revise antes de gastar cota')
    visual_issues=storyboard_warnings(shots)
    if visual_issues:
        raise ValueError('Planejamento visual repetitivo: '+str(visual_issues))
    return {'schema':'arquivo-otaku/master-storyboards/v2','id':ep_id,
            'visual_direction_version':'arquivo-otaku/visual-diversity/v1',
            'visual_diversity_qa':{'status':'planejamento_distinto',
                                   'warnings':visual_issues,'review_required':True},
            'title':episode.get('title',episode.get('titulo','')),
            'series':episode.get('series',episode.get('serie','Anime')),
            'effect':episode.get('effect',''), 'script':episode.get('script',episode.get('roteiro_melhorado','')),
            'narrative_beats':base['total_cenas'],
            'shot_count':len(shots),'estimated_duration_s':base['duracao_estimada_s'],
            'timing_source':'estimativa proporcional; sincronizar com a voz real',
            'scenes':shots, 'published':False}


def select_episode(ep_id: str, path: Path=MANIFEST)->dict:
    # Keep explicit manifest paths strict; only the default catalog is extended.
    sources=[path]
    if path==MANIFEST:
        sources.extend(extra for extra in (RECAPS_MANIFEST,FORMATOS_MANIFEST,JUJUTSU_MANIFEST,*GRADE_50_MANIFESTS)
                       if extra.is_file())
    matches=[]
    for source in sources:
        data=json.loads(source.read_text(encoding='utf-8-sig'))
        for ep in data.get('episodes',[]):
            if ep.get('id') == ep_id:
                # Metadados comuns do manifesto (por exemplo "series") são
                # herdados quando o episódio não repete o campo.
                normalized = dict(ep)
                if not normalized.get('series') and data.get('series'):
                    normalized['series'] = data['series']
                matches.append(normalized)
    if len(matches)!=1:
        raise ValueError('Episódio não encontrado ou duplicado no catálogo: '+ep_id)
    return matches[0]


def save_plan(ep:dict, *, max_hold:float=6, duration:float|None=None,
              output:Path=OUTPUT)->Path:
    plan=build_storyboard(ep,max_hold,duration)
    output.mkdir(parents=True,exist_ok=True)
    path=output/(plan['id']+'-master-dinamico.json')
    path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return path


def main()->int:
    parser=argparse.ArgumentParser(description='Enquadramentos em quantidade variável, sem chamadas de IA')
    parser.add_argument('--id',default='003-death-note-xadrez')
    parser.add_argument('--manifesto',type=Path,default=MANIFEST)
    parser.add_argument('--max-segundos-por-plano',type=float,default=6)
    parser.add_argument('--duracao',type=float)
    args=parser.parse_args()
    ep=select_episode(args.id,args.manifesto)
    file=save_plan(ep,max_hold=args.max_segundos_por_plano,duration=args.duracao)
    plan=json.loads(file.read_text(encoding='utf-8'))
    print(f"[OK] {plan['narrative_beats']} blocos narrativos → {plan['shot_count']} enquadramentos: {file}")
    for s in plan['scenes']:
        print(f" {s['id']} bloco {s['bloco_id']} | {s['inicio_estimado_s']:.1f}–{s['fim_estimado_s']:.1f}s | {s['tipo_plano'][:55]}")
    print('[QA] Este é um plano visual, não uma animação pronta. Nenhuma chamada de IA.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,OSError) as exc:
        import sys
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
