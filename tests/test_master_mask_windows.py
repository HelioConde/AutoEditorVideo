"""Windows cache regression: an existing mask may be locked by an image viewer.

Offline recomposition must not reopen/overwrite that path, because the
clean background and foreground have already been paid for and cached.
"""
import io
from pathlib import Path
import sys

import pytest

pytest.importorskip('numpy')
Image=pytest.importorskip('PIL.Image')
ImageDraw=pytest.importorskip('PIL.ImageDraw')
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import master_scenes as m


def blob(img):
    file=io.BytesIO()
    img.save(file,format='PNG')
    return file.getvalue()


def fixture_scene(tmp_path):
    directory=tmp_path/'master-scenes'/'06-594007f1c10bb8'
    directory.mkdir(parents=True)
    master=Image.new('RGB',m.SIZE,(30,60,90))
    ImageDraw.Draw(master).rectangle((200,300,660,1040),fill=(190,50,40))
    (directory/'master.png').write_bytes(blob(master))
    foreground=Image.new('RGBA',m.SIZE,(0,0,0,0))
    ImageDraw.Draw(foreground).rectangle((200,300,660,1040),fill=(190,50,40,255))
    (directory/'foreground-raw.png').write_bytes(blob(foreground))
    clean=Image.new('RGB',m.SIZE,(30,60,90))
    paid=blob(clean)
    (directory/'background-raw.png').write_bytes(paid)
    return directory,paid


def test_cached_background_never_overwrites_locked_mask(tmp_path,monkeypatch):
    directory,paid=fixture_scene(tmp_path)
    existing=b'OLD-LOCKED-MASK-BY-PHOTOSHOP'
    (directory/'background-mask.png').write_bytes(existing)
    original_atomic=m.atomic
    writes=[]

    def reject_mask_rewrites(path,data):
        writes.append(path.name)
        if path.name=='background-mask.png':
            raise OSError(22,'Invalid argument',str(path))
        return original_atomic(path,data)

    monkeypatch.setattr(m,'atomic',reject_mask_rewrites)
    result=m.execute_scene({'id':'test-episode'},
                           {'id':'06','subject':'personagens','prompt':'x'*60},
                           'gpt-image-1.5',directory=directory,offline=True)
    assert (directory/'background-mask.png').read_bytes()==existing
    assert 'background-mask.png' not in writes
    assert (directory/'background-raw.png').read_bytes()==paid
    with Image.open(directory/'background.png') as background:
        assert background.convert('RGB').getpixel((300,600))==(30,60,90)
    assert result['background_compositing']=='clean-direct'
    assert result['status']=='aguardando_revisao_visual'


def test_background_repair_still_creates_a_valid_mask(tmp_path):
    directory,_=fixture_scene(tmp_path)
    foreground=directory/'foreground-raw.png'
    mask=directory/'background-mask.png'
    m.make_mask(foreground,mask)
    with Image.open(mask) as img:
        assert img.format=='PNG'
        assert img.size==m.SIZE
        assert img.getchannel('A').getpixel((400,600))<20
    assert m.mask_fingerprint(mask)==m.mask_fingerprint(mask.read_bytes())


def test_repair_fails_with_useful_message_when_mask_is_locked(tmp_path,monkeypatch):
    directory,paid=fixture_scene(tmp_path)
    original_atomic=m.atomic
    def block_mask(path,data):
        if path.name=='background-mask.png':
            raise OSError(22,'Invalid argument',str(path))
        return original_atomic(path,data)
    monkeypatch.setattr(m,'atomic',block_mask)
    calls=[]
    def edit(*args,**kwargs):
        calls.append((args,kwargs))
        return paid
    with pytest.raises(OSError,match='Feche Photoshop'):
        m.execute_scene({'id':'test-episode'},
                        {'id':'06','subject':'personagens','prompt':'x'*60},
                        'gpt-image-1.5',directory=directory,
                        edit=edit,repair_background=True)
    assert not calls
    assert (directory/'background-raw.png').read_bytes()==paid
