"""Visual variety in the image pipeline; deterministic and NO paid requests."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

from diversidade_visual import (direction, direction_prompt, storyboard_warnings,
                                similar_masters)
from roteiro_para_storyboard import build_storyboard, select_episode
import master_scenes as master


def test_chess_plan_contains_action_angles_and_no_repeated_frontal_duels():
    ep=select_episode('003-death-note-xadrez')
    plan=build_storyboard(ep,max_hold=6)
    scenes=plan['scenes']
    assert plan['schema']=='arquivo-otaku/master-storyboards/v2'
    assert len(scenes)>=5
    assert storyboard_warnings(scenes)==[]
    assert len({(s['shot_type'],s['camera_angle']) for s in scenes})>=5
    assert all(s['must_differ_from_previous'] is True for s in scenes)
    assert all(s['visual_direction_version'].endswith('/v1') for s in scenes)
    assert all(len(s['prompt'])>100 for s in scenes)
    assert any(s['shot_type']=='light_moves_king' and
               'KING' in s['prompt'] and 'METAPHOR' in s['prompt']
               for s in scenes)
    assert any(s['shot_type']=='l_moves_king' and
               'WHITE KING' in s['prompt'] for s in scenes)
    assert any('over-the-shoulder' in s['camera_angle'] for s in scenes)
    assert sum(s['shot_type']=='wide_duel' for s in scenes)==1
    # Never drop words or alter the narrated order to force visual variety.
    assert ' '.join(s['trecho_roteiro'] for s in scenes)==' '.join(ep['script'].split())


@pytest.mark.parametrize('episode_id',[
    '004-death-note-segundo-kira',
    '005-death-note-sangue',
    '006-death-note-shinigami',
    '007-death-note-maca'
])
def test_other_episodes_get_reusable_varied_shots(episode_id):
    ep=select_episode(episode_id)
    plan=build_storyboard(ep,max_hold=6)
    assert storyboard_warnings(plan['scenes'])==[]
    assert len({s['shot_type'] for s in plan['scenes']})>=min(3,len(plan['scenes']))
    assert all(s['subject'] in ('personagens','objeto') for s in plan['scenes'])
    assert all('CRITICAL: Do NOT repeat' in s['prompt']
               for s in plan['scenes'][1:])


def test_storyboard_qa_detects_repeated_camera_and_shot():
    scenes=[
        {'id':'01','shot_type':'wide_duel','camera_angle':'frontal',
         'focus_subject':'L','action':'parado'},
        {'id':'02','shot_type':'wide_duel','camera_angle':'frontal',
         'focus_subject':'L','action':'parado'},
        {'id':'03','shot_type':'wide_duel','camera_angle':'low',
         'focus_subject':'Kira','action':'move'},
    ]
    warnings=storyboard_warnings(scenes)
    assert {'plano_repetido_consecutivo','direcao_visual_duplicada',
            'plano_usado_mais_de_duas_vezes'} <= {x['code'] for x in warnings}


def test_later_shots_never_repeat_previous_and_restrict_shot_count():
    ep=select_episode('003-death-note-xadrez')
    scenes=[]
    for idx in range(18):
        info=direction(ep,idx,'Uma ameaça é revelada','desenvolvimento',
                       previous=scenes,last=idx==17)
        assert not scenes or info['shot_type']!=scenes[-1]['shot_type']
        assert sum(s['shot_type']==info['shot_type'] for s in scenes)<2
        scenes.append({'id':f'{idx+1:02d}',**info})
    assert storyboard_warnings(scenes)==[]


def test_visual_similarity_detects_exact_and_near_duplicates_offline(tmp_path):
    first=tmp_path/'01.png'
    duplicate=tmp_path/'02.png'
    unrelated=tmp_path/'03.png'
    im=Image.new('RGB',(1024,1536),(30,85,125))
    d=ImageDraw.Draw(im)
    d.polygon([(80,1300),(700,350),(970,1280)],fill=(210,50,55))
    im.save(first)
    im.save(duplicate)
    difference=Image.new('RGB',(1024,1536),(220,210,160))
    d=ImageDraw.Draw(difference)
    d.rectangle((100,100,800,900),fill=(10,30,70))
    difference.save(unrelated)
    matches=similar_masters(duplicate,[('01',first)])
    assert len(matches)==1 and matches[0]['scene']=='01'
    assert matches[0]['code']=='composicao_repetitiva'
    assert similar_masters(unrelated,[('01',first)])==[]


def test_offline_duplicate_qa_marks_existing_scene_without_changing_png(tmp_path,monkeypatch):
    ep={'id':'ep-teste','scenes':[
        {'id':'01','subject':'personagens','prompt':'x'*55,'shot_type':'wide_duel'},
        {'id':'02','subject':'personagens','prompt':'y'*55,'shot_type':'ots_light'},
    ]}
    root=tmp_path/'master-scenes'
    previous=root/'01'
    current=root/'02'
    previous.mkdir(parents=True)
    current.mkdir(parents=True)
    source=Image.new('RGB',(1024,1536),(55,90,120))
    ImageDraw.Draw(source).ellipse((300,300,800,1050),fill=(155,40,35))
    source.save(previous/'master.png')
    source.save(current/'master.png')
    original=(current/'master.png').read_bytes()
    def scene_dir(ep,scene,model):
        return root/scene['id']
    monkeypatch.setattr(master,'scene_dir',scene_dir)
    report={'warnings':[],'status':'aguardando_revisao_visual'}
    output=master.review_visual_diversity(ep,ep['scenes'][1],
                                          'gpt-image-1.5',current,report)
    assert output['visual_diversity']['status']=='revisar_repeticao'
    assert output['warnings']==['composicao_repetitiva']
    assert (current/'master.png').read_bytes()==original
    assert json.loads((current/'qa.json').read_text())['visual_diversity']['review_required']


def test_existing_legacy_storyboard_works_without_director_metadata():
    legacy=[{'id':'01','prompt':'x'*60,'subject':'personagens'},
            {'id':'02','prompt':'y'*60,'subject':'personagens'}]
    assert storyboard_warnings(legacy)==[]
