#!/usr/bin/env python3
"""Prepare only visually rejected frames for NEW generation, with zero paid calls.

It updates the user's *local* production storyboard snapshot, not the repository.
Preserves the previous storyboard and every existing scene's cache. A new prompt
hash for each rejected shot makes accidental reuse of disapproved masters impossible.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from master_scenes import (atomic, cache_pin, master_prompt, production_storyboard,
                           read_storyboard, scene_dir, sha)
from revisao_visual_cenas import read_review

REVISION_SCHEMA="arquivo-otaku/rejected-scene-revision/v1"

# Never include user-supplied reasons verbatim in the image prompt. Reasons are
# review metadata, not trusted directions to a paid model.
SAFETY_APPENDIX=(
    "VISUAL REGENERATION / TAKE 2 - ORIGINAL GEOMETRY REJECTED. "
    "Design a physically plausible NEW composition and pose consistent with "
    "this scene's camera angle and story beat. In chess scenes, the table is "
    "a SOLID foreground surface. Torso, hips, knees, feet, legs and shoes MUST "
    "remain behind or below the table edge, never on the tabletop or chessboard. "
    "Only hands or forearms may touch or hover over the board to move a piece. "
    "Preserve correct occlusion: the tabletop occludes bodies behind it; "
    "chess pieces rest ON the board, characters never do. "
    "No doubled limbs, no floating body, no penetrations through the table. "
    "Make this a distinct camera composition rather than repeating the previous "
    "failed framing. Keep face, wrists, fingers and hair anatomically sound. "
    "The foreground extraction will later be made from EXACT pixels of this "
    "master. End of visual-revision instruction."
)


def prepare_rejected(ep_id:str,model:str,*,plan:Path|None=None)->dict:
    storyboard=production_storyboard(ep_id,6,selected=plan)
    data=read_storyboard(storyboard)
    if data['id']!=ep_id:
        raise ValueError('ID de episodio divergente do plano')
    pending=[]
    for scene in data['scenes']:
        previous=scene_dir(data,scene,model)
        review=read_review(previous)
        if not review or review['status']!='reprovado':
            continue
        if cache_pin(data,scene,model):
            raise ValueError(
                f"Cena {scene['id']}: cache fixado manualmente em config. "
                'Desvincule esse pin explicitamente antes de preparar uma nova versao.')
        if scene.get('correcao_visual',{}).get('schema')==REVISION_SCHEMA:
            # This also safeguards malformed manual edits to an existing draft:
            # no repeated auto-append to a prompt of a reviewed revision.
            raise ValueError(f"Cena {scene['id']} ja tem revisao visual no storyboard; "
                             'revise seu cache e nao prepare novamente por cima dela.')
        proposal=dict(scene)
        proposal['prompt']=scene['prompt'].rstrip()+'\n'+SAFETY_APPENDIX
        proposal['correcao_visual']={
            'schema':REVISION_SCHEMA,
            'source_cache':previous.name,
            'review_reason':review.get('reason',''),
            'status':'nova_imagem_pendente',
            'requires_manual_approval':True,
        }
        dest=scene_dir({**data,'scenes':[proposal]},proposal,model)
        if dest==previous:
            raise RuntimeError('Erro: o hash da nova imagem nao mudou')
        if dest.exists():
            raise RuntimeError('Diretorio de nova revisao ja existe: '+str(dest))
        pending.append((scene,proposal,previous,dest))
    if not pending:
        print('[PREPARO] Nenhuma cena atualmente reprovada no storyboard.')
        print('[PREPARO] Nenhum arquivo alterado; nenhum pedido de IA realizado.')
        return {'scenes':[],'changed':False,'plan':str(storyboard)}
    initial=storyboard.read_bytes()
    backup=storyboard.with_name(
        'storyboard-producao-backup-reprovadas-'+sha(initial.decode('utf-8-sig'))+'.json')
    if not backup.is_file():
        atomic(backup,initial)
    replacements={scene['id']:proposal for scene,proposal,_,_ in pending}
    changed={**data,'scenes':[replacements.get(s['id'],s) for s in data['scenes']]}
    # Explicitly preserve all non-targeted prompts and metadata byte-equivalent
    # as Python objects; do not call build_storyboard or regenerate any other shot.
    assert len(changed['scenes'])==len(data['scenes'])
    atomic(storyboard,
           (json.dumps(changed,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(f'[PREPARO] Storyboard anterior preservado em {backup}')
    for old,new,source,dest in pending:
        print(f'[NOVA VERSAO] {old["id"]}: {source.name} (reprovada) -> {dest.name} (pendente)')
    print(f'[PREPARO] {len(pending)} cenas prontas para geracao separada. '
          'Cenas aprovadas/nao marcadas intactas. Zero chamadas de IA.')
    return {'scenes':[x[0]['id'] for x in pending],
            'changed':True,'plan':str(storyboard),'backup':str(backup)}


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(description='Preparar nova versao de cenas REPROVADAS, zero IA')
    ap.add_argument('--id',required=True)
    ap.add_argument('--modelo',default='gpt-image-1.5',
                    choices=['gpt-image-1.5','gpt-image-2'])
    args=ap.parse_args(argv)
    prepare_rejected(args.id,args.modelo)
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,RuntimeError,OSError,KeyError) as exc:
        import sys
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
