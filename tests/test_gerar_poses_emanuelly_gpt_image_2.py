"""Offline tests for Emanuelly GPT Image 2 identity-preserving pose assets."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gerar_poses_emanuelly_gpt_image_2 as poses


def input_file(tmp_path, rgb=(71, 42, 106)):
    path = tmp_path / "foto.png"
    Image.new("RGB", (1122, 1402), rgb).save(path)
    return path


def cutout(*, actual_alpha=True):
    im = Image.new("RGBA", (1024, 1536), (255, 255, 255, 0 if actual_alpha else 255))
    d = ImageDraw.Draw(im)
    d.ellipse((320, 160, 720, 550), fill=(125, 70, 40, 255))
    d.rounded_rectangle((300, 550, 735, 1190), radius=80, fill=(203, 104, 139, 255))
    d.rounded_rectangle((340, 1160, 475, 1380), radius=20, fill=(130, 80, 120, 255))
    d.rounded_rectangle((550, 1160, 685, 1380), radius=20, fill=(130, 80, 120, 255))
    out = io.BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def ready(tmp_path):
    ref = input_file(tmp_path)
    installed = poses.install(ref, root=tmp_path)
    assert installed["upload"] is False
    return poses.private_ref(tmp_path)


def test_eight_distinct_one_pose_per_image_and_no_unwanted_character():
    assert len(poses.POSES) == 8
    assert poses.MODEL == "gpt-image-2"
    prompts = [poses.prompt(p) for p in poses.POSES]
    assert len(set(prompts)) == 8
    for text in prompts:
        assert "SAME CHILD CHARACTER" in text
        assert "TRANSPARENT ALPHA" in text
        assert "NO future characters" in text
        assert "1024x1536" in text
        assert "No floor" in text


def test_installed_reference_is_private_and_original_is_untouched(tmp_path):
    source = input_file(tmp_path)
    before = source.read_bytes()
    info = poses.install(source, root=tmp_path)
    assert info["status"] == "instalada"
    assert source.read_bytes() == before
    assert str(poses.private_ref(tmp_path)).endswith("assets/referencias-privadas/emanuelly-personagem-oficial.png")
    assert "/assets/referencias-privadas/" in (ROOT / ".gitignore").read_text()
    assert poses.install(source, root=tmp_path)["status"] == "ja_instalada"
    other = input_file(tmp_path, (220, 140, 110))
    with pytest.raises(ValueError, match="Ja existe referencia diferente"):
        poses.install(other, root=tmp_path)
    assert len(list(poses.private_ref(tmp_path).parent.glob("historico/*.png"))) == 0
    new = poses.install(other, root=tmp_path, replace=True)
    assert new["status"] == "instalada"
    assert len(list(poses.private_ref(tmp_path).parent.glob("historico/*.png"))) == 1


def test_budget_zero_cannot_issue_proxy_request(tmp_path):
    ready(tmp_path)
    calls = []
    def editor(*args, **kwargs):
        calls.append(1)
        return cutout()
    with pytest.raises(ValueError, match="NENHUMA chamada"):
        poses.generate(["em-pe"], root=tmp_path, budget=0,
                       editor=editor, key_provider=lambda: "test")
    assert not calls


def test_all_eight_call_gpt_image_2_with_the_exact_same_source_and_alpha(tmp_path):
    origin = ready(tmp_path)
    calls = []
    def edit(source, prompt, model, key, *, transparent):
        calls.append((source, prompt, model, transparent, key))
        return cutout()
    result = poses.generate(list(poses.POSES), root=tmp_path, budget=8,
                            editor=edit, key_provider=lambda: "test")
    assert result["geradas"] == 8 and result["publicadas"] == 0
    assert len(calls) == 8
    assert {x[0] for x in calls} == {origin}
    assert {x[2] for x in calls} == {"gpt-image-2"}
    assert all(x[3] is True for x in calls)
    assert len({x[1] for x in calls}) == 8
    for slug in poses.POSES:
        assert poses.valid(slug, tmp_path)
        img, meta = poses.paths(slug, tmp_path)
        saved = json.loads(meta.read_text())
        assert saved["reference_sha256"] == poses.image_check(origin)
        assert saved["status"] == "pending_visual_review"
        assert saved["identity_approved_by_human"] is False
        with Image.open(img) as im:
            assert im.mode == "RGBA" and im.size == (1024, 1536)
            assert im.getchannel("A").getextrema() == (0, 255)
    assert poses.plan(list(poses.POSES), root=tmp_path)["chamadas_necessarias"] == 0
    again = poses.generate(list(poses.POSES), root=tmp_path, budget=0,
                           editor=lambda *args, **kwargs: pytest.fail("cached"),
                           key_provider=lambda: pytest.fail("must not read secrets"))
    assert again["geradas"] == 0


def test_opaque_alpha_checkerboard_fails_before_saving(tmp_path):
    ready(tmp_path)
    with pytest.raises(ValueError, match="alpha inválido|alpha invalido"):
        poses.generate(["ajoelhada"], root=tmp_path, budget=1,
                       editor=lambda *args, **kwargs: cutout(actual_alpha=False),
                       key_provider=lambda: "test")
    assert not poses.paths("ajoelhada", tmp_path)[0].exists()


def test_changed_reference_requires_explicit_regeneration_and_preserves_backup(tmp_path):
    old = ready(tmp_path)
    poses.generate(["caminhando"], root=tmp_path, budget=1,
                   editor=lambda *args, **kwargs: cutout(),
                   key_provider=lambda: "test")
    old_art = poses.paths("caminhando", tmp_path)[0].read_bytes()
    new_source = input_file(tmp_path, (20, 30, 40))
    poses.install(new_source, root=tmp_path, replace=True)
    assert not poses.valid("caminhando", tmp_path)
    with pytest.raises(ValueError, match="Use -Refazer"):
        poses.generate(["caminhando"], root=tmp_path, budget=1,
                       editor=lambda *args, **kwargs: pytest.fail("should not call"))
    done = poses.generate(["caminhando"], root=tmp_path, budget=1,
                          replace=True, editor=lambda *args, **kwargs: cutout(),
                          key_provider=lambda: "test")
    assert done["geradas"] == 1
    backups = list((poses.pose_dir(tmp_path) / "historico").glob("*.png"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == old_art
    assert poses.valid("caminhando", tmp_path)


def test_story_pipeline_remains_separate_and_no_upload():
    program = (ROOT / "scripts" / "gerar_poses_emanuelly_gpt_image_2.py").read_text()
    assert "youtube.upload" not in program
    assert "videos().insert" not in program
    assert "gpt-image-1.5" not in program
    assert "render:emanuelly" not in program
