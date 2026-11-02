#!/usr/bin/env python3
"""Radar editorial offline. Pautas e evidencias sao hipoteses, NAO tendencias medidas."""
from __future__ import annotations
import argparse,csv,json,re,unicodedata
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'dados'/'pautas-otaku.json'
METRICS=ROOT/'dados'/'metricas-youtube.json'
OUTPUT=ROOT/'assets'/'gerados'/'radar-editorial'

def read_json(path:Path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def _number(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)):
        return None
    return float(value)

def performance_by_format(metrics:dict) -> dict:
    """Consolida so valores reais fornecidos pelo operador; nao inventa baseline."""
    buckets=defaultdict(list)
    for v in metrics.get('videos',[]):
        watched=_number(v.get('escolheram_assistir_pct'))
        avg=_number(v.get('percentual_medio_assistido'))
        if watched is None or avg is None or not (0<=watched<=100 and 0<=avg<=300):
            continue
        buckets[v.get('formato','desconhecido')].append((watched,avg))
    return {format:{'amostra':len(values),
                    'assistiram_vs_deslizaram_pct':round(sum(v[0] for v in values)/len(values),1),
                    'percentual_medio_assistido':round(sum(v[1] for v in values)/len(values),1)}
            for format,values in buckets.items()}

def risk_flags(item:dict)->list[str]:
    flags=[]
    for field in ('obra','formato','titulo_sugerido','gancho','prova_a_verificar'):
        if not str(item.get(field,'')).strip():flags.append(f'Campo ausente: {field}')
    if not item.get('fato_verificado'):
        flags.append('Revisar fatos e exemplos na obra antes de publicar')
    if item.get('spoiler')=='alto': flags.append('Spoiler alto: informar no roteiro ou preferir outra pauta')
    if re.search(r'\b(confirmado|vazou|acabou de sair|oficialmente)\b',str(item.get('titulo_sugerido','')).lower()):
        flags.append('Noticias e alegacoes atuais exigem fonte primária datada')
    if len(str(item.get('titulo_sugerido','')))>90:
        flags.append('Titulo extenso para Short: revisar comprimento')
    return flags

def score_idea(item:dict,studio_data:dict|None=None)->dict:
    manual=item.get('pontuacao_manual',{})
    weights={'curiosidade':7,'potencial_visual':5,'atemporal':4,'originalidade':4}
    values={k:max(0,min(5,int(manual.get(k,0)))) for k in weights}
    base=round(sum(values[k]*weights[k] for k in weights))
    # Pontuacao heuristica de pauta (0-100) nao e previsao de viralidade.
    flags=risk_flags(item)
    if not item.get('fato_verificado'):base-=12
    if item.get('spoiler')=='alto':base-=8
    if re.search(r'\b(confirmado|vazou|oficialmente)\b',str(item.get('titulo_sugerido','')).lower()):base-=18
    base=max(0,min(100,base))
    result=dict(item)
    result['nota_editorial']=base
    result['avisos']=flags
    if studio_data and item.get('formato') in studio_data:
        result['historico_do_formato']=studio_data[item['formato']]
    return result

def rank_diverse(items:list[dict], count:int)->list[dict]:
    pending=sorted(items,key=lambda x:(-x['nota_editorial'],x['id']))
    order=[]; fr=defaultdict(int); fmt=defaultdict(int)
    while pending and len(order)<count:
        def priority(x):
            return (x['nota_editorial']-14*fr[x['obra']]-6*fmt[x['formato']],x['nota_editorial'])
        next_item=max(pending,key=priority)
        pending.remove(next_item)
        order.append(next_item)
        fr[next_item['obra']]+=1
        fmt[next_item['formato']]+=1
    return order

def brief_for(item:dict)->str:
    return f"""# Brief de roteiro — {item['obra']}

**Pauta:** {item['pauta']}

**Titulo candidato:** {item['titulo_sugerido']}

**Gancho candidato:** {item['gancho']}

**Ponto que falta conferir na obra:** {item['prova_a_verificar']}

**Formato:** {item['formato']} | **Risco de spoiler:** {item['spoiler']}

## Orientacao para roteiro original

- 0-3s: conflito imediato sem saudacao inicial.
- 3-12s: fornecer um fato verificavel ou cena especifica.
- 12-30s: explicar causa e consequencia com uma interpretacao propria.
- 30-45s: contrapor a ideia e entregar a resposta.
- Encerramento: pergunta verdadeira que admite mais de uma leitura.
- Planejar 6-9 composicoes distintas, nao apenas recortes do mesmo rosto.
- Separar interpretacoes de fatos; nao inventar falas, datas ou anuncios.
- Antes de gerar imagens/ver publicar, revisar spoilers, fidelidade e direitos.

**Atencao:** este documento e uma pauta; nao e roteiro verificado, nem autorizacao para upload.
"""

