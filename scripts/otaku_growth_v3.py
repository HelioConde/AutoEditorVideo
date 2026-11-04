#!/usr/bin/env python3
"""Otaku Multicena 3.0: auditoria editorial e comparacao de metricas offline.

Sem acesso a redes sociais, APIs, proxy, imagem, TTS ou publicacao.
Uma auditoria automatica nunca substitui revisao factual, visual ou juridica.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOGS = (
    ROOT / "conteudos" / "otaku-multicena-grade-50-a.json",
    ROOT / "conteudos" / "otaku-multicena-grade-50-b.json",
)
GENERIC_OPENINGS = (
    "hoje vamos falar", "fala galera", "sejam bem-vindos",
    "bem-vindos ao canal", "no video de hoje",
)
MANUAL_GATES = (
    "fidelidade aos fatos e contexto do anime",
    "movimento real de personagens quando a narrativa exige",
    "audio e pronuncia, timing das legendas e MP4 final",
    "licencas de musica, imagens, personagens e divulgacao de IA",
)
WINDOWS_HOURS = (1, 6, 24, 72, 168)


def _words(value: str) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ]+\b", value.casefold())


def _issue(code: str, severity: str, message: str) -> dict:
    return {"code": code, "severity": severity, "message": message}


def audit_episode(episode: dict) -> dict:
    """Verifica invariantes objetivos; nao inventa score de viralizacao."""
    video_id = str(episode.get("id", "")).strip()
    series = str(episode.get("series", "")).strip()
    hook = str(episode.get("hook", "")).strip()
    script = str(episode.get("script", "")).strip()
    cta = str(episode.get("cta", "")).strip()
    title = str(episode.get("title", "")).strip()
    description = str(episode.get("description_youtube", "")).strip()
    issues = []

    if not video_id or not series:
        issues.append(_issue("topic_missing", "blocking", "ID e anime sao obrigatorios."))
    if not hook:
        issues.append(_issue("hook_missing", "blocking", "Gancho de abertura ausente."))
    elif len(_words(hook)) > 18:
        issues.append(_issue("hook_long", "advisory", "Gancho com mais de 18 palavras; revisar a abertura."))
    if any(hook.casefold().startswith(opening) for opening in GENERIC_OPENINGS):
        issues.append(_issue("generic_hook", "advisory", "Abertura generica, sem conflito ou curiosidade."))
    if not script:
        issues.append(_issue("script_missing", "blocking", "Roteiro ausente."))
    elif hook and not script.casefold().startswith(hook.casefold()):
        issues.append(_issue("hook_mismatch", "blocking", "A narracao nao comeca pelo gancho aprovado."))
    if script and not 35 <= len(_words(script)) <= 155:
        issues.append(_issue("script_length", "advisory", "Revisar duracao pela voz real; palavras fora da faixa exploratoria."))
    if cta and script and not script.endswith(cta):
        issues.append(_issue("cta_mismatch", "blocking", "CTA declarado nao corresponde ao final do roteiro."))
    if "otaku multicena" in script.casefold():
        issues.append(_issue("spoken_brand", "advisory", "Evitar narrar o nome da marca no CTA."))
    if not title or len(title) > 100:
        issues.append(_issue("title_invalid", "blocking", "Titulo ausente ou superior a 100 caracteres."))
    if not description:
        issues.append(_issue("description_missing", "blocking", "Descricao do video ausente."))
    elif "#otakumulticena" not in description.casefold():
        issues.append(_issue("brand_missing", "advisory", "Descricao nao identifica a marca atual."))
    if "arquivo otaku" in (title + " " + description).casefold():
        issues.append(_issue("old_brand", "blocking", "Referencia a marca antiga nos metadados."))

    return {
        "id": video_id,
        "series": series,
        "hook": hook,
        "hook_words": len(_words(hook)),
        "script_words": len(_words(script)),
        "issues": issues,
        "blocking": sum(i["severity"] == "blocking" for i in issues),
        "manual_review_required": list(MANUAL_GATES),
    }


def audit_batch(episodes: list[dict]) -> dict:
    """Detecta repeticoes sem reprovar automaticamente assuntos parecidos."""
    results = [audit_episode(ep) for ep in episodes]
    seen_hooks: dict[str, str] = {}
    for result in results:
        norm = " ".join(_words(result["hook"]))
        if norm and norm in seen_hooks:
            result["issues"].append(_issue("hook_duplicate", "advisory", "Gancho repetido de " + seen_hooks[norm]))
        else:
            seen_hooks[norm] = result["id"]

    for idx, left in enumerate(episodes):
        left_script = str(left.get("script", ""))
        left_cta = str(left.get("cta", ""))
        if left_cta and left_script.endswith(left_cta):
            left_script = left_script[:-len(left_cta)]
        for jdx in range(idx + 1, len(episodes)):
            right = episodes[jdx]
            right_script = str(right.get("script", ""))
            right_cta = str(right.get("cta", ""))
            if right_cta and right_script.endswith(right_cta):
                right_script = right_script[:-len(right_cta)]
            if len(left_script) > 80 and len(right_script) > 80:
                similarity = SequenceMatcher(None, " ".join(_words(left_script)), " ".join(_words(right_script))).ratio()
                if similarity >= 0.88:
                    results[jdx]["issues"].append(_issue(
                        "similar_script", "advisory",
                        "Narrativa muito semelhante a " + results[idx]["id"],
                    ))
    descriptions = Counter(
        re.sub(r"\s+", " ", str(ep.get("description_youtube", "")).casefold()).strip()[:60]
        for ep in episodes
    )
    for ep, result in zip(episodes, results):
        description = re.sub(r"\s+", " ", str(ep.get("description_youtube", "")).casefold()).strip()
        if description and descriptions[description[:60]] >= 3:
            result["issues"].append(_issue(
                "template_description", "advisory",
                "Inicio da descricao repetido em tres ou mais videos; personalizar.",
            ))
    for result in results:
        result["blocking"] = sum(i["severity"] == "blocking" for i in result["issues"])
    return {
        "schema": "otaku-multicena/editorial-audit/v3",
        "episodes": results,
        "summary": {
            "episodes": len(results),
            "blocking_issues": sum(r["blocking"] for r in results),
            "advisories": sum(
                i["severity"] == "advisory" for r in results for i in r["issues"]
            ),
            "human_review_pending": len(results),
        },
    }


def _age_hours(snapshot: dict) -> float | None:
    age = snapshot.get("age_hours")
    if age is not None:
        if isinstance(age, bool) or not isinstance(age, (int, float)) or age < 0:
            raise ValueError("age_hours deve ser numero nao negativo")
        return float(age)
    published, collected = snapshot.get("published_at"), snapshot.get("collected_at")
    if not published or not collected:
        return None
    start = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
    end = datetime.fromisoformat(str(collected).replace("Z", "+00:00"))
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Datas de metricas precisam conter fuso horario")
    hours = (end - start).total_seconds() / 3600
    if hours < 0:
        raise ValueError("Coleta anterior a publicacao")
    return hours


def compare_metrics(snapshots: list[dict]) -> dict:
    """Comparacoes por mesma idade; ausencia de valor nunca equivale a zero."""
    by_video: dict[tuple[str, str], list[tuple[float, dict]]] = {}
    for item in snapshots:
        platform = str(item.get("platform", "")).strip().lower()
        video = str(item.get("video_id", "")).strip()
        if not platform or not video:
            raise ValueError("platform e video_id sao obrigatorios")
        views = item.get("views")
        if views is not None and (isinstance(views, bool) or
                                  not isinstance(views, int) or views < 0):
            raise ValueError("views deve ser inteiro nao negativo ou null")
        age = _age_hours(item)
        if age is not None:
            by_video.setdefault((platform, video), []).append((age, item))
    rows = []
    for (platform, video), samples in sorted(by_video.items()):
        result = {"platform": platform, "video_id": video, "windows": {}}
        for target in WINDOWS_HOURS:
            tolerance = max(0.5, target * 0.25)
            candidates = [(abs(age - target), item, age) for age, item in samples
                          if abs(age - target) <= tolerance]
            if not candidates:
                result["windows"][str(target)] = None
                continue
            _, item, age = min(candidates, key=lambda x: x[0])
            result["windows"][str(target)] = {
                "age_hours": round(age, 3), "views": item.get("views"),
                "engaged_views": item.get("engaged_views"),
                "shown_in_feed": item.get("shown_in_feed"),
                "average_view_percentage": item.get("average_view_percentage"),
            }
        rows.append(result)
    return {"schema": "otaku-multicena/age-aligned-metrics/v3", "videos": rows}


def read_catalogs(paths: list[Path]) -> list[dict]:
    episodes: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict) or not isinstance(payload.get("episodes"), list):
            raise ValueError("Catalogo invalido: " + str(path))
        episodes.extend(payload["episodes"])
    return episodes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria offline Otaku Multicena 3.0")
    parser.add_argument("--catalog", action="append", type=Path, default=None)
    parser.add_argument("--id", action="append", default=None, help="Auditar apenas estes IDs")
    parser.add_argument("--metricas", type=Path, help="Arquivo JSON com snapshots, sem APIs")
    parser.add_argument("--saida", type=Path, help="Gravar relatorio JSON offline")
    parser.add_argument("--estrito", action="store_true", help="Falhar apenas com bloqueios objetivos")
    args = parser.parse_args(argv)
    episodes = read_catalogs(args.catalog or list(DEFAULT_CATALOGS))
    if args.id:
        episodes = [ep for ep in episodes if ep.get("id") in args.id]
        found = {ep.get("id") for ep in episodes}
        if found != set(args.id):
            parser.error("ID nao encontrado: " + ", ".join(sorted(set(args.id) - found)))
    report = audit_batch(episodes)
    if args.metricas:
        raw = json.loads(args.metricas.read_text(encoding="utf-8-sig"))
        if not isinstance(raw, list):
            parser.error("--metricas espera lista JSON de snapshots")
        report["metrics"] = compare_metrics(raw)
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(serialized, encoding="utf-8")
        print("[AUDITORIA] Relatorio salvo em " + str(args.saida))
    else:
        print(serialized)
    return 2 if args.estrito and report["summary"]["blocking_issues"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("[BLOQUEADO] " + str(error), file=sys.stderr)
        raise SystemExit(1)
