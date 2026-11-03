"""Regressão do piloto Jujutsu Kaisen sem misturar metadados Death Note."""
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from roteiro_para_storyboard import select_episode, build_storyboard
from metadata_shorts import load_episodes, publisher_episode


def test_jujutsu_catalogo_publicador():
    ep = select_episode("401-jujutsu-kaisen-ep01")
    assert ep["series"] == "Jujutsu Kaisen"
    assert ep["script"].startswith(ep["hook"])
    assert ep["script"].endswith(ep["cta"])
    assert ep["id"] in load_episodes(include_recaps=True)
    meta = publisher_episode(ep)
    assert "Jujutsu Kaisen" in meta["titulo_youtube"]
    assert "#JujutsuKaisen" in meta["descricao_youtube"]
    assert "Otaku Multicena" in meta["descricao_youtube"]
    assert "#DeathNote" not in meta["descricao_youtube"]
    assert "#ArquivoOtaku" not in meta["descricao_youtube"]
    assert len(meta["titulo_youtube"]) <= 100


def test_jujutsu_storyboard_offline():
    plan = build_storyboard(select_episode("401-jujutsu-kaisen-ep01"))
    assert plan["id"] == "401-jujutsu-kaisen-ep01"
    assert plan["shot_count"] >= 2
    assert all(scene["prompt"].strip() for scene in plan["scenes"])
    assert plan["estimated_duration_s"] <= 60


def test_catalog_inherits_series_from_manifest(tmp_path):
    """Legacy manifests may put series only at manifest root."""
    manifest = tmp_path / "catalog.json"
    manifest.write_text(json.dumps({
        "series": "Jujutsu Kaisen",
        "episodes": [{
            "id": "synthetic-jjk-test",
            "title": "Jujutsu Kaisen: piloto",
            "script": "Roteiro de teste.",
            "cover": "TESTE",
            "description_youtube": "Descricao de teste",
        }]
    }), encoding="utf-8")
    episode = select_episode("synthetic-jjk-test", path=manifest)
    assert episode["series"] == "Jujutsu Kaisen"
    exported = load_episodes(path=manifest)["synthetic-jjk-test"]
    assert exported["series"] == "Jujutsu Kaisen"
    assert publisher_episode(episode)["serie"] == "Jujutsu Kaisen"


def test_publisher_missing_series_raises_human_readable_error():
    with pytest.raises(ValueError, match="sem série"):
        publisher_episode({
            "id": "broken-episode",
            "title": "Sem anime",
            "script": "Roteiro",
            "cover": "CAPA",
            "description_youtube": "Descricao",
        })
