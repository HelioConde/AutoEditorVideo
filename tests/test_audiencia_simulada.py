"""Testes isolados: nenhuma API, segredo, imagem ou upload e necessario."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audiencia_simulada import DEFAULT_IDS, evaluate_manifest, inspect_episode, main, PERSONAS, summarize_markdown


def fake_episode(episode_id: str, hook: str = "E se a masmorra fosse uma cozinha?") -> dict:
    scenes = []
    for i in range(8):
        scenes.append({
            "number": i + 1,
            "editorial_beat": (
                f"E se a masmorra fosse uma cozinha? A cena {i + 1} acrescenta "
                "informacoes novas sobre energia, viagem e escolhas do grupo. "
                "Cada descoberta tem um efeito para a aventura e seus personagens."
            ) if i == 0 else (
                f"No momento {i + 1}, os personagens precisam compreender recursos "
                "diferentes. Existe um desafio pratico que modifica as escolhas "
                "e prepara uma consequencia para o final."
            ),
        })
    scenes[-1]["editorial_beat"] = (
        "Por isso, entender como os recursos mudam a jornada produz um "
        "desfecho coerente com a promessa inicial e a aventura termina."
    )
    return {
        "id": episode_id,
        "channel": "br",
        "title": "Dungeon Meshi: o que muda na masmorra?",
        "hook": hook,
        "cover_text": "COMIDA E ESTRATEGIA",
        "tags": ["anime", "Dungeon Meshi"],
        "scenes": scenes,
        "narration_script": " ".join(s["editorial_beat"] for s in scenes),
    }


class AudienceLabTests(unittest.TestCase):
    def test_persona_weights_sum_to_one(self):
        for persona, weights in PERSONAS.items():
            self.assertAlmostEqual(sum(weights.values()), 1.0, msg=persona)

    def test_three_episodes_and_no_forecast(self):
        manifest = {"episodes": [fake_episode(x) for x in DEFAULT_IDS]}
        report = evaluate_manifest(manifest, DEFAULT_IDS)
        self.assertEqual(report["analyzed_count"], 3)
        self.assertIn("nao preveem", report["disclaimer"])
        self.assertNotIn("predicted_views", report)
        for item in report["results"]:
            self.assertGreaterEqual(item["editorial_index_0_to_100"], 0)
            self.assertLessEqual(item["editorial_index_0_to_100"], 100)
            self.assertEqual(len(item["opening_experiments_for_human_review"]), 3)
            self.assertNotIn("narration_script", item)

    def test_hook_registered_but_not_narrated_is_flagged(self):
        row = fake_episode(DEFAULT_IDS[0], "Algo totalmente diferente da narracao!")
        item = inspect_episode(row)
        codes = {warning["code"] for warning in item["warnings"]}
        self.assertIn("GANCHO_DIFERENTE_DA_ABERTURA", codes)
        self.assertEqual(item["hook_lexical_alignment"], "revisar_abertura")
        self.assertFalse(item["hook_cadastrado_presente_na_abertura"])

    def test_reformulated_hook_is_not_called_missing(self):
        row = fake_episode(
            DEFAULT_IDS[0],
            "Uma Expansao de Dominio altera a luta e suas regras",
        )
        row["scenes"][0]["editorial_beat"] = (
            "Um Dominio altera as regras de uma luta e muda a estrategia. "
            "A tecnica importa porque as escolhas tambem se transformam."
        )
        row["narration_script"] = " ".join(
            scene["editorial_beat"] for scene in row["scenes"]
        )
        result = inspect_episode(row)
        codes = {item["code"] for item in result["warnings"]}
        self.assertEqual(result["hook_lexical_alignment"], "vocabulario_relacionado")
        self.assertIn("GANCHO_REFORMULADO", codes)
        self.assertNotIn("GANCHO_DIFERENTE_DA_ABERTURA", codes)
        self.assertFalse(result["hook_cadastrado_presente_na_abertura"])

    def test_markdown_report_does_not_claim_predictions(self):
        data = evaluate_manifest(
            {"episodes": [fake_episode(x) for x in DEFAULT_IDS]}, DEFAULT_IDS,
        )
        markdown = summarize_markdown(data)
        self.assertIn("Piloto BR", markdown)
        self.assertIn("nao preveem visualizacoes", markdown)
        self.assertIn("Nenhuma alteracao automatica", markdown)

    def test_duplicate_or_wrong_channel_rejected(self):
        episode = fake_episode(DEFAULT_IDS[0])
        with self.assertRaises(ValueError):
            evaluate_manifest({"episodes": [episode, episode]}, (DEFAULT_IDS[0],))
        with self.assertRaises(ValueError):
            evaluate_manifest({"episodes": [episode]}, (DEFAULT_IDS[0],), "en")
        with self.assertRaises(ValueError):
            evaluate_manifest({"episodes": [episode]}, (DEFAULT_IDS[0], DEFAULT_IDS[0]))

    def test_cli_generates_json_without_external_services(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            manifest = base / "input.json"
            output = base / "report.json"
            markdown = base / "report.md"
            manifest.write_text(json.dumps(
                {"episodes": [fake_episode(x) for x in DEFAULT_IDS]},
                ensure_ascii=False), encoding="utf-8")
            self.assertEqual(main([
                "--manifest", str(manifest),
                "--output", str(output),
                "--markdown-output", str(markdown),
            ]), 0)
            self.assertTrue(markdown.is_file())
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["analyzed_count"], 3)
            self.assertEqual(result["method"], "offline-deterministic-editorial-proxies")


if __name__ == "__main__":
    unittest.main()
