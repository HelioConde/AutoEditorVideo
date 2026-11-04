"""Offline QA for the official nine Fofinhos scene images and their source locks."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gerar_cenarios_fofinhos_gpt_image_2 as scenery
import kids_emanuelly_cenarios_camadas_v1 as canon


def setup_reference(root: Path) -> Path:
    ref = root / scenery.PRIVATE_STYLE
    ref.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1024, 1536), (160, 180, 200)).save(ref)
    return ref


def make_png(transparent=False, color=(80, 145, 180)) -> bytes:
    if transparent:
        img = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((315, 200, 715, 1220),
                                    fill=(*color, 255))
    else:
        img = Image.new("RGB", (1024, 1536), color)
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()


def fake_editor(calls):
    def do(source, instructions, model, key, *, transparent):
        calls.append((Path(source).name, instructions, model, transparent))
        return make_png(transparent=transparent)
    return do


def test_nine_canonical_slots_and_distinct_camera_prompts():
    assert len(scenery.ALL) == len(set(scenery.ALL)) == 9
    assert set(scenery.ALL) == set(canon.SLOTS)
    assert scenery.MODEL == "gpt-image-2"
    assert len({scenery.prompt(s) for s in scenery.ALL}) == 9
    for slot in scenery.ALL:
        assert "1024x1536" in scenery.prompt(slot)
        assert "jardim" in slot or "quarto" in slot or slot == "ovo-azul"
    for slot in scenery.ANGLES:
        assert "EXACT" in scenery.prompt(slot)
        assert "NO children" in scenery.prompt(slot)


def test_bases_use_one_private_style_then_scene_and_preserve_alpha(tmp_path):
    private = setup_reference(tmp_path)
    calls = []
    result = scenery.generate_batch(
        scenery.BASES, root=tmp_path, budget=3,
        editor=fake_editor(calls), key_provider=lambda: "test"
    )
    assert result["new_calls"] == 3 and result["uploads"] == 0
    assert [c[0] for c in calls] == [
        private.name, "jardim-01.png", "jardim-01.png"
    ]
    assert all(c[2] == "gpt-image-2" for c in calls)
    assert [c[3] for c in calls] == [False, False, True]
    for slot in scenery.BASES:
        assert canon.installed(slot, tmp_path)
        assert scenery.status(slot, tmp_path) == "em_cache"
    with Image.open(canon.official("ovo-azul", tmp_path)) as egg:
        assert egg.getchannel("A").getextrema() == (0, 255)
    with Image.open(canon.official("quarto-01", tmp_path)) as room:
        assert room.getchannel("A").getextrema() == (255, 255)
    assert json.loads(scenery.generated_meta("quarto-01", tmp_path).read_text())[
        "source"
    ].endswith("jardim-01.png")


def test_angles_all_use_immutable_garden_and_room_masters(tmp_path):
    setup_reference(tmp_path)
    calls = []
    edit = fake_editor(calls)
    scenery.generate_batch(scenery.BASES, root=tmp_path, budget=3,
                           editor=edit, key_provider=lambda: "test")
    assert len(calls) == 3
    result = scenery.generate_batch(scenery.ANGLES, root=tmp_path, budget=6,
                                    editor=edit, key_provider=lambda: "test")
    assert result["new_calls"] == 6
    assert [x[0] for x in calls[3:]] == [
        "jardim-01.png", "jardim-01.png", "jardim-01.png",
        "quarto-01.png", "quarto-01.png", "quarto-01.png"
    ]
    assert all(canon.installed(s, tmp_path) for s in scenery.ALL)
    assert scenery.report(tmp_path)["resumo"]["arquivos_registrados"] == 9
    again = scenery.generate_batch(scenery.ANGLES, root=tmp_path, budget=0,
                                   editor=lambda *_a, **_k: pytest.fail("No new AI"),
                                   key_provider=lambda: pytest.fail("No proxy"))
    assert again["new_calls"] == 0 and len(again["skipped_cache"]) == 6


def test_budget_preflight_prevents_partial_paid_call(tmp_path):
    setup_reference(tmp_path)
    calls = []
    with pytest.raises(ValueError, match="NENHUMA IA"):
        scenery.generate_batch(
            scenery.BASES, root=tmp_path, budget=2,
            editor=fake_editor(calls), key_provider=lambda: "test")
    assert not calls
    assert not any(canon.official(s, tmp_path).exists() for s in scenery.BASES)


def test_missing_base_blocks_variants_without_call(tmp_path):
    setup_reference(tmp_path)
    calls = []
    with pytest.raises(FileNotFoundError, match="jardim-01"):
        scenery.generate_batch(
            scenery.ANGLES, root=tmp_path, budget=6,
            editor=fake_editor(calls), key_provider=lambda: "test")
    assert not calls


def test_new_master_invalidates_derived_views(tmp_path):
    setup_reference(tmp_path)
    edit = fake_editor([])
    scenery.generate_batch(scenery.BASES, root=tmp_path, budget=3,
                           editor=edit, key_provider=lambda: "test")
    scenery.generate_batch(scenery.ANGLES, root=tmp_path, budget=6,
                           editor=edit, key_provider=lambda: "test")
    change = tmp_path / "changed.png"
    change.write_bytes(make_png(color=(33, 44, 55)))
    canon.install("jardim-01", change, root=tmp_path, replace=True)
    assert scenery.status("jardim-02", tmp_path) == "desatualizado"
    assert scenery.status("quarto-01", tmp_path) == "desatualizado"
    with pytest.raises(ValueError, match="Refazer"):
        scenery.generate_batch(scenery.ANGLES, root=tmp_path, budget=6,
                               editor=lambda *_a, **_kw: pytest.fail("No AI"))


def test_raw_paid_response_is_saved_before_qa_failure(tmp_path):
    setup_reference(tmp_path)
    calls = []
    def broken(*args, **kw):
        calls.append(1)
        return make_png(transparent=True)
    with pytest.raises(ValueError, match="opaco"):
        scenery.generate_batch(
            ("jardim-01",), root=tmp_path, budget=1,
            editor=broken, key_provider=lambda: "test")
    assert len(calls) == 1
    assert scenery.raw_reusable("jardim-01", tmp_path)
    assert not canon.installed("jardim-01", tmp_path)
    assert scenery.status("jardim-01", tmp_path) == "bruto_recuperavel"
    with pytest.raises(ValueError, match="opaco"):
        scenery.generate_batch(
            ("jardim-01",), root=tmp_path, budget=0,
            editor=lambda *_a, **_kw: pytest.fail("No second paid request"),
            key_provider=lambda: pytest.fail("No proxy"))
    assert len(calls) == 1


def test_no_automatic_upload_or_fallback():
    contents = (ROOT / "scripts/gerar_cenarios_fofinhos_gpt_image_2.py").read_text()
    launcher = (ROOT / "gerar-cenarios-fofinhos.ps1").read_text()
    assert "gpt-image-1.5" not in contents
    assert "youtube.upload" not in contents
    assert "videos().insert" not in contents
    assert "gpt-image-2" in launcher
    assert "BasesAprovadas" in launcher
