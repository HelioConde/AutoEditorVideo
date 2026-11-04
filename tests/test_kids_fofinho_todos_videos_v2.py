"""Offline QA: all four Fofinho Shorts use the SAME approved images."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kids_fofinho_storyboards_v2 as bible
import kids_emanuelly_series_assets_v2 as assets
import kids_emanuelly_todos_videos_v2 as composer
import serie_kids_emanuelly_v1 as story


def image_file(directory,name,*,transparent=False):
    path=directory/(name+".png")
    path.parent.mkdir(parents=True,exist_ok=True)
    if transparent:
        im=Image.new("RGBA",(1024,1536),(0,0,0,0))
        ImageDraw.Draw(im).ellipse((230,270,750,1250),fill=(65,145,220,255))
    else:
        im=Image.new("RGB",(1024,1536),(160,140,110))
    im.save(path)
    return path


def install_originals(tmp_path):
    temp=tmp_path/"input"
    for name in bible.CANON_OLD:
        file=image_file(temp,name,transparent=(name=="ovo-azul"))
        assets.install(name,file,root=tmp_path)
    original=tmp_path/"assets/referencias-privadas/emanuelly-fofinho.png"
    image_file(original.parent,"emanuelly-fofinho")
    return temp


def install_extras(tmp_path):
    originals=install_originals(tmp_path)
    for name in bible.ASSETS:
        file=image_file(originals,name,transparent=True)
        assets.install(name,file,root=tmp_path)
    assert all(assets.valid(n,tmp_path)
               for n in list(bible.CANON_OLD)+list(bible.ASSETS))


def test_canon_enumerates_four_shorts_and_future_characters_are_deferred():
    bible.validate_storyboard()
    data=bible.inventory()
    assert len(data["parts"])==4
    assert {int(p) for p in data["parts"]}=={1,2,3,4}
    assert [len(bible.STORYBOARDS[x]) for x in range(1,5)]==[9,10,9,9]
    assert len(bible.ASSETS)>=8
    assert set(data["future_characters_deferred"])=={
        "fofinha-arco-iris","fofinha-rosa","raposo","porco-espinho"}
    assert data["future_characters_allowed_in_EP01"] is False
    for part in range(1,5):
        imgs,poses=bible.resource_names(part)
        assert imgs and poses
        assert not (set(imgs)&set(bible.FUTURE_CAST))
        assert len(bible.STORYBOARDS[part])==len(story.load_parts()[part-1]["segments"])


def test_egg_and_fofinho_birth_rules_hold_in_every_shot():
    assert bible.STORYBOARDS[1][0]["pose"] is None
    assert bible.STORYBOARDS[1][0]["egg_phase"]=="closed"
    assert all(s["kitty"] is None for s in bible.STORYBOARDS[1])
    assert all(s["egg_phase"]=="closed" for s in bible.STORYBOARDS[1])
    assert all(s["kitty"] is None for s in bible.STORYBOARDS[2][:5])
    assert bible.STORYBOARDS[2][4]["egg_phase"]=="open"
    assert bible.STORYBOARDS[2][5]["kitty"]=="fofinho-azul"
    assert all(s["egg_phase"]=="none" for s in bible.STORYBOARDS[2][5:])
    assert all(s["egg_phase"]=="none" for p in (3,4)
               for s in bible.STORYBOARDS[p])
    assert bible.STORYBOARDS[2][9]["drops"]==1
    assert bible.STORYBOARDS[3][2]["drops"]==3
    assert bible.STORYBOARDS[4][-1]["future_glow"]
    assert bible.STORYBOARDS[4][-1]["kitty"] is None


def test_asset_lineage_hash_protects_egg_and_character(tmp_path):
    install_extras(tmp_path)
    assert assets.valid("ovo-rachado",tmp_path)
    assert assets.valid("ovo-aberto",tmp_path)
    assert assets.valid("fofinho-azul",tmp_path)
    assert assets.valid("fofinho-miando",tmp_path)
    egg=assets.reference("ovo-azul",tmp_path)
    Image.new("RGBA",(1024,1536),(35,60,120,255)).save(egg)
    assert not assets.valid("ovo-rachado",tmp_path)
    assert not assets.valid("ovo-aberto",tmp_path)
    assert not assets.valid("gotinha-agua",tmp_path)


def test_planning_all_parts_reports_absent_images_and_poses_without_ai(tmp_path):
    plan=assets.plan([1,2,3,4],root=tmp_path)
    assert plan["ready"] is False
    assert any("imagem:jardim-01"==s for s in plan["missing"])
    assert any("imagem:fofinho-azul"==s for s in plan["missing"])
    assert any("pose:fazendo-carinho"==s for s in plan["missing"])
    assert plan["uploads"]==0


def test_install_folder_partial_reuse_and_reject_unknown(tmp_path):
    source=tmp_path/"approved"
    src=image_file(source,"jardim-01")
    a=assets.install_folder(source,root=tmp_path)
    assert len(a["imported"])==1
    assert assets.valid("jardim-01",tmp_path)
    assert assets.install_folder(source,root=tmp_path)["uploads"]==0
    other=image_file(source,"ovo-inventado")
    assert other.is_file()
    with pytest.raises(FileNotFoundError,match="Nenhum PNG"):
        assets.install_folder(other.parent/"missing",root=tmp_path)
    replacement=Image.new("RGB",(1024,1536),(90,80,100))
    replacement.save(src)
    with pytest.raises(ValueError,match="Refazer"):
        assets.install_folder(source,root=tmp_path)
    assert assets.valid("jardim-01",tmp_path)


def test_only_gpt_image_2_and_parent_source_used_for_egg_variant(tmp_path):
    install_originals(tmp_path)
    import io
    from PIL import ImageDraw
    target=Image.new("RGBA",(1024,1536),(0,0,0,0))
    ImageDraw.Draw(target).ellipse((250,200,790,1230),fill=(45,150,255,255))
    out=io.BytesIO();target.save(out,"PNG")
    calls=[]
    def editor(src,prompt,model,key,*,transparent):
        calls.append((src,prompt,model,transparent))
        return out.getvalue()
    result=assets.generate("ovo-rachado",root=tmp_path,budget=1,
                           editor=editor,key_provider=lambda:"test")
    assert result["new_calls"]==1
    assert calls[0][0]==assets.reference("ovo-azul",tmp_path)
    assert calls[0][2]=="gpt-image-2" and calls[0][3] is True
    assert "SAME BLUE DRAGON EGG" in calls[0][1]
    assert assets.valid("ovo-rachado",tmp_path)
    assert assets.generate("ovo-rachado",root=tmp_path,budget=0)["new_calls"]==0


def test_render_props_all_four_are_layered_and_reuse_narration(tmp_path,monkeypatch):
    install_extras(tmp_path)
    for track in ("Wondertrail _Main Theme_.mp3","Wondertrail _Main Theme_2.mp3"):
        (tmp_path/track).write_bytes(b"ID3"+b"\x00"*120000)
    from pathlib import Path
    from PIL import Image
    monkeypatch.setattr(composer.poses,"valid",lambda slug,root:True)
    for p in range(1,5):
        chapter=story.load_parts()[p-1]
        audio=story.output_for(chapter,tmp_path)/"narracao.mp3"
        audio.parent.mkdir(parents=True,exist_ok=True)
        audio.write_bytes(b"mock-narration-"+str(p).encode())
    def fake_voice(chapter,root):
        return story.output_for(chapter,root)/"narracao.mp3",{"marked":True}
    monkeypatch.setattr(story,"read_voice",fake_voice)
    monkeypatch.setattr(story,"audio_seconds",lambda f:35.)
    def make_timing(ep,markers,frames):
        n=len(ep["kids_pacing"]["segments"])
        return [],[],[{"startFrame":i*110,"endFrame":(i+1)*110} for i in range(n)]
    monkeypatch.setattr(story,"scene_props",make_timing)
    for part in range(1,5):
        folder=tmp_path/"assets/gerados/kids-emanuelly/biblioteca-personagens/emanuelly/poses"
        folder.mkdir(parents=True,exist_ok=True)
        for shot in bible.STORYBOARDS[part]:
            if shot["pose"]:
                image_file(folder,"emanuelly-"+shot["pose"],transparent=True)
        before=(story.output_for(story.load_parts()[part-1],tmp_path)/
                "narracao.mp3").read_bytes()
        props,filename,metadata=composer.build(part,root=tmp_path)
        assert len(props["layeredScenes"])==len(bible.STORYBOARDS[part])
        assert props["frames"]==[]
        assert props["madeForKids"] is True
        assert props["music"]["volume"]<.12
        assert props["durationFrames"]<=1800
        assert filename.is_file() and metadata["signature"]
        assert props["layeredScenes"][0]["background"].startswith("generated/")
        if part==1:assert props["layeredScenes"][0]["pose"] is None
        if part==2:
            assert not props["layeredScenes"][4]["kitty"]
            assert props["layeredScenes"][5]["kitty"]
        assert (story.output_for(story.load_parts()[part-1],tmp_path)/
                "narracao.mp3").read_bytes()==before


def test_no_fofinha_premature_asset_rendering_or_publish():
    stage=(ROOT/"motion-remotion/src/emanuelly-layer-stage.tsx").read_text("utf8")
    assert "scene.kitty" in stage
    assert "scene.water" in stage
    assert "scene.nest" in stage
    assert "scene.futureGlow" in stage
    code=(ROOT/"scripts/kids_emanuelly_todos_videos_v2.py").read_text("utf8")
    assert "videos().insert" not in code
    assert "youtube.upload" not in code
    assert "gpt-image-1.5" not in code
