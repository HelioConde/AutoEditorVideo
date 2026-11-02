"""Offline regression tests for clean background + Photoshop foreground adjustment."""
import io
import json
from pathlib import Path
import sys

import pytest

pytest.importorskip('numpy')
Image=pytest.importorskip('PIL.Image')
ImageDraw=pytest.importorskip('PIL.ImageDraw')

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import master_scenes as master


def png(image):
    output=io.BytesIO()
    image.save(output,format='PNG')
    return output.getvalue()


def test_photoshop_style_composite_has_no_master_ghosts_and_preserves_raw(tmp_path,monkeypatch):
    monkeypatch.setattr(master,'ROOT',tmp_path)
    folder=tmp_path/'assets'/'gerados'/'shorts-animados'/'ep-teste'/'master-scenes'/'06-hash'
    folder.mkdir(parents=True)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({
        'schema':'arquivo-otaku/foreground-placements/v1',
        'placements':{'ep-teste/06-hash':{'x':0,'y':-211}}
    }),encoding='utf-8')

    scene={'id':'06','subject':'personagens','prompt':'x'*55}
    ep={'id':'ep-teste'}
    background=Image.new('RGB',master.SIZE,(28,56,112))
    ImageDraw.Draw(background).rectangle((200,1000,820,1140),fill=(75,90,115))
    original=background.copy()
    # The master includes a silhouette and an unmasked detached hair fragment.
    drawer=ImageDraw.Draw(original)
    drawer.rectangle((400,650,600,960),fill=(180,45,38))
    drawer.rectangle((40,280,58,306),fill=(180,45,38))
    (folder/'master.png').write_bytes(png(original))
    raw_foreground=Image.new('RGBA',master.SIZE,(0,0,0,0))
    ImageDraw.Draw(raw_foreground).rectangle((400,650,600,960),fill=(180,45,38,255))
    raw_data=png(raw_foreground)
    (folder/'foreground-raw.png').write_bytes(raw_data)
    raw_bg=png(background)
    (folder/'background-raw.png').write_bytes(raw_bg)

    report=master.execute_scene(ep,scene,'gpt-image-1.5',directory=folder,offline=True)
    with Image.open(folder/'background.png') as final_bg:
        assert final_bg.convert('RGB').getpixel((49,293))==(28,56,112)
        assert final_bg.convert('RGB').getpixel((490,740))==(28,56,112)
    with Image.open(folder/'foreground.png') as final_fg:
        assert final_fg.getpixel((490,480))[3]==255
        assert final_fg.getpixel((490,850))[3]==0
    # Background is already cached: no mask file needs to be rewritten.
    assert not (folder/'background-mask.png').exists()
    with Image.open(io.BytesIO(master.mask_png(folder/'foreground-normalized.png'))) as mask:
        # In-memory mask stays at master coordinates, not shifted display coords.
        assert mask.getchannel('A').getpixel((490,740)) < 20
    assert (folder/'foreground-raw.png').read_bytes()==raw_data
    assert (folder/'background-raw.png').read_bytes()==raw_bg
    assert report['foreground_offset']=={'x':0,'y':-211}
    assert report['background_compositing']=='clean-direct'
    assert (folder/'foreground-normalized.png').is_file()
    assert (folder/'comparacao.jpg').is_file()
    assert (folder/'diferencas.jpg').is_file()


def test_foreground_offset_scoped_to_exact_scene_hash(tmp_path,monkeypatch):
    monkeypatch.setattr(master,'ROOT',tmp_path)
    config=tmp_path/'configs'/'foreground-placements.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'schema':'arquivo-otaku/foreground-placements/v1',
             'placements':{'ep-teste/06-hash':{'x':0,'y':-211}}}))
    ep={'id':'ep-teste'}
    assert master.foreground_placement(ep,Path('/tmp/06-hash'))==(0,-211)
    assert master.foreground_placement(ep,Path('/tmp/06-outrohash'))==(0,0)
    assert master.foreground_placement({'id':'outro'},Path('/tmp/06-hash'))==(0,0)


@pytest.mark.parametrize('value',[
    {'x':None,'y':0}, {'x':10.5,'y':0}, {'x':0,'y':-1000},
])
def test_placement_validation_rejects_bad_offsets(tmp_path,monkeypatch,value):
    monkeypatch.setattr(master,'ROOT',tmp_path)
    path=tmp_path/'configs'/'foreground-placements.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'schema':'arquivo-otaku/foreground-placements/v1',
                                'placements':{'ep-teste/06-hash':value}}))
    with pytest.raises(ValueError):
        master.foreground_placement({'id':'ep-teste'},Path('06-hash'))


def test_zero_offset_keeps_original_foreground_bytes():
    im=Image.new('RGBA',master.SIZE,(0,0,0,0))
    ImageDraw.Draw(im).rectangle((100,200,200,400),fill=(200,20,40,255))
    source=png(im)
    assert master.reposition_foreground(source,0,0)==source
