"""Metric reconciliation tests: fixtures are synthetic, not user Analytics."""
from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audiencia_metricas_reais import (
    BR_CHANNEL_ID, MetricsError, compare, load_csv, markdown, main,
    parse_percentage, spearman,
)


def report(size: int = 3) -> dict:
    return {
        "schema": "autoeditorvideo/audience-lab-pilot/v1",
        "channel": "br",
        "results": [
            {
                "id": f"test-episode-{index}",
                "title": f"Episode {index}",
                "editorial_index_0_to_100": 50 + index * 3,
            } for index in range(size)
        ],
    }


def input_data(size: int = 3, *, published_on: str = "2026-10-01",
               captured_on: str = "2026-10-09") -> tuple[list[dict], list[dict]]:
    mapping, metrics = [], []
    for index in range(size):
        vid = f"{index:011d}"
        mapping.append({
            "episode_id": f"test-episode-{index}",
            "video_id": vid,
            "channel_id": BR_CHANNEL_ID,
            "published_on": published_on,
        })
        metrics.append({
            "video_id": vid,
            "window_start": published_on,
            "window_end": "2026-10-07",
            "captured_on": captured_on,
            "views": str(100 + index * 30),
            "engaged_views": str(80 + index * 20),
            "average_view_percentage": "126.5",  # Shorts may loop.
        })
    return mapping, metrics


def make_csv(path: Path, rows: list[dict]) -> None:
    import csv
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


class MetricsTests(unittest.TestCase):
    def test_missing_real_data_does_not_fabricate_comparison(self):
        result = compare(report(), [], [], as_of=date(2026, 11, 8))
        self.assertEqual(result["mature_matched_samples"], 0)
        self.assertIsNone(result["spearman_editorial_vs_engaged_views"])
        self.assertTrue(all(x["status"] == "sem_mapeamento" for x in result["records"]))
        self.assertIn("nao sao previsoes", markdown(result))

    def test_three_mature_videos_still_not_enough_for_association(self):
        mapping, rows = input_data()
        result = compare(report(), mapping, rows, as_of=date(2026, 11, 8))
        self.assertEqual(result["mature_matched_samples"], 3)
        self.assertTrue(all(x["status"] == "apto_comparacao" for x in result["records"]))
        self.assertEqual(result["records"][0]["metricas_7_dias"]["average_view_percentage"], 126.5)
        self.assertIsNone(result["spearman_editorial_vs_engaged_views"])
        self.assertIn("Insufficient mature data", result["association_note"])

    def test_eight_mature_videos_allow_descriptive_rank_association(self):
        mapping, rows = input_data(8)
        result = compare(report(8), mapping, rows, as_of=date(2026, 11, 8))
        self.assertEqual(result["mature_matched_samples"], 8)
        self.assertEqual(result["spearman_editorial_vs_engaged_views"], 1.0)
        self.assertIn("no causal inference", result["association_note"])

    def test_premature_window_is_excluded(self):
        mapping, rows = input_data(
            published_on="2026-11-03", captured_on="2026-11-08",
        )
        for row in rows:
            row["window_end"] = "2026-11-09"
        result = compare(report(), mapping, rows, as_of=date(2026, 11, 8))
        self.assertEqual(result["mature_matched_samples"], 0)
        self.assertEqual(result["records"][0]["status"], "janela_ainda_nao_completa")

    def test_channel_and_duplicate_guards(self):
        mapping, rows = input_data()
        mapping[0]["channel_id"] = "UCdifferentchannel1111111"
        with self.assertRaises(MetricsError):
            compare(report(), mapping, rows, as_of=date(2026, 11, 8))
        mapping, rows = input_data()
        mapping[1]["video_id"] = mapping[0]["video_id"]
        with self.assertRaises(MetricsError):
            compare(report(), mapping, rows, as_of=date(2026, 11, 8))

    def test_invalid_windows_and_engaged_views_block(self):
        mapping, rows = input_data()
        rows[0]["window_end"] = "2026-10-08"
        with self.assertRaises(MetricsError):
            compare(report(), mapping, rows, as_of=date(2026, 11, 8))
        mapping, rows = input_data()
        rows[0]["engaged_views"] = "9999"
        with self.assertRaises(MetricsError):
            compare(report(), mapping, rows, as_of=date(2026, 11, 8))
        mapping, rows = input_data()
        rows[0]["captured_on"] = "2026-12-30"
        with self.assertRaises(MetricsError):
            compare(report(), mapping, rows, as_of=date(2026, 11, 8))

    def test_percentage_validation_and_ties(self):
        self.assertEqual(parse_percentage("125.3"), 125.3)
        self.assertIsNone(spearman([1, 1, 1], [2, 3, 4]))
        with self.assertRaises(MetricsError):
            parse_percentage("nan")
        with self.assertRaises(MetricsError):
            parse_percentage("-1")

    def test_cli_never_requires_external_auth(self):
        mapping, rows = input_data()
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            editorial = base / "editorial.json"
            mapping_file, metrics_file = base / "mapping.csv", base / "metricas.csv"
            output, md = base / "comparison.json", base / "comparison.md"
            editorial.write_text(json.dumps(report()), encoding="utf-8")
            make_csv(mapping_file, mapping)
            make_csv(metrics_file, rows)
            self.assertEqual(main([
                "--editorial-report", str(editorial),
                "--mapping", str(mapping_file),
                "--metrics", str(metrics_file),
                "--output", str(output),
                "--markdown-output", str(md),
                "--as-of", "2026-11-08",
            ]), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["mature_matched_samples"], 3)
            self.assertIn("manual", result["data_provenance"])
            self.assertIn("Episode", md.read_text(encoding="utf-8"))

    def test_csv_header_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.csv"
            path.write_text("video_id,views\nabcdefghijk,99\n", encoding="utf-8")
            with self.assertRaises(MetricsError):
                load_csv(path, {"video_id", "window_start"})


if __name__ == "__main__":
    unittest.main()
