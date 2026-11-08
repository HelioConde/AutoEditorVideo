"""Testes isolados: nenhuma API, segredo, imagem ou upload e necessario."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audiencia_simulada import DEFAULT_IDS, evaluate_manifest, inspect_episode, main, PERSONAS


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
        self.assertIn("HOOK_CADASTRADO_NAO_NARRADO", codes)
        self.assertFalse(item["hook_cadastrado_presente_na_abertura"])

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
            manifest.write_text(json.dumps(
                {"episodes": [fake_episode(x) for x in DEFAULT_IDS]},
                ensure_ascii=False), encoding="utf-8")
            self.assertEqual(main([
                "--manifest", str(manifest),
                "--output", str(output),
            ]), 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["analyzed_count"], 3)
            self.assertEqual(result["method"], "offline-deterministic-editorial-proxies")


if __name__ == "__main__":
    unittest.main()
