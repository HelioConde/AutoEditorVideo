"""No-cost preparation of only rejected visual scenes for fresh image generation."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import master_scenes as m
from preparar_cenas_reprovadas import prepare_rejected,REVISION_SCHEMA,SAFETY_APPENDIX
from revisao_visual_cenas import write_review,read_review


def fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'OUT',tmp_path/'generated')
    monkeypatch.setattr(m,'ROOT',tmp_path)
    path=m.OUT/'003-death-note-xadrez'/'storyboard-producao.json'
    path.parent.mkdir(parents=True)
    data={
      'schema':'arquivo-otaku/master-storyboards/v2',
      'id':'003-death-note-xadrez',
      'title':'Death Note - chess',
      'scenes':[
         {'id':f'{i:02d}','subject':'personagens',
          'prompt':f'cinematic original unique frame {i:02d} '+('x'*100),
          'shot_type':'generic' if i%2 else 'close',
          'camera_angle':f'angle_{i}','action':'narrative beat'} for i in range(1,7)
      ],
    }
    raw=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
    path.write_text(raw,encoding='utf-8')
    for idx in (2,3,4):
        folder=m.scene_dir(data,data['scenes'][idx-1],'gpt-image-1.5')
        folder.mkdir(parents=True)
        Image.new('RGB',m.SIZE,(idx*10,30,40)).save(folder/'master.png')
        (folder/'foreground-raw.png').write_bytes(b'original paid layer')
        write_review(folder,status='reprovado',reason=f'geometry issue {idx}')
    return path,data,raw


def test_prepare_changes_only_rejected_with_different_hashes_and_backup(tmp_path,monkeypatch):
    path,original,raw=fixture(tmp_path,monkeypatch)
    before={s['id']:m.scene_dir(original,s,'gpt-image-1.5') for s in original['scenes']}
    report=prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert report['changed']
    assert report['scenes']==['02','03','04']
    saved=json.loads(path.read_text(encoding='utf-8'))
    for old,new in zip(original['scenes'],saved['scenes']):
        if old['id'] in ('02','03','04'):
            assert new['prompt'].startswith(old['prompt'])
            assert new['prompt'].endswith(SAFETY_APPENDIX)
            assert new['correcao_visual']['schema']==REVISION_SCHEMA
            assert new['camera_angle']==old['camera_angle']
            assert new['action']==old['action']
            after=m.scene_dir(saved,new,'gpt-image-1.5')
            assert before[old['id']]!=after
            assert not after.exists()
            assert read_review(before[old['id']])['status']=='reprovado'
            assert (before[old['id']]/'foreground-raw.png').read_bytes()==b'original paid layer'
        else:
            assert new==old
            assert m.scene_dir(saved,new,'gpt-image-1.5')==before[old['id']]
    assert Path(report['backup']).read_text(encoding='utf-8')==raw


def test_prepare_is_idempotent_and_never_replaces_new_prompt(tmp_path,monkeypatch):
    path,_,_=fixture(tmp_path,monkeypatch)
    prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    once=path.read_bytes()
    report=prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert not report['changed'] and report['scenes']==[]
    assert path.read_bytes()==once


def test_prepare_rejects_target_scene_explicitly_pinned_to_old_cache(tmp_path,monkeypatch):
    path,original,_=fixture(tmp_path,monkeypatch)
    pinned_folder=m.scene_dir(original,original['scenes'][1],'gpt-image-1.5')
    cfg=tmp_path/'configs'/'scene-cache-pins.json'
    cfg.parent.mkdir()
    cfg.write_text(json.dumps({
        'schema':'arquivo-otaku/scene-cache-pins/v1',
        'pins':{'003-death-note-xadrez/gpt-image-1.5/02':pinned_folder.name}
    }))
    before=path.read_bytes()
    with pytest.raises(ValueError,match='cache fixado'):
        prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert path.read_bytes()==before


def test_prepare_does_nothing_without_rejections(tmp_path,monkeypatch):
    path,data,_=fixture(tmp_path,monkeypatch)
    for index in (2,3,4):
        folder=m.scene_dir(data,data['scenes'][index-1],'gpt-image-1.5')
        write_review(folder,status='aprovado',reason='audited')
    before=path.read_bytes()
    result=prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert result['scenes']==[] and not result['changed']
    assert path.read_bytes()==before


def test_newly_rejected_second_take_can_prepare_third_without_changing_others(tmp_path,monkeypatch):
    path,_,_=fixture(tmp_path,monkeypatch)
    initial=prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert initial['scenes']==['02','03','04']
    take2=json.loads(path.read_text(encoding='utf-8'))
    scene=take2['scenes'][1]
    folder=m.scene_dir(take2,scene,'gpt-image-1.5')
    folder.mkdir(parents=True)
    Image.new('RGB',m.SIZE,(35,30,40)).save(folder/'master.png')
    write_review(folder,status='reprovado',reason='still bad foot')
    before=path.read_bytes()
    next_attempt=prepare_rejected('003-death-note-xadrez','gpt-image-1.5')
    assert next_attempt['scenes']==['02']
    take3=json.loads(path.read_text(encoding='utf-8'))
    new=take3['scenes'][1]
    assert new['correcao_visual']['take']==3
    assert 'TAKE 3' in new['prompt'] and 'TAKE 2' not in new['prompt']
    assert new['prompt'].count('VISUAL REGENERATION')==1
    assert m.scene_dir(take3,new,'gpt-image-1.5')!=folder
    for idx in (0,2,3,4,5):
        assert take3['scenes'][idx]==take2['scenes'][idx]
    assert Path(next_attempt['backup']).read_bytes()==before
