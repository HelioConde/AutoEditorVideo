#!/usr/bin/env python3
"""Fila segura de 50 Shorts Otaku Multicena para Windows.

Fluxo: validar -> preparar -> produzir MP4 -> validar QA -> publicar publicamente
o Short pronto, imediatamente e de forma individual, SEM agendamento.
Nenhum upload acontece sem --confirmar-publicacao.
"""
from __future__ import annotations

import argparse
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
from otaku_growth_v3 import audit_batch

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


def local_command(ep:dict,args:argparse.Namespace, *, publish:bool=False)->list[str]:
    command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
             str(PS_SCRIPT),'-Id',ep['id'],'-VozMotor','edge',
             '-Modelo',args.modelo,'-Perfil',args.perfil,
             '-MaxChamadas',str(0 if publish else args.max_chamadas_por_video),
             '-Privacidade','public' if publish else 'private']
    if args.refazer and not publish:
        command.append('-Refazer')
    if publish:
        command.append('-Publicar')
    return command


def invoke(command:list[str], *,label:str)->None:
    print('[EXECUTAR]',label,flush=True)
    result=subprocess.run(command,cwd=ROOT,check=False)
    if result.returncode:
        raise RuntimeError(f'{label}: processo falhou (codigo {result.returncode}); '
                           'estado local preservado. Nao reenviar cegamente.')


def ensure_ready(ep:dict,profile:str,*,
                 require_character_motion:bool=False)->Path:
    video,cover=video_paths(ep['id'],profile)
    if not cover.is_file() or cover.stat().st_size<10000:
        raise FileNotFoundError('Capa do Short ausente ou incompleta: '+str(cover))
    from PIL import Image
    with Image.open(cover) as image:
        image.load()
        width,height=image.size
        if (image.format!='JPEG' or height<640 or
                abs(width/height-9/16)>.02):
            raise ValueError('Thumbnail do Short nao e JPEG vertical 9:16: '+ep['id'])
    validate_video(video,stage='Fila grade 50 '+ep['id'])
    # Mandatory technical QA for new uploads: the user specifically rejected
    # still characters and abrupt virtual cuts. A video with zero independently
    # animatable characters cannot be described as character animation.
    qa_file=video.parent/'qa-master-multicenas.json'
    if not qa_file.is_file():
        raise RuntimeError('QA visual nao encontrado; renderize com o motor atualizado: '+ep['id'])
    qa=json.loads(qa_file.read_text(encoding='utf-8-sig'))
    if (qa.get('id')!=ep['id'] or
        Path(str(qa.get('mp4',''))).resolve()!=video.resolve()):
        raise RuntimeError('QA nao pertence ao MP4 atual: '+ep['id'])
    total=qa.get('visual_shots',0)
    camera_only=qa.get('camera_only_scenes')
    if qa.get('animation_mode')!='cinematica' or not isinstance(camera_only,int):
        raise RuntimeError('QA de movimento antigo; refaça a renderização: '+ep['id'])
    if not isinstance(total,int) or total<1 or camera_only<0 or camera_only>total:
        raise RuntimeError('Contagem de cenas inválida no QA: '+ep['id'])
    # The standard pipeline generates approved 2.5D foreground/background
    # assets, not automatically isolated semantic character RGBA masks.
    # Therefore camera_only==total is common and NOT evidence of corrupt media.
    # The author asked for smooth zoom AND immediate PUBLIC publishing; do not
    # deadlock the whole queue on an optional animation quality preference.
    if camera_only==total:
        if require_character_motion:
            raise RuntimeError(
                'QA estrito: nenhuma cena possui personagem animavel em '
                'camada RGBA segura: '+ep['id']+
                '. Extraia/aprove multicamadas antes de usar '
                '-ExigirMovimentoPersonagem.'
            )
        print(f'[AVISO MOVIMENTO] {ep["id"]}: {camera_only}/{total} '
              'cenas com arte plana/2.5D. Render permitido com zoom '
              'in/out continuo e sem flicker; NAO possui gestos reais de '
              'personagem. Use -ExigirMovimentoPersonagem para bloquear.',
              flush=True)
    elif camera_only:
        print(f'[AVISO MOVIMENTO] {ep["id"]}: {camera_only}/{total} '
              'cenas com zoom de arte plana/2.5D; demais com personagem '
              'em camada RGBA animavel.',flush=True)
    else:
        print(f'[MOVIMENTO] {ep["id"]}: {total} cenas com camadas '
              'de personagem animaveis.',flush=True)
    return video


