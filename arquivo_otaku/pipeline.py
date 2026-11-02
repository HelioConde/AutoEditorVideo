"""Plano editorial, sincronizacao de cortes e QA; sem rede ou upload.

Projetado para ser integrado ao MoneyPrinterTurbo existente: a geracao de imagens,
a narração e a publicacao continuam em scripts independentes e opt-in.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path


def slug(text: str) -> str:
    name = re.sub(r'[^a-z0-9-]+', '-', text.lower()).strip('-')
    if not name or len(name) > 70:
        raise ValueError('ID invalido, use ate 70 letras minusculas, numeros ou hifens')
    return name


def split_sentences(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in chunks if p.strip()]


def load_episode(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    for key in ('id', 'obra', 'titulo', 'roteiro', 'cenas'):
        if key not in data or not data[key]:
            raise ValueError(f'Episodio incompleto: {key}')
    if slug(data['id']) != data['id']:
        raise ValueError('ID nao pode conter path traversal ou espacos')
    if not isinstance(data['cenas'], list) or not 1 <= len(data['cenas']) <= 60:
        raise ValueError('Precisa de 1 a 60 cenas (limite técnico, sem quantidade fixa)')
    for scene in data['cenas']:
        if not scene.get('descricao') or not scene.get('papel'):
            raise ValueError('Cada cena precisa de descricao e papel narrativo')
    return data


def read_srt(path: Path) -> list[dict]:
    text = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    cues = []
    def ms(token):
        h, m, sec, milli = [int(n) for n in re.split(r'[:,]', token)]
        return ((h*60+m)*60+sec)*1000 + milli
    for chunk in re.split(r'\n\s*\n', text.strip()):
        lines = [s.strip() for s in chunk.split('\n') if s.strip()]
        match = next((m for l in lines if (m := re.fullmatch(r'(\d\d:\d\d:\d\d,\d{3})\s*-->\s*(\d\d:\d\d:\d\d,\d{3}).*', l))), None)
        if match is None:
            continue
        start, end = map(ms, match.groups())
        content = ' '.join(lines[lines.index(match.group(0))+1:]).strip()
        if end <= start or (cues and start < cues[-1]['start_ms']):
            raise ValueError('SRT com tempos invalidos ou fora de ordem')
        cues.append({'start_ms':start,'end_ms':end,'texto':content})
    if not cues:
        raise ValueError('SRT vazio ou sem intervalos validos')
    return cues


def plan_cuts(episode: dict, cues: list[dict] | None = None, seconds: float | None = None) -> dict:
    """Prefere tempos de legenda reais; sem SRT, marca estimativa explicitamente."""
    scenes = episode['cenas']
    if cues:
        stop = max(c['end_ms'] for c in cues)
        cuts = []
        # Distribui as frases do roteiro (por ordem), preservando limites de cada cue.
        # A edicao final pode usar start/end sem qualquer suposicao de FPS.
        count = len(cues)
        for i, c in enumerate(cues):
            scene = scenes[min(len(scenes)-1, i*len(scenes)//count)]
            cuts.append({'inicio_ms':c['start_ms'],'fim_ms':c['end_ms'],
                         'cena_id':scene['id'], 'papel':scene['papel'], 'texto':c['texto'],
                         'origem_tempo':'srt'})
        source='srt'
    else:
        sentence_count = max(1, len(split_sentences(episode['roteiro'])))
        estimated = max(len(scenes)*2200, sentence_count*2700)
        total = round((float(seconds)*1000) if seconds else estimated)
        if total <= 0:
            raise ValueError('Duracao deve ser positiva')
        cuts=[]
        for i, scene in enumerate(scenes):
            a=round(i*total/len(scenes)); b=round((i+1)*total/len(scenes))
            cuts.append({'inicio_ms':a,'fim_ms':b,'cena_id':scene['id'],
                         'papel':scene['papel'],'origem_tempo':'estimado'})
        stop=total;source='estimativa (substituir por SRT antes da publicacao)'
    warnings=[]
    for c in cuts:
        if c['fim_ms']-c['inicio_ms']>6500:
            warnings.append(f"Plano longo {c['cena_id']} ({(c['fim_ms']-c['inicio_ms'])/1000:.1f}s): variar enquadramento")
    return {'id':episode['id'],'obra':episode['obra'],'titulo':episode['titulo'],
            'origem_tempos':source,'duracao_ms':stop,'planos':cuts,'alertas':warnings,
            'revisao_obrigatoria':not episode.get('fatos_revisados', False),
            'publicacao_automatica':False}


def visual_qa(paths: list[Path]) -> dict:
    try:
        from PIL import Image, ImageStat
    except ImportError:
        raise RuntimeError('Instale Pillow para QA visual: pip install pillow') from None
    rows=[]
    for p in paths:
        with Image.open(p) as image:
            size=image.size
            reduced=image.convert('L').resize((128,128))
            histogram=reduced.histogram()
            dark=sum(histogram[:64])/sum(histogram)
            mean=ImageStat.Stat(reduced).mean[0]
            rows.append({'arquivo':p.name,'largura':size[0],'altura':size[1],
                         'brilho_medio':round(mean,1),'fracao_sombras':round(dark,3),
                         'alertas':(['Iluminacao muito escura'] if dark>0.82 else []) +
                         (['Resolucao baixa'] if min(size)<640 else [])})
    return {'quantidade':len(rows),'imagens':rows,'alertas_total':sum(len(x['alertas']) for x in rows)}


def main(argv=None):
    ap=argparse.ArgumentParser(description='Arquivo Otaku: validar plano, cortes e imagens sem acessar APIs')
    ap.add_argument('--episodio',type=Path,required=True)
    ap.add_argument('--srt',type=Path)
    ap.add_argument('--duracao',type=float)
    ap.add_argument('--saida',type=Path,default=Path('assets/gerados/plano-cortes.json'))
    ap.add_argument('--imagem',type=Path,action='append',default=[])
    args=ap.parse_args(argv)
    ep=load_episode(args.episodio)
    cues=read_srt(args.srt) if args.srt else None
    plan=plan_cuts(ep,cues,args.duracao)
    if args.imagem:
        plan['qa_imagens']=visual_qa(args.imagem)
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f"[OK] {len(plan['planos'])} planos: {args.saida} (sem IA e sem upload)")
    if plan['revisao_obrigatoria']:
        print('[ATENCAO] Evidencias editoriais ainda nao revisadas: NAO publicar automaticamente.')
    if cues is None:
        print('[ATENCAO] Duracoes estimadas. Forneca SRT para sincronizar aos limites reais das falas.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
