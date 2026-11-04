"""Offline tests for reusable garden/bedroom/egg assets and scene layering."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kids_emanuelly_cenarios_camadas_v1 as layers


def background(tmp_path, name="scene", color=(90,180,120)):
    out=tmp_path/(name+".png")
    Image.new("RGB",(1080,1920),color).save(out)
    return out


def egg(tmp_path):
    out=tmp_path/"egg.png"
    im=Image.new("RGBA",(850,1000),(0,0,0,0))
    from PIL import ImageDraw
    ImageDraw.Draw(im).ellipse((200,100,710,900),fill=(45,170,255,255))
    im.save(out)
    return out


def nine_files(tmp_path):
    source=tmp_path/"input"
    source.mkdir()
    for i in range(1,5):
        background(source,f"jardim-{i:02d}")
        background(source,f"quarto-{i:02d}",(190,130,110))
    egg(source).rename(source/"ovo-azul.png")
    return source


def test_install_canon_and_no_edit_without_explicit_replace(tmp_path):
    source=background(tmp_path)
    a=layers.install("jardim-01",source,root=tmp_path)
    assert a["uploaded"] is False and layers.installed("jardim-01",tmp_path)
    assert layers.install("jardim-01",source,root=tmp_path)["status"]=="ja_instalado"
    old_sha=a["sha256"]
    different=background(tmp_path,"other",(30,30,40))
    with pytest.raises(ValueError,match="Refazer"):
        layers.install("jardim-01",different,root=tmp_path)
    assert layers.installed("jardim-01",tmp_path)
    updated=layers.install("jardim-01",different,root=tmp_path,replace=True)
    assert updated["sha256"]!=old_sha
    assert len(list((tmp_path/layers.CANON/"historico").glob("*.png")))==1


def test_egg_must_be_real_transparency_and_reused(tmp_path):
    solid=background(tmp_path)
    with pytest.raises(ValueError,match="transparente"):
        layers.install("ovo-azul",solid,root=tmp_path)
    r=layers.install("ovo-azul",egg(tmp_path),root=tmp_path)
    assert r["uploaded"] is False
    assert layers.installed("ovo-azul",tmp_path)
    assert len(layers.SHOTS)==9
    assert all(s["showEgg"] for s in layers.SHOTS)
    assert layers.SHOTS[0]["pose"] is None
    assert all(s["pose"] is None or s["pose"] in layers.required_poses()
               for s in layers.SHOTS)
    assert all(not s.get("future_characters") for s in layers.SHOTS)


def test_import_lote_all_nine_assets(tmp_path):
    src=nine_files(tmp_path)
    result=layers.install_directory(src,root=tmp_path)
    assert len(result["installed"])==9
    assert set(layers.SLOTS)==set([f"jardim-{i:02d}" for i in range(1,5)]
                                  +[f"quarto-{i:02d}" for i in range(1,5)]
                                  +["ovo-azul"])
    assert all(layers.installed(slot,tmp_path) for slot in layers.SLOTS)
    assert layers.install_directory(src,root=tmp_path)["uploads"]==0


def test_missing_source_in_lote_fails_before_any_file_write(tmp_path):
    src=nine_files(tmp_path)
    (src/"jardim-04.png").unlink()
    with pytest.raises(FileNotFoundError,match="jardim-04"):
        layers.install_directory(src,root=tmp_path)
    assert not any(layers.official(slot,tmp_path).exists() for slot in layers.SLOTS)


def test_bad_opaque_egg_rejects_entire_batch_without_partial_install(tmp_path):
    src=nine_files(tmp_path)
    background(src,"ovo-azul",(20,40,100))
    with pytest.raises(ValueError,match="Ovo sem alfa real"):
        layers.install_directory(src,root=tmp_path)
    assert all(not layers.official(slot,tmp_path).exists() for slot in layers.SLOTS)


def test_preflight_missing_pose_or_voice_blocks_without_placeholder(tmp_path,monkeypatch):
    src=nine_files(tmp_path)
    layers.install_directory(src,root=tmp_path)
    monkeypatch.setattr(layers.poses,"valid",lambda slug,root:False)
    result=layers.preflight(root=tmp_path)
    assert not result["ready"]
    assert "pose:caminhando" in result["missing"]
    assert "narracao_original" in result["missing"]
    with pytest.raises(ValueError,match="Materiais em falta"):
        layers.build_props(root=tmp_path)
    assert not list((tmp_path/"motion-remotion").glob("props*.json"))


def test_storyboard_only_one_egg_no_manu_initial_and_rooms_after_garden():
    assert [s["backdrop"] for s in layers.SHOTS[:5]]==[
        "jardim-01","jardim-02","jardim-03","jardim-04","jardim-01"]
    assert [s["backdrop"] for s in layers.SHOTS[5:]]==[
        "quarto-01","quarto-02","quarto-03","quarto-04"]
    assert layers.SHOTS[0]["pose"] is None
    assert layers.SHOTS[7]["movement"]=="rock"
    assert layers.SHOTS[7]["night"]
    assert len(set(s["pose"] for s in layers.SHOTS if s["pose"]))<8


def test_props_combine_canon_images_and_keep_voice_music(tmp_path,monkeypatch):
    src=nine_files(tmp_path)
    layers.install_directory(src,root=tmp_path)
    part=layers.part1()
    folder=layers.story.output_for(part,tmp_path)
    folder.mkdir(parents=True,exist_ok=True)
    audio=folder/"narracao.mp3"
    audio.write_bytes(b"fake-voice")
    (tmp_path/"Wondertrail _Main Theme_.mp3").write_bytes(
        b"ID3"+b"\x00"*120000)
    pose_folder=layers.poses.pose_dir(tmp_path)
    pose_folder.mkdir(parents=True,exist_ok=True)
    for name in layers.required_poses():
        image=pose_folder/("emanuelly-"+name+".png")
        Image.new("RGBA",(1024,1536),(0,0,0,0)).save(image)
    monkeypatch.setattr(layers.poses,"valid",lambda slug,root: True)
    monkeypatch.setattr(layers.story,"read_voice",lambda p,root:(audio,{"fake":True}))
    monkeypatch.setattr(layers.story,"audio_seconds",lambda p:36.0)
    beats=[{"startFrame":j*110,"endFrame":(j+1)*110}
           for j in range(9)]
    monkeypatch.setattr(layers.story,"scene_props",
                        lambda _ep,_marker,_frames:([],[],beats))
    before_audio=audio.read_bytes()
    props,path,qa=layers.build_props(root=tmp_path)
    assert props["frames"]==[]
    assert props["layeredScenes"][0]["pose"] is None
    assert len(props["layeredScenes"])==9
    assert props["durationFrames"]<1800
    assert props["madeForKids"] is True
    assert props["audio"].endswith("layers/narracao.mp3")
    assert props["music"]["volume"]<.12
    assert len({item["egg"] for item in props["layeredScenes"]})==1
    assert all("layers" in item["background"] for item in props["layeredScenes"])
    assert qa["signature"] and path.is_file()
    assert audio.read_bytes()==before_audio


def test_still_image_pipeline_untouched():
    text=(ROOT/"motion-remotion/src/emanuelly-short.tsx").read_text("utf8")
    assert "layeredScenes?" in text
    assert "EmanuellyLayerStage" in text
    assert "active&&" in text
    ps=(ROOT/"animar-emanuelly.ps1").read_text("utf8")
    assert "Modo Catalogo e Planejar nao geram imagens" in ps
    assert "GerarImagens" in ps
    assert "Start-Process" in ps
    assert "upload" in ps.lower()
