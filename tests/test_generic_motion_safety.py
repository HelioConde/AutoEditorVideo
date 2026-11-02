"""Automatic motion metadata should generalize to any video and character.

Uses only synthetic masks; no paid images, passwords, snapshots or cache edits.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import renderizar_master_remotion as render
from scene_layer_profiles import Layer


def image(path,rectangle,color=(165,85,95,255),size=(256,384)):
    im=Image.new("RGBA",size,(0,0,0,0))
    ImageDraw.Draw(im).rectangle(rectangle,fill=color)
    im.save(path)
    return path


def scene_layers(tmp_path):
    # Two fully different figures, one table and an attached hero object.
    actor_a=Layer("personagem_α","back_character",10,"")
    table=Layer("escrivaninha","occluder",20,"")
    prop=Layer("bola_hero","hero_prop",30,"")
    actor_b=Layer("paladino_22","front_character",40,"")
    layers=[
        (actor_a,image(tmp_path/"a.png",(15,40,100,330))),
        (table,image(tmp_path/"table.png",(10,270,140,380))),
        (prop,image(tmp_path/"hero.png",(42,65,78,97))),
        (actor_b,image(tmp_path/"b.png",(173,65,245,275))),
    ]
    return layers


def test_contact_geometry_is_detected_without_scene_ids_or_person_names(tmp_path):
    ordered=scene_layers(tmp_path)
    a=render.layer_motion_safety(*ordered[0],ordered,"video-qualquer","cena-X")
    b=render.layer_motion_safety(*ordered[3],ordered,"video-qualquer","cena-X")
    assert 0<a["contactRisk"]<1
    assert a["heroRisk"]>0.04
    assert b["heroRisk"]==0
    assert b["contactRisk"]<a["contactRisk"]
    assert 0<a["heightFraction"]<=1
    assert b["motionSeed"]!=a["motionSeed"]


def test_mask_metrics_are_deterministic_and_caches_remain_byte_identical(tmp_path):
    ordered=scene_layers(tmp_path)
    before={p:hashlib.sha256(p.read_bytes()).hexdigest() for _,p in ordered}
    geometry1=[render.layer_motion_safety(layer,p,ordered,"ep","scene-5")
               for layer,p in (ordered[0],ordered[3])]
    geometry2=[render.layer_motion_safety(layer,p,ordered,"ep","scene-5")
               for layer,p in (ordered[0],ordered[3])]
    assert geometry1==geometry2
    assert before=={p:hashlib.sha256(p.read_bytes()).hexdigest()
                   for _,p in ordered}
    other_episode=render.layer_motion_safety(*ordered[0],ordered,"outro-ep","scene-5")
    assert other_episode["motionSeed"]!=geometry1[0]["motionSeed"]


def test_generic_props_expose_collision_metadata_without_automatic_rigging(
        tmp_path,monkeypatch):
    ordered=scene_layers(tmp_path)
    frame={"id":"cena-99","subject":"personagens","shot_type":"portrait_reaction"}
    master=tmp_path/"master.png"
    Image.new("RGB",(256,384),(20,20,30)).save(master)
    bg=tmp_path/"bg.png"
    Image.new("RGB",(256,384),(20,20,30)).save(bg)
    entry={"scene":frame,"render_mode":"multilayer","folder":tmp_path,
           "files":{"master":master},
           "multi":{"background":bg,"layers":ordered},
           "fidelity":{}}
    monkeypatch.setattr(render,"validate_scenes",lambda *a,**kw:[entry])
    monkeypatch.setattr(render,"select_episode",lambda *_:{"cover":"Something"})
    audio=tmp_path/"audio.mp3";audio.write_bytes(b"audio")
    props=render.build_props({"id":"outro-video","scenes":[frame]},audio,[],4,
         public=tmp_path/"public",character_preset="ultrassutil")
    assert props["animationMode"]=="cinematica"
    items={i["id"]:i for i in props["scenes"][0]["layers"]}
    for name in ("personagem_α","paladino_22"):
        data=items[name]
        assert 0<=data["contactRisk"]<=1
        assert 0<=data["heroRisk"]<=1
        assert isinstance(data["motionSeed"],int)
        assert data["heightFraction"]>0
        assert "rigFrames" not in data
    assert "contactRisk" not in items["escrivaninha"]
    assert "contactRisk" not in items["bola_hero"]
