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


def edge_cutout():
    """RGBA with an otherwise valid figure very close to the LEFT border."""
    im = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 200, 825, 1120), fill=(165, 80, 90, 255))
    d.rounded_rectangle((160, 920, 720, 1340), radius=50,
                        fill=(205, 105, 130, 255))
    output = io.BytesIO()
    im.save(output, "PNG")
    return output.getvalue()


def test_near_edge_character_auto_reframes_without_another_api_call(tmp_path):
    ready(tmp_path)
    invocations = []
    def editor(source, instruction, model, key, *, transparent):
        invocations.append((source, model, transparent))
        return edge_cutout()
    result = poses.generate(["caminhando"], root=tmp_path, budget=1,
                            editor=editor, key_provider=lambda: "test")
    assert len(invocations) == 1
    assert result["novas_chamadas"] == 1
    assert result["reenquadradas_sem_ia"] == ["caminhando"]
    assert poses.valid("caminhando", tmp_path)
    art, details = poses.paths("caminhando", tmp_path)
    meta = json.loads(details.read_text())
    assert meta["source_qa"]["margin_warning"]
    assert meta["reframe"]["reframed"]
    assert meta["reframe"]["source_may_already_be_cropped"]
    assert meta["status"] == "pending_visual_review"
    assert not meta["qa"]["margin_warning"]
    assert meta["raw_sha256"] == poses.digest(edge_cutout())
    with Image.open(art) as image:
        alpha = image.getchannel("A")
        bounds = alpha.getbbox()
        assert bounds[0] >= 70
        assert bounds[1] >= 70
        assert bounds[2] <= 1024 - 70
        assert bounds[3] <= 1536 - 70


def test_paid_raw_is_kept_after_failed_qa_and_resume_with_zero_calls(tmp_path, monkeypatch):
    reference = ready(tmp_path)
    called = []
    def editor(*_args, **_kw):
        called.append("paid")
        return edge_cutout()
    actual_fit = poses.fit_transparent_pose
    def fail_qa(_image):
        raise ValueError("QA proposital depois do pagamento")
    monkeypatch.setattr(poses, "fit_transparent_pose", fail_qa)
    with pytest.raises(ValueError, match="QA proposital"):
        poses.generate(["caminhando"], root=tmp_path, budget=1,
                       editor=editor, key_provider=lambda: "test")
    assert called == ["paid"]
    assert not poses.paths("caminhando", tmp_path)[0].is_file()
    assert poses.raw_valid("caminhando", poses.image_check(reference), tmp_path)
    assert poses.plan(["caminhando"], root=tmp_path)["chamadas_necessarias"] == 0
    assert poses.plan(["caminhando"], root=tmp_path)["brutos_recuperaveis"] == 1

    monkeypatch.setattr(poses, "fit_transparent_pose", actual_fit)
    recovered = poses.generate(
        ["caminhando"], root=tmp_path, budget=0,
        editor=lambda *_a, **_kw: pytest.fail("Must not make a second request"),
        key_provider=lambda: pytest.fail("No proxy credentials needed"),
    )
    assert recovered["novas_chamadas"] == 0
    assert recovered["recuperadas_cache_bruto"] == ["caminhando"]
    assert poses.valid("caminhando", tmp_path)


def test_succeeded_em_pe_under_previous_prompt_still_valid_and_budget_7(tmp_path):
    ref = ready(tmp_path)
    poses.generate(["em-pe"], root=tmp_path, budget=1,
                   editor=lambda *_a, **_kw: cutout(),
                   key_provider=lambda: "test")
    path, meta_path = poses.paths("em-pe", tmp_path)
    saved = json.loads(meta_path.read_text())
    saved["signature"] = poses.expected_before_margin_fix(
        poses.image_check(ref), "em-pe"
    )
    meta_path.write_text(json.dumps(saved), encoding="utf8")
    assert poses.valid("em-pe", tmp_path)
    summary = poses.plan(list(poses.POSES), root=tmp_path)
    assert summary["chamadas_necessarias"] == 7
    calls = []
    result = poses.generate(
        list(poses.POSES), root=tmp_path, budget=7,
        editor=lambda *_a, **_kw: (calls.append(1), cutout())[1],
        key_provider=lambda: "test"
    )
    assert len(calls) == 7
    assert result["geradas"] == 7
    assert path.is_file()
    assert poses.valid("em-pe", tmp_path)
