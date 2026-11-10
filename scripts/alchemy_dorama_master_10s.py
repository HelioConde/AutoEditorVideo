#!/usr/bin/env python3
"""Alchemy Lab: one original master scene -> edits from THE SAME master -> 10s Remotion.

Deliberately independent of the 175s episode and Kids renderer.
One creator-approved, SHA-pinned source image and five image-edits, ALL from master.png.
No YouTube SDK, no upload, no paid voice, no secrets written to artifacts.
This only produces an unreviewed LOCAL preview and its visual evidence.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave

from PIL import Image, ImageOps
import requests

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "assets/gerados/alchemy-dorama-original/teste10"
PUBLIC = ROOT / "motion-remotion/public/generated/alchemy-dorama-master10"
PROPS = ROOT / "motion-remotion/props-alchemy-dorama-master10.json"
MP4 = PROJECT / "teste-10s-camadas.mp4"
QA = PROJECT / "qa-master-camadas-10s.json"
MODEL = "gpt-image-2"
API_BASE = "http://127.0.0.1:8080/v1/images"
SIZE = (1024, 1536)
FRAMES = 300
FPS = 30
EPISODE = "alchemy-114-conquiste-princesa-ep01"
MAX_CALLS = 5
ASSETS = ("master", "background", "ren", "king", "elara", "sword")
# EXACT SHA-256 of the creator's approved 941x1672 PNG shown on 2026-11-10.
# No text-to-image master generation allowed: use the actual source bytes.
REFERENCE_PATH = ROOT / "canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra/referencia-aprovada-20261110.png"
REFERENCE_SHA256 = "4b3f9ebf534537b1fb862d8df0167ca5730007b485ae04d40e3ce055a518c0b2"
REFERENCE_SIZE = (941, 1672)

MASTER_PROMPT = (
    "Create exactly ONE original complete cinematic Japanese anime fantasy "
    "scene (NOT a collage, poster montage or contact sheet) to be used as the "
    "single locked master reference for extracting separately animated layers. "
    "Portrait 2:3 safe for center-crop to 9:16. Entire scene in the same "
    "physical throne room, no close-up overlays, no split-screen, no lettering. "
    "Highly polished premium Japanese fantasy romance anime key animation look "
    "with intricate cel shading, vivid cinematic blue and gold lighting, "
    "baroque ornament, expressive faces and natural spatial depth. "
    "A magnificent Gothic stone throne hall with BLUE stained glass, two "
    "burgundy banners bearing gold SUN emblems, an elaborate gilded red velvet "
    "throne on stairs, mirrored gray marble floor with gold SUN COMPASS symbol. "
    "At foreground LEFT, REN a 21-year-old slim dark-haired young adult with "
    "amber eyes and a vertical scar through the LEFT eyebrow KNEELS on both "
    "knees facing right and looking upward in terror and defiance; wearing a "
    "worn torn navy tunic over beige shirt, dark trousers, brown leather belt "
    "and boots. In the central BACKGROUND on the elevated gold throne sits "
    "KING VALDREN: 52-year-old silver-gray swept-back hair, square gray beard, "
    "gold crown with prominent ruby, burgundy cape, black plate armor with "
    "gold trim, furiously pointing down at Ren. At RIGHT stands Princess "
    "ELARA, 22, long silver hair with fine side braid, violet-gray eyes, "
    "silver tiara with blue gemstone, long navy gown with elegant SILVER "
    "embroidery, observing Ren with a thoughtful hand near her chin. "
    "Extreme RIGHT foreground only the glove/arm of an executioner holding "
    "a large diagonal steel SWORD, pointing down into the frame. "
    "Characters have believable anatomy, five fingers, physically grounded "
    "kneeling and standing positions, and legible detailed silhouettes. "
    "Place all essential characters inside the CENTER 75% of horizontal "
    "canvas, with feet visible, leaving safe margins for portrait cropping. "
    "Lighting and shadows coherent across all objects. "
    "NO extra people, NO floating UI, NO letters, NO watermarks, NO flashbacks."
)

# Each edit MUST receive the exact bytes of master.png through images/edits.
# No other character sheet, unrelated screenshot, or previously generated
# portrait can be substituted as the source image.
EDIT_PROMPTS = {
    "background": (
        "Edit the ATTACHED MASTER SCENE into a seamless empty background plate. "
        "Keep the camera, EXACT same framing, pixel spatial layout, lighting, "
        "stone architecture, blue windows, banners, gold throne, throne steps "
        "and marble solar emblem unchanged. Inpaint where Ren, King, Elara, "
        "the executioner arm and sword are; the gold throne stays EMPTY. "
        "NO people, NO weapon, NO hologram, NO lettering. Opaque entire frame."
    ),
    "ren": (
        "Using only this ATTACHED MASTER SCENE as reference, extract the "
        "kneeling dark-haired Ren visible in the LEFT foreground as an isolated "
        "transparent RGBA character layer. Retain EXACT same pixel canvas, "
        "camera perspective, POSITION, SCALE, kneeling POSE, hairstyle, face, "
        "scar, eyes, outfit, color, and local lighting. Everything other "
        "than Ren must become FULLY TRANSPARENT. Do NOT recenter, zoom or "
        "enlarge Ren, do NOT invent another pose, do NOT add floor or shadow. "
        "Full original canvas dimensions 1024x1536."
    ),
    "king": (
        "Using only this ATTACHED MASTER SCENE as reference, isolate ONLY "
        "King Valdren's BODY, crown, cape, armor and pointing arm as one "
        "transparent RGBA layer. Preserve exact same pixel canvas, SIZE and "
        "POSITION atop the original throne. The THRONE itself becomes "
        "transparent because it already remains in the background plate. "
        "Retain his face and existing lighting. No re-centering, zoom, "
        "new body pose, furniture, platform, floor, or background; the "
        "entire remaining canvas must be completely transparent."
    ),
    "elara": (
        "Using only this ATTACHED MASTER SCENE as reference, extract only "
        "Princess Elara as a transparent RGBA layer at the EXACT same "
        "position, scale and stance on the RIGHT. Same silver hair, tiara, "
        "violet-gray eyes, navy dress and silver embroidery, same thoughtful "
        "expression. All hall, floor, other characters and throne become "
        "fully transparent. Maintain original full canvas and perspective. "
        "DO NOT recenter or enlarge."
    ),
    "sword": (
        "Edit this ATTACHED MASTER SCENE to isolate ONLY the executioner's "
        "steel SWORD and the gloved hand plus forearm holding it in the "
        "EXTREME RIGHT foreground, retaining EXACT position, original "
        "diagonal angle, scale, material, and cinematic perspective. "
        "Everything else FULLY TRANSPARENT RGBA on the unchanged original "
        "1024x1536 canvas. Do not move/recenter or add a new weapon."
    ),
}


class StageError(RuntimeError):
    pass


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha_file(path: Path) -> str:
    return digest(path.read_bytes())


def approved_budget(reuse: bool, max_calls: str, model: str) -> None:
    if reuse:
        if max_calls != "0":
            raise StageError("REUSE_MODE_MUST_HAVE_ZERO_IMAGE_CALLS")
    elif max_calls != str(MAX_CALLS) or model != MODEL:
        raise StageError("IMAGE_CALL_LIMIT_OR_MODEL_INVALID")


def call_image(secret: str, prompt: str, master: Path | None, transparent: bool) -> bytes:
    payload = {
        "model": MODEL, "prompt": prompt, "n": 1,
        "size": "1024x1536",
        "output_format": "png",
        "background": "transparent" if transparent else "opaque",
    }
    method = "generations"
    if master is not None:
        method = "edits"
        src = master.read_bytes()
        payload["images"] = [{"image_url": "data:image/png;base64," +
                              base64.b64encode(src).decode("ascii")}]
    try:
        response = requests.post(
            API_BASE + "/" + method,
            json=payload, headers={"Authorization": "Bearer " + secret},
            timeout=(20, 360),
        )
    except requests.RequestException:
        raise StageError("IMAGE_PROXY_UNREACHABLE") from None
    if response.status_code != 200:
        # Never echo a provider response; it may expose private session data.
        raise StageError("IMAGE_PROVIDER_HTTP_" + str(response.status_code))
    try:
        first = response.json()["data"][0]
        encoded = first.get("b64_json") or first.get("url")
        if not isinstance(encoded, str):
            raise ValueError("missing")
        if encoded.startswith("data:image/"):
            encoded = encoded.split(",", 1)[1]
        if encoded.startswith("http"):
            raise ValueError("remote URL forbidden")
        raw = base64.b64decode(encoded, validate=True)
        if not (50_000 <= len(raw) <= 25_000_000):
            raise ValueError("size")
        return raw
    except (KeyError, ValueError, TypeError, IndexError):
        raise StageError("IMAGE_PROVIDER_INVALID_RESPONSE") from None


def validate_png(data: bytes, transparent: bool, label: str) -> tuple[bytes, dict]:
    try:
        with Image.open(io.BytesIO(data)) as incoming:
            incoming.load()
            if incoming.format != "PNG":
                raise StageError(label + "_NOT_PNG")
            if incoming.size != SIZE:
                raise StageError(label + "_WRONG_CANVAS")
            if transparent and incoming.mode != "RGBA":
                raise StageError(label + "_NOT_RGBA")
            img = incoming.convert("RGBA" if transparent else "RGB")
            alpha_coverage = 1.0
            if transparent:
                lo, hi = img.getchannel("A").getextrema()
                if lo > 12 or hi < 240:
                    raise StageError(label + "_ALPHA_NOT_TRANSPARENT")
                hist = img.getchannel("A").histogram()
                alpha_coverage = sum(hist[180:]) / (SIZE[0] * SIZE[1])
                if not 0.001 < alpha_coverage < 0.75:
                    raise StageError(label + "_ALPHA_COVERAGE_IMPLAUSIBLE")
            out = io.BytesIO()
            img.save(out, format="PNG")
            return out.getvalue(), {
                "size": list(SIZE), "alpha_coverage": round(alpha_coverage, 5),
                "mode": img.mode, "automated_qa_only": True,
            }
    except (OSError, ValueError):
        raise StageError(label + "_INVALID_PNG") from None


def atomic_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".partial")
    tmp.write_bytes(data)
    tmp.replace(path)


def prepare_pinned_master() -> tuple[bytes, str]:
    """Use the creator's EXACT approved original, never regenerate a master.

    Fit the 9:16 user image inside the proxy's 2:3 reference canvas with
    side padding; Remotion's center-crop restores the original composition.
    The original is 941x1672 RGB; padding adds no newly invented imagery.
    """
    if not REFERENCE_PATH.is_file():
        raise StageError("APPROVED_REFERENCE_NOT_ON_GITHUB_UPLOAD_ORIGINAL_PNG_FIRST")
    original_bytes = REFERENCE_PATH.read_bytes()
    original_sha = digest(original_bytes)
    if original_sha != REFERENCE_SHA256:
        raise StageError("REFERENCE_SHA256_MISMATCH_DO_NOT_SUBSTITUTE")
    try:
        with Image.open(io.BytesIO(original_bytes)) as image:
            image.load()
            if image.format != "PNG" or image.size != REFERENCE_SIZE:
                raise StageError("APPROVED_REFERENCE_FORMAT_OR_SIZE_CHANGED")
            final = ImageOps.pad(image.convert("RGB"), SIZE,
                                 method=Image.Resampling.LANCZOS,
                                 color=(15, 16, 27), centering=(.5, .5))
            output = io.BytesIO()
            final.save(output, format="PNG")
    except (OSError, ValueError):
        raise StageError("APPROVED_REFERENCE_INVALID_PNG") from None
    return output.getvalue(), original_sha


def ensure_images(reuse: bool) -> dict:
    # Validate reference authenticity even if cached assets already exist.
    master_png, source_hash = prepare_pinned_master()
    expected_hash = digest(master_png)
    PROJECT.mkdir(parents=True, exist_ok=True)
    expected = PROJECT / "master.png"
    secret = "" if reuse else os.environ.get("PROXY_API_KEY", "")
    metadata = PROJECT / "manifest-master-layers.json"
    old = json.loads(metadata.read_text(encoding="utf-8")) if metadata.exists() else {}
    calls = 0
    result = {"schema": "alchemy-dorama/master-to-layers-10s/v2",
              "channel": "alchemy", "episode": EPISODE,
              "source_strategy": "CREATOR_APPROVED_PINNED_IMAGE_THEN_SAME_SOURCE_EDITS",
              "original_sha256": source_hash,
              "size": list(SIZE), "assets": {}, "image_calls_this_run": 0,
              "visual_review": "PENDING", "publication": "DISABLED"}
    if not expected.exists():
        if reuse:
            raise StageError("PREPARED_MASTER_MISSING_REUSE_BLOCKED")
        atomic_file(expected, master_png)
    elif sha_file(expected) != expected_hash:
        raise StageError("CACHE_MASTER_DIFFERS_FROM_APPROVED_IMAGE")
    _, probe = validate_png(expected.read_bytes(), False, "master")
    master_hash = sha_file(expected)
    if old and (old.get("master_sha256") != master_hash or
                old.get("original_sha256") != source_hash):
        raise StageError("CACHE_WRONG_CREATOR_REFERENCE_SHA256")
    result["master_sha256"] = master_hash
    result["assets"]["master"] = {"path": str(expected.relative_to(ROOT)),
                                  "sha256": master_hash, **probe,
                                  "source": "creator_approved_original_png"}
    # Persist the canonical SHA before costly /images/edits; only the
    # anchored source can seed layer-cache reuse, not independent prompts.
    if not old:
        atomic_file(metadata, (json.dumps(result, ensure_ascii=False, indent=2) +
                               "\n").encode("utf-8"))
    for label, prompt in EDIT_PROMPTS.items():
        location = PROJECT / (label + ".png")
        previous = old.get("assets", {}).get(label, {})
        if location.exists():
            if (not previous or previous.get("master_sha256") != master_hash or
                    previous.get("sha256") != sha_file(location)):
                raise StageError("CACHED_LAYER_WITHOUT_MATCHING_SOURCE_" + label)
            png, probe = validate_png(location.read_bytes(), label != "background", label)
        else:
            if reuse:
                raise StageError("LAYER_MISSING_IN_REUSE_MODE_" + label)
            if len(secret) < 15:
                raise StageError("PROXY_API_KEY_NOT_CONFIGURED")
            # All five API calls are edits of the same approved image.
            raw = call_image(secret, prompt, expected, label != "background")
            calls += 1
            png, probe = validate_png(raw, label != "background", label)
            atomic_file(location, png)
        result["assets"][label] = {
            "path": str(location.relative_to(ROOT)),
            "sha256": digest(png), "master_sha256": master_hash,
            "source": "images/edits", **probe,
            "approved": False,
        }
        result["image_calls_this_run"] = calls
        atomic_file(metadata, (json.dumps(result, ensure_ascii=False, indent=2) +
                               "\n").encode("utf-8"))
        print("[MASTER10] "+label+": derived from PINNED creator reference="+
              source_hash[:12], flush=True)
        # Keep the ORIGINAL cached manifest immutable during this invocation.
        # Mutating old here would drop later cached layer entries on reuse.
    if calls > MAX_CALLS:
        raise StageError("IMAGE_LIMIT_EXCEEDED")
    result["image_calls_this_run"] = calls
    result["asset_count"] = len(result["assets"])
    atomic_file(metadata, (json.dumps(result, ensure_ascii=False, indent=2) +
                           "\n").encode("utf-8"))
    return result


def audio_ambient(path: Path) -> None:
    """Original synthesized audio, no licensed music and no robotic speech."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 24000
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for start in range(0, sample_rate * 10, 4096):
            frames = bytearray()
            for i in range(start, min(start + 4096, sample_rate * 10)):
                t = i / sample_rate
                # cinematic drone: faint 55Hz + harmonics, sword accent at 5s,
                # interface rise at 7.5s; safe peak level < -12 dBFS.
                drone = 0.034 * (math.sin(2 * math.pi * 55 * t) +
                                 0.4 * math.sin(2 * math.pi * 82.4 * t))
                sword = (0.075 * math.exp(-8 * (t - 5.0)) *
                         math.sin(2 * math.pi * (320 - 75 * (t - 5.0)) * t)
                         if 5.0 <= t <= 5.8 else 0.0)
                ui = (0.05 * math.sin(2 * math.pi * (520 + 65 * (t - 7.4)) * t)
                      if 7.4 <= t <= 9.4 else 0.0)
                fade = min(1, t / 0.35, max(0.0, (10 - t) / 0.25))
                sample = max(-0.3, min(0.3, fade * (drone + sword + ui)))
                frames.extend(struct.pack("<h", int(sample * 32767)))
            wav.writeframes(bytes(frames))


