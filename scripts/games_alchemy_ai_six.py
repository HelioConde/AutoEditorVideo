#!/usr/bin/env python3
"""One-shot AutoEditorVideo illustrated Shorts renderer. NO GAMEPLAY CAPTURE.

This runner creates five original AI images per Short through the repository's
existing image provider, a PT-BR narration, captions and an animated MP4.
It never accesses YouTube credentials or uploads anything. It is not a general
batch entrypoint: the six reserved episodes and owner are hard-coded.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS

MANIFEST = ROOT / "conteudos" / "lote-6-games-alchemy-producao-v1.json"
OUTPUT = ROOT / "cloud-games-alchemy-ai-six"
OWNER = "games_alchemy_six_shorts_20261105"
EXPECTED = {
    "games": ["game-001-gta4-gta5", "game-002-primeira-noite-minecraft",
              "game-003-minecraft-sem-amarelo"],
    "alchemy": ["alchemy-001-chatgpt-gifs",
                "alchemy-002-images-26-consistencia",
                "alchemy-003-gif-animado-tutorial"],
}
IMAGE_CALLS = 30
VOICE = "pt-BR-AntonioNeural"
WIDTH, HEIGHT = 720, 1280
FPS = 24

class PilotError(ValueError):
    pass

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _run(argv: list[str]) -> None:
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    if result.returncode:
        # Never print provider credentials, request payload or personal paths.
        raise PilotError("MEDIA_TOOL_ERROR_" + str(result.returncode))

def _probe(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=False)
    if result.returncode:
        raise PilotError("FFPROBE_FAILED")
    try:
        seconds = float(result.stdout.strip())
    except ValueError:
        raise PilotError("FFPROBE_BAD_DURATION") from None
    if not (0 < seconds < 200):
        raise PilotError("DURATION_OUTSIDE_EXPECTED_RANGE")
    return seconds

def load_manifest() -> dict:
    obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if obj.get("schema") != "autoeditorvideo/games-alchemy-six-video-pilot/v1":
        raise PilotError("UNKNOWN_MANIFEST_SCHEMA")
    if obj.get("production_owner") != OWNER:
        raise PilotError("WRONG_RESERVATION_OWNER")
    if obj.get("visual_policy") != "only_ai_generated_original_illustrations_and_smooth_animation_no_real_gameplay_or_fake_product_UI":
        raise PilotError("AI_ONLY_POLICY_REQUIRED")
    jobs = obj.get("batch")
    if not isinstance(jobs, list) or len(jobs) != 6:
        raise PilotError("EXACTLY_SIX_EPISODES_REQUIRED")
    seen = {"games": [], "alchemy": []}
    for job in jobs:
        channel = job.get("channel")
        if channel not in EXPECTED:
            raise PilotError("UNAPPROVED_CHANNEL")
        seen[channel].append(job.get("reservation_id"))
        assert_reserved(channel, job["reservation_id"], OWNER)
        if job.get("channel_id") != KNOWN_IDS[channel]:
            raise PilotError("CHANNEL_ID_MISMATCH")
        if job.get("ai_illustrations_only") is not True or job.get("footage_required") is not False:
            raise PilotError("REAL_GAMEPLAY_IS_FORBIDDEN")
        if job.get("scene_count") != 5 or len(job.get("scenes", [])) != 5:
            raise PilotError("FIVE_AI_SCENES_PER_VIDEO_REQUIRED")
        if len(job.get("narration_script_draft", "").split()) < 60:
            raise PilotError("NARRATION_TOO_SHORT")
        if not all(s.get("type") == "ai_generated_illustration" and len(s.get("prompt_en", "")) >= 100
                   for s in job["scenes"]):
            raise PilotError("AI_PROMPTS_NOT_READY")
        if job.get("qa", {}).get("youtube_uploaded") is not False:
            raise PilotError("ALREADY_UPLOADED_IN_MANIFEST")
        if not (job.get("title_draft") and job.get("description_draft") and job.get("tags")):
            raise PilotError("SEO_MISSING")
        if len(job["title_draft"]) > 100:
            raise PilotError("TITLE_TOO_LONG")
        if "Visuais ilustrativos" not in job["description_draft"] and "Ilustrações geradas por IA" not in job["description_draft"]:
            raise PilotError("AI_DISCLOSURE_MISSING")
    if any(seen[c] != ids for c, ids in EXPECTED.items()):
        raise PilotError("RESERVED_EPISODES_ORDER_MISMATCH")
    return obj

def environment_guard() -> None:
    if os.getenv("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise PilotError("WRONG_REPOSITORY")
    if os.getenv("GITHUB_REF") != "refs/heads/main":
        raise PilotError("MAIN_ONLY")
    if os.getenv("GITHUB_EVENT_NAME") != "push":
        raise PilotError("ONE_SHOT_PUSH_ONLY")
    if os.getenv("GITHUB_RUN_ATTEMPT") != "1":
        raise PilotError("NO_RERUN_TO_AVOID_DUPLICATE_COST")
    if os.getenv("IMAGE_MODEL") != "gpt-image-2":
        raise PilotError("WRONG_IMAGE_MODEL")
    if os.getenv("MAX_IMAGE_CALLS") != str(IMAGE_CALLS):
        raise PilotError("IMAGE_BUDGET_NOT_30")
    if not os.getenv("PROXY_API_KEY"):
        raise PilotError("IMAGE_PROVIDER_SECRET_UNAVAILABLE")

async def _speak(text: str, out: Path) -> list[dict]:
    import edge_tts
    talk = edge_tts.Communicate(text, VOICE, rate="-6%", boundary="WordBoundary")
    audio = bytearray()
    words = []
    async for event in talk.stream():
        if event.get("type") == "audio":
            audio.extend(event.get("data") or b"")
        elif event.get("type") == "WordBoundary":
            start = event["offset"] / 10000000
            duration = event["duration"] / 10000000
            words.append({"start": start, "end": start + duration, "text": event.get("text", "")})
    if len(audio) < 4000 or len(words) < 35:
        raise PilotError("VOICE_OR_WORD_TIMINGS_MISSING")
    out.write_bytes(audio)
    return words

def _ass_time(seconds: float) -> str:
    centis = max(0, round(seconds * 100))
    hours, remainder = divmod(centis, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02}:{seconds:02}.{cs:02}"

def write_subtitles(words: list[dict], path: Path, duration: float) -> None:
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\nWrapStyle: 2\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,DejaVu Sans,49,&H00FFFFFF,&H00FFFFFF,&H00102030,&H99000000,"
        "1,0,0,0,100,100,0,0,1,3,1,2,42,42,230,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    parts = [header]
    for start in range(0, len(words), 5):
        group = words[start:start + 5]
        txt = " ".join(str(w["text"]).strip() for w in group).replace("{", "(").replace("}", ")")
        txt = txt.replace("\\", "").replace("\n", " ").replace(",", ",")
        begin = max(0, group[0]["start"] - .04)
        end = min(duration + .1, max(group[-1]["end"] + .12, begin + .35))
        parts.append(f"Dialogue: 0,{_ass_time(begin)},{_ass_time(end)},Default,,0,0,0,,{txt}\n")
    path.write_text("".join(parts), encoding="utf-8-sig")

def create_cover(image: Path, dest: Path, title: str, channel: str) -> None:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    with Image.open(image) as raw:
        art = ImageOps.fit(raw.convert("RGB"), (WIDTH, HEIGHT),
                           method=Image.Resampling.LANCZOS, centering=(.5, .4))
    drawer = ImageDraw.Draw(art, "RGBA")
    drawer.rounded_rectangle((25, 735, 695, 1100), radius=34, fill=(8, 14, 29, 205))
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font = ImageFont.truetype(font_path, 49)
    brand = ImageFont.truetype(font_path, 22)
    drawer.text((55, 765), "HÉLIO CONDE" if channel == "games" else "ALCHEMY FLAMES",
                font=brand, fill=(135, 237, 235, 255))
    words, lines, current = title.split(), [], ""
    for word in words:
        proposed = (current + " " + word).strip()
        if drawer.textbbox((0, 0), proposed, font=font)[2] > 596 and current:
            lines.append(current)
            current = word
        else:
            current = proposed
    if current:
        lines.append(current)
    for i, line in enumerate(lines[:4]):
        drawer.text((55, 815 + i * 62), line, font=font, fill=(255, 255, 255, 255),
                    stroke_width=1, stroke_fill=(7, 10, 20, 255))
    dest.parent.mkdir(parents=True, exist_ok=True)
    art.save(dest, "JPEG", quality=92, optimize=True)

def make_segment(image: Path, path: Path, seconds: float) -> None:
    frames = max(1, round(seconds * FPS))
    filter_graph = (
        "scale=720:1280:force_original_aspect_ratio=increase,"
        "crop=720:1280,"
        "zoompan=z='min(zoom+0.00025,1.07)':d=1:s=720x1280:fps=24,"
        "format=yuv420p"
    )
    _run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
          "-loop", "1", "-framerate", str(FPS), "-i", str(image),
          "-frames:v", str(frames), "-vf", filter_graph,
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
          "-pix_fmt", "yuv420p", str(path)])

def render_video(images: list[Path], audio: Path, subtitles: Path, out: Path, duration: float) -> None:
    # Alternate illustrated images with smooth camera motion, never game footage.
    base = duration + .65
    clip_seconds = base / len(images)
    clips = []
    for i, img in enumerate(images):
        clip = out.parent / f"clip-{i + 1:02}.mp4"
        make_segment(img, clip, clip_seconds + .10)
        clips.append(clip)
    listing = out.parent / "list.txt"
    listing.write_text("".join("file '" + p.name + "'\n" for p in clips), encoding="utf-8")
    joined = out.parent / "joined.mp4"
    _run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
          "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", str(joined)])
    # ASS subtitles use timing from the TTS WordBoundary events, not guesses.
    _run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
          "-i", str(joined), "-i", str(audio), "-vf", f"ass={subtitles.name}",
          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
          "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
          str(out)])

def validate_media(video: Path, cover: Path, pictures: list[Path], duration: float) -> dict:
    from PIL import Image
    seconds = _probe(video)
    if abs(seconds - duration) > 3 or not 20 <= seconds <= 180:
        raise PilotError("VIDEO_DURATION_QA_FAILED")
    if not video.is_file() or video.stat().st_size < 250000:
        raise PilotError("EMPTY_VIDEO")
    if not cover.is_file() or cover.stat().st_size < 25000:
        raise PilotError("INVALID_THUMBNAIL")
    with Image.open(cover) as picture:
        if picture.format != "JPEG" or picture.size != (WIDTH, HEIGHT):
            raise PilotError("THUMBNAIL_SHAPE_INVALID")
    if len(pictures) != 5 or len({_sha(p) for p in pictures}) != 5:
        raise PilotError("MISSING_OR_DUPLICATED_AI_ART")
    return {"duration_seconds": round(seconds, 2), "mp4_sha256": _sha(video),
            "cover_sha256": _sha(cover),
            "image_sha256": [_sha(p) for p in pictures],
            "structural_qa": "passed",
            "manual_visual_qc": "not_performed"}

def render_all() -> None:
    manifest = load_manifest()
    environment_guard()
    from gerar_video_codex import proxy_key, request_image, check_proxy_accounts
    key = proxy_key()
    check_proxy_accounts(key)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {"schema": "autoeditorvideo/six-ai-illustrated-review/v1",
               "production_owner": OWNER, "count": 6,
               "publication": "not_performed", "videos": []}
    for job in manifest["batch"]:
        ep = job["reservation_id"]
        target = OUTPUT / ep
        target.mkdir(parents=True, exist_ok=True)
        voice = target / "narracao.mp3"
        words = asyncio.run(_speak(job["narration_script_draft"], voice))
        duration = _probe(voice)
        if not (25 <= duration <= 110):
            raise PilotError("VOICE_DURATION_OUTSIDE_SHORT_RANGE")
        subtitles = target / "legendas.ass"
        write_subtitles(words, subtitles, duration)
        images = []
        for i, scene in enumerate(job["scenes"], 1):
            path = target / f"scene-{i:02}.png"
            if path.exists():
                raise PilotError("UNVERIFIED_IMAGE_CACHE_FOUND")
            raw = request_image(scene["prompt_en"], "gpt-image-2", key, "1024x1536")
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as picture:
                if picture.width < 512 or picture.height < 768:
                    raise PilotError("AI_IMAGE_TOO_SMALL")
                picture.convert("RGB").save(path, "PNG")
            images.append(path)
        cover = target / "thumb.jpg"
        create_cover(images[0], cover, job["title_draft"], job["channel"])
        video = target / "final.mp4"
        render_video(images, voice, subtitles, video, duration)
        qa = validate_media(video, cover, images, duration)
        meta = {"id": ep, "channel": job["channel"], "channel_id": job["channel_id"],
                "title": job["title_draft"], "description": job["description_draft"],
                "tags": job["tags"], "categoryId": "20" if job["channel"] == "games" else "28",
                "containsSyntheticMedia": True, "render_sha256": qa["mp4_sha256"],
                "cover_sha256": qa["cover_sha256"],
                "ai_visuals_only": True, "publication_intent": "private_first"}
        (target / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
        (target / "qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
        # Delete intermediates and full generated images from upload artifacts
        # after validating the finished video, preserving only MP4, cover, QA, metadata.
        for f in target.glob("clip-*.mp4"):
            f.unlink()
        for f in target.glob("scene-*.png"):
            f.unlink()
        for f in [target / "joined.mp4", target / "list.txt", target / "legendas.ass", voice]:
            f.unlink(missing_ok=True)
        summary["videos"].append({"id": ep, "channel": job["channel"],
                                  "video": ep + "/final.mp4",
                                  "cover": ep + "/thumb.jpg",
                                  "metadata": ep + "/metadata.json",
                                  "qa": ep + "/qa.json",
                                  "sha256": qa["mp4_sha256"]})
        print("RENDERED_" + ep, flush=True)
    if len(summary["videos"]) != 6:
        raise PilotError("PARTIAL_BATCH")
    (OUTPUT / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SIX_ILLUSTRATED_SHORTS_RENDERED_NO_YOUTUBE_UPLOAD", flush=True)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--action", choices=["validate", "render"], default="validate")
    args = p.parse_args()
    try:
        manifest = load_manifest()
        if args.action == "validate":
            print("SIX_AI_PILOT_VALIDATED_" + str(len(manifest["batch"])))
        else:
            render_all()
        return 0
    except Exception as exc:
        # Public CI logs must not contain proxy response bodies, keys or auth data.
        code = str(exc) if isinstance(exc, PilotError) else type(exc).__name__
        print("AI_PILOT_BLOCKED_" + code, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
