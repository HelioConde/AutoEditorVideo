"""Explicit manual visual review on exact cached scene outputs.

Manual marks are stored in ignored local cache, never in the GitHub repo.
Rejection blocks video/covers until the image is fixed and reviewed again.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REVIEW_FILENAME='visual-review.json'
VALID_STATES={'reprovado','aprovado'}


def read_review(folder:Path)->dict|None:
    path=folder/REVIEW_FILENAME
    if not path.is_file():
        return None
    result=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(result,dict) or result.get('status') not in VALID_STATES:
        raise ValueError('Arquivo de revisao visual invalido: '+str(path))
    if result.get('version')!='arquivo-otaku/visual-review/v1':
        raise ValueError('Versao de revisao visual desconhecida: '+str(path))
    return result


def write_review(folder:Path,*,status:str,reason:str)->dict:
    if status not in VALID_STATES:
        raise ValueError('A revisao deve ser aprovada ou reprovada')
    if status=='reprovado' and not reason.strip():
        raise ValueError('Informe o motivo da reprovacao')
    if not folder.is_dir() or not (folder/'master.png').is_file():
        raise FileNotFoundError('Cache da cena sem master.png: '+str(folder))
    review={'version':'arquivo-otaku/visual-review/v1','status':status,
            'reason':reason.strip(),'cache_folder':folder.name}
    from master_scenes import atomic
    atomic(folder/REVIEW_FILENAME,
           (json.dumps(review,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    return review


def main(argv:list[str]|None=None)->int:
    from master_scenes import production_storyboard,read_storyboard,scene_dir
    ap=argparse.ArgumentParser(description='Aprovar/reprovar arte em cache; zero chamadas de IA')
    ap.add_argument('--id',required=True)
    ap.add_argument('--modelo',default='gpt-image-1.5')
    ap.add_argument('--cena',type=int,required=True)
    ap.add_argument('--status',required=True,choices=sorted(VALID_STATES))
    ap.add_argument('--motivo',default='')
    ap.add_argument('--plano',type=Path)
    args=ap.parse_args(argv)
    ep=read_storyboard(production_storyboard(args.id,6,selected=args.plano))
    scene=next((s for s in ep['scenes'] if int(s['id'])==args.cena),None)
    if scene is None:
        raise ValueError('Cena inexistente no storyboard')
    folder=scene_dir(ep,scene,args.modelo)
    result=write_review(folder,status=args.status,reason=args.motivo)
    print('[REVISAO VISUAL]',ep['id'],scene['id'],result['status'],
          result['reason'],'|',folder)
    print('Nenhum pedido de imagem nem upload foi enviado.')
    return 0


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,FileNotFoundError,OSError) as exc:
        import sys
        print('[ERRO] '+str(exc),file=sys.stderr)
        raise SystemExit(1)
