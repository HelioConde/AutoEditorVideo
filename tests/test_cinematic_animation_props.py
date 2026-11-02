"""Safe animation props from original approved layers; no image generation."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import renderizar_master_remotion as renderer
from scene_layer_profiles import Layer


def test_animation_metrics_read_only_and_anchor_on_character_lower_edge(tmp_path):
    path=tmp_path/"character.png"
    im=Image.new("RGBA",(1024,1536),(0,0,0,0))
    ImageDraw.Draw(im).rectangle((100,200,410,1150),fill=(255,220,180,255))
    im.save(path)
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    meta=renderer.layer_animation_metrics(path)
    assert 0.17<meta["alphaCoverage"]<0.21
    assert 24<meta["anchorX"]<26
    assert 60<meta["anchorY"]<70
    assert before==hashlib.sha256(path.read_bytes()).hexdigest()


def test_approved_semantic_scene_props_include_guarded_motion_metadata(
        tmp_path,monkeypatch):
    folder=tmp_path/"scene";folder.mkdir()
    master=folder/"master.png"
    bg=folder/"background.png"
    Image.new("RGB",(1024,1536),(18,30,50)).save(master)
    Image.new("RGB",(1024,1536),(18,30,50)).save(bg)
    actor=folder/"l.png"
    layer=Image.new("RGBA",(1024,1536),(0,0,0,0))
    ImageDraw.Draw(layer).rectangle((150,200,540,1030),fill=(200,180,170,255))
    layer.save(actor)
    king=folder/"king_hand.png"
    ImageDraw.Draw(layer).rectangle((250,700,520,1010),fill=(5,5,5,255))
    layer.save(king)
    scene={"id":"03","subject":"personagens","shot_type":"light_moves_king",
           "camera_angle":"low","focus_subject":"Light","action":"moves king"}
    entry={
        "render_mode":"multilayer",
        "scene":scene,
        "files":{"master":master},
        "multi":{"background":bg,"layers":[
            (Layer("l","front_character",40,""),actor),
            (Layer("king_hand","hero_prop",50,""),king),
        ]},
        "fidelity":{},
    }
    monkeypatch.setattr(renderer,"validate_scenes",lambda *a,**k:[entry])
    monkeypatch.setattr(renderer,"select_episode",lambda *_:{"cover":"CHESS"})
    voice=tmp_path/"voice.mp3";voice.write_bytes(b"audio")
    public=tmp_path/"public"
    props=renderer.build_props({"id":"episode","scenes":[scene]},voice,[],4,
                               public=public,animation_mode="cinematica")
    assert props["animationMode"]=="cinematica"
    assert props["scenes"][0]["shotType"]=="light_moves_king"
    layers=props["scenes"][0]["layers"]
    assert [p["role"] for p in layers]==["front_character","hero_prop"]
    assert all(0<=p["alphaCoverage"]<=1 for p in layers)
    assert all(0<=p["anchorX"]<=100 and 0<=p["anchorY"]<=100 for p in layers)
    assert (public/"generated"/"episode"/"scene-03-layer-king_hand.png").exists()
    props_off=renderer.build_props({"id":"episode","scenes":[scene]},voice,[],4,
                                  public=public,animation_mode="desligada")
    assert props_off["animationMode"]=="desligada"


def test_animation_modes_validate_without_touching_paid_assets(tmp_path,monkeypatch):
    scene={"id":"01","subject":"personagens"}
    monkeypatch.setattr(renderer,"validate_scenes",lambda *args,**kwargs:[{
        "scene":scene,"render_mode":"master_static",
        "files":{"master":tmp_path/"master.png"},"fidelity":{}
    }])
    monkeypatch.setattr(renderer,"select_episode",lambda *_:{"cover":"C"})
    Image.new("RGB",(1024,1536),(20,20,20)).save(tmp_path/"master.png")
    voice=tmp_path/"voice.mp3";voice.write_bytes(b"audio")
    import pytest
    with pytest.raises(ValueError,match="Modo de animacao"):
        renderer.build_props({"id":"test","scenes":[scene]},voice,[],4,
                             public=tmp_path/"public",animation_mode="random")
