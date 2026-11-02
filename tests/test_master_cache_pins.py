"""Pinned-cache resolution must never spend IA credits or mix other scene variants."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import master_scenes as master

EP={'id':'003-death-note-xadrez'}
SCENE={'id':'06','subject':'personagens','prompt':'a very different new storyboard prompt ' + 'x'*60}
MODEL='gpt-image-1.5'
PIN='06-594007f1c10bb8'


def setup_pin(tmp_path,monkeypatch):
    monkeypatch.setattr(master,'ROOT',tmp_path)
    monkeypatch.setattr(master,'OUT',tmp_path/'assets'/'gerados'/'shorts-animados')
    cfg=tmp_path/'configs'
    cfg.mkdir(parents=True,exist_ok=True)
    (cfg/'scene-cache-pins.json').write_text(json.dumps({
        'schema':'arquivo-otaku/scene-cache-pins/v1',
        'pins':{'003-death-note-xadrez/gpt-image-1.5/06':PIN}
    }),encoding='utf-8')
    cache=master.OUT/EP['id']/'master-scenes'/PIN
    cache.mkdir(parents=True)
    return cache


def test_pinned_cache_uses_existing_reviewed_hash_and_no_new_calls(tmp_path,monkeypatch):
    cache=setup_pin(tmp_path,monkeypatch)
    for name in ('master.png','foreground-raw.png','background-raw.png'):
        (cache/name).write_bytes(b'paid-cache-untouched')
    (cache/'qa.json').write_text(json.dumps(
        {'episode':EP['id'],'scene':SCENE['id']}),encoding='utf-8')
    assert master.scene_dir(EP,SCENE,MODEL)==cache
    master.validate_cache_pin(EP,SCENE,MODEL)
    assert master.estimate(EP,[SCENE],MODEL)==[]
    assert master.estimate(EP,[SCENE],MODEL,repair_background=True)==['06/background-repair']
    assert master.cache_pin(EP,SCENE,'gpt-image-2') is None
    assert master.scene_dir(EP,SCENE,'gpt-image-2')!=cache


def test_missing_pinned_cache_fails_before_generation(tmp_path,monkeypatch):
    cache=setup_pin(tmp_path,monkeypatch)
    with pytest.raises(RuntimeError,match='indisponivel ou incompleto'):
        master.validate_cache_pin(EP,SCENE,MODEL)
    (cache/'master.png').write_bytes(b'x')
    (cache/'foreground-raw.png').write_bytes(b'x')
    (cache/'background-raw.png').write_bytes(b'x')
    (cache/'qa.json').write_text(json.dumps({'episode':EP['id'],'scene':'05'}))
    with pytest.raises(ValueError,match='nao corresponde'):
        master.validate_cache_pin(EP,SCENE,MODEL)


@pytest.mark.parametrize('filename',[
    '../06-594007f1c10bb8', '06-foo', '05-594007f1c10bb8',
    '/etc/passwd', 123
])
def test_pin_rejects_malformed_or_foreign_scene_folder(tmp_path,monkeypatch,filename):
    setup_pin(tmp_path,monkeypatch)
    path=tmp_path/'configs'/'scene-cache-pins.json'
    cfg=json.loads(path.read_text())
    cfg['pins']['003-death-note-xadrez/gpt-image-1.5/06']=filename
    path.write_text(json.dumps(cfg))
    with pytest.raises(ValueError,match='Pin de cache invalido'):
        master.scene_dir(EP,SCENE,MODEL)


def test_unpinned_scene_keeps_prompt_hashed_cache_path(tmp_path,monkeypatch):
    setup_pin(tmp_path,monkeypatch)
    other={'id':'05','subject':'personagens','prompt':'z'*90}
    expected=master.sha(MODEL+'\n'+master.master_prompt(EP,other))
    assert master.scene_dir(EP,other,MODEL).name=='05-'+expected
    assert master.cache_pin(EP,other,MODEL) is None


def test_old_photoshop_foreground_mapping_is_found_in_selected_cache(tmp_path,monkeypatch):
    cache=setup_pin(tmp_path,monkeypatch)
    cfg=tmp_path/'configs'/'foreground-placements.json'
    cfg.write_text(json.dumps({
        'schema':'arquivo-otaku/foreground-placements/v1',
        'placements':{EP['id']+'/'+PIN:{'x':0,'y':-211}}
    }))
    assert master.foreground_placement(EP,master.scene_dir(EP,SCENE,MODEL))==(0,-211)
