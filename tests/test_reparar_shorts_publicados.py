"""Regression tests for UTF-8 metadata and safe repair of existing Shorts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import metadata_shorts as metadata
import reparar_shorts_publicados as repair


def test_all_five_descriptions_are_valid_ptbr_unicode(tmp_path):
    episodes = metadata.load_episodes()
    assert len(episodes) == 5
    for episode_id in repair.IDS:
        entry = metadata.publisher_episode(episodes[episode_id])
        title = entry["titulo_youtube"]
        description = entry["descricao_youtube"]
        assert len(title) <= 100
        assert "Análise e comentário sobre Death Note" in description
        assert "Ilustrações geradas" in description
        assert not any(bad in description for bad in ("AnÃ", "Ã§", "\ufffd"))
        p = tmp_path / (episode_id + ".json")
        p.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        assert json.loads(p.read_text(encoding="utf-8"))["descricao_youtube"] == description


def test_plan_finds_only_exact_saved_upload_records_and_covers(tmp_path):
    src = metadata.MANIFEST
    content = src.read_text(encoding="utf-8")
    manifest = tmp_path / "conteudos" / src.name
    manifest.parent.mkdir(parents=True)
    manifest.write_text(content, encoding="utf-8")
    states = tmp_path / "assets" / "gerados" / "publicacao-youtube"
    states.mkdir(parents=True)
    for index, ep_id in enumerate(repair.IDS):
        folder = tmp_path / "assets" / "gerados" / "shorts-animados" / ep_id
        folder.mkdir(parents=True)
        mp4 = folder / f"{ep_id}-master-multicenas-personagens-v3-equilibrado.mp4"
        mp4.write_bytes(f"distinct video {index}".encode("ascii"))
        digest = hashlib.sha256(mp4.read_bytes()).hexdigest()
        (states / f"estado-upload-{digest[:12]}.json").write_text(
            json.dumps({"video_sha256": digest, "video_id": f"VIDEO_id_{index}"}),
            encoding="utf-8",
        )
        Image.new("RGB", (1080, 1920), "navy").save(folder / f"{ep_id}-master-capa.jpg")
    planned = repair.plan_items(root=tmp_path)
    assert len(planned) == 5
    assert len({item["video_id"] for item in planned}) == 5
    assert all(item["cover"].name.endswith("-master-capa.jpg") for item in planned)
    planned[0]["state_path"].unlink()
    with pytest.raises(FileNotFoundError, match="Registro do upload ausente"):
        repair.plan_items(root=tmp_path)


def test_remote_title_category_and_tags_are_not_dropped():
    remote = {
        "id": "video123",
        "snippet": {
            "title": "Título já publicado",
            "categoryId": "24",
            "tags": ["Anime", "Death Note"],
            "defaultLanguage": "pt-BR",
            "description": "AnÃ¡lise",
        },
    }
    payload = repair.build_snippet_update(remote, "Análise corrigida")
    assert payload["id"] == "video123"
    assert payload["snippet"]["title"] == "Título já publicado"
    assert payload["snippet"]["categoryId"] == "24"
    assert payload["snippet"]["tags"] == ["Anime", "Death Note"]
    assert payload["snippet"]["defaultLanguage"] == "pt-BR"
    assert payload["snippet"]["description"] == "Análise corrigida"
    assert "status" not in payload


def test_covers_reject_landscape_and_are_checked_before_network(tmp_path):
    cover = tmp_path / "cover.jpg"
    Image.new("RGB", (1280, 720), "red").save(cover)
    with pytest.raises(ValueError, match="9:16"):
        repair.validate_cover(cover)
    Image.new("RGB", (1080, 1920), "red").save(cover)
    repair.validate_cover(cover)
