"""Valida o motor de camadas sem consumir cota de IA."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import motion_layers


def test_animation_has_independent_layer_motion():
    f=motion_layers.filters(True)
    assert "[personagem]" in f and "[objeto]" in f
    assert f.count("overlay=")==2
    assert "sin(0.8*t)" in f and "sin(1.1*t)" in f


def test_ffmpeg_command_with_and_without_object():
    bg,fg,obj,audio,out=(Path(s) for s in ("fundo.jpg","ator.png","caderno.png","voz.wav","saida.mp4"))
    simple=motion_layers.build_command(bg,fg,out,3)
    complex_=motion_layers.build_command(bg,fg,out,3,obj=obj,audio=audio)
    assert simple.count("-i")==2
    assert complex_.count("-i")==4
    assert complex_[complex_.index("-map")+1]=="[v]"
    assert "3:a:0" in complex_
    assert "-an" in simple
    assert complex_[-1]=="saida.mp4"


def test_invalid_clip_duration():
    with pytest.raises(ValueError):
        motion_layers.build_command(Path("f"),Path("c"),Path("o"),120)


def test_transparent_png_required(tmp_path):
    from PIL import Image
    opaque=tmp_path/"opaque.png"
    alpha=tmp_path/"translucido.png"
    Image.new("RGB",(10,10),"red").save(opaque)
    im=Image.new("RGBA",(10,10),(255,0,0,255))
    im.putpixel((0,0),(0,0,0,0))
    im.save(alpha)
    with pytest.raises(ValueError):
        motion_layers.validate_alpha(opaque)
    motion_layers.validate_alpha(alpha)
