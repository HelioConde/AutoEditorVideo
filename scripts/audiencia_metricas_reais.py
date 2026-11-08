#!/usr/bin/env python3
"""Compara rubricas editoriais a metricas reais exportadas, sem APIs.

Fontes: relatorio JSON do piloto + mapa explicito episodio/video + CSV
de metricas agregadas para os 7 DIAS DE CALENDARIO desde a publicacao.
Nao publica, nao busca dados na rede e nao trata associacao como previsao.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, timedelta, timezone, datetime
import json
import math
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]
BR_CHANNEL_ID = "UCXGYTuBYn-0Ziqin5ajKhOw"
VIDEO_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAPPING_COLUMNS = {"episode_id", "video_id", "channel_id", "published_on"}
METRIC_COLUMNS = {
    "video_id", "window_start", "window_end", "captured_on",
    "views", "engaged_views", "average_view_percentage",
}
MIN_ASSOCIATION_SAMPLE = 8


class MetricsError(ValueError):
    """CSV invalid or unsafe to compare."""


def parse_day(raw: str, field: str) -> date:
    if not DAY_RE.fullmatch(str(raw)):
        raise MetricsError(f"{field}: expected YYYY-MM-DD")
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise MetricsError(f"{field}: invalid date") from exc


def parse_nonnegative_int(raw: str, field: str) -> int:
    if not re.fullmatch(r"\d+", str(raw)):
        raise MetricsError(f"{field}: expected non-negative integer")
    return int(raw)


def parse_percentage(raw: str) -> float:
    try:
        value = float(raw)
    except (ValueError, TypeError) as exc:
        raise MetricsError("average_view_percentage: invalid value") from exc
    # Looping Shorts can legitimately exceed 100% average viewed.
    if not math.isfinite(value) or not 0 <= value <= 1000:
        raise MetricsError("average_view_percentage: expected between 0 and 1000")
    return round(value, 3)


def load_csv(path: Path, required: set[str]) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required.issubset(fields):
            raise MetricsError(f"{path.name}: absent/duplicated required CSV columns")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise MetricsError(f"{path.name}: malformed CSV row")
    return rows


def rank(values: list[float]) -> list[float]:
    # Ranks with average rank for ties; no scipy dependency.
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        middle = (start + 1 + end) / 2
        for pos in order[start:end]:
            out[pos] = middle
        start = end
    return out


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) != len(y) or len(x) < 2:
        return None
    a, b = rank(x), rank(y)
    mean_a, mean_b = statistics.mean(a), statistics.mean(b)
    num = sum((i - mean_a) * (j - mean_b) for i, j in zip(a, b))
    den = math.sqrt(sum((i - mean_a) ** 2 for i in a)
                    * sum((j - mean_b) ** 2 for j in b))
    return round(num / den, 4) if den else None


def compare(
    editorial_report: dict,
    mapping_rows: list[dict],
    metric_rows: list[dict],
    *,
    channel_id: str = BR_CHANNEL_ID,
    as_of: date | None = None,
) -> dict:
    today = as_of or date.today()
    episodes = editorial_report.get("results", [])
    if editorial_report.get("schema") != "autoeditorvideo/audience-lab-pilot/v1":
        raise MetricsError("Editorial report schema unsupported")
    if editorial_report.get("channel") != "br" or channel_id != BR_CHANNEL_ID:
        raise MetricsError("Pilot only permits Otaku Multicena BR at this stage")
    if not isinstance(episodes, list) or not episodes:
        raise MetricsError("Editorial report has no episodes")

    editorial = {}
    for item in episodes:
        eid = item.get("id")
        score = item.get("editorial_index_0_to_100")
        if not eid or eid in editorial or isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
            raise MetricsError("Duplicate ID or invalid editorial index")
        editorial[eid] = item

    maps = {}
    video_ids = set()
    for row in mapping_rows:
        episode_id = row.get("episode_id", "").strip()
        video_id = row.get("video_id", "").strip()
        if episode_id not in editorial:
            raise MetricsError("Mapping references unknown episode")
        if episode_id in maps or video_id in video_ids:
            raise MetricsError("Duplicated episode/video in mapping")
        if row.get("channel_id", "").strip() != channel_id or not VIDEO_RE.fullmatch(video_id):
            raise MetricsError("Invalid video ID or different channel")
        published = parse_day(row.get("published_on", "").strip(), "published_on")
        maps[episode_id] = {"video_id": video_id, "published_on": published}
        video_ids.add(video_id)

    metrics = {}
    for row in metric_rows:
        video_id = row.get("video_id", "").strip()
        if video_id not in video_ids or video_id in metrics:
            raise MetricsError("Metric video not mapped or duplicated")
        start = parse_day(row.get("window_start", "").strip(), "window_start")
        end = parse_day(row.get("window_end", "").strip(), "window_end")
        captured = parse_day(row.get("captured_on", "").strip(), "captured_on")
        views = parse_nonnegative_int(row.get("views", "").strip(), "views")
        engaged = parse_nonnegative_int(row.get("engaged_views", "").strip(), "engaged_views")
        percent = parse_percentage(row.get("average_view_percentage", "").strip())
        if engaged > views:
            raise MetricsError("engaged_views greater than views; check definitions/window")
        if end != start + timedelta(days=6):
            raise MetricsError("Only fixed seven-calendar-day windows accepted")
        if captured > today:
            raise MetricsError("captured_on cannot be after as_of")
        metrics[video_id] = {
            "window_start": start, "window_end": end, "captured_on": captured,
            "views": views, "engaged_views": engaged,
            "average_view_percentage": percent,
        }

    out = []
    eligible = []
    for episode_id, item in editorial.items():
        entry = {
            "episode_id": episode_id,
            "title": item.get("title", ""),
            "editorial_index": item["editorial_index_0_to_100"],
            "status": "sem_mapeamento",
        }
        mapping = maps.get(episode_id)
        if mapping is not None:
            published = mapping["published_on"]
            video_id = mapping["video_id"]
            entry.update({"video_id": video_id, "published_on": published.isoformat()})
            metric = metrics.get(video_id)
            if published > today:
                entry["status"] = "publicacao_no_futuro"
            elif metric is None:
                entry["status"] = "aguardando_metrica"
            elif metric["window_start"] != published:
                raise MetricsError("Window start does not match video publication date")
            elif metric["captured_on"] <= metric["window_end"] or today <= metric["window_end"]:
                entry["status"] = "janela_ainda_nao_completa"
            else:
                entry["status"] = "apto_comparacao"
                entry["metricas_7_dias"] = {
                    "views": metric["views"],
                    "engaged_views": metric["engaged_views"],
                    "average_view_percentage": metric["average_view_percentage"],
                }
                eligible.append(entry)
        out.append(entry)

    assoc = None
    # Spearman is descriptive only, never significance, prediction or causation.
    if (len(eligible) >= MIN_ASSOCIATION_SAMPLE
            and len({r["editorial_index"] for r in eligible}) >= 4
            and len({r["metricas_7_dias"]["engaged_views"] for r in eligible}) >= 4):
        assoc = spearman(
            [float(r["editorial_index"]) for r in eligible],
            [float(r["metricas_7_dias"]["engaged_views"]) for r in eligible],
        )
    result = {
        "schema": "autoeditorvideo/audience-metrics-comparison/v1",
        "method": "offline-explicit-video-map-seven-calendar-days",
        "data_provenance": "manually_supplied_csv_not_verified_against_youtube",
        "as_of": today.isoformat(),
        "channel_id": channel_id,
        "window_definition": "7 calendar days starting on the local publish date, inclusive",
        "editorial_samples": len(out),
        "mature_matched_samples": len(eligible),
        "required_samples_for_association": MIN_ASSOCIATION_SAMPLE,
        "spearman_editorial_vs_engaged_views": assoc,
        "association_note": (
            "Descriptive rank association only; no causal inference or predictions."
            if assoc is not None else
            "Insufficient mature data or variation: do not estimate an association."
        ),
        "records": out,
    }
    return result


def markdown(result: dict) -> str:
    lines = [
        "# Laboratorio de Audiencia — metricas reais", "",
        "**Dados importados manualmente, nao verificados na API.** "
        "Notas editoriais nao sao previsoes de views.", "",
        f"Janela: {result['window_definition']}. "
        f"Data de referencia: {result['as_of']}.", "",
        "| Episodio | Indice | Situação | Engaged views (7 dias) |",
        "|---|---:|---|---:|",
    ]
    for record in result["records"]:
        title = str(record["title"]).replace("|", "/").replace("\n", " ")
        views = record.get("metricas_7_dias", {}).get("engaged_views", "—")
        lines.append(
            f"| {title} | {record['editorial_index']}/100 | "
            f"{record['status']} | {views} |"
        )
    lines += [
        "",
        f"Amostras maduras: {result['mature_matched_samples']} / "
        f"{result['editorial_samples']}.",
        f"Associacao de ranking: {result['spearman_editorial_vs_engaged_views']}",
        result["association_note"], "",
        "A analise nao modifica roteiros, publicacao nem privacidade dos videos.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--editorial-report", type=Path,
        default=ROOT / "reports" / "audiencia-simulada-br-piloto.json",
    )
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "dados-privados" / "audiencia" / "comparacao.json",
    )
    parser.add_argument("--markdown-output", type=Path, default=None)
    args = parser.parse_args(argv)
    if bool(args.mapping) != bool(args.metrics):
        parser.error("Pass --mapping and --metrics together, or neither")
    editor = json.loads(args.editorial_report.read_text(encoding="utf-8"))
    mapping_rows = load_csv(args.mapping, MAPPING_COLUMNS) if args.mapping else []
    metrics_rows = load_csv(args.metrics, METRIC_COLUMNS) if args.metrics else []
    report = compare(editor, mapping_rows, metrics_rows, as_of=parse_day(args.as_of, "as_of"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown(report), encoding="utf-8")
    print("[AUDIENCIA METRICAS] "
          f"{report['mature_matched_samples']}/{report['editorial_samples']} "
          "episodios com 7 dias validos. Nenhum upload/API/secret.")
    print("[RELATORIO PRIVADO] " + str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
