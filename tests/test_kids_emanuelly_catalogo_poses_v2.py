"""Future-proof Emanuelly pose catalog: selective GPT Image 2 with no wasted calls."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kids_emanuelly_catalogo_poses_v2 as catalog
import gerar_poses_emanuelly_gpt_image_2 as generator


def dummy_reference(tmp_path: Path) -> Path:
    source = tmp_path / "reference.png"
    Image.new("RGB", (1024, 1536), (100, 65, 105)).save(source)
    generator.install(source, root=tmp_path)
    return generator.private_ref(tmp_path)


def cutout() -> bytes:
    image = Image.new("RGBA", (1024, 1536), (0, 0, 0, 0))
    art = ImageDraw.Draw(image)
    art.ellipse((320, 150, 700, 490), fill=(125, 78, 45, 255))
    art.rounded_rectangle((300, 540, 720, 1200), radius=55,
                          fill=(170, 75, 155, 255))
    art.rounded_rectangle((360, 1110, 460, 1380), radius=20,
                          fill=(130, 90, 145, 255))
    art.rounded_rectangle((580, 1110, 680, 1380), radius=20,
                          fill=(130, 90, 145, 255))
    b = io.BytesIO()
    image.save(b, "PNG")
    return b.getvalue()


def test_catalog_covers_current_story_and_future_events_without_duplicates():
    assert len(catalog.ESSENCIAIS) == 8
    assert len(catalog.EXTRA_POSES) == 46
    assert len(generator.POSES) == 54
    assert len(set(generator.POSES)) == 54
    assert catalog.choose("Essenciais") == list(catalog.ESSENCIAIS)
    assert len(catalog.choose("Ep01")) == 16
    assert len(catalog.choose("Carinho")) == 8
    assert len(catalog.choose("Emocoes")) == 8
    assert len(catalog.choose("Movimento")) == 8
    assert len(catalog.choose("Brincadeiras")) == 6
    assert len(catalog.choose("Cotidiano")) == 8
    assert len(catalog.choose("Futuras")) == 38
    assert len(catalog.choose("Todas")) == 54
    for label, group in catalog.GROUPS.items():
        assert len(group) == len(set(group)), label
        assert set(group) <= set(generator.POSES)
    assert catalog.choose("Carinho", "fazendo-carinho") == ["fazendo-carinho"]
    with pytest.raises(ValueError, match="desconhecid"):
        catalog.choose("Carinho", "../foto")
    with pytest.raises(ValueError, match="desconhecid"):
        catalog.choose("desconhecido")


def test_story_actions_and_kindness_prompts_are_character_only():
    for action in ["fazendo-carinho", "abracando-pelucia", "consolando",
                   "ninando", "segurando-ovo", "dando-beijinho", "caminhando"]:
        prompt = generator.prompt(action)
        assert "TRUE TRANSPARENT ALPHA" in prompt
        assert "gpt-image-1.5" not in prompt
        assert "No floor, scenery" in prompt
        assert "Fofinho" in prompt  # Forbidden by negative instructions.
        assert "NO future characters" in prompt
        assert "ONE single coherent FULL BODY" in prompt
    for action in catalog.EXTRA_POSES:
        assert len(generator.POSES[action]) == 2
        assert "NO future characters" in generator.prompt(action)


def test_new_carinho_pose_is_independent_png_not_a_composite(tmp_path):
    ref = dummy_reference(tmp_path)
    requests = []
    def edit(image_source, instruction, model, key, *, transparent):
        requests.append((image_source, instruction, model, transparent))
        return cutout()
    done = generator.generate(["fazendo-carinho"], root=tmp_path,
                              budget=1, editor=edit,
                              key_provider=lambda: "temporary-test-secret")
    assert done["novas_chamadas"] == 1
    assert done["geradas"] == 1
    assert requests[0][0] == ref
    assert requests[0][2] == "gpt-image-2"
    assert requests[0][3] is True
    assert "INVISIBLE small plush" in requests[0][1]
    path, qa = generator.paths("fazendo-carinho", tmp_path)
    assert path.name == "emanuelly-fazendo-carinho.png"
    assert generator.valid("fazendo-carinho", tmp_path)
    metadata = json.loads(qa.read_text(encoding="utf8"))
    assert metadata["identity_approved_by_human"] is False
    assert metadata["youtube_upload"] is False
    assert generator.plan(["fazendo-carinho"], root=tmp_path)["chamadas_necessarias"] == 0


def test_new_pose_budget_blocks_before_proxy_call(tmp_path):
    dummy_reference(tmp_path)
    called = []
    with pytest.raises(ValueError, match="NENHUMA chamada"):
        generator.generate(catalog.choose("Carinho"), root=tmp_path, budget=1,
                           editor=lambda *a, **k: called.append(1),
                           key_provider=lambda: "test")
    assert called == []


def test_catalog_cli_returns_group_counts_with_no_private_photo(monkeypatch, capsys):
    def forbidden(*_a, **_kw):
        pytest.fail("catalog should be offline")
    monkeypatch.setattr(generator, "generate", forbidden)
    result = generator.main(["--acao", "catalogo"])
    out = json.loads(capsys.readouterr().out)
    assert result == 0
    assert out["groups"]["Carinho"]["total"] == 8
    assert out["groups"]["Todas"]["total"] == 54
    assert out["no_youtube_upload"] is True


def test_incremental_limit_chooses_only_next_missing_poses(monkeypatch):
    valid_pose = {"fazendo-carinho"}
    monkeypatch.setattr(generator, "valid", lambda slug: slug in valid_pose)
    observed = []
    def fake_gen(selected, *, budget, replace):
        observed.append((selected, budget, replace))
        return {"geradas": len(selected), "publicadas": 0}
    monkeypatch.setattr(generator, "generate", fake_gen)
    assert generator.main(["--acao", "gerar", "--grupo", "Carinho",
                           "--quantidade", "2", "--max-chamadas", "2"]) == 0
    assert observed == [(["acariciando-cabeca", "abracando-pelucia"], 2, False)]


def test_legacy_eight_prompts_keep_previous_cache_signatures(tmp_path):
    ref = dummy_reference(tmp_path)
    for slug in catalog.ESSENCIAIS:
        # Earlier prompt does not depend on added group membership.
        assert generator.expected_before_margin_fix(
            generator.image_check(ref), slug
        ) != generator.expected(generator.image_check(ref), slug)
    assert generator.POSES["em-pe"][0].startswith("Standing upright")
    assert generator.POSES["caminhando"][0].startswith("Walking forward")
    assert catalog.ANIMATION_SEQUENCES["carinho-fofinho"][0] == "sentada-carinho"
    assert "fazendo-carinho" in catalog.ANIMATION_SEQUENCES["carinho-fofinho"]
