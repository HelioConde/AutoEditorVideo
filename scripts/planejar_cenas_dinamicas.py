#!/usr/bin/env python3
"""Divide roteiros em acontecimentos visuais, sem meta fixa de imagens.

É uma proposta offline para revisão. Não gera imagens, áudio ou uploads.
Se o editor fornecer blocos_visuais, eles têm prioridade sobre a heurística.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conteudos" / "testes-animados-5.json"

PIVOTS = re.compile(
    r"^(?:mas|só que|so que|então|entao|até que|ate que|de repente|"
    r"porém|porem|enquanto isso|ao mesmo tempo|por outro lado|"
    r"no entanto|depois disso|a partir daí|a partir dai|"
    r"quando|por trás|por tras|no fim|finalmente|a verdade é que|"
    r"o problema é que|a consequência|a consequencia)\b",
    re.I
)
ENDING = re.compile(
    r"^(?:e você|e voce|você acha|voce acha|na sua opinião|"
    r"na sua opiniao|agora me diz|então me diz|entao me diz|"
    r"e aí|e ai|mas e você|mas e voce)\b", re.I
)
STOP = set("a o e de da do das dos que em um uma uns umas com por para no na nos nas "
           "como mais mas era foi são eram sua seu seus suas ele ela eles elas isso "
           "esse essa se não nao já ja só so sobre quando entre depois mesmo ainda "
           "muito tudo cada até ate outro outra".split())
FOCUSES = {"light","kira","misa","ryuk","near","mello","caderno","tabuleiro",
           "peças","pecas","maçã","maca","shinigami","investigação","investigacao","sangue"}
SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+(?=[\w\"“'«])")
MARKER = "[[CENA]]"


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[\wÀ-ÿ]+", text.lower())
            if len(w)>2 and w not in STOP}


def subject_shift(before: str, after: str) -> bool:
    old=tokens(before)&FOCUSES
    new=tokens(after)&FOCUSES
    # A change of topic is a signal, not a compulsory cut.
    return bool(old and new and not (old&new))


def break_automatically(text: str) -> list[dict]:
    paragraphs = re.split(r"(?:\r?\n\s*\r?\n|\[\[CENA\]\])", text.strip())
    result: list[dict] = []
    for pidx,paragraph in enumerate(paragraphs):
        if not paragraph.strip():
            continue
        chunks=sentences(" ".join(paragraph.split()))
        current: list[str] = []
        for s in chunks:
            preceding = " ".join(current)
            change = (PIVOTS.match(s) or ENDING.match(s) or
                      subject_shift(current[-1],s) if current else False)
            # Avoid cutting between a very short hook and its explanation.
            if change and len(preceding.split())>=9:
                result.append({"texto":" ".join(current),
                               "motivo":"mudança narrativa ou de foco"})
                current=[]
            current.append(s)
        if current:
            result.append({"texto":" ".join(current),
                           "motivo":"bloco narrativo" if pidx==0 else "parágrafo ou divisão marcada"})
    return result


def scene_plan(episode: dict, *, duration: float | None = None) -> dict:
    script = str(episode.get("script") or episode.get("roteiro_melhorado")
                 or episode.get("roteiro") or "").strip()
    if not script:
        raise ValueError("Roteiro ausente")
    manual = episode.get("blocos_visuais")
    if manual is not None:
        if not isinstance(manual, list) or not manual or not all(isinstance(s,str) and s.strip() for s in manual):
            raise ValueError("blocos_visuais deve ser lista não vazia de textos")
        # No silently missing or reordering narration in a manually supplied plan.
        check=lambda t: re.sub(r"\s+"," ",t.replace(MARKER," ")).strip()
        if check(" ".join(manual))!=check(script):
            raise ValueError("Os blocos_visuais precisam preservar o roteiro integral e na mesma ordem")
        blocks=[{"texto":s.strip(),"motivo":"definição explícita do roteirista"} for s in manual]
        method="roteirista"
    else:
        blocks=break_automatically(script)
        method="heurística por mudanças de assunto, contraste e parágrafos"
    if not blocks:
        raise ValueError("Nenhuma cena visual identificada")
    counts=[max(1,len(re.findall(r"[\wÀ-ÿ]+",s["texto"]))) for s in blocks]
    total_words=sum(counts)
    # The timing is an estimate, never exact synchronization with speech.
    estimated = duration if duration is not None else total_words/2.5
    if estimated<=0:
        raise ValueError("Duração precisa ser positiva")
    pos=0.0
    scenes=[]
    for i,(block,count) in enumerate(zip(blocks,counts),1):
        start=round(pos,3)
        pos+=estimated*count/total_words
        end=round(estimated if i==len(blocks) else pos,3)
        words=block["texto"]
        role=("fechamento" if ENDING.match(words) else
              "virada" if PIVOTS.match(words) else
              "gancho" if i==1 else "desenvolvimento")
        scenes.append({
            "id":f"{i:02}",
            "trecho_roteiro":words,
            "papel":role,
            "inicio_estimado_s":start,
            "fim_estimado_s":end,
            "duracao_estimada_s":round(end-start,3),
            "motivo_divisao":block["motivo"],
            "prompt_visual":"",  # Direção visual deve ser criada para o acontecimento.
            "revisao_visual_pendente":True
        })
    return {
        "versao":"arquivo-otaku/cenas-dinamicas/v1",
        "episodio":episode.get("id",""),
        "total_cenas":len(scenes),
        "duracao_estimada_s":round(estimated,3),
        "origem":"estimativa sem TTS" if duration is None else "duracao informada; cortes ainda estimados",
        "metodo":method,
        "cenas":scenes,
        "observacao":"Nenhuma meta fixa de cenas. Revisar as transições e sincronizar com áudio/legendas antes de renderizar.",
        "publicacao_automatica":False
    }


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Planejamento visual dinâmico, sem IA, sem upload")
    parser.add_argument("--episodio",required=True,help="ID no manifesto ou caminho JSON de um episódio")
    parser.add_argument("--manifesto",type=Path,default=MANIFEST)
    parser.add_argument("--duracao",type=float)
    parser.add_argument("--saida",type=Path)
    args=parser.parse_args(argv)
    source=Path(args.episodio)
    if source.suffix.lower()==".json":
        data=json.loads(source.read_text(encoding="utf-8-sig"))
    else:
        manifest=json.loads(args.manifesto.read_text(encoding="utf-8-sig"))
        data=next((ep for ep in manifest.get("episodes",[]) if ep.get("id")==args.episodio),None)
        if data is None:raise ValueError("Episódio não encontrado")
    plan=scene_plan(data,duration=args.duracao)
    ep_id=data.get("id","episodio")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",ep_id):
        raise ValueError("ID de episódio inválido")
    output=args.saida or ROOT/"assets"/"gerados"/"planos-visuais"/f"{ep_id}-cenas.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"[OK] {plan['total_cenas']} cenas propostas a partir do roteiro: {output}")
    for s in plan["cenas"]:
        print(f"  {s['id']}: {s['inicio_estimado_s']:.1f}–{s['fim_estimado_s']:.1f}s | {s['papel']} | {s['trecho_roteiro'][:95]}")
    print("[QA] Reveja os cortes e os prompts. Sem chamadas de IA ou upload.")
    return 0


if __name__=="__main__":
    try:raise SystemExit(main())
    except (ValueError,OSError,KeyError) as exc:
        import sys
        print("[ERRO] "+str(exc),file=sys.stderr)
        raise SystemExit(1)
