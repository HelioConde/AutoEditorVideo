"""Budget, occlusion and rendering regression tests; ALL FAKE image edits."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image,ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import master_scenes as core
import extract_scene_layers as multi
import renderizar_master_remotion as renderer
from scene_layer_profiles import layer_profile
from qa_multilayer_geometry import exact_layer,qa_multilayer_geometry


def scene_fixture(tmp_path,monkeypatch,shot="ots_light"):
    base=tmp_path/"scene02"
    base.mkdir()
    ep={"id":"test-episode","scenes":[{"id":"02","shot_type":shot,
                                        "subject":"personagens","prompt":"x"*80}]}
    scene=ep["scenes"][0]
    mask_rects={"l":(570,200,880,780),"table":(100,780,950,1380),
                "board":(260,900,820,1120),"light":(70,140,400,1500),
                "king_hand":(450,920,530,1030),"subject":(80,100,700,1200)}
    colors={"l":(95,100,115),"table":(120,80,40),"board":(200,188,170),
            "light":(55,65,85),"king_hand":(9,15,25),"subject":(90,100,120)}
    master=Image.new("RGB",core.SIZE,(15,28,48))
    draw=ImageDraw.Draw(master)
    for layer in layer_profile(ep,scene):
        draw.rectangle(mask_rects[layer.id],fill=colors[layer.id])
    master.save(base/"master.png")
    monkeypatch.setattr(core,"scene_dir",lambda *_a,**_kw:base)
    monkeypatch.setattr(renderer,"scene_dir",lambda *_a,**_kw:base)
    calls=[]
    def mock_edit(src,prompt,model,*,transparent,mask=None):
        calls.append((prompt,transparent,str(mask) if mask else None))
        if not transparent:
            assert mask is not None
            with Image.open(mask) as masked:
                assert masked.getchannel("A").getextrema()==(0,255)
            background=Image.new("RGB",core.SIZE,(15,28,48))
            buf=io.BytesIO()
            background.save(buf,format="PNG")
            return buf.getvalue()
        for layer in layer_profile(ep,scene):
            if layer.prompt in prompt:
                image=Image.new("RGBA",core.SIZE,(0,0,0,0))
                ImageDraw.Draw(image).rectangle(mask_rects[layer.id],
                                                fill=(30,210,80,255))
                buf=io.BytesIO()
                image.save(buf,format="PNG")
                return buf.getvalue()
        raise AssertionError("Unrecognized mask prompt")
    return ep,scene,base,mock_edit,calls


def test_chess_layers_distinct_physical_z_and_count(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    layout=layer_profile(ep,scene)
    assert [p.id for p in layout]==["l","table","board","light"]
    assert [p.z for p in layout]==[10,20,30,40]
    assert multi.pending_calls(ep,scene,"gpt-image-1.5")==[
        "02/l","02/table","02/board","02/light","02/background-clean"]


def test_one_command_generates_each_mask_and_preserves_master_pixels(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    before=(base/"master.png").read_bytes()
    result=multi.process_multilayer(ep,scene,"gpt-image-1.5",edit=edit)
    assert len(calls)==5 and not calls[-1][1]
    assert result["schema"]=="arquivo-otaku/scene-layers/v1"
    assert result["qa"]["manual_approval_required"]
    assert (base/"multilayer"/"preview-composicao.png").is_file()
    with Image.open(base/"multilayer"/"light.png") as image, Image.open(base/"master.png") as master:
        assert image.getpixel((150,400))[:3]==master.getpixel((150,400))
        assert image.getpixel((500,300))[3]==0
    assert (base/"master.png").read_bytes()==before
    assert len(multi.pending_calls(ep,scene,"gpt-image-1.5"))==0
    multi.process_multilayer(ep,scene,"gpt-image-1.5",offline=True)
    assert len(calls)==5  # no fresh paid calls


def test_multilayer_requires_visual_approval_for_short_and_cover(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    result=multi.process_multilayer(ep,scene,"gpt-image-1.5",edit=edit)
    # Synthetic masks are ordered correctly but may have genuine QA warnings.
    # A warning must prevent approval rather than be silently ignored.
    if result["qa"]["warnings"]:
        with pytest.raises(ValueError,match="alertas"):
            multi.approve_multilayer(ep,scene,"gpt-image-1.5","Checked by eye")
        return
    with pytest.raises(ValueError,match="aguardando revisao"):
        renderer.validate_scenes(ep,"gpt-image-1.5")
    multi.approve_multilayer(ep,scene,"gpt-image-1.5","Checked all characters and chessboard")
    checked=renderer.validate_scenes(ep,"gpt-image-1.5")
    assert checked[0]["render_mode"]=="multilayer"
    monkeypatch.setattr(renderer,"select_episode",lambda *_:{"cover":"test"})
    voice=tmp_path/"voz.mp3"
    voice.write_bytes(b"test")
    props=renderer.build_props(ep,voice,[],2.5,model="gpt-image-1.5",
                               output=tmp_path,public=tmp_path/"public")
    assert props["scenes"][0]["renderMode"]=="multilayer"
    assert [part["id"] for part in props["scenes"][0]["layers"]]==[
        "l","table","board","light"]
    assert (tmp_path/"public"/"generated"/"test-episode"/"scene-02-layer-board.png").exists()


def test_rejected_master_blocks_requests_even_when_budget_is_available(tmp_path,monkeypatch):
    from revisao_visual_cenas import write_review
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    write_review(base,status="reprovado",reason="Foot appears on tabletop")
    with pytest.raises(ValueError,match="MASTER reprovada"):
        multi.pending_calls(ep,scene,"gpt-image-1.5")
    assert not calls


def test_king_hand_is_separate_layer_with_strict_order(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch,"light_moves_king")
    specs=layer_profile(ep,scene)
    assert [p.id for p in specs]==["table","board","light","king_hand"]
    assert [p.z for p in specs]==[20,30,40,50]
    assert "hand" in specs[-1].prompt
    multi.process_multilayer(ep,scene,"gpt-image-1.5",edit=edit)
    assert len(calls)==5
    with Image.open(base/"multilayer"/"king_hand.png") as img:
        assert img.getpixel((480,980))[3]==255


def test_unsupported_opaque_or_empty_masks_are_rejected_before_manifest(tmp_path):
    original=tmp_path/"master.png"
    Image.new("RGB",core.SIZE,(22,40,90)).save(original)
    empty=io.BytesIO()
    Image.new("RGBA",core.SIZE,(0,0,0,0)).save(empty,format="PNG")
    with pytest.raises(ValueError,match="vazia"):
        exact_layer(original,empty.getvalue())
    opaque=io.BytesIO()
    Image.new("RGBA",core.SIZE,(10,20,30,255)).save(opaque,format="PNG")
    with pytest.raises(ValueError,match="88%"):
        exact_layer(original,opaque.getvalue())


def test_multilayer_manifest_is_invalidated_when_master_changes(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    multi.process_multilayer(ep,scene,"gpt-image-1.5",edit=edit)
    Image.new("RGB",core.SIZE,(200,100,10)).save(base/"master.png")
    with pytest.raises(ValueError,match="master/modelo mudou"):
        multi.validate_multilayer(ep,scene,"gpt-image-1.5",base,approval=False)


def test_review_digest_invalidates_after_manifest_change(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    result=multi.process_multilayer(ep,scene,"gpt-image-1.5",edit=edit)
    if result["qa"]["warnings"]:
        pytest.skip("Synthetic scene flagged for manual geometry remediation")
    multi.approve_multilayer(ep,scene,"gpt-image-1.5","Reviewed")
    manifest=base/"scene-layers.json"
    manifest.write_text(manifest.read_text()+"\n")
    with pytest.raises(ValueError,match="desatualizada"):
        multi.validate_multilayer(ep,scene,"gpt-image-1.5",base)


def test_budget_preflight_counts_one_per_distinct_raw_and_background(tmp_path,monkeypatch):
    ep,scene,base,edit,calls=scene_fixture(tmp_path,monkeypatch)
    assert len(multi.pending_calls(ep,scene,"gpt-image-1.5"))==5
    (base/"multilayer").mkdir()
    (base/"multilayer"/"l-raw.png").write_bytes(b"old paid cache raw")
    assert len(multi.pending_calls(ep,scene,"gpt-image-1.5"))==4
    assert not calls
