"""Preflight editorial and metadata QA for Death Note 40-second curiosity.

Offline: does not synthesize voice, generate art, render or upload.
"""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from roteiro_para_storyboard import select_episode
from metadata_shorts import publisher_episode


def test_death_note_40s_hook_cta_and_factual_exception():
    episode = select_episode("202-death-note-40-segundos")
    assert episode["series"] == "Death Note"
    assert episode["format_type"] == "curiosidade"
    assert episode["script"].startswith(episode["hook"])
    assert episode["script"].endswith(episode["cta"])
    assert episode["hook"] == "Um nome. Um rosto. Quarenta segundos."
    assert 100 <= len(episode["script"].split()) <= 135
    assert "não indicar outra causa" in episode["script"]
    assert "nem toda morte" in episode["script"]
    assert "Light" in episode["script"]
    assert "Otaku Multicena" not in episode["script"]


def test_death_note_40s_uses_brand_and_accurate_metadata():
    episode = select_episode("202-death-note-40-segundos")
    data = publisher_episode(episode)
    assert data["serie"] == "Death Note"
    assert "40 SEGUNDOS" in data["titulo_youtube"]
    assert len(data["titulo_youtube"]) <= 100
    desc = data["descricao_youtube"]
    assert "#DeathNote" in desc
    assert "#OtakuMulticena" in desc
    assert "#ArquivoOtaku" not in desc
    assert "não significam que todas as mortes" in desc
    assert "geradas por IA" in desc
    assert len(desc) <= 5000