def create_props() -> Path:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for label in ASSETS:
        shutil.copy2(PROJECT / (label + ".png"), PUBLIC / (label + ".png"))
    wav = PROJECT / "ambiencia-original.wav"
    audio_ambient(wav)
    shutil.copy2(wav, PUBLIC / "ambiencia-original.wav")
    data = {
        "pilotId": "alchemy-dorama-master-layer-10s-v1",
        "durationFrames": FRAMES,
        "master": "generated/alchemy-dorama-master10/master.png",
        "background": "generated/alchemy-dorama-master10/background.png",
        "ren": "generated/alchemy-dorama-master10/ren.png",
        "king": "generated/alchemy-dorama-master10/king.png",
        "elara": "generated/alchemy-dorama-master10/elara.png",
        "sword": "generated/alchemy-dorama-master10/sword.png",
        "audio": "generated/alchemy-dorama-master10/ambiencia-original.wav",
        "frameReferenceSha": sha_file(PROJECT / "master.png"),
        "noNarration": True, "noYouTubeUpload": True,
    }
    PROPS.parent.mkdir(parents=True, exist_ok=True)
    PROPS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    return PROPS


def create_comparison(video: Path) -> None:
    frame = PROJECT / "frame-composito-05s.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "5", "-i",
                    str(video), "-frames:v", "1", str(frame)],
                   check=True, timeout=60)
    with Image.open(PROJECT / "master.png") as ma, Image.open(frame) as comp:
        # Exactly the same center-crop behavior as CSS object-fit: cover.
        left = ImageOps.fit(ma.convert("RGB"), (540, 960),
                            method=Image.Resampling.LANCZOS,
                            centering=(0.5, 0.5))
        right = comp.convert("RGB").resize((540, 960), Image.Resampling.LANCZOS)
        compare = Image.new("RGB", (1080, 960))
        compare.paste(left, (0, 0))
        compare.paste(right, (540, 0))
        compare.save(PROJECT / "comparacao-master-vs-camadas.jpg", quality=88)


