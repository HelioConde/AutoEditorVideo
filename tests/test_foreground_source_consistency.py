"""Redrawn-character detection and safe master-image fallback (no paid calls)."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from qa_foreground_fidelity import foreground_fidelity
import master_scenes as master
import renderizar_master_remotion as renderer


def png(im:Image.Image)->bytes:
    out=io.BytesIO()
    im.save(out,format='PNG')
    return out.getvalue()


def scene_art(tmp_path:Path,*,redrawn:bool)->tuple[Path,bytes]:
    folder=tmp_path/'04-test'
    folder.mkdir(parents=True)
    original=Image.new('RGB',master.SIZE,(31,64,107))
    draw=ImageDraw.Draw(original)
    draw.rectangle((150,140,810,1100),fill=(178,65,44))
    draw.rectangle((0,1180,1023,1450),fill=(102,83,60))
    (folder/'master.png').write_bytes(png(original))
    foreground=Image.new('RGBA',master.SIZE,(0,0,0,0))
    d=ImageDraw.Draw(foreground)
    if redrawn:
        # Model altered pose/torso and painted it over the board.
        d.rectangle((50,340,930,1320),fill=(235,220,190,255))
    else:
        d.rectangle((150,140,810,1100),fill=(178,65,44,255))
    raw=png(foreground)
    (folder/'foreground-raw.png').write_bytes(raw)
    (folder/'background-raw.png').write_bytes(
        png(Image.new('RGB',master.SIZE,(31,64,107))))
    return folder,raw


def test_detect_redrawn_torso_over_board_and_preserve_paid_cache(tmp_path):
    folder,raw=scene_art(tmp_path,redrawn=True)
    score=foreground_fidelity(folder/'master.png',folder/'foreground-raw.png')
    assert score['redrawn']
    assert score['render_recommendation']=='master_static'
    assert score['mean_difference']>45
    result=master.execute_scene({'id':'ep-test'},
          {'id':'04','subject':'personagens','prompt':'x'*55},
          'gpt-image-1.5',directory=folder,offline=True)
    assert 'foreground_redesenhado' in result['warnings']
    assert result['foreground_source_consistency']['redrawn']
    assert (folder/'foreground-raw.png').read_bytes()==raw
    assert json.loads((folder/'qa.json').read_text())['foreground_source_consistency']['render_recommendation']=='master_static'


def test_good_alpha_extraction_is_not_flagged(tmp_path):
    folder,_=scene_art(tmp_path,redrawn=False)
    result=master.execute_scene({'id':'ep-test'},
        {'id':'04','subject':'personagens','prompt':'x'*55},
        'gpt-image-1.5',directory=folder,offline=True)
    assert not result['foreground_source_consistency']['redrawn']
    assert 'foreground_redesenhado' not in result['warnings']


def test_static_master_fallback_protects_video_and_raw_files(tmp_path,monkeypatch):
    folder,_=scene_art(tmp_path,redrawn=True)
    ep={'id':'ep-test','scenes':[{'id':'04','subject':'personagens',
                                  'trecho_roteiro':'momento forte da historia'}]}
    (folder/'foreground.png').write_bytes((folder/'foreground-raw.png').read_bytes())
    (folder/'background.png').write_bytes((folder/'background-raw.png').read_bytes())
    (folder/'foreground-normalized.png').write_bytes(
        (folder/'foreground-raw.png').read_bytes())
    (folder/'qa.json').write_text(json.dumps(
        {'status':'aguardando_revisao_visual','warnings':[],
         'alpha':{'margin_warning':False},'composition':{'alignment_warning':False}}))
    monkeypatch.setattr(renderer,'scene_dir',lambda *args:folder)
    monkeypatch.setattr(renderer,'select_episode',lambda *args:{'cover':'EXEMPLO'})
    validated=renderer.validate_scenes(ep,'gpt-image-1.5',output=tmp_path)
    assert validated[0]['render_mode']=='master_static'
    before=(folder/'foreground.png').read_bytes()
    voice=tmp_path/'voice.mp3'
    voice.write_bytes(b'fake mp3 for props')
    public=tmp_path/'public'
    props=renderer.build_props(ep,voice,[],3.0,model='gpt-image-1.5',
                               output=tmp_path,public=public)
    assert props['scenes'][0]['renderMode']=='master_static'
    target=public/'generated'/'ep-test'
    assert (target/'scene-04-background.png').read_bytes()==(
        folder/'master.png').read_bytes()
    with Image.open(target/'scene-04-foreground.png') as foreground:
        assert foreground.getchannel('A').getextrema()==(0,0)
    assert (folder/'foreground.png').read_bytes()==before


def test_cover_uses_master_for_redrawn_foreground(tmp_path,monkeypatch):
    folder,_=scene_art(tmp_path,redrawn=True)
    (folder/'foreground.png').write_bytes((folder/'foreground-raw.png').read_bytes())
    (folder/'background.png').write_bytes((folder/'background-raw.png').read_bytes())
    ep={'id':'ep-test','scenes':[{'id':'04','subject':'personagens','prompt':'x'*55}]}
    monkeypatch.setattr(renderer,'scene_dir',lambda *args:folder)
    monkeypatch.setattr(renderer,'cover_options',lambda *args:{
       'scene':'04','title':'JOGO MENTAL','zoom':1.06,'focus_x':.5,'focus_y':.4})
    report=renderer.cover_from_master(ep,'gpt-image-1.5',tmp_path/'capa.jpg')
    assert report['source']=='master-static-qa'
    assert (tmp_path/'capa.jpg').is_file()


def test_stored_photoshop_position_does_not_trigger_redraw_false_positive(tmp_path):
    folder,_=scene_art(tmp_path,redrawn=False)
    # Shifted layer would mismatch, therefore fidelity checks raw only.
    moved=master.reposition_foreground((folder/'foreground-raw.png').read_bytes(),-25,-88,1.10)
    (folder/'foreground.png').write_bytes(moved)
    score=foreground_fidelity(folder/'master.png',folder/'foreground-raw.png')
    assert not score['redrawn']
