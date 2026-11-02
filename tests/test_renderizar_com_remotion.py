"""Smoke tests offline for Remotion adapter; no proxy / no uploads."""
import json
import sys
from pathlib import Path
import pytest
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import renderizar_com_remotion as mod


def fixture_layers(root:Path, green=False):
    root.mkdir(parents=True,exist_ok=True)
    Image.new('RGB',(720,1080),'#152046').save(root/'background-test.png')
    for kind in ('character','object','extra_object'):
        img=Image.new('RGBA',(720,1080),(0,0,0,0))
        ImageDraw.Draw(img).ellipse((180,180,520,920),fill='#00ff00' if green and kind=='character' else '#ba1540')
        img.save(root/f'{kind}-test.png')
    (root/'voz-demo.mp3').write_bytes(b'fake-voice')
    (root/'legendas.ass').write_text(
        'Dialogue: 0,0:00:00.00,0:00:03.00,Main,,0,0,0,,LEGENDAS TESTE\n',encoding='utf-8')


def test_five_effects_present():
    episodes=json.loads((ROOT/'conteudos'/'testes-animados-5.json').read_text())['episodes']
    assert len(episodes)==5
    assert {e['effect'] for e in episodes}=={'chess','second_kira','blood','ryuk','apple'}


def test_layer_preflight_and_props(tmp_path,monkeypatch):
    folder=tmp_path/'cache'
    fixture_layers(folder)
    monkeypatch.setattr(mod,'audio_duration',lambda _:28.5)
    episodes=json.loads((ROOT/'conteudos'/'testes-animados-5.json').read_text())['episodes']
    effects=set()
    for ep in episodes:
        p=mod.build_episode(ep,folder,tmp_path/'public')
        effects.update(layer['motion'] for layer in p['layers'])
        assert p['audio'].endswith('/voz.mp3')
        assert p['durationFrames']>800
        assert p['captions'][0]['text']=='LEGENDAS TESTE'
    assert {'chess-slide','apple-bounce','blood-drop','reveal','feather'}.issubset(effects)


def test_invalid_alpha_rejected(tmp_path):
    path=tmp_path/'opaque.png'
    Image.new('RGB',(720,1080),'red').save(path)
    with pytest.raises(ValueError,match='alpha'):
        mod.inspect_alpha(path)


def test_chroma_green_rejected(tmp_path):
    fixture_layers(tmp_path,green=True)
    with pytest.raises(ValueError,match='verde residual'):
        mod.inspect_alpha(tmp_path/'character-test.png')


def test_crop_trims_empty_margins(tmp_path):
    fixture_layers(tmp_path)
    output=tmp_path/'cropped.png'
    stats=mod.copy_asset(tmp_path/'object-test.png',output,'object')
    assert output.exists()
    assert Image.open(output).width<720
    assert stats['alpha_fraction']>.1


def test_no_upload():
    source=(ROOT/'scripts'/'renderizar_com_remotion.py').read_text()
    assert 'youtube.videos().insert' not in source
    assert 'publishAt' not in source
