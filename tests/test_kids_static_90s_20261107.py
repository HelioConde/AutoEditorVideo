#!/usr/bin/env python3
"""Offline contract tests: Kids standalone 90s one-shot production, no API calls."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kids_static_90s_20261107 import check_manifest, IDS, CHANNEL_ID, story_cuts
from capa_cinematografica import render_cover

class IndependentKidsShorts(unittest.TestCase):
    def test_three_reserved_separated_from_fofinhos(self):
        episodes = check_manifest()
        self.assertEqual(tuple(x["id"] for x in episodes), IDS)
        for ep in episodes:
            self.assertTrue(ep["made_for_kids"])
            self.assertEqual(ep["channel_id"], CHANNEL_ID)
            self.assertEqual(len(ep["scenes"]), 8)
            self.assertNotIn("fofinho", ep["narration_script"].lower())
            self.assertEqual(ep["production_state"]["upload"], "not_started")
            self.assertGreaterEqual(len(ep["narration_script"].split()), 240)
            self.assertLessEqual(len(",".join(ep["tags"])), 500)
            self.assertTrue(ep["description"])
            self.assertIn("EmanuellyKids", ep["description"])

    def test_not_reusing_fofinhos_scenes_or_metadata(self):
        d = json.loads((ROOT / "conteudos" / "lote-12-estatico-90s-20261107.json").read_text(encoding="utf-8"))
        self.assertEqual(len(d["episodes"]), 12)
        self.assertEqual(len([x for x in d["episodes"] if x["channel"] == "kids"]), 3)
        self.assertEqual(len([x for x in d["episodes"] if x["channel"] == "br"]), 0)
        self.assertTrue(d["quality_gates"]["kids_original_standalone_no_fofinhos"])
        self.assertTrue(d["quality_gates"]["kids_real_duration_validation_required"])

    def test_scene_cuts_use_actual_word_boundaries(self):
        row = check_manifest()[0]
        words = [{"start": i * .36, "end": (i + 1) * .36, "text": "palavra"} for i in range(300)]
        cuts = story_cuts(row, words, 108)
        self.assertEqual(len(cuts), 9)
        self.assertEqual(cuts[0], 0)
        self.assertEqual(cuts[-1], 3240)
        self.assertTrue(all(b > a for a, b in zip(cuts, cuts[1:])))

    def test_canonical_kids_cover_still_works(self):
        from PIL import Image
        image = Image.new("RGB", (1024, 1536), (166, 220, 245))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cover.jpg"
            result = render_cover(image, "QUE ANIMAL É?", p, zoom=1.0, template="kids-pastel")
            self.assertEqual(result["template"], "kids-pastel")
            with Image.open(p) as actual:
                self.assertEqual(actual.size, (1080, 1920))
                self.assertEqual(actual.format, "JPEG")

if __name__ == "__main__":
    unittest.main()
