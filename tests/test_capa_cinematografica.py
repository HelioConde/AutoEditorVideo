"""Offline regression tests for the new reusable cinematic Shorts cover."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from capa_cinematografica import (
    SIZE, STYLE, cover_options, load_font, render_cover, title_layout
)
import renderizar_master_remotion as renderer
from shorts_studio import build_command


def make_source() -> Image.Image:
    image=Image.new('RGB',(1024,1536),(45,61,92))
    painter=ImageDraw.Draw(image)
    painter.rectangle((0,0,500,1536),fill=(25,86,140))
    painter.rectangle((530,0,1023,1535),fill=(149,31,39))
    painter.ellipse((120,300,430,900),fill=(222,163,94))
    painter.ellipse((620,310,940,900),fill=(202,171,130))
    painter.rectangle((180,1040,880,1260),fill=(89,81,69))
    return image


def test_cinematic_cover_is_full_9_16_not_letterboxed(tmp_path):
    destination=tmp_path/'premium.jpg'
    report=render_cover(make_source(),'XEQUE-MATE MENTAL',destination,zoom=1.10)
    assert destination.is_file()
    assert report['style']==STYLE
    assert report['size']==[1080,1920]
    with Image.open(destination) as im:
        assert im.size==SIZE and im.format=='JPEG'
        # No artificial black bands at the bottom, unlike the old cover.
        assert max(im.getpixel((540,1870)))>12
        # Large, bright top headline visible on small screens.
        cropped=im.crop((45,160,1030,500))
        assert max(cropped.convert('L').getextrema())>205
    assert destination.stat().st_size>20_000


def test_short_title_gets_two_large_rows():
    im=Image.new('RGB',SIZE,'black')
    lines,font,size=title_layout(ImageDraw.Draw(im),'XEQUE-MATE MENTAL')
    assert lines==['XEQUE-MATE','MENTAL']
    assert size>=54
    assert font is not None


def test_story_specific_cover_config_and_default(tmp_path):
    folder=tmp_path/'configs'
    folder.mkdir()
    (folder/'cover-design.json').write_text(json.dumps({
       'schema':'arquivo-otaku/cover-design/v1',
       'default':{'style':STYLE,'zoom':1.05,'focus_x':.5,'focus_y':.4},
       'episodes':{'003-death-note-xadrez':{
          'scene':'06','zoom':1.10,'title':'XEQUE-MATE MENTAL'
       }}
    }))
    ours=cover_options(tmp_path,'003-death-note-xadrez')
    assert ours['scene']=='06' and ours['title']=='XEQUE-MATE MENTAL'
    assert cover_options(tmp_path,'outro-episodio')['zoom']==1.05


def test_cover_selects_cached_layers_from_configured_scene(tmp_path,monkeypatch):
    monkeypatch.setattr(renderer,'ROOT',tmp_path)
    folder=tmp_path/'scene06'
    folder.mkdir()
    from PIL import Image
    background=make_source()
    foreground=Image.new('RGBA',(1024,1536),(0,0,0,0))
    ImageDraw.Draw(foreground).rectangle((350,200,750,920),
                                         fill=(205,177,140,255))
    background.save(folder/'background.png')
    foreground.save(folder/'foreground.png')
    # New fidelity QA compares the extracted foreground to its original
    # master at the same coordinates; the test needs a faithful source.
    Image.alpha_composite(background.convert('RGBA'),foreground).convert('RGB').save(
        folder/'master.png')
    monkeypatch.setattr(renderer,'scene_dir',lambda ep,scene,model:folder)
    monkeypatch.setattr(renderer,'cover_options',
                        lambda root,epid:{'scene':'06','zoom':1.06,
                                          'focus_x':.5,'focus_y':.4,
                                          'title':'XEQUE-MATE MENTAL'})
    # Selecting an explicit episode scene does not regenerate any source.
    def forbidden(*args,**kwargs):
        raise AssertionError('A geracao paga nao deve ser chamada na capa')
    monkeypatch.setattr(renderer,'ensure_voice',forbidden)
    ep={'id':'003-death-note-xadrez','scenes':[
        {'id':'01','subject':'personagens','prompt':'x'*60},
        {'id':'06','subject':'personagens','prompt':'y'*60},
    ]}
    result=renderer.cover_from_master(ep,'gpt-image-1.5',tmp_path/'output.jpg')
    assert result['source']=='background+foreground'
    assert result['scene']=='06'
    assert (tmp_path/'output.jpg').is_file()


def test_studio_cover_button_is_offline_with_zero_image_calls(tmp_path):
    cmd=build_command({'action':'capa','id':'003-death-note-xadrez',
                       'scene':6,'model':'gpt-image-1.5',
                       'budget':0,'all':False},root=tmp_path)
    assert '-SomenteCapa' in cmd
    assert cmd[-1]=='0'
    assert '-Renderizar' not in cmd and '-CriarVoz' not in cmd


@pytest.mark.parametrize('bad',[
    {'zoom':.6},{'zoom':2.0},{'focus_x':-1},{'focus_y':1.3},
    {'scene':'../../foo'},{'style':'unsupported'},
])
def test_cover_options_reject_invalid_layout(tmp_path,bad):
    folder=tmp_path/'configs'
    folder.mkdir()
    default={'style':STYLE,'zoom':1.07,'focus_x':.5,'focus_y':.4}
    (folder/'cover-design.json').write_text(json.dumps({
         'schema':'arquivo-otaku/cover-design/v1',
         'default':{**default,**bad}
    }))
    with pytest.raises(ValueError):
        cover_options(tmp_path,'episodio')


def test_cover_only_cli_skips_voice_and_rendering(tmp_path,monkeypatch):
    monkeypatch.setattr(renderer,'OUT',tmp_path)
    monkeypatch.setattr(renderer,'production_storyboard',
                        lambda *args,**kwargs:tmp_path/'dummy.json')
    monkeypatch.setattr(renderer,'read_storyboard',
                        lambda path:{'id':'003-death-note-xadrez','scenes':[{
                            'id':'01','subject':'personagens','prompt':'x'*50
                        }]})
    def no_voice(*args,**kwargs):
        raise AssertionError('Modo so capa nao deve chamar voz')
    monkeypatch.setattr(renderer,'ensure_voice',no_voice)
    def fake_cover(ep,model,destination):
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(b'jpeg fixture')
        return {'style':STYLE,'title':'TESTE','scene':'01'}
    monkeypatch.setattr(renderer,'cover_from_master',fake_cover)
    assert renderer.main(['--id','003-death-note-xadrez','--somente-capa'])==0
    assert (tmp_path/'003-death-note-xadrez'/'qa-capa.json').is_file()