def render(manifest: dict) -> dict:
    prop = create_props()
    if MP4.exists():
        raise StageError("PREVIOUS_RENDER_EXISTS_DO_NOT_OVERWRITE")
    subprocess.run(["npx", "remotion", "render", "src/index.ts",
                    "AlchemyDoramaMaster10s", str(MP4.resolve()),
                    "--props", str(prop.resolve()), "--codec", "h264",
                    "--concurrency", "2", "--log", "error"],
                   cwd=ROOT / "motion-remotion", check=True, timeout=1500)
    p = subprocess.run(["ffprobe", "-v", "error", "-of", "json",
                        "-show_streams", "-show_format", str(MP4)],
                       capture_output=True, text=True, check=True, timeout=30)
    media = json.loads(p.stdout)
    vid = next((x for x in media.get("streams", [])
                if x.get("codec_type") == "video"), None)
    aud = next((x for x in media.get("streams", [])
                if x.get("codec_type") == "audio"), None)
    length = float(media.get("format", {}).get("duration", 0))
    if (not vid or not aud or vid["width"] != 1080 or
            vid["height"] != 1920 or not 9.93 <= length <= 10.10):
        raise StageError("MP4_FAILED_DURATION_DIMENSION_OR_AUDIO_QA")
    create_comparison(MP4)
    report = {
        "schema": "alchemy-dorama/master-10s-render-qa/v1",
        "status": "RENDERED_UNREVIEWED", "mp4": str(MP4.relative_to(ROOT)),
        "duration_seconds": round(length, 3), "frame_rate": FPS,
        "target_frames": FRAMES, "resolution": [1080, 1920],
        "mp4_sha256": sha_file(MP4),
        "master_sha256": manifest["master_sha256"],
        "derived_from_single_source": all(
            item["master_sha256"] == manifest["master_sha256"]
            for key, item in manifest["assets"].items() if key != "master"),
        "image_calls_this_run": manifest["image_calls_this_run"],
        "object_independent": True,
        "character_layers_independent": ["ren", "king", "elara"],
        "comparison": "assets/gerados/alchemy-dorama-original/teste10/comparacao-master-vs-camadas.jpg",
        "audio": "procedural_ambient_no_robotic_TTS",
        "visual_review_required": True, "publish_authorized": False,
        "youtube_uploads": 0, "made_for_kids": False,
    }
    QA.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                  encoding="utf-8")
    return report


