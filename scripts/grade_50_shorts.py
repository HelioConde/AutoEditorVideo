#!/usr/bin/env python3
"""Fila segura de 50 Shorts Otaku Multicena para Windows.

Fluxo: validar (read-only) -> preparar (storyboards/metadados locais) ->
produzir (voz/arte/cache/MP4) -> agendar (YouTube PRIVATE com publishAt).
Nenhuma etapa de upload acontece sem --confirmar-publicacao.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

from roteiro_para_storyboard import select_episode, save_plan
from metadata_shorts import publisher_episode
from shorts_duration import validate_video

CATALOGS=(
    ROOT/'conteudos'/'otaku-multicena-grade-50-a.json',
    ROOT/'conteudos'/'otaku-multicena-grade-50-b.json',
)
QUEUE_STATE=ROOT/'assets'/'gerados'/'publicacao-youtube'/'grade-50-estado.json'
VIDEO_DIR=ROOT/'assets'/'gerados'/'shorts-animados'
PUBLICATION=ROOT/'assets'/'gerados'/'publicacao-youtube'
PS_SCRIPT=ROOT/'criar-publicar-short.ps1'
CTA='Inscreva-se para acompanhar mais histórias de anime!'


def load_queue()->list[dict]:
    result=[]
    for path in CATALOGS:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('schema')!='otaku-multicena/grade-50/v1':
            raise ValueError('Catalogo incompatível: '+str(path))
        result.extend(data['episodes'])
    if len(result)!=50 or len({ep['id'] for ep in result})!=50:
        raise ValueError('Grade deve ter exatamente 50 IDs diferentes')
    for index,ep in enumerate(result,1):
        if ep['queue_position']!=index or ep['id']!=f'{5000+index}-'+ep['id'].split('-',1)[1]:
            raise ValueError('Posicao/ID divergentes em '+str(index))
        if not ep.get('series') or ep.get('effect')!='curiosity':
            raise ValueError('Anime ou efeito invalido: '+ep['id'])
        if not ep['script'].startswith(ep['hook']) or not ep['script'].endswith(ep['cta']):
            raise ValueError('Gancho/CTA nao correspondem ao roteiro: '+ep['id'])
        if ep['cta']!=CTA or 'Otaku Multicena' in ep['script']:
            raise ValueError('CTA da marca falado indevidamente: '+ep['id'])
        if '#OtakuMulticena' not in ep['description_youtube']:
            raise ValueError('Marca ausente na descricao: '+ep['id'])
        if len(ep['script'].split())>140 or len(ep['script'].split())<65:
            raise ValueError('Roteiro de tamanho inadequado: '+ep['id'])
        publisher_episode(ep)
        # Both catalog selectors must resolve exactly the same episode.
        normalized=select_episode(ep['id'])
        if normalized['script']!=ep['script']:
            raise ValueError('Selecionador desatualizado para '+ep['id'])
    return result


def selection(queue:list[dict], start:int, count:int)->list[dict]:
    if not 1<=start<=50 or not 1<=count<=50 or start+count>51:
        raise ValueError('Use InicioNaLista 1..50 e Quantidade dentro dos 50 videos')
    return queue[start-1:start-1+count]


def load_journal()->dict:
    if QUEUE_STATE.is_file():
        data=json.loads(QUEUE_STATE.read_text(encoding='utf-8-sig'))
        if not isinstance(data,dict):
            raise ValueError('Estado da fila corrompido')
        return data
    return {}


def save_journal(value:dict)->None:
    QUEUE_STATE.parent.mkdir(parents=True,exist_ok=True)
    temp=QUEUE_STATE.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',
                    encoding='utf-8')
    temp.replace(QUEUE_STATE)


def video_paths(ep_id:str,profile:str)->tuple[Path,Path]:
    folder=VIDEO_DIR/ep_id
    return (folder/f'{ep_id}-master-multicenas-personagens-v3-{profile}.mp4',
            folder/f'{ep_id}-master-capa.jpg')


def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def confirmed_existing_upload(video:Path)->dict|None:
    if not video.is_file():
        return None
    key=digest(video)[:12]
    path=PUBLICATION/f'estado-upload-{key}.json'
    if not path.is_file():
        return None
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if not data.get('video_id'):
        raise ValueError('Upload com status ambiguo: '+str(path))
    return data


def local_command(ep:dict,args:argparse.Namespace, *, publish:bool=False,
                  schedule:str='')->list[str]:
    command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
             str(PS_SCRIPT),'-Id',ep['id'],'-VozMotor','edge',
             '-Modelo',args.modelo,'-Perfil',args.perfil,
             '-MaxChamadas',str(0 if publish else args.max_chamadas_por_video),
             '-Privacidade','private']
    if args.refazer and not publish:
        command.append('-Refazer')
    if publish:
        command.append('-Publicar')
        if schedule:
            command.extend(['-AgendarEm',schedule])
    return command


def invoke(command:list[str], *,label:str)->None:
    print('[EXECUTAR]',label,flush=True)
    result=subprocess.run(command,cwd=ROOT,check=False)
    if result.returncode:
        raise RuntimeError(f'{label}: processo falhou (codigo {result.returncode}); '
                           'estado local preservado. Nao reenviar cegamente.')


def scheduled_at(start:str, offset:int, hours:int)->str:
    try:
        timestamp=datetime.fromisoformat(start.replace('Z','+00:00'))
    except ValueError as exc:
        raise ValueError('InicioAgendamento deve ser data ISO8601 com fuso') from exc
    if timestamp.tzinfo is None:
        raise ValueError('InicioAgendamento exige -03:00 ou outro fuso explicito')
    when=timestamp+timedelta(hours=offset*hours)
    if when.astimezone(timezone.utc)<=datetime.now(timezone.utc)+timedelta(minutes=30):
        raise ValueError('Primeira publicacao precisa estar mais de 30 min no futuro')
    return when.isoformat(timespec='seconds')


def ensure_ready(ep:dict,profile:str)->Path:
    video,cover=video_paths(ep['id'],profile)
    if not cover.is_file():
        raise FileNotFoundError('Capa do Short ausente: '+str(cover))
    validate_video(video,stage='Fila grade 50 '+ep['id'])
    return video


def run(args:argparse.Namespace)->int:
    queue=load_queue()
    chosen=selection(queue,args.inicio_na_lista,args.quantidade)
    for ep in chosen:
        print(f"[{ep['queue_position']:02d}/50] {ep['series']} — {ep['id']}",flush=True)
    print(f'[VALIDADO] {len(queue)} roteiros originais / {len(chosen)} selecionados; '
          'nada enviado ao YouTube.',flush=True)
    if args.acao=='validar':
        return 0
    if args.acao=='preparar':
        target=PUBLICATION/'episodios'
        target.mkdir(parents=True,exist_ok=True)
        for ep in chosen:
            save_plan(ep,max_hold=6)
            (target/(ep['id']+'.json')).write_text(
                json.dumps(publisher_episode(ep),ensure_ascii=False,indent=2)+'\n',
                encoding='utf-8')
            print('[ROTEIRO PRONTO]',ep['id'],flush=True)
        return 0
    if sys.platform!='win32':
        raise RuntimeError('Gerar ou publicar requer Windows local com PowerShell e cache')
    if args.acao=='produzir':
        if args.max_chamadas_por_video>0 and not args.confirmar_cota_imagem:
            raise ValueError('Confirme o teto de chamadas de imagem com '
                             '-ConfirmarCotaImagem; nao ha custo estimado garantido')
        print(f'[ORCAMENTO MAXIMO] {len(chosen)*args.max_chamadas_por_video} '
              'chamadas IA permitidas na selecao (nao representa custo garantido).')
        for ep in chosen:
            if confirmed_existing_upload(video_paths(ep['id'],args.perfil)[0]):
                print('[JA PUBLICADO] Nao recriar automaticamente: '+ep['id'],flush=True)
                continue
            invoke(local_command(ep,args),label='Produzir '+ep['id'])
        return 0
    if args.acao!='agendar':
        raise ValueError('Acao desconhecida: '+args.acao)
    if not args.confirmar_publicacao:
        raise ValueError('Para publicar, indique explicitamente -ConfirmarPublicacao')
    if not args.inicio_agendamento or args.intervalo_horas<1:
        raise ValueError('Agendar exige InicioAgendamento com fuso e intervalo >=1 hora')
    if args.max_chamadas_por_video:
        raise ValueError('Publicacao usa apenas cache pronto; MaxChamadasPorVideo deve ser 0')
    # Validate every file and every publication time before any remote write.
    slots=[]
    for ep in chosen:
        time_iso=scheduled_at(args.inicio_agendamento,ep['queue_position']-1,
                             args.intervalo_horas)
        video=ensure_ready(ep,args.perfil)
        slots.append((ep,time_iso,video))
    journal=load_journal()
    for ep,when,video in slots:
        previous=confirmed_existing_upload(video)
        if previous or journal.get(ep['id'],{}).get('video_id'):
            print('[JA ENVIADO] Nao duplicar '+ep['id'],flush=True)
            continue
        invoke(local_command(ep,args,publish=True,schedule=when),
               label='Agendar '+ep['id']+' para '+when)
        uploaded=confirmed_existing_upload(video)
        if not uploaded:
            raise RuntimeError('YouTube nao confirmou upload. Conferir Studio antes de retomar.')
        if not uploaded.get('agendamento_confirmado'):
            raise RuntimeError('YouTube nao confirmou agendamento: '+ep['id'])
        journal[ep['id']]={'video_id':uploaded['video_id'],
                           'agendado_para':when,'video_sha256':digest(video),
                           'status':'agendado-confirmado'}
        save_journal(journal)
        print('[AGENDADO] '+ep['id']+' '+when+' id='+uploaded['video_id'],flush=True)
    return 0


def parser()->argparse.ArgumentParser:
    ap=argparse.ArgumentParser(description='Grade Otaku Multicena: 50 Shorts')
    ap.add_argument('--acao',choices=('validar','preparar','produzir','agendar'),
                    default='validar')
    ap.add_argument('--inicio-na-lista',type=int,default=1)
    ap.add_argument('--quantidade',type=int,default=50)
    ap.add_argument('--modelo',choices=('gpt-image-1.5','gpt-image-2'),
                    default='gpt-image-2')
    ap.add_argument('--perfil',choices=('ultrassutil','equilibrado','vivo'),
                    default='equilibrado')
    ap.add_argument('--max-chamadas-por-video',type=int,default=0)
    ap.add_argument('--confirmar-cota-imagem',action='store_true')
    ap.add_argument('--inicio-agendamento',default='')
    ap.add_argument('--intervalo-horas',type=int,default=24)
    ap.add_argument('--confirmar-publicacao',action='store_true')
    ap.add_argument('--refazer',action='store_true')
    return ap


def main(argv:list[str]|None=None)->int:
    ap=parser()
    args=ap.parse_args(argv)
    if not 0<=args.max_chamadas_por_video<=180:
        ap.error('MaxChamadasPorVideo entre 0 e 180')
    return run(args)


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except (ValueError,RuntimeError,OSError,KeyError,subprocess.SubprocessError) as exc:
        print('[BLOQUEADO] '+str(exc),file=sys.stderr,flush=True)
        raise SystemExit(1)
