"""The one-command EN uploader must use signed local Remotion outputs only."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publicar_shorts_en as uploader


def _episode():
    return json.loads((ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json")
                      .read_text(encoding="utf-8"))["episodes"][0]


def _make_render(tmp_path, *, bad_sha=False, bad_origin=False):
    ep = _episode()
    folder = tmp_path / ep["id"] / "en-US"
    folder.mkdir(parents=True)
    video = folder / f"{ep['id']}-en-US-retention-v2.mp4"
    video.write_bytes(b"local mock MP4" * 1000)
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    qa = {
        "id": ep["id"], "status": "renderizado_qa_automatico",
        "render_origin": "external" if bad_origin else "AutoEditorVideo/local/remotion",
        "language": "en-US", "automatic_technical_qa": True,
        "video_sha256": "invalid" if bad_sha else digest,
    }
    (folder / "qa-en-US.json").write_text(json.dumps(qa), encoding="utf-8")
    return ep, video


def test_new_short_selected_from_dedicated_manifest_and_signed_qa(monkeypatch, tmp_path):
    ep, path = _make_render(tmp_path)
    monkeypatch.setattr(uploader, "OUT", tmp_path)
    monkeypatch.setattr(uploader, "validate_mp4", lambda p: None)
    selected = uploader.candidates(
        "vivo", ep["id"], 1,
        ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json"
    )
    assert len(selected) == 1
    assert selected[0]["path"] == path
    assert selected[0]["sha"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert selected[0]["meta"]["idioma"] == "en"
    assert selected[0]["meta"]["categoria"] == "1"


@pytest.mark.parametrize("bad_sha,bad_origin", [(True, False), (False, True)])
def test_tampered_or_external_render_never_uploads(monkeypatch, tmp_path, bad_sha, bad_origin):
    ep, _ = _make_render(tmp_path, bad_sha=bad_sha, bad_origin=bad_origin)
    monkeypatch.setattr(uploader, "OUT", tmp_path)
    monkeypatch.setattr(uploader, "validate_mp4", lambda p: None)
    with pytest.raises(ValueError, match="origem|checksum"):
        uploader.candidates(
            "vivo", ep["id"], 1,
            ROOT / "conteudos" / "otaku-reframe-did-you-know-201-en.json"
        )


def test_different_mp4_same_episode_does_not_duplicate_upload(monkeypatch, tmp_path):
    monkeypatch.setattr(uploader, "STATE", tmp_path / "en" / "estado.json")
    ep = _episode()
    row = {"id": ep["id"], "sha": "newvideo", "path": tmp_path / "render.mp4",
           "meta": {"titulo": ep["title"]}}
    previous = {"id": ep["id"], "sha256": "oldvideo", "status": "enviado",
                "video_id": "YTprevious"}
    saved = {"items": {"oldvideo": previous}}
    with pytest.raises(RuntimeError, match="segunda publicacao automatica"):
        uploader.upload(None, row, "private", saved)


def test_explicit_channel_verification_still_applies():
    with pytest.raises(RuntimeError, match="CONTA ERRADA"):
        uploader.verify_channel_identity(
            [{"id": "UC" + "b" * 22, "snippet": {"title": "Brazilian channel"}}],
            "UC" + "a" * 22
        )