def main() -> int:
    args = argparse.ArgumentParser()
    args.add_argument("--acao", choices=("planejar", "gerar"), default="planejar")
    cfg = args.parse_args()
    if cfg.acao == "planejar":
        print(json.dumps({
            "strategy": "exact creator-approved image (SHA-256 pinned) + five same-source edits",
            "master": "master.png",
            "transparent_layers": ["ren.png", "king.png", "elara.png", "sword.png"],
            "opaque_background": "background.png",
            "all_edits_use_master_sha256": True,
            "image_call_limit": MAX_CALLS,
            "approved_source_file": str(REFERENCE_PATH.relative_to(ROOT)),
            "approved_source_sha256": REFERENCE_SHA256,
            "duration_seconds": 10, "render_composition": "AlchemyDoramaMaster10s",
            "no_youtube_upload": True,
        }, ensure_ascii=False, indent=2))
        return 0
    reuse = os.environ.get("ALCH10_REUSE_ONLY") == "1"
    approved_budget(reuse, os.environ.get("MAX_IMAGE_CALLS", ""),
                    os.environ.get("IMAGE_MODEL", ""))
    refs = ensure_images(reuse)
    print("[MASTER10] ALL_LAYERS_PREPARED", flush=True)
    qa = render(refs)
    print("[MASTER10] MP4_10S_READY_FOR_HUMAN_REVIEW", flush=True)
    print(json.dumps({key: qa[key] for key in (
        "duration_seconds", "master_sha256", "derived_from_single_source",
        "image_calls_this_run", "mp4")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StageError as e:
        print("[MASTER10 BLOCKED] " + str(e), file=sys.stderr)
        raise SystemExit(1)
    except (OSError, subprocess.SubprocessError):
        print("[MASTER10 BLOCKED] LOCAL_RENDER_OR_DEPENDENCY_FAILED", file=sys.stderr)
        raise SystemExit(1)
