"""Offline regression tests: HARD 60s ceiling for every Arquivo Otaku Short."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import shorts_duration as guard
import publicar_tiktok as tiktok
import publicar_shorts_en as youtube_en


@pytest.mark.parametrize("seconds", [1, 30, 55, 59, 59.999, 60])
def test_up_to_60_seconds_is_allowed(seconds):
    assert guard.validate_seconds(seconds) == float(seconds)


@pytest.mark.parametrize("seconds", [0, -1, 60.001, 60.01, 61, 600, math.inf, -math.inf, math.nan])
def test_overlong_or_invalid_short_is_rejected(seconds):
    with pytest.raises(ValueError, match=r"\[60S"):
        guard.validate_seconds(seconds, stage="Teste")


def test_voice_needs_room_for_ending_and_renderer_tail():
    assert guard.validate_planned_audio(59.0) < 60
    with pytest.raises(ValueError, match="60S BLOQUEADO"):
        guard.validate_planned_audio(59.7)
    assert guard.TARGET_MIN_SECONDS == 55
    assert guard.TARGET_MAX_SECONDS == 59
    assert guard.RENDER_TAIL_SECONDS == 0.4


@pytest.mark.parametrize("duration,approved", [(59.99, True), (60.0, True), (60.001, False)])
def test_actual_mp4_duration_is_checked_with_ffprobe(tmp_path, monkeypatch, duration, approved):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"fake-fixture")
    seen = []

    def fake_run(args, **kwargs):
        seen.append((args, kwargs))
        return SimpleNamespace(stdout=str(duration) + "\n")

    monkeypatch.setattr(guard.subprocess, "run", fake_run)
    if approved:
        assert guard.validate_video(video) == duration
    else:
        with pytest.raises(ValueError, match="60S BLOQUEADO"):
            guard.validate_video(video)
    assert seen[0][0][0] == "ffprobe"
    assert seen[0][1].get("check") is True


def test_unverifiable_mp4_is_rejected_before_upload(tmp_path, monkeypatch):
    video = tmp_path / "bad.mp4"
    video.write_bytes(b"invalid")
    monkeypatch.setattr(guard.subprocess, "run",
                        lambda *_args, **_kwargs: SimpleNamespace(stdout="N/A"))
    with pytest.raises(RuntimeError, match="duracao valida"):
        guard.validate_video(video)


@pytest.mark.parametrize("duration,approved", [(59.99, True), (60.01, False)])
def test_tiktok_uploader_rejects_overlong_files_even_as_drafts(tmp_path, monkeypatch, duration, approved):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"dummy")
    probe = {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920,
             "codec_name": "h264", "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac"},
        ],
        "format": {"duration": str(duration)},
    }
    monkeypatch.setattr(tiktok.subprocess, "run",
                        lambda *_args, **_kwargs: SimpleNamespace(stdout=json.dumps(probe)))
    if approved:
        assert tiktok.ffprobe_video(video)["duration"] == duration
    else:
        with pytest.raises(tiktok.TikTokError, match="60S BLOQUEADO"):
            tiktok.ffprobe_video(video)


@pytest.mark.parametrize("duration,approved", [(60, True), (60.001, False)])
def test_english_youtube_uploader_refuses_long_videos(tmp_path, monkeypatch, duration, approved):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"x" * 100001)
    probe = {
        "streams": [
            {"codec_type": "video", "width": 1080, "height": 1920},
            {"codec_type": "audio"},
        ],
        "format": {"duration": str(duration)},
    }
    monkeypatch.setattr(youtube_en.subprocess, "run",
                        lambda *_args, **_kwargs: SimpleNamespace(stdout=json.dumps(probe)))
    if approved:
        youtube_en.validate_mp4(video)
    else:
        with pytest.raises(ValueError, match="60S BLOQUEADO"):
            youtube_en.validate_mp4(video)
