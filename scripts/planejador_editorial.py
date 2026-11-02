"""Planejamento editorial com fontes e controles de qualidade (sem APIs)."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]

def audit_plan(plan:dict)->dict:
    script=plan.get('roteiro_melhorado','')
    hook=plan.get('gancho_primeiros_segundos','')
    words=re.findall(r'\b[\wÀ-ÿ]+\b',script)
    word_count=len(words)
    duration_range=(round(word_count/2.8,1),round(word_count/2.3,1))
    scenes=plan.get('cenas',[])
    issues=[]
    if len(hook.split())>18:issues.append('Gancho possivelmente longo: tente ate 18 palavras')
    if not script.lower().startswith(hook[:22].lower()): issues.append('Gancho do plano diferente da abertura do roteiro')
    if not script.strip().endswith('?'):issues.append('Considere um encerramento com pergunta relevante')
    if not scenes:issues.append('Falta propor cenas visuais com base nos acontecimentos do roteiro')
    if word_count>150:issues.append('Roteiro longo: ajuste com uma narracao de teste antes de publicar')
    if word_count<55:issues.append('Roteiro possivelmente curto: verificar se entrega uma ideia completa')
    if len(scenes)>=4 and len(set(x.get('tipo') for x in scenes))<=2:issues.append('Avaliar variedade visual: objetos, ambientes e contrapontos quando o roteiro pedir')
    if not plan.get('tese_original'):
        issues.append('Especifique a tese interpretativa original do episodio e um exemplo da obra')
    if any(x in script.lower() for x in ['vazou oficialmente','foi confirmado oficialmente','acaba de ser anunciado']):
        issues.append('Declaracao de novidade exige fonte verificavel antes da publicacao')
    return {'serie':plan.get('serie'),'palavras':word_count,
        'duracao_estimada_segundos':duration_range,
        'titulo_atual':plan.get('titulo'),
        'ganchos_para_testar':[
          hook,
          f'O que torna {plan.get("serie", "este anime")} tao diferente?',
          f'A estrategia mais perigosa de {plan.get("serie", "este anime")} nao envolve forca.'
        ],
        'estrutura':plan.get('estrutura_curto',{}),'cenas':len(scenes),
        'alertas':issues,
        'regras':['Nao inventar noticias ou fontes','Nao copiar roteiros de canais concorrentes',
                  'Verificar informacoes atuais antes de publicar','Revisar o video antes de enviar como publico'],
        'benchmark':['Locomotiva Pop: titulos de curiosidade e cultura pop',
                     'Time Trends: perguntas especificas sobre anime e tendencias',
                     'Vicio Nerd: conflitos morais e temas comparaveis',
                     'buruno: tese critica e demonstracao narrativa',
                     'Hashi Quebrado: misterio e atmosfera sombria',
                     'Daniel Morais: motivações e consequencias de personagens'],
        'nota_metodologica':'Benchmarks baseados em catalogo/titulos publicos; nao houve acesso a retencao nem a analytics dos canais.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--plano',type=Path,default=ROOT/'conteudos'/'001-death-note-direcao.json');ap.add_argument('--saida',type=Path,default=ROOT/'assets'/'gerados'/'relatorio-editorial-v07.json');args=ap.parse_args()
    plan=json.loads(args.plano.read_text(encoding='utf-8-sig'))
    result=audit_plan(plan)
    args.saida.parent.mkdir(parents=True,exist_ok=True)
    args.saida.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'[OK] Relatorio editorial: {args.saida}')
    print(f'[INFO] {result["palavras"]} palavras; estimativa {result["duracao_estimada_segundos"]} segundos (depende do TTS).')
    for a in result['alertas']:print('[ALERTA] '+a)

if __name__=='__main__': main()
