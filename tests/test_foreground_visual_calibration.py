"""Reference-alignment regression for Death Note frames 01 and 05.

Uses synthetic cached RGBA images only; never invokes a paid image endpoint.
Approved frames 02/03/04/06 and other models must remain unchanged.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import pytest

pytest.importorskip('numpy')
Image=pytest.importorskip('PIL.Image')
ImageDraw=pytest.importorskip('PIL.ImageDraw')

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import master_scenes as m


def to_png(im):
    out=io.BytesIO()
    im.save(out,format='PNG')
    return out.getvalue()


def test_reference_adjustments_require_explicit_config_and_remain_model_scoped(tmp_path,monkeypatch):
    """Calibration must be explicitly configured, not silently hardcoded.

    Shipped defaults are empty. The creator's private local adjustments are
    never fabricated or overwritten. A model-specific placement is opt-in.
    """
    monkeypatch.setattr(m,'ROOT',tmp_path)
    ep={'id':'003-death-note-xadrez'}
    for scene in ('01','05','06'):
        assert m.foreground_transform(ep,Path(scene+'-otherhash'),'gpt-image-1.5')==(0,0,1.0)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({
        'schema':'arquivo-otaku/foreground-placements/v1',
        'scene_defaults':{
            '003-death-note-xadrez/gpt-image-1.5/01':{'x':-4,'y':-15,'scale':1.03},
            '003-death-note-xadrez/gpt-image-1.5/05':{'x':-25,'y':-88,'scale':1.10},
        },
        'placements':{
            '003-death-note-xadrez/06-594007f1c10bb8':{'x':0,'y':-211}
        },
    }),encoding='utf-8')
    assert m.foreground_transform(ep,Path('01-otherhash'),'gpt-image-1.5')==(-4,-15,1.03)
    assert m.foreground_transform(ep,Path('05-otherhash'),'gpt-image-1.5')==(-25,-88,1.10)
    for number in ('02','03','04'):
        assert m.foreground_transform(ep,Path(number+'-otherhash'),'gpt-image-1.5')==(0,0,1.0)
    assert m.foreground_transform(ep,Path('06-594007f1c10bb8'),'gpt-image-1.5')==(0,-211,1.0)
    for number in ('01','05'):
        assert m.foreground_transform(ep,Path(number+'-otherhash'),'gpt-image-2')==(0,0,1.0)
        assert m.foreground_transform({'id':'outro-episodio'},
                                      Path(number+'-otherhash'),'gpt-image-1.5')==(0,0,1.0)

def test_foreground_scale_translation_keeps_raw_and_canvas():
    original=Image.new('RGBA',m.SIZE,(0,0,0,0))
    ImageDraw.Draw(original).rectangle((130,220,390,610),fill=(210,30,50,255))
    raw=to_png(original)
    result=m.reposition_foreground(raw,-25,-88,1.10)
    with Image.open(io.BytesIO(result)) as image:
        assert image.size==m.SIZE
        assert image.getpixel((round(160*1.10)-25,round(300*1.10)-88))[3]==255
        assert image.getpixel((160,300))[3]==255
        assert image.getpixel((170,600))[3]==0
    assert raw==to_png(original)


def test_cache_recomposition_uses_scaled_foreground_without_new_ia(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'ROOT',tmp_path)
    folder=tmp_path/'master-scenes'/'05-hash'
    folder.mkdir(parents=True)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({
       'schema':'arquivo-otaku/foreground-placements/v1',
       'scene_defaults':{'ep-teste/gpt-image-1.5/05':{'scale':1.10,'x':-25,'y':-88}}
    }),encoding='utf-8')
    original=Image.new('RGB',m.SIZE,(20,40,70))
    ImageDraw.Draw(original).rectangle((130,220,390,610),fill=(210,30,50))
    (folder/'master.png').write_bytes(to_png(original))
    layer=Image.new('RGBA',m.SIZE,(0,0,0,0))
    ImageDraw.Draw(layer).rectangle((130,220,390,610),fill=(210,30,50,255))
    foreground_raw=to_png(layer)
    (folder/'foreground-raw.png').write_bytes(foreground_raw)
    background_raw=to_png(Image.new('RGB',m.SIZE,(20,40,70)))
    (folder/'background-raw.png').write_bytes(background_raw)
    result=m.execute_scene({'id':'ep-teste'},
       {'id':'05','subject':'personagens','prompt':'x'*60},
       'gpt-image-1.5',directory=folder,offline=True)
    assert result['foreground_scale']==1.10
    assert result['foreground_offset']=={'x':-25,'y':-88}
    assert result['background_compositing']=='clean-direct'
    assert (folder/'foreground-raw.png').read_bytes()==foreground_raw
    assert (folder/'background-raw.png').read_bytes()==background_raw
    assert not (folder/'background-mask.png').exists()
    with Image.open(folder/'foreground-normalized.png') as normalized:
        assert normalized.getpixel((130,220))[3]==255
    with Image.open(folder/'foreground.png') as placed:
        assert placed.getpixel((170,600))[3]==0
        assert placed.getpixel((150,300))[3]==255


@pytest.mark.parametrize('scale',[0,0.7,1.4,True,'1.1',None])
def test_invalid_foreground_scale_is_rejected(tmp_path,monkeypatch,scale):
    monkeypatch.setattr(m,'ROOT',tmp_path)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({
      'schema':'arquivo-otaku/foreground-placements/v1',
      'scene_defaults':{'ep-test/gpt-image-1.5/01':{'scale':scale}}
    }))
    with pytest.raises(ValueError,match='Escala'):
        m.foreground_transform({'id':'ep-test'},Path('01-hash'),'gpt-image-1.5')


def test_exact_placement_overrides_model_scoped_default(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'ROOT',tmp_path)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({
       'schema':'arquivo-otaku/foreground-placements/v1',
       'placements':{'ep-test/05-hash':{'x':8,'y':-15}},
       'scene_defaults':{'ep-test/gpt-image-1.5/05':{'scale':1.10,'x':-25,'y':-88}}
    }))
    assert m.foreground_transform({'id':'ep-test'},Path('05-hash'),'gpt-image-1.5')==(8,-15,1.0)
