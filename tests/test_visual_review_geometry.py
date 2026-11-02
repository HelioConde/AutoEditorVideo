"""Reject broken master anatomy locally and prevent unusable shots in the Short."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from revisao_visual_cenas import read_review, write_review
from diversidade_visual import direction, direction_prompt
import renderizar_master_remotion as renderer
import master_scenes as master


def test_bad_geometry_manual_review_stays_in_ignored_local_scene_cache(tmp_path):
    folder=tmp_path/'master-scenes'/'04-daebc75c5d3819'
    folder.mkdir(parents=True)
    Image.new('RGB',master.SIZE,(50,60,80)).save(folder/'master.png')
    bad=write_review(folder,status='reprovado',
                     reason='Corpo atravessando o tabuleiro')
    assert bad['status']=='reprovado'
    assert read_review(folder)['reason']=='Corpo atravessando o tabuleiro'
    assert (folder/'visual-review.json').is_file()
    good=write_review(folder,status='aprovado',
                      reason='Refeito e inspecionado')
    assert good['status']=='aprovado'


def test_cannot_reject_without_reason_or_master(tmp_path):
    folder=tmp_path/'master-scenes'/'02-hash'
    folder.mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        write_review(folder,status='reprovado',reason='pe sobre a mesa')
    Image.new('RGB',master.SIZE).save(folder/'master.png')
    with pytest.raises(ValueError):
        write_review(folder,status='reprovado',reason='   ')


def test_manual_rejection_blocks_video_before_copying_or_rendering(tmp_path,monkeypatch):
    folder=tmp_path/'master-scenes'/'02-hash'
    folder.mkdir(parents=True)
    Image.new('RGB',master.SIZE,(20,35,50)).save(folder/'master.png')
    Image.new('RGB',master.SIZE,(20,35,50)).save(folder/'background.png')
    fg=Image.new('RGBA',master.SIZE,(0,0,0,0))
    from PIL import ImageDraw
    ImageDraw.Draw(fg).rectangle((200,400,700,1100),fill=(140,120,100,255))
    fg.save(folder/'foreground.png')
    (folder/'qa.json').write_text(json.dumps({'status':'aguardando_revisao_visual'}))
    write_review(folder,status='reprovado',reason='L tem o pe no tabuleiro')
    monkeypatch.setattr(renderer,'scene_dir',lambda *args:folder)
    ep={'id':'teste','scenes':[{'id':'02','subject':'personagens','prompt':'x'*55}]}
    with pytest.raises(ValueError,match='pe no tabuleiro'):
        renderer.validate_scenes(ep,'gpt-image-1.5',output=tmp_path)
    monkeypatch.setattr(renderer,'cover_options',lambda *args:{
       'scene':'02','title':'Xeque','zoom':1.07,'focus_x':.5,'focus_y':.38})
    with pytest.raises(ValueError,match='Capa bloqueada'):
        renderer.cover_from_master(ep,'gpt-image-1.5',tmp_path/'capa.jpg')


def test_new_chess_prompts_enforce_physical_body_table_geometry():
    ep={'id':'ep-test','effect':'chess'}
    for idx in range(6):
        selected=direction(ep,idx,'um momento','desenvolvimento')
        prompt=direction_prompt(ep,selected)
        assert 'UNDER the table' in prompt
        assert 'BEHIND the tabletop edge' in prompt
        assert 'Only hands and forearms' in prompt


def test_segmentation_prompt_does_not_allow_chessboard_or_redrawn_feet():
    p=master.foreground_prompt({'id':'04','subject':'personagens'})
    assert 'PIXEL-PRESERVING SEGMENTATION' in p
    assert 'chessboard squares' in p
    assert 'feet' in p
    assert 'Do not move the subject' in p
