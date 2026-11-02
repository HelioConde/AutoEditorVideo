"""Protect the black chess king and require user approval of regenerated takes."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw, ImageChops

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from chess_composition_safety import master_static_for_chess_action,hero_prop_prompt
from revisao_visual_cenas import write_review
import master_scenes as master
import renderizar_master_remotion as renderer


def make_scene(tmp_path):
    folder=tmp_path/'03-test'
    folder.mkdir()
    plain=Image.new('RGB',master.SIZE,(25,38,55))
    draw=ImageDraw.Draw(plain)
    draw.rectangle((0,820,1023,1535),fill=(140,119,90))
    draw.rectangle((150,400,750,775),fill=(80,60,90))
    before=plain.copy()
    draw2=ImageDraw.Draw(before)
    # King is in the master but NOT the generic person's alpha layer
    draw2.polygon([(430,1030),(490,890),(550,1030)],fill=(0,0,0))
    before.save(folder/'master.png')
    plain.save(folder/'background-raw.png')
    fg=Image.new('RGBA',master.SIZE,(0,0,0,0))
    ImageDraw.Draw(fg).rectangle((150,400,750,775),fill=(80,60,90,255))
    fg.save(folder/'foreground-raw.png')
    return folder, before,plain


def test_chess_hero_preview_keeps_piece_and_saves_bad_layers_diagnostic(tmp_path):
    folder,original,background=make_scene(tmp_path)
    scene={'id':'03','subject':'personagens','prompt':'x'*60,'shot_type':'light_moves_king'}
    result=master.execute_scene({'id':'chess-test'},scene,'gpt-image-1.5',
                                directory=folder,offline=True)
    assert result['render_mode_recommended']=='master_static'
    assert 'peca_xadrez_pode_sumir_na_recomposicao' in result['warnings']
    assert (folder/'comparacao.jpg').is_file()
    assert (folder/'comparacao-camadas.jpg').is_file()
    assert (folder/'preview-render-seguro.jpg').is_file()
    assert result['composition']['layer_comparison_diagnostic'].endswith('comparacao-camadas.jpg')
    with Image.open(folder/'preview-render-seguro.jpg') as preview:
        assert preview.convert('RGB').getpixel((490,980))[0] < 30
    with Image.open(folder/'background.png') as bad_bg:
        assert bad_bg.convert('RGB').getpixel((490,980))[0] > 100
    assert (folder/'master.png').read_bytes() # untouched master
    assert 'chess king' in hero_prop_prompt(scene)


def test_render_uses_only_master_not_damaged_king_layer(tmp_path,monkeypatch):
    folder,original,background=make_scene(tmp_path)
    scene={'id':'03','subject':'personagens','prompt':'x'*60,'shot_type':'light_moves_king',
           'trecho_roteiro':'Light move o rei preto com segurança'}
    master.execute_scene({'id':'chess-test'},scene,'gpt-image-1.5',
                         directory=folder,offline=True)
    ep={'id':'chess-test','scenes':[scene]}
    monkeypatch.setattr(renderer,'scene_dir',lambda *args:folder)
    monkeypatch.setattr(renderer,'select_episode',lambda *args:{'cover':'Chess'})
    verified=renderer.validate_scenes(ep,'gpt-image-1.5',output=tmp_path)
    assert verified[0]['render_mode']=='master_static'
    voice=tmp_path/'voz.mp3'
    voice.write_bytes(b'test')
    public=tmp_path/'public'
    props=renderer.build_props(ep,voice,[],2.0,model='gpt-image-1.5',
                               output=tmp_path,public=public)
    assert props['scenes'][0]['renderMode']=='master_static'
    target=public/'generated'/'chess-test'
    assert (target/'scene-03-background.png').read_bytes()==(
        folder/'master.png').read_bytes()
    with Image.open(target/'scene-03-foreground.png') as fg:
        assert fg.getchannel('A').getextrema()==(0,0)


def test_revised_take_is_blocked_until_explicitly_approved(tmp_path,monkeypatch):
    folder,_,_=make_scene(tmp_path)
    scene={'id':'04','subject':'personagens','prompt':'x'*60,'shot_type':'l_reaction',
           'correcao_visual':{'requires_manual_approval':True}}
    master.execute_scene({'id':'chess-test'},scene,'gpt-image-1.5',
                         directory=folder,offline=True)
    ep={'id':'chess-test','scenes':[scene]}
    monkeypatch.setattr(renderer,'scene_dir',lambda *args:folder)
    monkeypatch.setattr(renderer,'cover_options',lambda *args:{
        'scene':'04','title':'CHESS','zoom':1.07,'focus_x':.5,'focus_y':.38})
    with pytest.raises(ValueError,match='APROVACAO'):
        renderer.validate_scenes(ep,'gpt-image-1.5',output=tmp_path)
    with pytest.raises(ValueError,match='nao foi aprovada'):
        renderer.cover_from_master(ep,'gpt-image-1.5',tmp_path/'capa.jpg')
    write_review(folder,status='aprovado',reason='Foto conferida')
    assert renderer.validate_scenes(ep,'gpt-image-1.5',output=tmp_path)


def test_existing_approved_legacy_scenes_continue_working():
    assert master_static_for_chess_action({'shot_type':'light_moves_king'})
    assert master_static_for_chess_action({'shot_type':'l_moves_king'})
    assert not master_static_for_chess_action({'shot_type':'ots_light'})
    assert not master_static_for_chess_action({'shot_type':'l_reaction'})
    assert not master_static_for_chess_action({'subject':'personagens'})
