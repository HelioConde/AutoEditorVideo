"""Testes editoriais da série Kids Emanuelly (sem TTS, sem render ou upload)."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CANON = ROOT / "docs" / "KIDS-EMANUELLY-SERIE-BIBLIA-V1.md"
MANIFEST = ROOT / "conteudos" / "kids-emanuelly-ep01-shortserie-v1.json"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_full_story_is_preserved_verbatim_in_canon_file():
    text = CANON.read_text(encoding="utf-8")
    assert "O Ovo Azul e o Nascimento de Fofinho" in text
    assert "Emanuelly levou o ovo para casa" in text
    assert "Do ovo saiu um bichinho pequeno" in text
    assert "uma gotinha cair de leve na ponta do nariz" in text
    assert "outros ovos especiais ainda apareceriam" in text
    assert "Fofinha Arco-Íris" in text
    assert "Fofinha Rosa" in text
    assert "Raposo" in text
    assert "Porco-espinho" in text
    assert "irmão mais velho" in text
    assert "gêmeas" in text


def test_four_separate_short_scripts_for_one_original_episode():
    data = load()
    assert data["schema"] == "mini-mundo/emanuelly-serie-shorts/v1"
    assert data["episode"] == 1
    assert data["parts_count"] == 4
    assert len(data["parts"]) == 4
    assert data["language"] == "pt-BR"
    assert data["channel"] == "kids"
    assert data["made_for_kids"] is True
    assert data["publish_enabled"] is False
    assert data["upload_authorized"] is False
    assert data["max_video_duration_seconds"] == 60
    assert data["max_audio_duration_seconds"] == 59.2
    assert data["target_duration_seconds"] == {"min": 45, "max": 55}
    assert data["estimated_duration_status"].startswith("requer medicao")
    assert data["origin_story"] == "docs/KIDS-EMANUELLY-SERIE-BIBLIA-V1.md"


def test_each_short_starts_with_hook_and_ends_with_gentle_continuation():
    data = load()
    for i, item in enumerate(data["parts"], 1):
        assert item["part"] == i
        assert item["heading"] == f"EP 01 — Parte {i:02d}/04"
        assert item["id"].startswith(f"kids-emanuelly-ep01-p{i:02d}-")
        assert item["title"].endswith("#Shorts")
        assert len(item["segments"]) >= 7
        assert item["hook"] == item["segments"][0]["spoken_text"]
        assert item["closing_teaser"] == item["segments"][-1]["spoken_text"]
        assert item["narration"] == " ".join(s["spoken_text"] for s in item["segments"])
        assert item["mini_payoff"]
        assert item["estimated_duration_status"] == "nao_cronometrado_por_tts"
        assert item["voice"] == "pt-BR-FranciscaNeural"
        assert "?" in item["hook"]
        assert "?" in item["closing_teaser"]
        assert item["segments"][-1]["pause_after_s"] >= 1.5
        assert 60 <= len(item["narration"].split()) <= 115
        assert item["segments"][0]["pause_after_s"] >= .5
        assert len({s["visual_cue"] for s in item["segments"]}) == len(item["segments"])
        for j, segment in enumerate(item["segments"], 1):
            assert segment["index"] == j
            assert segment["spoken_text"]
            assert segment["visual_cue"]
            assert 0.35 <= segment["pause_after_s"] <= 2
        text = (item["narration"] + " " + item["title"]).casefold()
        for forbidden in ("inscreva-se", "comente", "deixe um like", "compre agora"):
            assert forbidden not in text
        if i == 1:
            assert item["continuity_from_previous"] is None
        else:
            previous = data["parts"][i - 2]
            assert previous["continuity_to_next"] == item["continuity_from_previous"]


def test_story_chronology_and_no_early_twins_birth():
    parts = load()["parts"]
    assert "ovo azul" in parts[0]["narration"].casefold()
    assert "toc, toc" in parts[0]["narration"].casefold()
    assert "toc, toc" in parts[1]["hook"].casefold()
    assert "gatinho de pelúcia azul" in parts[1]["narration"].casefold()
    assert "Fofinho" in parts[1]["narration"]
    assert "gotinha" in parts[1]["closing_teaser"]
    assert "gotinha" in parts[2]["hook"]
    assert "brincar com a água" in parts[2]["narration"]
    assert "triste" in parts[2]["closing_teaser"]
    assert "tristinha" in parts[3]["hook"]
    assert "Abraço".casefold() not in parts[1]["narration"].casefold()
    assert "amigos a magia traria" in parts[3]["closing_teaser"]
    assert not any("fofinha rosa" in p["narration"].casefold() for p in parts)
    assert not any("fofinha arco-íris" in p["narration"].casefold() for p in parts)


def test_no_unverified_video_timing_or_automatic_publish_claim():
    data = load()
    assert all(p["estimated_duration_status"] == "nao_cronometrado_por_tts" for p in data["parts"])
    assert data["publish_enabled"] is False
    assert data["upload_authorized"] is False
    assert "medicao real de TTS" in data["estimated_duration_status"]
    assert "Não" not in ""  # The validation task itself is strictly offline.