def render_md(rows:list[dict],metrics:dict)->str:
    lines=['# Radar Editorial — Arquivo Otaku v0.8','','**Aviso:** notas editoriais sao heuristicas, nao dados de views nem previsao de viralidade.','','## Fila sugerida','','| Ordem | Obra | Angulo | Titulo sugerido | Nota | Alertas |','|---|---|---|---|---:|---:|']
    for n,item in enumerate(rows,1):
        lines.append(f'| {n} | {item["obra"]} | {item["formato"]} | {item["titulo_sugerido"]} | {item["nota_editorial"]} | {len(item["avisos"])} |')
    lines+=['','## Variaveis a medir apos publicar','','- Percentual que escolheu assistir em vez de deslizar','- Percentual medio assistido e duracao media','- Onde o espectador abandona o video','- Comentarios que demonstram interesse em mais episodios','','Nenhuma cota do Codex Proxy foi utilizada. Nenhum video foi enviado.']
    if metrics:
        lines+=['','## Dados inseridos manualmente do Studio','', '| Formato | Amostra | Assistiram vs deslizaram (%) | Media assistida (%) |','|---|---:|---:|---:|']
        for kind,v in sorted(metrics.items()):lines.append(f'| {kind} | {v["amostra"]} | {v["assistiram_vs_deslizaram_pct"]} | {v["percentual_medio_assistido"]} |')
    return '\n'.join(lines)+'\n'

def run(ideas_path=DATA,metrics_path=METRICS,output=OUTPUT,quantity=8,selected_id=''):
    ideas=read_json(ideas_path)['pautas']
    if len({x['id'] for x in ideas})!=len(ideas):raise ValueError('IDs repetidos em pautas-otaku.json')
    data=performance_by_format(read_json(metrics_path)) if Path(metrics_path).is_file() else {}
    ranked=rank_diverse([score_idea(i,data) for i in ideas],max(1,quantity))
    output.mkdir(parents=True,exist_ok=True)
    (output/'fila-editorial.json').write_text(json.dumps({'versao':'0.8','metodo':'heuristica, sem APIs externas','fila':ranked,'metricas_reais_disponiveis':data},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output/'fila-editorial.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f,delimiter=';');writer.writerow(['ordem','id','obra','formato','titulo_sugerido','nota_editorial','ponto_a_verificar','avisos'])
        for n,x in enumerate(ranked,1):writer.writerow([n,x['id'],x['obra'],x['formato'],x['titulo_sugerido'],x['nota_editorial'],x['prova_a_verificar'],' | '.join(x['avisos'])])
    (output/'fila-editorial.md').write_text(render_md(ranked,data),encoding='utf-8')
    if selected_id:
        if not re.fullmatch(r'[a-z0-9-]{1,60}',selected_id):
            raise ValueError('ID invalido: use letras minusculas, numeros ou hifen')
        matches=[x for x in ideas if x['id']==selected_id]
        if not matches:raise ValueError(f'Pauta desconhecida: {selected_id}')
        (output/f'brief-{selected_id}.md').write_text(brief_for(matches[0]),encoding='utf-8')
    return ranked

def main():
    p=argparse.ArgumentParser(description='Radar editoral offline sem chamadas IA')
    p.add_argument('--quantidade',type=int,default=8);p.add_argument('--id',default='');p.add_argument('--pautas',type=Path,default=DATA);p.add_argument('--metricas',type=Path,default=METRICS);p.add_argument('--saida',type=Path,default=OUTPUT)
    args=p.parse_args();r=run(args.pautas,args.metricas,args.saida,args.quantidade,args.id)
    print(f'[OK] Radar editorial: {args.saida} ({len(r)} pautas). Sem API, sem upload.')
    for n,x in enumerate(r,1):print(f'  {n}. [{x["nota_editorial"]}/100] {x["titulo_sugerido"]} ({x["obra"]})')
    if args.id:print(f'[OK] Brief: {args.saida / ("brief-"+args.id+".md")}')

if __name__=='__main__': main()