def run(args:argparse.Namespace)->int:
    queue=load_queue()
    chosen=selection(queue,args.inicio_na_lista,args.quantidade)
    for ep in chosen:
        print(f"[{ep['queue_position']:02d}/50] {ep['series']} — {ep['id']}",flush=True)
    print(f'[VALIDADO] {len(queue)} roteiros originais / {len(chosen)} selecionados. '
          'Upload somente na acao produzir-publicar com confirmacao explicita.',
          flush=True)
    # Relatorio editorial sem imagens, upload ou modificacao de video.
    if args.acao in ('validar', 'preparar') or args.auditar_editorial or args.exigir_gates_editoriais:
        report = audit_batch(chosen)
        summary = report['summary']
        print('[EDITORIAL V3] ' + str(summary['episodes']) + ' roteiros; ' +
              str(summary['blocking_issues']) + ' bloqueios objetivos; ' +
              str(summary['advisories']) + ' avisos. ' +
              'Revisao factual, visual e de direitos continua obrigatoria.',
              flush=True)
        for item in report['episodes']:
            for issue in item['issues']:
                if issue['severity'] == 'blocking':
                    print('[EDITORIAL BLOQUEIO] ' + item['id'] + ': ' +
                          issue['message'], flush=True)
        if args.exigir_gates_editoriais and summary['blocking_issues']:
            raise ValueError('Gate editorial V3 reprovou roteiros; corrigir antes de produzir.')
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
    if args.acao not in ('produzir','produzir-publicar'):
        raise ValueError('Acao desconhecida: '+args.acao)
    publish_now=args.acao=='produzir-publicar'
    # Never spend image credits or attempt any upload without both explicit
    # authorizations. If a user's prior upload is uncertain, stop instead
    # of treating it as "missing" and uploading again.
    if args.max_chamadas_por_video>0 and not args.confirmar_cota_imagem:
        raise ValueError('Confirme o teto de chamadas de imagem com '
                         '-ConfirmarCotaImagem; nao ha custo estimado garantido')
    if publish_now and not args.confirmar_publicacao:
        raise ValueError('Publicacao imediata exige -ConfirmarPublicacao')
    if publish_now:
        from publicar_arquivo_otaku import verify_oauth_config
        verify_oauth_config()  # validate credentials before consuming image budget
        if not (ROOT/'.secrets'/'youtube-token.json').is_file():
            print('[OAUTH] Token do YouTube ainda nao salvo. '
                  'O publicador podera exigir login na primeira publicacao.',
                  flush=True)
    print(f'[ORCAMENTO MAXIMO] {len(chosen)*args.max_chamadas_por_video} '
          'chamadas IA permitidas na selecao (teto, nao custo garantido).',
          flush=True)
    journal=load_journal()
    skipped=[]
    consecutive_production_failures=0
    for ep in chosen:
        ep_id=ep['id']
        video=video_paths(ep_id,args.perfil)[0]
        prior=journal.get(ep_id,{})
        if prior.get('video_id'):
            print('[JA PUBLICADO] '+ep_id+' id='+str(prior['video_id']),flush=True)
            continue
        # A previous process may have finished the remote upload but died
        # before writing the queue journal. Reconcile against the publisher
        # per-MP4 receipt first, without attempting a second upload.
        previous=confirmed_existing_upload(video)
        if previous:
            if previous.get('publicacao_publica_confirmada') is True:
                journal[ep_id]={'video_id':previous['video_id'],
                                'status':'publicado-publico',
                                'thumbnail_status':previous.get('thumbnail_status','pending'),
                                'video_sha256':digest(video)}
                save_journal(journal)
                print('[JA ENVIADO] '+ep_id+' https://youtu.be/'+
                      previous['video_id']+'. Nao duplicar.',flush=True)
                continue
            raise RuntimeError('Existe upload anterior de '+ep_id+
                               ' com visibilidade nao confirmada. '
                               'Confira o Studio antes de prosseguir.')
        if prior.get('status') in ('upload_iniciado','upload_indeterminado'):
            raise RuntimeError(
                'Upload anterior sem confirmacao local: '+ep_id+
                '. Confira o YouTube Studio antes de retomar; '
                'nenhum reenvio automatico.'
            )
        try:
            invoke(local_command(ep,args),label='Produzir '+ep_id)
        except (RuntimeError,OSError,subprocess.SubprocessError) as exc:
            if not args.continuar_apos_falha:
                raise
            # A failed production is safe to skip; an uncertain YouTube upload
            # is NEVER safe to skip. No incomplete MP4 was submitted.
            skipped.append(ep_id)
            consecutive_production_failures+=1
            journal[ep_id]={'status':'falha_producao',
                            'causa':'geracao_ou_render_incompleto'}
            save_journal(journal)
            print(f'[PULADO, SEM UPLOAD] {ep_id}: {type(exc).__name__}. '
                  'Cache salvo; somente este episodio fica pendente.',
                  flush=True)
            if consecutive_production_failures>=3:
                raise RuntimeError(
                    'Tres falhas consecutivas de producao. '
                    'Possivel problema geral com o Codex Proxy ou dependencias; '
                    'nao continuar desperdicando recursos. '
                    'Pendentes: '+', '.join(skipped)
                ) from exc
            continue
        consecutive_production_failures=0
        if not publish_now:
            continue
        # The generated video is validated before the irreversible upload.
        ready_video=ensure_ready(
            ep,args.perfil,
            require_character_motion=args.exigir_movimento_personagem)
        if confirmed_existing_upload(ready_video):
            print('[JA ENVIADO] '+ep_id+' encontrado apos render. Pular.',flush=True)
            continue
        journal[ep_id]={'status':'upload_iniciado',
                        'video_sha256':digest(ready_video)}
        save_journal(journal)
        try:
            # Second run reuses voice/images/MP4. MaxChamadas=0 ensures
            # the publishing stage never pays for extra artwork.
            invoke(local_command(ep,args,publish=True),
                   label='Publicar imediatamente como PUBLICO '+ep_id)
        except (RuntimeError,OSError,subprocess.SubprocessError):
            journal[ep_id]['status']='upload_indeterminado'
            save_journal(journal)
            raise
        uploaded=confirmed_existing_upload(ready_video)
        if not uploaded:
            journal[ep_id]['status']='upload_indeterminado'
            save_journal(journal)
            raise RuntimeError('Upload sem ID confirmado. Conferir Studio; nao reenvie '+ep_id)
        if uploaded.get('privacidade_solicitada')!='public':
            journal[ep_id]['status']='upload_indeterminado'
            save_journal(journal)
            raise RuntimeError('Privacidade PUBLICA nao confirmada: '+ep_id)
        if uploaded.get('publicacao_publica_confirmada') is not True:
            journal[ep_id]['status']='upload_indeterminado'
            save_journal(journal)
            raise RuntimeError('YouTube nao confirmou status PUBLIC. '
                               'Verifique Studio sem reenviar '+ep_id)
        journal[ep_id]={'video_id':uploaded['video_id'],
                        'status':'publicado-publico',
                        'thumbnail_status':uploaded.get('thumbnail_status','pending'),
                        'video_sha256':digest(ready_video)}
        save_journal(journal)
        print('[PUBLICADO AGORA] '+ep_id+' https://youtu.be/'+uploaded['video_id'],
              flush=True)
        if uploaded.get('thumbnail_status')!='success':
            print('[CAPA PENDENTE] Arquivo vertical salvo. '
                  'Verifique YouTube Studio (Shorts > Miniatura) e NAO reenvie o MP4.',
                  flush=True)
    if skipped:
        print('[LOTE PARCIAL] Episodios nao publicados por falha de '
              'producao: '+', '.join(skipped)+
              '. Nao perderam o cache. Retome-os apos corrigir o proxy.',
              flush=True)
        return 2
    return 0

