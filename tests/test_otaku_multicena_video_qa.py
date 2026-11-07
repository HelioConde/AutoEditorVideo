"""Offline technical MP4 QA tests with no ffmpeg/video rendering or uploads."""
import importlib
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
av=importlib.import_module("otaku_multicena_video_qa")

def sample_probe(**overrides):
    video={"codec_type":"video","codec_name":"h264","width":1080,
           "height":1920,"avg_frame_rate":"30/1"}
    video.update(overrides)
    return {"streams":[video,{"codec_type":"audio","codec_name":"aac"}],
            "format":{"duration":"40.0"}}

def test_accepts_1080x1920_30fps_with_real_audio_track():
    info=av.parse_probe(sample_probe())
    assert info["fps"]==30 and info["duration_seconds"]==40
    assert info["audio_tracks"]==1
    with pytest.raises(av.AVBlocked,match="PREVIEW_NOT_1080x1920"):
        av.parse_probe(sample_probe(width=1920))
    without_audio=sample_probe()
    without_audio["streams"]=without_audio["streams"][:1]
    with pytest.raises(av.AVBlocked,match="PREVIEW_MISSING_VIDEO_OR_AUDIO"):
        av.parse_probe(without_audio)

def test_barely_audible_and_clipping_are_flagged():
    from_healthy=av.metrics_from_ffmpeg("mean_volume: -18.1 dB\nmax_volume: -2.4 dB\n")
    assert from_healthy["audio_warnings"]==[]
    quiet=av.metrics_from_ffmpeg("mean_volume: -31.1 dB\nmax_volume: -1.0 dB")
    assert "VOICE_MAY_BE_TOO_QUIET" in quiet["audio_warnings"]
    too_loud=av.metrics_from_ffmpeg("mean_volume: -16 dB\nmax_volume: -0.0 dB")
    assert "AUDIO_PEAK_MAY_CLIP" in too_loud["audio_warnings"]
    with pytest.raises(av.AVBlocked,match="VOICE_VIRTUALLY_INAUDIBLE"):
        av.metrics_from_ffmpeg("mean_volume: -70.0 dB\nmax_volume: -60.0 dB")

def test_video_report_never_claims_true_animation_or_human_review(monkeypatch,tmp_path):
    video=tmp_path/"sample.mp4"
    video.write_bytes(b"X"*220000)
    import json
    probe=json.dumps(sample_probe())
    def fake_run(args,*,timeout=160):
        if args[0]=="ffprobe":return probe,""
        if "volumedetect" in args:return "","mean_volume: -17.6 dB\nmax_volume: -2.0 dB"
        return "","black_duration: 3.2\nfreeze_duration: 7.2"
    monkeypatch.setattr(av,"run",fake_run)
    report=av.inspect(video)
    assert report["technical_audio_video_checked"] is True
    assert report["published"] is False
    assert report["human_visual_review"] is False
    assert report["actual_character_motion_verified"] is False
    assert "LONG_BLACK_SEGMENT_REVIEW" in report["warnings"]
    assert "STATIC_VIDEO_OR_LONG_HOLD_REVIEW" in report["warnings"]
    with pytest.raises(av.AVBlocked,match="MP4_CHECKSUM_MISMATCH"):
        av.inspect(video,expected_sha256="0"*64)

def test_quality_qa_has_no_publication_or_image_calls():
    src=(ROOT/"scripts/otaku_multicena_video_qa.py").read_text(encoding="utf-8")
    for marker in ("youtube.videos()", "request_image(", "gh workflow run", "publish("):
        assert marker not in src


def test_ninety_second_video_is_opt_in_and_measured_from_mp4():
    p=sample_probe()
    p["format"]["duration"]="90.07"
    assert av.parse_probe(p,duration_profile="short_90s_test")["duration_seconds"]==90.07
    with pytest.raises(av.AVBlocked,match="VIDEO_OUTSIDE_SHORT_DURATION"):
        av.parse_probe(p)
    for seconds in ("86.8","93.3","180.0"):
        p["format"]["duration"]=seconds
        with pytest.raises(av.AVBlocked,match="NINETY_SECOND_VIDEO_OUTSIDE"):
            av.parse_probe(p,duration_profile="short_90s_test")
    with pytest.raises(av.AVBlocked,match="UNKNOWN_DURATION_PROFILE"):
        av.parse_probe(sample_probe(),duration_profile="invented")
