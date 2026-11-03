"""Regressão do piloto Jujutsu Kaisen sem misturar metadados Death Note."""
from pathlib import Path
import sys

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
