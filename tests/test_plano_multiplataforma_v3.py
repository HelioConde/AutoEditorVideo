"""QA offline para o plano multiplataforma do Otaku Multicena."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import plano_multiplataforma_v3 as plan


def first_episode():
    return plan.load_episodes(include_recaps=True)["5001-black-clover"]


def test_plan_uses_existing_episode_and_never_uploads(tmp_path):
    item = plan.make_plan(first_episode(), root=tmp_path)
    assert item["mode"] == "offline_proposal_only"
    assert item["automated_publications"] == 0
    assert item["media"]["status"] == "not_checked"
    assert item["platforms"]["youtube"]["publication"] == "no_action"
    assert item["platforms"]["instagram"]["publication"] == "manual_after_review"
    assert item["platforms"]["tiktok"]["publication"] == "manual_after_review"
    assert item["platforms"]["kwai"]["publication"] == "manual_after_review"
    assert item["platforms"]["instagram"]["caption_draft"].startswith(first_episode()["hook"])
    assert "#BlackClover" in item["platforms"]["tiktok"]["caption_draft"]
    assert "#OtakuMulticena" in item["platforms"]["kwai"]["caption_draft"]
    assert set(item["story"]["hook_review_prompts"]) == {
        "curiosidade", "contradicao", "decisao", "misterio", "consequencia"
    }


def test_audio_removed_blocks_only_tiktok(tmp_path):
    item = plan.make_plan(first_episode(), root=tmp_path, tiktok_audio_removed=True)
    assert item["platforms"]["tiktok"]["publication"] == "blocked"
    assert item["platforms"]["tiktok"]["review_status"] == "sound_removed"
    assert "NAO reenviar" in item["platforms"]["tiktok"]["checks"][0]
    assert item["platforms"]["youtube"]["publication"] == "no_action"
    assert item["platforms"]["instagram"]["publication"] == "manual_after_review"
    assert item["platforms"]["kwai"]["publication"] == "manual_after_review"


def test_prevent_path_traversal():
    with pytest.raises(ValueError, match="ID invalido"):
        plan._render_path("../secrets", "equilibrado", Path("/tmp"))


def test_mp4_missing_does_not_claim_ready(tmp_path):
    item = plan.make_plan(first_episode(), root=tmp_path, verify_mp4=True)
    assert item["media"]["status"] == "missing"


def test_ffprobe_verified_video_requires_vertical_audio_and_duration(tmp_path, monkeypatch):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"mock")
    def successful(*args, **kwargs):
        assert args[0][0] == "ffprobe"
        return SimpleNamespace(stdout=json.dumps({
            "format": {"duration": "39.4"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }))
    monkeypatch.setattr(plan.subprocess, "run", successful)
    status = plan.inspect_video(video)
    assert status["status"] == "pass"
    assert status["audio_stream_present"]
    assert status["duration_seconds"] == 39.4
    assert status["resolution"] == [1080, 1920]


def test_ffprobe_rejects_no_audio_long_video_or_bad_aspect(tmp_path, monkeypatch):
    video = tmp_path / "bad.mp4"
    video.write_bytes(b"mock")
    monkeypatch.setattr(plan.subprocess, "run", lambda *_a, **_kw:
        SimpleNamespace(stdout=json.dumps({
            "format": {"duration": "61.2"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
        })))
    status = plan.inspect_video(video)
    assert status["status"] == "failed"
    assert len(status["issues"]) == 3


def test_cli_requires_existing_id_and_outputs_json(tmp_path, capsys):
    out = tmp_path / "multiplatform.json"
    assert plan.main(["--id", "5001-black-clover", "--saida", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["episodes"] == 1
    assert data["automated_publications"] == 0
    assert data["episodes"][0]["id"] == "5001-black-clover"
    assert "Plano salvo" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        plan.main(["--id", "id-inexistente"])


def test_no_automatic_publication_action_in_code():
    source = (ROOT / "scripts" / "plano_multiplataforma_v3.py").read_text(encoding="utf-8")
    assert "requests.post" not in source
    assert "video.publish" not in source
    assert "webbrowser.open" not in source
    assert "tiktok-token.json" not in source
    assert "youtube-token.json" not in source
