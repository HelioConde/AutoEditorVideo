"""Check real H.264 Remotion smoke render and detect motion via sampled frames.

Only CI-generated synthetic assets; never use private images or music.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path


def media_info(video: Path) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format",
         "-of", "json", str(video)], check=True, capture_output=True, text=True, timeout=45,
    )
    return json.loads(result.stdout)


def validate(info: dict) -> None:
    videos = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    if len(videos) != 1:
        raise ValueError("expected one video stream")
    vid = videos[0]
    if (int(vid.get("width", 0)), int(vid.get("height", 0))) != (480, 854):
        raise ValueError("unexpected resolution")
    if vid.get("codec_name") != "h264":
        raise ValueError("unexpected codec")
    duration = float(info.get("format", {}).get("duration", 0))
    if not 1.4 <= duration <= 1.6:
        raise ValueError("unexpected duration")
    if vid.get("r_frame_rate") != "24/1":
        raise ValueError("unexpected framerate")


def grab(video: Path, seek: float, out: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", str(seek), "-i", str(video), "-frames:v", "1", str(out)],
        check=True, capture_output=True, text=True, timeout=45,
    )


def check_motion(first: Path, last: Path) -> int:
    from PIL import Image, ImageChops
    with Image.open(first) as a, Image.open(last) as b:
        diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
        if diff.getbbox() is None:
            raise ValueError("no visual motion between frames")
        # Avoid counting compression noise as meaningful character/egg motion.
        histogram = diff.convert("L").histogram()
        significant = sum(histogram[18:])
        if significant < 350:
            raise ValueError("insufficient change between frames")
        return significant


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: cloud_smoke_qa.py <synthetic-video-path>")
        return 2
    video = Path(argv[1])
    folder = video.parent
    try:
        validate(media_info(video))
        first = folder / "cloud-smoke-frame-start.png"
        last = folder / "cloud-smoke-frame-end.png"
        grab(video, 0.1, first)
        grab(video, 1.25, last)
        pixels = check_motion(first, last)
        result = {"status":"passed","codec":"h264","resolution":"480x854",
                  "fps":24,"duration_seconds":1.5,
                  "significantly_changed_pixels":pixels,
                  "assets":"synthetic-only","ai_calls":0,"uploads":0}
        (folder / "cloud-smoke-qa.json").write_text(json.dumps(result, indent=2)+"\n",encoding="utf-8")
        print(f"[PASS] H264 Remotion smoke, 480x854, 24fps, moving frames: {pixels}")
        return 0
    except Exception as exc:
        print(f"[FAIL] Cloud render QA: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