def parser()->argparse.ArgumentParser:
    ap=argparse.ArgumentParser(description='Grade Otaku Multicena: 50 Shorts')
    ap.add_argument('--acao',choices=('validar','preparar','produzir','produzir-publicar'),
                    default='validar')
    ap.add_argument('--inicio-na-lista',type=int,default=1)
    ap.add_argument('--quantidade',type=int,default=50)
    ap.add_argument('--modelo',choices=('gpt-image-1.5','gpt-image-2'),
                    default='gpt-image-2')
    ap.add_argument('--perfil',choices=('ultrassutil','equilibrado','vivo'),
                    default='equilibrado')
    ap.add_argument('--max-chamadas-por-video',type=int,default=0)
    ap.add_argument('--confirmar-cota-imagem',action='store_true')
    ap.add_argument('--confirmar-publicacao',action='store_true')
    ap.add_argument('--refazer',action='store_true')
    ap.add_argument('--exigir-movimento-personagem',action='store_true',
                    help='QA estrito opcional: bloqueia se todas as cenas '
                         'forem apenas 2.5D/imagem plana com zoom')
    ap.add_argument('--auditar-editorial',action='store_true',
                    help='Auditoria V3 informativa antes da producao (offline).')
    ap.add_argument('--exigir-gates-editoriais',action='store_true',
                    help='Bloquear problemas objetivos, mantendo QA humano obrigatorio.')
    ap.add_argument('--continuar-apos-falha',action='store_true',
                    help='Se uma producao de imagens/render falhar, salvar '
                         'pendencia SEM upload e tentar o proximo episodio. '
                         'Parar apos 3 falhas consecutivas. Nunca ignorar '
                         'falhas de upload ou de QA do video ja renderizado.')
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
