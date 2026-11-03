"""Offline tests for the resumable one-command AI Short production and YouTube workflow."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fluxo_unico_short as flow
from metadata_shorts import load_episodes, publisher_episode
from roteiro_para_storyboard import select_episode, build_storyboard


def test_death_note_first_three_recaps_registered_in_both_catalogs():
    catalog = load_episodes(include_recaps=True)
    for num in (1, 2, 3):
        ep_id = f"10{num}-death-note-ep0{num}"
        assert ep_id in catalog
        episode = select_episode(ep_id)
        assert episode["episode_number"] == num
        assert episode["series"] == "Death Note"
        assert episode["effect"] == "recap"
        assert 90 <= len(episode["script"].split()) <= 135
        assert "Inscreva-se" in episode["script"]
        assert "continua" in episode["script"] or "continua" in episode["script"].lower()
        assert len(episode["cover"]) >= 8
        metadata = publisher_episode(episode)
        assert metadata["titulo_youtube"] == episode["title"]
        assert metadata["capa_texto"] == episode["cover"]
        assert "episódio" in metadata["descricao_youtube"]
        assert "Ilustrações" not in metadata["descricao_youtube"] or "geradas por IA" in metadata["descricao_youtube"]


def test_all_three_recaps_plan_distinct_scenes_without_calling_ai():
    for n in (1, 2, 3):
        ep = select_episode(f"10{n}-death-note-ep0{n}")
        plan = build_storyboard(ep, max_hold=6)
        assert 3 <= len(plan["scenes"]) <= 60
        assert plan["id"] == ep["id"]
        assert all("Cena inspirada" in scene["prompt"] for scene in plan["scenes"])
        assert all("NÃO desenhar texto" in scene["prompt"] for scene in plan["scenes"])


def test_retry_consumes_budget_and_recovers_cached_partial_scene(monkeypatch):
    pending = [3]
    attempts = []
    def fake_pending(*_args):
        return pending[0]
    def runner(parts, *, label):
        attempts.append((label, parts))
        pending[0] = 2 if len(attempts) == 1 else 0
        return len(attempts) == 2
    monkeypatch.setattr(flow, "pending_calls", fake_pending)
    budget = [5]
    assert flow.generate_scene_with_retry(
        {"id": "recap-test"}, {"id": "01"}, model="gpt-image-1.5",
        budget=budget, attempts=2, runner=runner
    )
    assert len(attempts) == 2
    assert budget[0] == 2
    assert attempts[0][1][-1] == "3"
    assert attempts[1][1][-1] == "2"


def test_retry_never_ignores_missing_assets(monkeypatch):
    monkeypatch.setattr(flow, "pending_calls", lambda *_args: 3)
    calls = []
    def always_fail(args, *, label):
        calls.append(label)
        return False
    budget = [4]
    assert not flow.generate_scene_with_retry(
        {"id": "ep"}, {"id": "01"}, model="gpt-image-1.5",
        budget=budget, attempts=2, runner=always_fail
    )
    assert len(calls) == 2
    assert budget[0] == 2


def test_no_spend_if_lacks_budget_for_one_scene(monkeypatch):
    monkeypatch.setattr(flow, "pending_calls", lambda *_args: 3)
    def unsafe(*_args, **_kwargs):
        pytest.fail("the generator must not be called")
    assert not flow.generate_scene_with_retry(
        {"id": "ep"}, {"id": "01"}, model="gpt-image-1.5",
        budget=[2], attempts=2, runner=unsafe
    )


def test_missing_approved_cover_prevents_publication(tmp_path, monkeypatch):
    monkeypatch.setattr(flow, "OUTPUT", tmp_path / "shorts-animados")
    cached = flow.OUTPUT / "101-death-note-ep01"
    cached.mkdir(parents=True)
    (cached / "voz-master.mp3").write_bytes(b"legacy-edge-test")
    (cached / "legendas.ass").write_text("test", encoding="utf-8")
    monkeypatch.setattr(flow, "validate_video", lambda *_args, **_kwargs: 55)
    monkeypatch.setattr(flow, "run_command", lambda *_args, **_kwargs: True)
    with pytest.raises(flow.PipelineError, match="Capa vertical ausente"):
        flow.ensure_render("101-death-note-ep01", model="gpt-image-1.5",
                           profile="equilibrado", refazer=True, attempts=1)


def test_no_publish_without_explicit_switch(monkeypatch):
    episode = select_episode("101-death-note-ep01")
    monkeypatch.setattr(flow, "select_episode", lambda *_args: episode)
    monkeypatch.setattr(flow, "ensure_voice", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(flow, "generate_scenes", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(flow, "ensure_render", lambda *_args, **_kwargs:
                        (Path("video.mp4"), Path("cover.jpg")))
    monkeypatch.setattr(flow, "metadata_for", lambda *_args: Path("meta.json"))
    monkeypatch.setattr(flow, "publish", lambda *_args, **_kwargs:
                        pytest.fail("Upload must be explicit"))
    assert flow.main(["--id", "101-death-note-ep01", "--max-chamadas", "0"]) == 0


def test_publication_with_nonexistent_oauth_fails_before_generating(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "OAUTH", tmp_path / "missing.json")
    monkeypatch.setattr(flow, "ensure_voice", lambda *_args, **_kwargs:
                        pytest.fail("Cannot generate before preflight OAuth"))
    with pytest.raises(flow.PipelineError, match="OAuth"):
        flow.main(["--id", "101-death-note-ep01", "--publicar"])


def test_missing_mp4_rejected_by_preview(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "OUTPUT", tmp_path)
    with pytest.raises(FileNotFoundError):
        flow.main(["--id", "101-death-note-ep01", "--somente-validar"])


def test_metadata_correct_for_each_episode_separately(tmp_path, monkeypatch):
    monkeypatch.setattr(flow, "PUBLICATION", tmp_path / "youtube")
    seen = []
    for n in (1, 2, 3):
        ep_id = f"10{n}-death-note-ep0{n}"
        path = flow.metadata_for(ep_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        seen.append(data["titulo_youtube"])
        assert data["capa_texto"] == select_episode(ep_id)["cover"]
    assert len(set(seen)) == 3


def test_invalid_metadata_stops_before_voice_images_or_render(monkeypatch):
    """The former JJK KeyError must fail before expensive image generation."""
    ep = select_episode("401-jujutsu-kaisen-ep01")
    monkeypatch.setattr(flow, "select_episode", lambda *_args: ep)
    def bad_metadata(_episode_id):
        raise ValueError("Metadados invalidos de teste")
    monkeypatch.setattr(flow, "metadata_for", bad_metadata)
    monkeypatch.setattr(flow, "ensure_voice", lambda *_a, **_k:
                        pytest.fail("Voz nao pode iniciar antes do metadata preflight"))
    monkeypatch.setattr(flow, "generate_scenes", lambda *_a, **_k:
                        pytest.fail("Imagens nao podem iniciar antes do metadata preflight"))
    monkeypatch.setattr(flow, "ensure_render", lambda *_a, **_k:
                        pytest.fail("Render nao pode iniciar antes do metadata preflight"))
    with pytest.raises(ValueError, match="Metadados invalidos"):
        flow.main(["--id", ep["id"], "--max-chamadas", "0"])
