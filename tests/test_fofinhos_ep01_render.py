"""Offline checks for new Fofinhos 15-scene voice and guarded render pipeline."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fofinhos_ep01_canon as approved
import fofinhos_ep01_render as production
import kids_emanuelly_cenarios_camadas_v1 as scenery


def fixture(root):
    dest = root / approved.CANON
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / approved.CANON, dest)
    return dest


def background(root, slot):
    target = root / (slot + ".png")
    Image.new("RGB", (1024, 1536), (70, 150, 185)).save(target)
    scenery.install(slot, target, root=root)


def egg(root):
    image = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse((340, 260, 740, 1300), fill=(34, 130, 240, 255))
    target = root / "egg-source.png"
    image.save(target)
    scenery.install("ovo-azul", target, root=root)


def test_preflight_on_unprepared_assets_protects_old_video(tmp_path):
    fixture(tmp_path)
    status = production.plan(tmp_path)
    assert status["approved_scenes"] == 15
    assert status["voice_ready"] is False
    assert status["ready_for_preview"] is False
    assert status["flowers"] == "nao_calibrado"
    assert "cenario:jardim-03" in status["visual_assets_missing"]
    assert "ovo:ovo-azul" in status["visual_assets_missing"]
    assert not (tmp_path / "assets/gerados/fofinhos").exists()


def test_guia_flores_has_no_fake_approved_coordinates(tmp_path):
    fixture(tmp_path)
    for slot in production.FLOWER_VIEWS:
        background(tmp_path, slot)
    guide = production.guide_flowers(tmp_path)
    assert guide["uploads"] == 0
    assert len(guide["guides"]) == 2
    for entry in guide["guides"]:
        assert Path(entry).exists()
    data = json.loads(production.placements_file(tmp_path).read_text())
    assert all(data["angles"][slot]["x"] is None for slot in production.FLOWER_VIEWS)
    with pytest.raises(ValueError, match="Selecione"):
        production.read_placement(tmp_path)


def approved_flower_points(root):
    data = json.loads(production.placements_file(root).read_text())
    for slot in production.FLOWER_VIEWS:
        data["angles"][slot].update(x=.35, y=.62, aprovado_visual=True)
    production.save_json(production.placements_file(root), data)


def test_garden_change_invalidates_human_flower_approval(tmp_path):
    fixture(tmp_path)
    for slot in production.FLOWER_VIEWS:
        background(tmp_path, slot)
    production.guide_flowers(tmp_path)
    approved_flower_points(tmp_path)
    production.read_placement(tmp_path, approved=True)
    another = tmp_path / "other.png"
    Image.new("RGB", (1024, 1536), (210, 60, 40)).save(another)
    scenery.install("jardim-03", another, root=tmp_path, replace=True)
    with pytest.raises(ValueError, match="mudou"):
        production.read_placement(tmp_path, approved=True)


def test_scene_layout_respects_actual_manual_flower_points():
    data = approved.read_canon()
    placement = {"angles": {
        "jardim-03": {"x": .27, "y": .77},
        "jardim-04": {"x": .68, "y": .52},
    }}
    positions = [production.layout(scene, placement) for scene in data["scenes"]]
    assert len(positions) == 15
    assert positions[0]["showEgg"] is False
    assert positions[1]["showEgg"] is False
    assert all(x["eggX"] == .27 and x["eggY"] == .77 for x in positions[2:5])
    assert all(x["eggX"] == .68 and x["eggY"] == .52 for x in positions[5:9])
    assert positions[9]["eggLocation"] == "nas_maos"
    assert positions[13]["animation"] == "rock"
    assert all(x["night"] for x in positions[12:])
    assert all(x["visualReviewRequired"] for x in positions)


def test_voice_uses_approved_15_scenes_precise_pauses_not_legacy(tmp_path):
    fixture(tmp_path)
    called = []
    async def synth(text, voice, rate):
        called.append(text)
        return b"MP3" + b"0" * 1800, [
            {"text": "Era", "start": .11, "end": .29},
            {"text": "uma", "start": .32, "end": .44},
        ]
    def decoder(_file):
        return b"\0\0" * production.PCM_RATE
    def encoder(_pcm, _wav, path):
        path.write_bytes(b"ID3" + b"\0" * 12000)
    expected_seconds = 15 + sum(production.pauses(tmp_path))
    assert len(production.pauses(tmp_path)) == 15
    result = production.make_voice(
        tmp_path, synthesizer=synth, decode=decoder, encoder=encoder,
        probe=lambda _: expected_seconds
    )
    assert result["status"] == "gerada_canonica"
    assert len(called) == 15
    assert called[0].startswith("Era uma vez uma menina")
    assert "entre as flores" in called[6]
    marker = json.loads(production.voice_paths(tmp_path)[1].read_text())
    assert [marker["segments"][i-1]["pause_after_s"] for i in (4, 6, 14)] == [1, .8, 1.8]
    assert marker["duration_s"] == pytest.approx(expected_seconds, abs=.0001)
    assert marker["no_speech_cuts"] is True
    cached = production.make_voice(
        tmp_path, synthesizer=lambda *_: pytest.fail("should use cache")
    )
    assert cached["status"] == "cache"
    assert len(called) == 15


def test_no_render_without_explicit_flower_approval(tmp_path):
    fixture(tmp_path)
    for slot in production.FLOWER_VIEWS:
        background(tmp_path, slot)
    production.guide_flowers(tmp_path)
    with pytest.raises(ValueError, match="Selecione"):
        production.read_placement(tmp_path, approved=True)


def test_scripts_keep_legacy_paths_untouched_and_no_image_api():
    program = (ROOT / "scripts/fofinhos_ep01_render.py").read_text(encoding="utf-8")
    assert "MAX_SECONDS = 600" in program
    assert "render:fofinhos" in program
    assert "request_edit" not in program
    assert "videos().insert" not in program
    assert "fofinhos/ep01-parte01-canonico" in program
    assert "caminho" in (ROOT / approved.CANON).read_text(encoding="utf-8").lower()
    root = (ROOT / "motion-remotion/src/root.tsx").read_text(encoding="utf-8")
    assert 'id="FofinhosEP01Canonico"' in root
    launcher = (ROOT / "fofinhos-ep01.ps1").read_text(encoding="utf-8")
    assert "GuiaFlores" in launcher and "Renderizar" in launcher
    old = (ROOT / "gerar-historia-kids.ps1").read_text(encoding="utf-8")
    assert "fofinhos-ep01.ps1" in old
