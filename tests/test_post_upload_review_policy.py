"""Nenhum clique de aprovacao visual e requisito para render ou capa.

O video completo sera avaliado no YouTube Studio, apos upload privado.
Os erros tecnicos e uma reprovação expressa continuam bloqueando.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import renderizar_master_remotion as renderer
from revisao_visual_cenas import write_review


def setup_scene(tmp_path, monkeypatch):
    folder = tmp_path / "scene01"
    folder.mkdir()
    Image.new("RGB", (1024, 1536), (16, 23, 42)).save(folder / "master.png")
    Image.new("RGB", (1024, 1536), (18, 22, 40)).save(folder / "background.png")
    fg = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    ImageDraw.Draw(fg).rectangle((220, 260, 720, 1230), fill=(80, 97, 117, 255))
    fg.save(folder / "foreground.png")
    (folder / "qa.json").write_text(
        json.dumps({"status": "aguardando_revisao_visual", "warnings": []}),
        encoding="utf-8",
    )
    ep = {
        "id": "test-ep",
        "scenes": [{
            "id": "01", "subject": "personagens", "prompt": "cinematic frame" * 8,
            "correcao_visual": {"requires_manual_approval": True},
        }],
    }
    monkeypatch.setattr(renderer, "scene_dir", lambda *_a, **_kw: folder)
    monkeypatch.setattr(
        renderer, "foreground_fidelity",
        lambda *_a, **_kw: {"status": "ok", "redrawn": False, "review_required": False},
    )
    return ep, folder


def test_unreviewed_legacy_scene_can_render_without_forging_approval(tmp_path, monkeypatch):
    episode, folder = setup_scene(tmp_path, monkeypatch)
    result = renderer.validate_scenes(episode, "gpt-image-1.5")
    assert result[0]["render_mode"] == "2_5d"
    assert not (folder / "visual-review.json").exists()
    assert episode["scenes"][0]["correcao_visual"]["requires_manual_approval"]


def test_unreviewed_legacy_cover_can_be_created(tmp_path, monkeypatch):
    episode, folder = setup_scene(tmp_path, monkeypatch)
    monkeypatch.setattr(renderer, "cover_options", lambda *_a: {
        "scene": "01", "title": "História", "zoom": 1.07,
    })
    monkeypatch.setattr(renderer, "render_cover", lambda *_a, **_kw: {"source": "test"})
    report = renderer.cover_from_master(
        episode, "gpt-image-1.5", tmp_path / "cover.jpg"
    )
    assert report["scene"] == "01"
    assert not (folder / "visual-review.json").exists()


def test_explicit_rejection_still_blocks_render_and_cover(tmp_path, monkeypatch):
    episode, folder = setup_scene(tmp_path, monkeypatch)
    write_review(folder, status="reprovado", reason="imagem comprometida")
    with pytest.raises(ValueError, match="imagem comprometida"):
        renderer.validate_scenes(episode, "gpt-image-1.5")
    monkeypatch.setattr(renderer, "cover_options", lambda *_a: {
        "scene": "01", "title": "historia",
    })
    with pytest.raises(ValueError, match="Capa bloqueada"):
        renderer.cover_from_master(episode, "gpt-image-1.5", tmp_path / "cover.jpg")


def test_missing_technical_qa_still_blocks(tmp_path, monkeypatch):
    episode, folder = setup_scene(tmp_path, monkeypatch)
    (folder / "qa.json").unlink()
    with pytest.raises(ValueError, match="falta QA"):
        renderer.validate_scenes(episode, "gpt-image-1.5")
