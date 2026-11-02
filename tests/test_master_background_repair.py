"""Regression tests for background cleanup; no proxy or paid calls."""
import io
from pathlib import Path
import sys

import pytest

pytest.importorskip('numpy')
Image = pytest.importorskip('PIL.Image')
ImageDraw = pytest.importorskip('PIL.ImageDraw')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from master_scenes import (SIZE, estimate, execute_scene, find_clean_background,
                           make_mask, background_mask_warnings, mask_fingerprint)


def as_png(im):
    stream = io.BytesIO()
    im.save(stream, format='PNG')
    return stream.getvalue()


def test_mask_covers_hair_tips_and_fingers(tmp_path):
    fg = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(fg).rectangle((500, 500, 520, 540), fill=(200, 50, 50, 255))
    path = tmp_path / 'foreground.png'
    path.write_bytes(as_png(fg))
    mask = tmp_path / 'background-mask.png'
    make_mask(path, mask)
    with Image.open(mask) as image:
        alpha = image.getchannel('A')
        assert alpha.getpixel((510, 520)) < 20
        assert alpha.getpixel((486, 520)) < 20
        assert alpha.getpixel((410, 520)) > 230


def test_clean_background_requires_matching_camera(tmp_path):
    scenes = tmp_path / 'master-scenes'
    current = scenes / '06-test'
    candidate = scenes / '03-test'
    current.mkdir(parents=True)
    candidate.mkdir(parents=True)
    base = Image.new('RGB', SIZE, (70, 110, 160))
    ImageDraw.Draw(base).rectangle((0, 350, 1023, 380), fill=(180, 120, 50))
    clean = base.copy()
    ImageDraw.Draw(base).rectangle((340, 450, 680, 1150), fill=(220, 45, 40))
    master = current / 'master.png'
    master.write_bytes(as_png(base))
    mask = Image.new('RGBA', SIZE, (0, 0, 0, 255))
    ImageDraw.Draw(mask).rectangle((325, 425, 695, 1175), fill=(0, 0, 0, 0))
    mask_path = current / 'background-mask.png'
    mask_path.write_bytes(as_png(mask))
    # Generated backgrounds are NOT clean/approved by default.
    unapproved = candidate / 'background.png'
    unapproved.write_bytes(as_png(clean))
    assert find_clean_background(master, mask_path, current) is None
    plate = candidate / 'background-clean.png'
    plate.write_bytes(as_png(clean))
    assert find_clean_background(master, mask_path, current) == plate
    plate.write_bytes(as_png(Image.new('RGB', SIZE, (40, 40, 40))))
    assert find_clean_background(master, mask_path, current) is None


def test_repair_background_preserves_raw_backup(tmp_path):
    folder = tmp_path / 'master-scenes' / '06-test'
    folder.mkdir(parents=True)
    scene = {'id': '06', 'subject': 'personagens', 'prompt': 'x' * 60}
    ep = {'id': 'test-episode'}
    master = Image.new('RGB', SIZE, (62, 82, 113))
    ImageDraw.Draw(master).rectangle((300, 410, 730, 1180), fill=(200, 40, 40))
    (folder / 'master.png').write_bytes(as_png(master))
    fg = Image.new('RGBA', SIZE, (0, 0, 0, 0))
    ImageDraw.Draw(fg).rectangle((300, 410, 730, 1180), fill=(200, 40, 40, 255))
    (folder / 'foreground-raw.png').write_bytes(as_png(fg))
    old = as_png(Image.new('RGB', SIZE, (30, 70, 100)))
    replacement = as_png(Image.new('RGB', SIZE, (62, 82, 113)))
    (folder / 'background-raw.png').write_bytes(old)
    calls = []

    def edit(image, prompt, model, **kwargs):
        calls.append((image, kwargs))
        return replacement

    result = execute_scene(ep, scene, 'gpt-image-1.5', directory=folder,
                           edit=edit, repair_background=True)
    backups = list(folder.glob('background-raw-backup-*.png'))
    assert len(calls) == 1
    assert len(backups) == 1
    assert backups[0].read_bytes() == old
    assert (folder / 'background-raw.png').read_bytes() == replacement
    assert (folder / 'background-raw-mask.sha256').read_text().strip() == mask_fingerprint(
        folder / 'background-mask.png')
    assert result['warnings'] == []
    assert result['background_source'] == 'inpainting'
    assert (folder / 'qa.json').is_file()


def test_estimate_counts_only_requested_background_repair(monkeypatch, tmp_path):
    import master_scenes
    monkeypatch.setattr(master_scenes, 'scene_dir',
                        lambda ep, scene, model: tmp_path / ep['id'] / scene['id'])
    ep = {'id': 'test-episode'}
    scene = {'id': '01', 'subject': 'personagens', 'prompt': 'x' * 60}
    folder = master_scenes.scene_dir(ep, scene, 'gpt-image-1.5')
    folder.mkdir(parents=True)
    for name in ('master.png', 'foreground-raw.png', 'background-raw.png'):
        (folder / name).write_bytes(b'existing')
    assert estimate(ep, [scene], 'gpt-image-1.5') == []
    assert estimate(ep, [scene], 'gpt-image-1.5', repair_background=True) == ['01/background-repair']


def test_old_background_without_mask_record_is_flagged(tmp_path):
    mask = tmp_path / 'background-mask.png'
    mask.write_bytes(b'mask-1')
    assert background_mask_warnings(tmp_path, mask) == ['background_sem_registro_de_mascara']
    (tmp_path / 'background-raw-mask.sha256').write_text(mask_fingerprint(mask)+'\n')
    assert background_mask_warnings(tmp_path, mask) == []
    mask.write_bytes(b'mask-2')
    assert background_mask_warnings(tmp_path, mask) == ['background_gerado_com_mascara_diferente']


def test_previously_approved_clean_plate_is_not_taken_from_another_camera(tmp_path):
    scenes = tmp_path / 'master-scenes'
    target = scenes / '05'
    other = scenes / '04'
    target.mkdir(parents=True)
    other.mkdir(parents=True)
    Image.new('RGB', SIZE, (180, 100, 80)).save(target / 'master.png')
    Image.new('RGBA', SIZE, (0, 0, 0, 255)).save(target / 'background-mask.png')
    Image.new('RGB', SIZE, (40, 120, 190)).save(other / 'background-clean.png')
    assert find_clean_background(target / 'master.png',
                                 target / 'background-mask.png', target) is None
