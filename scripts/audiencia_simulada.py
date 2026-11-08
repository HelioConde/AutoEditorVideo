#!/usr/bin/env python3
"""Laboratorio editorial offline, inspirado em avaliacao multiagente.

Nao e o motor MiroFish nem uma simulacao real de espectadores. Os perfis sao
heuristicas deterministicas e NAO preveem views, CTR ou retencao. Somente le
um manifesto, avalia roteiros existentes e grava um relatorio local.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "conteudos" / "lote-15-canais-20261108.json"
DEFAULT_IDS = (
    "5015-jujutsu-kaisen-dominio",
    "5016-dungeon-meshi-masmorra",
    "5017-attack-on-titan-muralhas",
)
STOPWORDS = {
    "para", "por", "porque", "como", "quando", "onde", "dos", "das", "uma",
    "uns", "com", "sem", "que", "the", "and", "why", "what", "about",
    "not", "isso", "essa", "esse", "este", "sobre", "muda", "muito",
}
# Pesos somam 1.0 e refletem prioridades editoriais, NAO pessoas reais.
PERSONAS = {
    "curioso_iniciante": {
        "hook": .30, "clareza": .29, "ritmo": .15,
        "estrutura": .12, "desfecho": .09, "metadados": .05,
    },
    "fa_de_anime": {
        "hook": .17, "clareza": .14, "ritmo": .13,
        "estrutura": .28, "desfecho": .23, "metadados": .05,
    },
    "espectador_mobile": {
        "hook": .34, "clareza": .22, "ritmo": .26,
        "estrutura": .08, "desfecho": .05, "metadados": .05,
    },
    "revisor_critico": {
        "hook": .11, "clareza": .24, "ritmo": .12,
        "estrutura": .28, "desfecho": .20, "metadados": .05,
    },
    "espectador_recorrente": {
        "hook": .18, "clareza": .17, "ritmo": .14,
        "estrutura": .16, "desfecho": .30, "metadados": .05,
    },
}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).lower())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def words(text: str) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ]+(?:['’-][\wÀ-ÿ]+)*\b", text, re.UNICODE)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def first_sentence(text: str) -> str:
    return (sentences(text) or [""])[0]


def relevant_tokens(text: str) -> set[str]:
    return {x for x in normalize(text).split() if len(x) >= 4 and x not in STOPWORDS}


def inspect_episode(row: dict) -> dict:
    """Avalia indicadores editáveis e retorna observacoes verificaveis."""
    episode_id = row.get("id")
    title = str(row.get("title", "")).strip()
    scenes = row.get("scenes", [])
    script = str(row.get("narration_script", "")).strip()
    if not episode_id or not title or not script or not isinstance(scenes, list) or not scenes:
        raise ValueError("Roteiro sem id/titulo/narracao/cenas")
    beats = [str(scene.get("editorial_beat", "")).strip() for scene in scenes]
    if any(not beat for beat in beats):
        raise ValueError(f"Cena sem narracao em {episode_id}")

    declared_hook = str(row.get("hook", "")).strip()
    first_beat = beats[0]
    last_beat = beats[-1]
    first = first_sentence(script)
    last = sentences(last_beat)[-1] if sentences(last_beat) else last_beat
    narration_words = words(script)
    lengths = [len(words(s)) for s in sentences(script)]
    beat_counts = [len(words(b)) for b in beats]
    avg_sentence = statistics.mean(lengths) if lengths else 0
    max_sentence = max(lengths, default=0)
    opening = normalize(script[:360])
    hook_in_audio = bool(declared_hook and normalize(declared_hook) in opening)
    title_tokens = relevant_tokens(title)
    script_tokens = relevant_tokens(script[:450])
    title_overlap = len(title_tokens & script_tokens)

    hook = clamp(
        53 + (19 if hook_in_audio else (-16 if declared_hook else 0))
        + (10 if 20 <= len(declared_hook or first) <= 130 else -8)
        + (8 if "?" in (declared_hook or first) else 0)
        + (8 if re.search(r"\b(n[aã]o|mas|e se|por que|why|but)\b",
                          (declared_hook or first).lower()) else 0)
        + (5 if title_overlap else 0)
        - (15 if normalize(first).startswith(("hoje vamos", "neste video")) else 0)
    )
    clareza = clamp(
        65 + (15 if 0 < avg_sentence <= 22 else (5 if avg_sentence <= 29 else -15))
        + (10 if max_sentence <= 35 else -14)
        - (10 if max_sentence > 48 else 0)
    )
    imbalance = (statistics.pstdev(beat_counts) / statistics.mean(beat_counts)
                 if statistics.mean(beat_counts) else 1)
    ritmo = clamp(
        50 + (15 if 6 <= len(beats) <= 12 else -12)
        + (15 if 240 <= len(narration_words) <= 360 else -12)
        + (10 if 22 <= statistics.mean(beat_counts) <= 48 else -5)
        + (10 if imbalance <= .45 else -8)
    )
    # Sinal simples de repeticao; nao prova causalidade nem continuidade.
    overlap = []
    for a, b in zip(beats, beats[1:]):
        sa, sb = relevant_tokens(a), relevant_tokens(b)
        overlap.append(len(sa & sb) / max(1, len(sa | sb)))
    duplicate_beats = sum(similarity > .70 for similarity in overlap)
    estrutura = clamp(
        62 + (14 if 6 <= len(beats) <= 12 else -14)
        + (12 if title_overlap else -12)
        + (12 if not duplicate_beats else -18)
    )
    payoff_signal = bool(re.search(
        r"\b(por isso|no fim|a grande ideia|assim|consequ[eê]ncia|"
        r"portanto|afinal|em resumo)\b", last_beat.lower()
    ))
    generic_cta = bool(re.search(
        r"\b(inscreva.se|deixe seu like|curta o video|subscribe)\b",
        normalize(last_beat),
    ))
    desfecho = clamp(
        56 + (22 if payoff_signal else -7)
        + (12 if len(words(last_beat)) >= 25 else -8)
        - (25 if generic_cta else 0)
    )
    cover = str(row.get("cover_text", "")).strip()
    tags = row.get("tags", [])
    tags_ok = isinstance(tags, list) and bool(tags) and len(",".join(map(str, tags))) <= 500
    metadados = clamp(
        45 + (18 if 24 <= len(title) <= 100 else -12)
        + (18 if 8 <= len(cover) <= 42 else -12)
        + (18 if tags_ok else -18)
    )
    dimensions = {
        "hook": hook, "clareza": clareza, "ritmo": ritmo,
        "estrutura": estrutura, "desfecho": desfecho, "metadados": metadados,
    }
    personas = {
        name: clamp(sum(dimensions[key] * weight for key, weight in weights.items()))
        for name, weights in PERSONAS.items()
    }
    warnings = []
    if declared_hook and not hook_in_audio:
        warnings.append({
            "code": "HOOK_CADASTRADO_NAO_NARRADO",
            "action": "Conferir se o gancho cadastrado deve abrir a narracao; revisar manualmente a transicao.",
        })
    if avg_sentence > 26 or max_sentence > 35:
        warnings.append({
            "code": "FRASES_LONGAS",
            "action": "Dividir as frases mais longas e comparar o ritmo da narracao em voz alta.",
        })
    if not payoff_signal:
        warnings.append({
            "code": "DESFECHO_SEM_MARCADOR",
            "action": "Rever se o ultimo bloco entrega claramente a promessa da abertura.",
        })
    if duplicate_beats:
        warnings.append({
            "code": "CENAS_PARECIDAS",
            "action": "Verificar se cenas adjacentes acrescentam informacao nova.",
        })
    if not tags_ok:
        warnings.append({
            "code": "TAGS_INVALIDAS",
            "action": "Verificar tags e limite de 500 caracteres.",
        })
    if generic_cta:
        warnings.append({
            "code": "CTA_GENERICO_NO_FINAL",
            "action": "Priorizar o fechamento narrativo em vez de convite generico.",
        })
    if not warnings:
        warnings.append({
            "code": "REVISAR_MANUALMENTE",
            "action": "Revisar coerencia factual, ritmo, naturalidade e conformidade antes de gerar imagens.",
        })

    index = clamp(statistics.mean(personas.values()))
    return {
        "id": episode_id,
        "channel": row.get("channel"),
        "title": title,
        "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "narration_word_count": len(narration_words),
        "scene_count": len(beats),
        "hook_cadastrado_presente_na_abertura": hook_in_audio,
        "indicators_0_to_100": dimensions,
        "heuristic_persona_scores_0_to_100": personas,
        "editorial_index_0_to_100": index,
        "classification": (
            "revisao_humana" if index >= 75 else
            "revisar_pontos_especificos" if index >= 60 else
            "revisar_roteiro"
        ),
        "diagnostics": {
            "avg_words_per_sentence": round(avg_sentence, 2),
            "max_words_in_sentence": max_sentence,
            "adjacent_beat_near_duplicates": duplicate_beats,
        },
        "warnings": warnings,
        "opening_experiments_for_human_review": [
            {"approach": "original_narrado", "text": first},
            {"approach": "gancho_cadastrado", "text": declared_hook or first},
            {
                "approach": "conclusao_antecipada",
                "text": last,
                "note": "Hipotese de remontagem; requer conferir sentido e fatos no roteiro.",
            },
        ],
    }


def evaluate_manifest(manifest: dict, ids: tuple[str, ...], channel: str = "br") -> dict:
    episodes = manifest.get("episodes", [])
    if not isinstance(episodes, list) or not ids or len(set(ids)) != len(ids):
        raise ValueError("Lista de episodios invalida")
    selected = []
    for episode_id in ids:
        matches = [item for item in episodes
                   if item.get("id") == episode_id and item.get("channel") == channel]
        if len(matches) != 1:
            raise ValueError(f"Episodio ausente/duplicado ou canal incorreto: {episode_id}")
        selected.append(inspect_episode(matches[0]))
    return {
        "schema": "autoeditorvideo/audience-lab-pilot/v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "offline-deterministic-editorial-proxies",
        "disclaimer": (
            "Perfis sao rubricas de avaliacao, nao usuarios reais ou agentes "
            "MiroFish. Notas sao heuristicas; nao preveem visualizacoes, "
            "CTR, retencao nem autorizam publicacao."
        ),
        "channel": channel,
        "analyzed_count": len(selected),
        "results": selected,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--ids", nargs="+", default=list(DEFAULT_IDS))
    parser.add_argument("--channel", default="br")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "reports" / "audiencia-simulada-br-piloto.json")
    args = parser.parse_args(argv)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
    report = evaluate_manifest(manifest, tuple(args.ids), args.channel)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"[AUDIENCIA LAB] {len(report['results'])} roteiros avaliados; 0 chamadas IA; 0 uploads")
    for item in report["results"]:
        codes = ",".join(w["code"] for w in item["warnings"])
        print(f"  {item['id']}: indice editorial={item['editorial_index_0_to_100']}/100; {codes}")
    print(f"[RELATORIO] {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
