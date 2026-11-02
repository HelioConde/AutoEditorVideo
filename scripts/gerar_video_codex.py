#!/usr/bin/env python3
"""Arquivo Otaku 0.6 — cenas dirigidas, QA antes de renderizar e MPT local.

Nao envia o video ao YouTube. Cada nova cena usa 1 requisicao ao Codex Proxy.
Cache de imagem com hash de prompt evita refazer chamadas ja concluidas.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import io
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'.mpt-runtime'
PROXY_ENV=ROOT/'chatgpt-codex-proxy'/'.env'
PLAN=ROOT/'conteudos'/'001-death-note-direcao.json'
MATERIAL_DIR=RUNTIME/'storage'/'local_videos'
REPORT=ROOT/'assets'/'gerados'/'qa-visual-v06.json'

sys.path.insert(0,str(Path(__file__).parent))
from diretor_visual import load_plan,scene_prompt,scene_digest,process_file,duplicate_warnings,_sample_stats,visual_signature
from editor_shorts import create_shot_sequence, CUT_DURATION_SECONDS
from finalizador_audio import normalize_video_audio
from planejador_editorial import audit_plan


def proxy_key(path:Path=PROXY_ENV)->str:
    if not path.is_file(): raise RuntimeError('Proxy nao encontrado. Rode testar-codex-proxy.ps1 -Acao instalar')
    m=re.search(r'(?m)^PROXY_API_KEY\s*=\s*(.*?)\s*$',path.read_text(encoding='utf-8-sig'))
    if not m: raise RuntimeError('PROXY_API_KEY ausente em chatgpt-codex-proxy/.env')
    key=m.group(1).strip().strip("\"'")
    if len(key)<15 or key.startswith('change-me'):
        raise RuntimeError('Chave do proxy invalida')
    return key


def check_proxy_accounts(key:str, base:str='http://127.0.0.1:8080'):
    import requests
    r=requests.get(base+'/admin/accounts',headers={'Authorization':'Bearer '+key},timeout=(5,20))
    r.raise_for_status()
    accounts=r.json().get('accounts',[])
    if not any(x.get('eligible_now') is True for x in accounts):
        raise RuntimeError('Nenhuma conta elegivel no Codex Proxy. Verifique -Acao status/cota e nao gaste chamadas.')


def request_image(prompt:str, model:str, key:str, size:str='1024x1536')->bytes:
    import requests
    r=requests.post('http://127.0.0.1:8080/v1/images/generations',
        json={'model':model,'prompt':prompt,'n':1,'size':size},
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},timeout=(15,300))
    if not r.ok:
        raise RuntimeError(f'Imagem recusada (HTTP {r.status_code}): {r.text[:220]}')
    items=r.json().get('data',[])
    if not items:raise RuntimeError('Resposta nao possui imagens')
    obj=items[0]
    if obj.get('b64_json'):
        data=base64.b64decode(obj['b64_json'],validate=True)
    elif obj.get('url','').startswith('data:image/'):
        data=base64.b64decode(obj['url'].split(',',1)[1],validate=True)
    elif obj.get('url','').startswith('https://'):
        url=obj['url']
        # No arbitrary local network URLs returned by an external service.
        r2=requests.get(url,timeout=(10,120),stream=True)
        r2.raise_for_status()
        chunks=[]; size_so_far=0
        for chunk in r2.iter_content(65536):
            size_so_far+=len(chunk)
            if size_so_far>25_000_000: raise RuntimeError('Imagem >25MB')
            chunks.append(chunk)
        data=b''.join(chunks)
    else:raise RuntimeError('A API nao devolveu b64_json ou URL HTTPS de imagem')
    if not data or len(data)>25_000_000:raise RuntimeError('Arquivo de imagem invalido')
    return data


def _json_atomic(path:Path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)


def stage_images(plan:dict,model:str, key:str|None=None,fetcher=request_image, material_dir:Path=MATERIAL_DIR, report:Path=REPORT)->list[Path]:
    material_dir.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    rows=[];files=[]
    for scene in plan['cenas']:
        prompt=scene_prompt(scene,plan)
        checksum=scene_digest(prompt,model)
        stem=f'arquivo-otaku-v06-{scene["id"]}-{checksum}'
        raw=material_dir/(stem+'-original.png')
        final=material_dir/(stem+'.jpg')
        qa_path=material_dir/(stem+'-qa.json')
        if final.is_file() and qa_path.is_file():
            qa=json.loads(qa_path.read_text(encoding='utf-8'))
            print(f'[CACHE] Cena {scene["id"]}: usando material ja revisado. Sem nova chamada de IA.',flush=True)
        else:
            if key is None:raise RuntimeError('Falta chave para gerar cenas nao armazenadas em cache')
            print(f'[IA] Gerando cena {scene["id"]}/{len(plan["cenas"])} ({scene["tipo"]})',flush=True)
            blob=fetcher(prompt,model,key)
            from PIL import Image
            with Image.open(io.BytesIO(blob)) as im:
                im.load()
                if min(im.size)<640:raise RuntimeError('Imagem devolvida com resolucao baixa')
                im.convert('RGB').save(raw,'PNG')
            qa=process_file(raw,final,scene,prompt,model)
            _json_atomic(qa_path,qa)
        rows.append(qa);files.append(final)
        _json_atomic(report,{'versao':'0.6','status':'em_progresso','cenas':rows,
                             'alertas':duplicate_warnings(rows)})
    _json_atomic(report,{'versao':'0.6','status':'concluido','modelo':model,
                         'cenas':rows,'alertas':duplicate_warnings(rows)})
    for warning in duplicate_warnings(rows):print('[ATENCAO] '+warning)
    print(f'[OK] QA de {len(rows)} cenas: {report}',flush=True)
    return files



# Arquivos PNG da primeira versao do Short, identificados nas imagens fornecidas
# pelo usuario. A selecao por nome evita que a montagem recicle a capa/titulo.
_OLD_SCENE_NAMES = {
    '01': 'openai-image-3ac809aae11b.png',  # Light e L no xadrez
    '02': 'openai-image-a64df63fa0f8.png',  # Light no corredor
    '03': 'openai-image-6ca00534820a.png',  # L sentado
    '04': 'openai-image-4e3cf553947c.png',  # caderno na mesa
    '05': 'openai-image-3ac809aae11b.png',  # xadrez, outro corte
    '06': 'openai-image-88ec8c8a025d.png',  # Light na janela
    '07': 'openai-image-3ac809aae11b.png',  # confronto final
}


def find_existing_images(source_folder: Path | None = None) -> list[Path]:
    """Encontra somente imagens de cenas do MPT; nunca importa tokens ou capas."""
    folders = [source_folder] if source_folder else [
        ROOT/'assets'/'gerados'/'imagens-reutilizadas',
        ROOT/'assets'/'gerados',
        RUNTIME/'storage'/'tasks',
    ]
    found = []
    seen_hashes = set()
    from PIL import Image
    for folder in folders:
        if folder is None or not folder.is_dir():
            continue
        for f in sorted(folder.rglob('*')):
            if not f.is_file() or f.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
                continue
            name=f.name.lower()
            if not (name.startswith('openai-image-') or name.startswith('teste-codex-proxy')
                    or (source_folder is not None and not name.startswith('miniatura') and not name.startswith('capa-'))):
                continue
            try:
                with Image.open(f) as im:
                    if min(im.size) < 640 or im.width < 800: continue
                # Evita ter a mesma imagem copiada em pastas diferentes.
                identity=hashlib.sha256(f.read_bytes()).hexdigest()
            except Exception:
                continue
            if identity not in seen_hashes:
                found.append(f)
                seen_hashes.add(identity)
    return found


def stage_existing_images(plan: dict, model: str, source_folder: Path | None = None,
                          material_dir: Path = MATERIAL_DIR, report: Path = REPORT) -> list[Path]:
    """Reaproveita imagens da primeira versao sem acessar o Codex Proxy.

    Se nao houver as cinco imagens nomeadas no computador, usa as imagens
    validas encontradas e deixa registrada a correspondencia aproximada.
    """
    images=find_existing_images(source_folder)
    if len(images)<3:
        raise RuntimeError(
          'Encontrei menos de 3 imagens validas. Copie os PNG do primeiro video '
          r'para assets\gerados\imagens-reutilizadas ou use '
          r'-PastaImagens C:\caminho\para\pasta. Nada foi enviado nem gerado por IA.'
        )
    material_dir.mkdir(parents=True,exist_ok=True)
    report.parent.mkdir(parents=True,exist_ok=True)
    by_name={f.name.lower():f for f in images}
    rows,files=[],[]
    for index,scene in enumerate(plan['cenas']):
        source=by_name.get(_OLD_SCENE_NAMES.get(scene['id'],'')) or images[index%len(images)]
        source_sha=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        out=material_dir/f'arquivo-otaku-v061-reuso-{scene["id"]}-{source_sha}.jpg'
        qa_file=out.with_suffix('.qa.json')
        if out.is_file() and qa_file.is_file():
            qa=json.loads(qa_file.read_text(encoding='utf-8'))
            print(f'[CACHE] Cena {scene["id"]}: reutilizada, sem IA.')
        else:
            qa=process_file(source,out,scene,scene_prompt(scene,plan),model)
            qa['reutilizada']=True
            qa['origem']=str(source)
            qa['aviso']='A imagem original pode nao corresponder exatamente a esta cena do novo roteiro.'
            _json_atomic(qa_file,qa)
        files.append(out)
        rows.append(qa)
        print(f'[LOCAL] Cena {scene["id"]}/{len(plan["cenas"])}: {source.name}',flush=True)
    duplicate=duplicate_warnings(rows)
    _json_atomic(report,{'versao':'0.6.1','status':'concluido','modo':'reutilizacao sem IA',
                         'modelo_da_arte_original':'nao verificado','cenas':rows,
                         'alertas':duplicate,
                         'observacao':'Sem chamadas ao proxy; imagens repetidas sao esperadas.'})
    for warn in duplicate: print('[ATENCAO] '+warn)
    print(f'[OK] Reaproveitadas {len(rows)} cenas com {len(images)} imagens encontradas. Sem gastar cota.')
    return files

def mpt_args(mpt:Path,plan:dict,local_files:list[Path]) -> list[str]:
    # MPT only allows materials from $MPT_HOME/storage/local_videos.
    # Absolute paths are accepted as long as they remain inside that directory.
    if any(not f.is_relative_to(MATERIAL_DIR) for f in local_files):
        raise RuntimeError('Material fora da pasta segura do MPT')
    return [str(mpt),'cli',
        '--video-subject',plan['titulo'],
        '--video-script',plan['roteiro_melhorado'],
        '--video-language','pt-BR',
        '--video-source','local',
        '--video-materials',','.join(str(f) for f in local_files),
        '--video-aspect','9:16',
        '--video-fit-mode','cover',
        '--video-concat-mode','sequential',
        '--image-motion','zoom',
        '--video-clip-duration',str(CUT_DURATION_SECONDS),
        '--voice-name','pt-BR-AntonioNeural',
        '--voice-rate','1.09',
        '--bgm-type','none',
        '--subtitle-enabled',
        '--subtitle-position','custom',
        '--custom-position','72',
        '--subtitle-display-mode','word_by_word',
        '--text-fore-color','#FFFFFF',
        '--stroke-color','#000000',
        '--stroke-width','3.5',
        '--font-size','83',
        '--video-count','1',
        '--stop-at','video']


def output_filename(plan: dict, reused: bool) -> str:
    """Ensure different episodes never silently overwrite a previous MP4."""
    episode_id = str(plan.get('id', '')).strip()
    if episode_id == '001-death-note':
        return 'arquivo-otaku-piloto-v07-reuso.mp4' if reused else 'arquivo-otaku-piloto-codex-v07.mp4'
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', episode_id) or len(episode_id) > 80:
        raise ValueError('ID do episodio invalido para nome de arquivo')
    return f'arquivo-otaku-{episode_id}-{"reuso" if reused else "codex"}.mp4'


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--modelo',choices=['gpt-image-1.5','gpt-image-2'],default='gpt-image-1.5')
    parser.add_argument('--somente-configurar',action='store_true')
    parser.add_argument('--apenas-qa',action='store_true')
    parser.add_argument('--reutilizar-imagens',action='store_true')
    parser.add_argument('--pasta-imagens',type=Path,default=None)
    parser.add_argument('--plano',type=Path,default=PLAN)
    args=parser.parse_args()
    plan=load_plan(args.plano)
    out=ROOT/'assets'/'gerados'
    out.mkdir(parents=True,exist_ok=True)
    _json_atomic(out/'plano-visual-v06.json',plan)
    # v0.8: auditoria antes de gerar imagens. Nao usa API nem consome cotas.
    editorial=audit_plan(plan)
    _json_atomic(out/'relatorio-editorial-v08.json',editorial)
    for aviso in editorial.get('alertas',[]):
        print('[EDITORIAL] '+aviso,flush=True)
    if args.somente_configurar:
        print(f'[OK] Plano {plan["id"]} de {len(plan["cenas"])} cenas validado; nenhuma imagem gerada e nenhum video enviado.')
        return 0
    os.environ['MPT_HOME']=str(RUNTIME)
    if args.apenas_qa:
        cached=list(MATERIAL_DIR.glob('arquivo-otaku-v06-*-qa.json'))
        rows=[json.loads(p.read_text(encoding='utf-8')) for p in cached]
        _json_atomic(REPORT,{'status':'somente_qa','cenas':rows,'alertas':duplicate_warnings(rows)})
        print(f'[OK] {len(rows)} relatórios de cena encontrados. Nao foi chamada nenhuma IA.');return 0
    python_scripts=Path(sys.executable).parent
    mpt=python_scripts/('mpt.exe' if os.name=='nt' else 'mpt')
    if not mpt.is_file():raise RuntimeError('mpt.exe ausente: verifique o ambiente .venv do projeto')
    # Modo offline: reaproveita imagens sem autenticar ou gastar conta ChatGPT.
    if args.reutilizar_imagens:
        files=stage_existing_images(plan,args.modelo,args.pasta_imagens)
    else:
        # Readonly preflight before any API calls.
        key=proxy_key()
        # stage_images itself is cache aware and must not require a live account if
        # every scene has already been generated.
        missing=[]
        for scene in plan['cenas']:
            stem=f'arquivo-otaku-v06-{scene["id"]}-{scene_digest(scene_prompt(scene,plan),args.modelo)}'
            if not (MATERIAL_DIR/(stem+'.jpg')).is_file() or not (MATERIAL_DIR/(stem+'-qa.json')).is_file():
                missing.append(scene['id'])
        if missing:check_proxy_accounts(key)
        print(f'[INFO] {len(missing)} cenas exigem IA; {len(plan["cenas"])-len(missing)} serao reaproveitadas.',flush=True)
        files=stage_images(plan,args.modelo,key)
    # Corte mais agil sem novas chamadas de IA: 2 recortes por cena.
    shots=create_shot_sequence(files,MATERIAL_DIR/'arquivo-otaku-shots-v07')
    print(f'[EDICAO] {len(shots)} planos de {CUT_DURATION_SECONDS}s preparados; 0 chamadas de IA adicionais.',flush=True)
    print('[MPT] Montando video com cenas revisadas e narracao em portugues...',flush=True)
    inicio=datetime.now(timezone.utc).timestamp()-5
    code=subprocess.call(mpt_args(mpt,plan,shots),cwd=str(ROOT),env=os.environ.copy())
    if code:
        raise RuntimeError(f'MoneyPrinterTurbo retornou codigo {code}. Os materiais ja criados ficam no cache.')
    tasks=RUNTIME/'storage'/'tasks'
    candidates=sorted((f for f in tasks.glob('*/final-*.mp4') if f.stat().st_mtime>=inicio),key=lambda x:x.stat().st_mtime,reverse=True)
    if not candidates:raise RuntimeError('Montagem concluiu, mas nenhum MP4 novo foi encontrado. Confira os logs do MoneyPrinterTurbo.')
    # Explicit distinct filename: never silently replace the already published pilot.
    final=out/output_filename(plan,args.reutilizar_imagens)
    import shutil
    shutil.copy2(candidates[0],final)
    audio_report=normalize_video_audio(final)
    print('[AUDIO] '+audio_report['status']+' — '+str(audio_report.get('reason','-16 LUFS')) )
    _json_atomic(out/'resultado-video-v07.json',{
        'criado_em':datetime.now(timezone.utc).isoformat(),
        'modelo':args.modelo,'arquivo':str(final),'plano':str(args.plano),
        'modo':'reuso offline' if args.reutilizar_imagens else 'nova geracao Codex',
        'cenas':[str(x) for x in files],'shots':[str(x) for x in shots],'qa':str(REPORT),'audio':audio_report})
    print(f'[OK] NOVO video gerado (nao publicado): {final}',flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(f'[ERRO] {type(exc).__name__}: {exc}',file=sys.stderr)
        raise SystemExit(1)
