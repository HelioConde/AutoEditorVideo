"""Fofinhos EP01: approved narration, 15-scene visual coherence and stale-cache safety.

Read-only/offline tests: no photos, image API, TTS provider or video uploads.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fofinhos_ep01_canon as canon
import serie_kids_emanuelly_v1 as story
import kids_emanuelly_todos_videos_v2 as layered


def copied_manifest(tmp_path: Path) -> None:
    for path in (canon.CANON, canon.MANIFEST):
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / path, dest)


def test_approved_story_has_all_original_lines_and_precise_pauses():
    data = canon.read_canon()
    assert data["series"] == "Fofinhos"
    assert data["approval"] == "user_provided_2026-11-04"
    assert len(data["scenes"]) == 15
    assert [s["index"] for s in data["scenes"]] == list(range(1, 16))
    text = canon.approved_text()
    for fragment in (
        "Era uma vez uma menina linda, doce e muito carinhosa chamada Emanuelly.",
        "Emanuelly adorava brincar no jardim, pertinho das flores coloridas.",
        "Um ovo azul brilhante, com pequenas gotinhas desenhadas na casca!",
        "E viu aquele lindo ovo azul brilhando entre as flores.",
        "Ela se ajoelhou e estendeu a mão, bem devagarzinho.",
        "Quando chegou perto, o ovo começou a brilhar ainda mais!",
        "Com muito cuidado, pegou o ovo e levou para casa.",
        "Lá, preparou uma caminha bem macia, com uma mantinha e uma almofada fofinha.",
        "Naquela noite, enquanto Emanuelly observava o ovo...",
        "Toc... toc...",
        "O ovo começou a balançar!",
        "Mas... quem será que estava lá dentro?",
        "Continua na Parte 2...",
    ):
        assert fragment in text
    assert [(p["after_scene"], p["seconds"]) for p in data["pauses"]] == [
        (4, 1), (6, .8), (14, 1.8)
    ]


def test_egg_is_in_flowers_not_road_with_correct_day_night():
    scenes = canon.read_canon()["scenes"]
    assert all(s["egg_location"] == "entre_flores" for s in scenes[2:9])
    assert all(s["background"].startswith("jardim") for s in scenes[:10])
    assert all(s["background"].startswith("quarto") for s in scenes[10:])
    assert all(not s["night"] for s in scenes[:12])
    assert all(s["night"] for s in scenes[12:])
    assert "PROIBIDO ovo no caminho" in scenes[6]["forbidden"]
    assert scenes[7]["pose"] == "estendendo-mao"
    assert scenes[10]["pose"] == "preparando-caminha"
    assert scenes[13]["egg_location"] == "caminha_quarto"


def test_legacy_short_is_explicitly_marked_obsolete_and_not_approved():
    report = canon.compare_short_draft()
    manifest = json.loads((ROOT / canon.MANIFEST).read_text(encoding="utf-8"))
    assert manifest["series"] == "Fofinhos"
    assert manifest["approved_part1_source"] == str(canon.CANON)
    assert manifest["parts"][0]["status"] == "rascunho_obsoleto_nao_renderizar"
    assert report["approved_scene_count"] == 15
    assert report["legacy_short_scene_count"] == 9
    assert report["legacy_script_matches_approved"] is False
    assert report["legacy_part1_render_authorized"] is False
    assert report["uploads"] == 0


def test_obsolete_part1_blocks_voice_frames_render_even_with_existing_mp3(tmp_path):
    copied_manifest(tmp_path)
    obsolete = story.load_parts()[0]
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        canon.ensure_approved_script(obsolete, tmp_path)
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        story.make_voice(obsolete, root=tmp_path)
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        story.make_images([obsolete], root=tmp_path, budget=100,
                          editor=lambda *a, **k: pytest.fail("No AI"))
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        story.read_voice(obsolete, tmp_path)
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        story.build_props(obsolete, root=tmp_path)
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        story.render(obsolete, root=tmp_path)
    with pytest.raises(ValueError, match="narracao ANTIGA"):
        layered.build(1, root=tmp_path)


def test_untouched_parts_2_through_4_remain_eligible_for_processing(tmp_path):
    copied_manifest(tmp_path)
    for part in story.load_parts()[1:]:
        canon.ensure_approved_script(part, tmp_path)


def test_cannot_change_flower_location_or_approved_pause(tmp_path):
    copied_manifest(tmp_path)
    path = tmp_path / canon.CANON
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scenes"][6]["egg_location"] = "caminho"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="flores"):
        canon.read_canon(tmp_path)
    data["scenes"][6]["egg_location"] = "entre_flores"
    data["pauses"][0]["seconds"] = 0.2
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Pausas"):
        canon.read_canon(tmp_path)
