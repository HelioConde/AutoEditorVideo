"""Regression tests: creator-approved 5s visual reference and original program engines."""
from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image, ImageDraw
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from capa_cinematografica import render_cover
from gamer_reference_style_5s import EP, OWNER, SCRIPT, validate, guard, PreviewError

def test_five_second_test_is_reserved_in_github():
    validate()
    assert EP=="game-901-estilo-referencia-5s"
    assert "Minecraft" in SCRIPT
    assert "não é gameplay" not in SCRIPT

def test_official_cover_renders_reference_preset(tmp_path):
    source=Image.new("RGB",(1024,1536),(88,65,101))
    painter=ImageDraw.Draw(source)
    painter.rectangle((0,430,1024,1536),fill=(194,124,50))
    painter.ellipse((140,380,700,1100),fill=(45,76,133))
    out=tmp_path/"thumb.jpg"
    report=render_cover(source,"PRIMEIRA NOITE",out,
                        template="gamer-alchemy-reference")
    assert out.is_file() and out.stat().st_size>20_000
    assert report["template"]=="gamer-alchemy-reference"
    assert report["style"]=="duelo-cinematografico"
    with Image.open(out) as pic:
        assert pic.format=="JPEG"
        assert pic.size==(1080,1920)
        # Bright white-serif letters are near top of frame.
        top=pic.crop((75,125,1005,420)).convert("L")
        assert top.getextrema()[1]>240
        # The reference does not add any bottom caption to the thumbnail.
        assert pic.getpixel((540,1800))[0]>0

def test_unknown_cover_template_is_rejected(tmp_path):
    with pytest.raises(ValueError,match="Preset"):
        render_cover(Image.new("RGB",(1024,1536),"grey"),"NOITE",
                     tmp_path/"no.jpg",template="invalid")

def test_reference_visuals_keep_other_remotion_channels_unchanged():
    source=(ROOT/"motion-remotion/src/master-short.tsx").read_text(encoding="utf-8")
    assert "visualProfile?:'original'|'gamer-alchemy-reference'" in source
    assert "visualProfile='original'" in source
    assert "visualProfile==='gamer-alchemy-reference'" in source
    assert "color:active?'#ffd166':'#fff'" in source
    assert "top:1272,left:94,right:94" in source
    assert "whiteSpace:'pre-line'" in source

def test_one_shot_requires_exact_main_env(monkeypatch):
    for key in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME",
                "GITHUB_RUN_ATTEMPT","GITHUB_WORKFLOW","STYLE_5S_APPROVED",
                "SOURCE_RENDER_RUN_ID"):
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(PreviewError,match="SINGLE_APPROVED_MAIN_PUSH_REQUIRED"):
        guard()
