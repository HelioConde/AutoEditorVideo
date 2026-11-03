"""Renderer-cache regression: visual edits must invalidate an old valid MP4.

All fixtures are local; never invokes TTS, API, Remotion, GitHub or YouTube.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fluxo_unico_short as flow
import narracao_shorts


def test_renderer_fingerprint_changes_for_motion_and_caption_edits(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "ROOT", tmp_path)
    monkeypatch.setattr(flow, "RENDER_SOURCES", ("master.tsx", "caption.ts"))
    (tmp_path / "master.tsx").write_text("first camera", encoding="utf-8")
    (tmp_path / "caption.ts").write_text("small captions", encoding="utf-8")
    initial, _ = flow.renderer_signature()
    assert flow.renderer_signature()[0] == initial
    (tmp_path / "caption.ts").write_text("larger captions", encoding="utf-8")
    assert flow.renderer_signature()[0] != initial
    (tmp_path / "master.tsx").unlink()
    with pytest.raises(flow.PipelineError, match="Fonte do renderizador ausente"):
        flow.renderer_signature()


def test_existing_mp4_rerenders_when_renderer_changes(monkeypatch, tmp_path):
    monkeypatch.setattr(flow, "ROOT", tmp_path)
    monkeypatch.setattr(flow, "RENDER_SOURCES", ("visual.tsx",))
    code = tmp_path / "visual.tsx"
    code.write_text("original", encoding="utf-8")
    out = tmp_path / "shorts-animados"
    episode_id = "qa-ep01"
    folder = out / episode_id
    folder.mkdir(parents=True)
    monkeypatch.setattr(flow, "OUTPUT", out)
    audio = folder / "voz-master.mp3"
    audio.write_bytes(b"real-audio-for-fingerprint-test" * 100)
    ass = folder / "legendas.ass"
    ass.write_text("ASS captions", encoding="utf-8")
    video = folder / "qa-ep01-master-multicenas-personagens-v3-equilibrado.mp4"
    video.write_bytes(b"existing-valid-video")
    cover = folder / "qa-ep01-master-capa.jpg"
    Image.effect_noise((720, 1280), 32).convert("RGB").save(cover, quality=90)
    assert cover.stat().st_size > 10000

    monkeypatch.setattr(flow, "paths", lambda *_a, **_k: (video, cover))
    monkeypatch.setattr(flow, "select_episode", lambda *_a, **_k: {"id": episode_id, "script": "teste"})
    monkeypatch.setattr(narracao_shorts, "ensure_voice", lambda *_a, **_k: (audio, ass))
    monkeypatch.setattr(flow, "validate_video", lambda *_a, **_k: 49.5)
    monkeypatch.setattr(flow, "require_success", lambda *_a, **_k: None)
    renders = []
    monkeypatch.setattr(flow, "run_command", lambda *_a, **kw: renders.append(kw["label"]) or True)

    state = folder / "build-voz-equilibrado.json"
    state.write_text(json.dumps({
        "voice_motor": "edge",
        "voice_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
        "renderer_sha256": "outdated-renderer",
    }), encoding="utf-8")
    kwargs = {"model": "gpt-image-1.5", "profile": "equilibrado",
              "refazer": False, "attempts": 1, "voice_motor": "edge"}
    assert flow.ensure_render(episode_id, **kwargs) == (video, cover)
    assert len(renders) == 1 and "Render" in renders[0]
    state_data = json.loads(state.read_text(encoding="utf-8"))
    assert state_data["renderer_sha256"] == flow.renderer_signature()[0]
    renders.clear()
    assert flow.ensure_render(episode_id, **kwargs) == (video, cover)
    assert renders == []
    code.write_text("camera opening changed", encoding="utf-8")
    assert flow.ensure_render(episode_id, **kwargs) == (video, cover)
    assert len(renders) == 1
