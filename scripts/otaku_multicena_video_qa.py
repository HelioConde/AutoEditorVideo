#!/usr/bin/env python3
"""Local-only technical audio/video inspection for AutoEditorVideo previews.

Checks the actual MP4 *after* rendering, but cannot certify story accuracy,
character identity, soundtrack licensing, or human visual quality. No upload.
Requires ffmpeg and ffprobe binaries installed on the machine running it.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import subprocess

class AVBlocked(ValueError):
    pass

def run(argv: list[str], *, timeout: int=160) -> tuple[str, str]:
    try:
        completed = subprocess.run(argv,capture_output=True,text=True,
                                   timeout=timeout,check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise AVBlocked("MEDIA_TOOL_UNAVAILABLE_OR_TIMEOUT") from None
    if completed.returncode:
        raise AVBlocked("MEDIA_TOOL_RETURNED_NONZERO")
    return completed.stdout,completed.stderr

def parse_probe(probe: dict, *, duration_profile: str="legacy_short") -> dict:
    streams=probe.get("streams", [])
    video=[x for x in streams if x.get("codec_type")=="video"]
    audio=[x for x in streams if x.get("codec_type")=="audio"]
    if len(video)!=1 or not audio:
        raise AVBlocked("PREVIEW_MISSING_VIDEO_OR_AUDIO")
    v=video[0]
    if v.get("width")!=1080 or v.get("height")!=1920:
        raise AVBlocked("PREVIEW_NOT_1080x1920")
    try:
        rate=float(Fraction(str(v.get("avg_frame_rate","0"))))
        seconds=float(probe["format"]["duration"])
    except (ValueError,ZeroDivisionError,TypeError,KeyError):
        raise AVBlocked("UNREADABLE_VIDEO_TIMING") from None
    if duration_profile=="short_90s_test":
        if not math.isfinite(seconds) or not 87<=seconds<=93:
            raise AVBlocked("NINETY_SECOND_VIDEO_OUTSIDE_87_TO_93S")
    elif duration_profile=="legacy_short":
        if not math.isfinite(seconds) or not 20<=seconds<=60:
            raise AVBlocked("VIDEO_OUTSIDE_SHORT_DURATION")
    else:
        raise AVBlocked("UNKNOWN_DURATION_PROFILE")
    if not 29.5<=rate<=30.5:
        raise AVBlocked("PREVIEW_NOT_30FPS")
    return {"duration_seconds":round(seconds,3),"fps":round(rate,3),
            "audio_tracks":len(audio),"video_codec":str(v.get("codec_name","unknown"))}

def metrics_from_ffmpeg(log:str) -> dict:
    means=re.findall(r"\bmean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB",log)
    peaks=re.findall(r"\bmax_volume:\s*(-?\d+(?:\.\d+)?)\s*dB",log)
    if not means or not peaks:
        raise AVBlocked("UNREADABLE_VOICE_LEVEL")
    mean=float(means[-1]);peak=float(peaks[-1])
    if mean < -45 or peak < -35:
        raise AVBlocked("VOICE_VIRTUALLY_INAUDIBLE")
    warnings=[]
    if mean < -29:
        warnings.append("VOICE_MAY_BE_TOO_QUIET")
    if peak > -0.2:
        warnings.append("AUDIO_PEAK_MAY_CLIP")
    return {"mean_audio_db":mean,"peak_audio_db":peak,"audio_warnings":warnings}

def inspect(video_path:Path, *, expected_sha256:str|None=None,
            duration_profile:str="legacy_short")->dict:
    path=Path(video_path)
    if not path.is_file() or path.suffix.lower()!=".mp4" or path.stat().st_size<200000:
        raise AVBlocked("VIDEO_FILE_MISSING_OR_TOO_SMALL")
    video_sha=sha256(path.read_bytes()).hexdigest()
    if expected_sha256 and video_sha!=expected_sha256:
        raise AVBlocked("MP4_CHECKSUM_MISMATCH")
    output,_=run(["ffprobe","-v","error","-show_format","-show_streams",
                  "-of","json",str(path)])
    try:
        media=parse_probe(json.loads(output),duration_profile=duration_profile)
    except json.JSONDecodeError:
        raise AVBlocked("FFPROBE_INVALID_JSON") from None
    _,levels=run(["ffmpeg","-hide_banner","-nostdin","-i",str(path),
                  "-vn","-af","volumedetect","-f","null","-"],timeout=180)
    sound=metrics_from_ffmpeg(levels)
    _,vision=run(["ffmpeg","-hide_banner","-nostdin","-i",str(path),
                  "-an","-vf","blackdetect=d=1:pix_th=0.07,"
                   "freezedetect=n=-50dB:d=4",
                  "-f","null","-"],timeout=220)
    # Detected boundaries are editorial review signals, not proof of defects.
    black_spans=[float(v) for v in re.findall(
        r"black_duration:\s*(\d+(?:\.\d+)?)",vision)]
    freeze_spans=[float(v) for v in re.findall(
        r"freeze_duration:\s*(\d+(?:\.\d+)?)",vision)]
    warnings=list(sound["audio_warnings"])
    if any(x>1.8 for x in black_spans):
        warnings.append("LONG_BLACK_SEGMENT_REVIEW")
    if any(x>6 for x in freeze_spans):
        warnings.append("STATIC_VIDEO_OR_LONG_HOLD_REVIEW")
    return {
        "schema":"autoeditorvideo/av-inspection/v1",
        "duration_profile":duration_profile,
        "target_duration_seconds":90 if duration_profile=="short_90s_test" else None,
        "video_sha256":video_sha,
        **media, **sound,
        "longest_black_seconds":max(black_spans,default=0),
        "longest_freeze_seconds":max(freeze_spans,default=0),
        "warnings":warnings,
        "technical_audio_video_checked":True,
        "actual_character_motion_verified":False,
        "semantic_narration_to_image_verified":False,
        "human_visual_review":False,
        "published":False,
        "status":"NEEDS_MANUAL_REVIEW_BEFORE_PUBLICATION",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--video",type=Path,required=True)
    p.add_argument("--duration-profile",choices=("legacy_short","short_90s_test"),default="legacy_short")
    p.add_argument("--expected-sha256",default=None)
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    result=inspect(a.video,expected_sha256=a.expected_sha256,
                   duration_profile=a.duration_profile)
    message=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(message,encoding="utf-8")
    else:
        print(message,end="")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (AVBlocked,OSError) as exc:
        raise SystemExit("[AV REVIEW BLOCKED] "+str(exc)) from None
