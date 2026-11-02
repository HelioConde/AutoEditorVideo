"""Rigby2D sequence interchange: original images remain local and immutable."""
from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import pytest
from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import rigby2d_bridge as rig
import renderizar_master_remotion as renderer
from scene_layer_profiles import Layer


def fixture(tmp_path):
    scene=tmp_path/"scene"
    folder=scene/"multilayer"
    folder.mkdir(parents=True)
    source=Image.new("RGBA",rig.SIZE,(75,48,27,0))
    ImageDraw.Draw(source).ellipse((250,250,630,900),fill=(200,140,90,255))
    src=folder/"l.png";source.save(src)
    source_bytes=src.read_bytes()
    exported=tmp_path/"exported";exported.mkdir()
    for i in range(3):
        image=Image.new("RGBA",rig.SIZE,(0,0,0,0))
        dx=i*3
        ImageDraw.Draw(image).ellipse((250+dx,250,630+dx,900),
                                      fill=(200,140,90,255))
        image.save(exported/f"export-{i:03d}.png")
    return scene,src,source_bytes,exported


def test_prepare_is_local_and_explicit_about_missing_body_parts(tmp_path):
    scene,src,source,exported=fixture(tmp_path)
    directory=rig.prepare(scene,"l")
    data=(directory/"rigby2d-guide.json").read_text()
    assert "PARTES_ANATOMICAS_NAO_SEPARADAS" in data
    assert "upperarm_left" in data
    assert (directory/"character-reference.png").is_file()
    assert not (directory/"frames").exists()
    assert src.read_bytes()==source
    assert rig.prepare(scene,"l")==directory
    with pytest.raises(ValueError,match="Personagem nao suportado"):
        rig.prepare(scene,"shadow")


def test_import_approve_and_rollback_on_changed_frame(tmp_path):
    scene,src,source,exported=fixture(tmp_path)
    manifest=rig.import_sequence(scene,"l",exported,24)
    assert manifest.is_file()
    with pytest.raises(ValueError,match="aguardando revisao"):
        rig.approved_frames(scene,"l")
    with pytest.raises(ValueError,match="justificativa"):
        rig.approve(scene,"l","")
    rig.approve(scene,"l","Confirmado no preview de ossos")
    approved=rig.approved_frames(scene,"l")
    assert approved["fps"]==24 and len(approved["files"])==3
    assert src.read_bytes()==source
    with pytest.raises(ValueError,match="Frames existentes"):
        rig.import_sequence(scene,"l",exported,24)
    # Changing a single pose invalidates its signed scene export.
    Image.new("RGBA",rig.SIZE,(15,50,25,255)).save(approved["files"][2])
    with pytest.raises(ValueError,match="editado"):
        rig.approved_frames(scene,"l")


def test_missing_parts_are_not_misrepresented_as_automatic_bone_rig(tmp_path):
    scene,src,source,exported=fixture(tmp_path)
    rig.prepare(scene,"l")
    assert rig.approved_frames(scene,"l") is None
    with pytest.raises(ValueError,match="3 frames"):
        rig.validate_frames(scene,"l")


def test_import_rejects_wrong_canvas_and_opaque_frame(tmp_path):
    scene,src,source,exported=fixture(tmp_path)
    Image.new("RGB",rig.SIZE,(200,0,0)).save(exported/"export-001.png")
    with pytest.raises(ValueError,match="RGBA"):
        rig.import_sequence(scene,"l",exported,30)
    assert not (rig.rig_folder(scene,"l")/"frames").exists()


def test_render_props_use_real_rigged_frames_only_after_approval(tmp_path,monkeypatch):
    scene,src,source,exported=fixture(tmp_path)
    shot={"id":"04","subject":"personagens","shot_type":"l_reaction"}
    image=Image.new("RGB",rig.SIZE,(30,30,30))
    master=scene/"master.png";image.save(master)
    background=scene/"multilayer"/"background.png";image.save(background)
    entry={
        "render_mode":"multilayer","scene":shot,"folder":scene,
        "files":{"master":master},
        "multi":{"background":background,
                 "layers":[(Layer("l","back_character",10,""),src)]},
        "fidelity":{},
    }
    monkeypatch.setattr(renderer,"validate_scenes",lambda *a,**kw:[entry])
    monkeypatch.setattr(renderer,"select_episode",lambda *_:{"cover":"chess"})
    voice=tmp_path/"voice.mp3";voice.write_bytes(b"audio")
    public=tmp_path/"public"
    with pytest.raises(ValueError,match="Nenhuma sequencia Rigby2D aprovada"):
        renderer.build_props({"id":"ep","scenes":[shot]},voice,[],4,public=public,
                             animation_mode="esqueleto2d")
    rig.import_sequence(scene,"l",exported,30)
    with pytest.raises(ValueError,match="aguardando revisao"):
        renderer.build_props({"id":"ep","scenes":[shot]},voice,[],4,public=public,
                             animation_mode="esqueleto2d")
    rig.approve(scene,"l","Articulacoes revisadas")
    props=renderer.build_props({"id":"ep","scenes":[shot]},voice,[],4,public=public,
                                animation_mode="esqueleto2d")
    part=props["scenes"][0]["layers"][0]
    assert len(part["rigFrames"]["frames"])==3
    assert part["rigFrames"]["fps"]==30
    for path in part["rigFrames"]["frames"]:
        assert (public/path).is_file()
    assert src.read_bytes()==source
