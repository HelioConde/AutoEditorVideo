#!/usr/bin/env python3
"""One review-only V7: deform a single authentic RGBA character with a 2D mesh.

Deterministic CPU mesh (OpenCV remap); Remotion composes foreground, background,
original Edge TTS and captions. Never calls a generative provider or YouTube.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import wave

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from legendas_precisas import captions_from_markers
from otaku_multicena_duration_90 import PLAN, PAUSE, load

NAME = "Otaku V7 - Malha 2D 8s real AutoEditorVideo preview (no upload)"
EPISODE = "otaku-v7-malha-8s-review-only"
OWNER = "chatgpt_v7_mesh_trial_20261107"
ORIGINAL_RUN = "42332358380"
ORIGINAL = ROOT / "assets/gerados/otaku-v6-real-90s"
MEDIA = ROOT / "motion-remotion/public/generated/otaku-v7-mesh"
REVIEW = ROOT / "otaku-v7-mesh-review"
WIDTH, HEIGHT = 1024, 1536
VIDEO_FPS, MESH_FPS, SECONDS = 30, 15, 8
GRID = (12, 18)  # 12 x 18 quadrilateral control mesh, bilinear deformation
SHA = {
    "pose-05-1.png": "fcebfb9b195325d52ec79abc3d58d287ed8c456b8f39f888873cb6b8026709e8",
    "background-05.png": "038181a5ce82ffa061f9ce4bf5f56cb62445e130672a7eeb61a26d541f120db5",
    "voz-master.mp3": "d67cd58ff30c45d4aeede31484434360e96f9bd855a27fce96f2866646927398",
    "marcacoes-voz.json": "544f61af96fade7b23639725894b3336727a55bb6c95c97a3b402c049e19c530",
}

class MeshBlocked(RuntimeError):
    pass

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def preflight(env: dict[str, str]) -> dict:
    required = {
        "GITHUB_REPOSITORY": "HelioConde/AutoEditorVideo",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_WORKFLOW": NAME,
        "OTAKU_V7_MESH_ONE_REVIEW": "1",
        "MAX_IMAGE_CALLS": "0",
    }
    if any(env.get(key) != value for key, value in required.items()):
        raise MeshBlocked("ONE_MAIN_REVIEW_ONLY_ZERO_IMAGE_CALLS")
    if env.get("PROXY_API_KEY") or env.get("YOUTUBE_BR_TOKEN_JSON"):
        raise MeshBlocked("PAID_GENERATION_OR_YOUTUBE_SECRETS_FORBIDDEN")
    gate = load(PAUSE)
    if not (gate.get("pause_requested") is True
            and gate.get("authorized_public") is False
            and gate.get("resume_authorized_after_maintenance") is False):
        raise MeshBlocked("PUBLISHING_QUEUE_MUST_REMAIN_PAUSED")
    reservations = json.loads((ROOT / "conteudos/otaku-production-reservations.json").read_text(encoding="utf-8"))
    matched = [entry for entry in reservations["entries"]
               if entry.get("channel") == "br" and entry.get("id") == EPISODE]
    if len(matched) != 1 or matched[0].get("reservation_owner") != OWNER or matched[0].get("status") != "reserved":
        raise MeshBlocked("MISSING_EXACT_V7_REVIEW_RESERVATION")
    return load(PLAN)["items"][0]

def check_originals() -> None:
    for name, expected in SHA.items():
        file = ORIGINAL / name
        if not file.is_file() or digest(file) != expected:
            raise MeshBlocked("ORIGINAL_EVIDENCE_INVALID_" + name)
    with Image.open(ORIGINAL / "pose-05-1.png") as image:
        if image.mode != "RGBA" or image.size != (WIDTH, HEIGHT):
            raise MeshBlocked("SOURCE_MUST_BE_AUTHENTIC_RGBA")
    with Image.open(ORIGINAL / "background-05.png") as image:
        if image.size != (WIDTH, HEIGHT):
            raise MeshBlocked("BACKGROUND_DIMENSIONS_INVALID")

def smooth(x: float) -> float:
    t = max(0.0, min(1.0, x))
    return t*t*(3-2*t)

def mesh_displacement(t: float) -> tuple[np.ndarray, np.ndarray]:
    """Displacement is interpolated from a regular mesh, not separate poses.

    Head, chest and hanging hand are gently deformed. The hip/feet remain
    anchored; amplitudes stay low to minimize facial and clothing distortion.
    """
    cols, rows = GRID
    xx, yy = np.meshgrid(np.linspace(0, 1, cols+1, dtype=np.float32),
                         np.linspace(0, 1, rows+1, dtype=np.float32))
    def influence(x: float, y: float, sx: float, sy: float) -> np.ndarray:
        return np.exp(-0.5*(((xx-x)/sx)**2+((yy-y)/sy)**2))
    head = influence(.49, .30, .22, .19)
    chest = influence(.50, .51, .31, .24)
    wrist = influence(.75, .86, .13, .23)
    # Smooth start and return to the exact starting artwork at the end.
    envelope = math.sin(math.pi*min(SECONDS,max(0,t))/SECONDS)**2
    breath = math.sin(2*math.pi*.28*t)
    glance = smooth((t-3.45)/1.15)-smooth((t-6.15)/1.0)
    gesture = smooth((t-4.2)/1.0)-smooth((t-6.55)/.9)
    vx = (3.8*breath*chest + 14.0*glance*head + 20.0*gesture*wrist)*envelope
    vy = (-4.8*breath*chest - 3.3*glance*head - 9.0*gesture*wrist)*envelope
    return vx.astype(np.float32), vy.astype(np.float32)

def deform_same_rgba(image: np.ndarray, t: float) -> np.ndarray:
    if image.shape != (HEIGHT, WIDTH, 4) or image.dtype != np.uint8:
        raise MeshBlocked("MESH_REQUIRES_1024x1536_RGBA_UINT8")
    if t <= 0 or t >= SECONDS:
        return image.copy()
    vx, vy = mesh_displacement(t)
    # CPU bilinear interpolation of the regular 2D vertex grid.
    # OpenCV remap evaluates the same subject texture once per frame;
    # no whole-character opacity crossfades or regenerated identities.
    delta_x = cv2.resize(vx, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    delta_y = cv2.resize(vy, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    source_x = np.arange(WIDTH, dtype=np.float32)[None, :] - delta_x
    source_y = np.arange(HEIGHT, dtype=np.float32)[:, None] - delta_y
    return cv2.remap(image, source_x, source_y, cv2.INTER_LINEAR,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0,0))

def make_music() -> None:
    hz = 24000
    time = np.arange(SECONDS*hz, dtype=np.float32)/hz
    audio = np.zeros_like(time)
    for f in (110., 138.59, 164.81):
        audio += np.sin(2*math.pi*f*time).astype(np.float32)*.025
    fade = np.clip(np.minimum(time/.9, (SECONDS-time)/.9), 0, 1)
    audio *= fade
    with wave.open(str(MEDIA/"music-original.wav"), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(hz)
        out.writeframes((audio*32767).astype("<i2").tobytes())

def build(row: dict) -> dict:
    if MEDIA.exists() or REVIEW.exists():
        raise MeshBlocked("REVIEW_EXISTS_DO_NOT_DUPLICATE")
    check_originals()
    MEDIA.mkdir(parents=True)
    REVIEW.mkdir(parents=True)
    shutil.copy2(ORIGINAL/"background-05.png", MEDIA/"background.png")
    shutil.copy2(ORIGINAL/"voz-master.mp3", MEDIA/"voice.mp3")
    original = np.asarray(Image.open(ORIGINAL/"pose-05-1.png").convert("RGBA"))
    visible = original[:, :, 3] > 32
    paths = []
    samples = []
    for number in range(SECONDS*MESH_FPS):
        t = number/MESH_FPS
        current = deform_same_rgba(original, t)
        name = f"mesh-{number:03d}.webp"
        Image.fromarray(current, "RGBA").save(MEDIA/name, "WEBP", quality=93, method=4)
        paths.append("generated/otaku-v7-mesh/"+name)
        if number in (0,30,60,75,90,119):
            sample = Image.fromarray(current, "RGBA")
            sample.save(REVIEW/f"evidence-{number:03d}.png")
            changed = np.any(np.abs(current[:, :, :3].astype(np.int16)-original[:, :, :3].astype(np.int16))>25,axis=2)
            fraction = float((changed & visible).sum()/max(1,int(visible.sum())))
            current_visible = current[:, :, 3] > 32
            iou = float(np.logical_and(visible,current_visible).sum()/max(1,int(np.logical_or(visible,current_visible).sum())))
            samples.append({"frame": number, "second":round(t,3),
                            "subject_changed_fraction":round(fraction,4),
                            "alpha_iou_with_original":round(iou,4)})
    if samples[0]["subject_changed_fraction"] != 0:
        raise MeshBlocked("BASE_FRAME_WAS_CHANGED")
    if not any(s["subject_changed_fraction"] > .08 and s["alpha_iou_with_original"] > .90 for s in samples):
        raise MeshBlocked("MESH_MOTION_NOT_VISIBLE_OR_UNSTABLE")
    if min(s["alpha_iou_with_original"] for s in samples) < .90:
        raise MeshBlocked("MESH_DEFORMATION_EXCESSIVE")
    make_music()
    captions = captions_from_markers(ORIGINAL/"voz-master.mp3",
                                    row["narration_script"],91.44,fps=VIDEO_FPS)
    if not captions:
        raise MeshBlocked("ORIGINAL_TTS_CAPTIONS_UNAVAILABLE")
    captions = [{**x,"endFrame":min(x["endFrame"], SECONDS*VIDEO_FPS)}
                for x in captions if x["startFrame"] < SECONDS*VIDEO_FPS]
    if not captions:
        raise MeshBlocked("NO_CAPTIONS_IN_FIRST_EIGHT_SECONDS")
    props = {
        "id": EPISODE, "durationFrames": VIDEO_FPS*SECONDS,
        "audio": "generated/otaku-v7-mesh/voice.mp3",
        "scenes": [{
          "id": "v7-01", "subject": "personagens",
          "startFrame": 0, "endFrame": VIDEO_FPS*SECONDS,
          "background": "generated/otaku-v7-mesh/background.png",
          "foreground": "generated/otaku-v7-mesh/background.png",
          "renderMode": "mesh2d", "shotType": "close",
          "beatRole": "setup", "transitionStyle": "hard",
          "layers": [{
              "id":"consistent-single-character", "role":"character", "z":10,
              "src": "generated/otaku-v7-mesh/"+Path(paths[0]).name,
              "meshFrames":{"fps":MESH_FPS, "frames":paths}
          }]
        }],
        "captions":captions, "hook":"V7 • MALHA 2D",
        "animationMode":"malha2d",
        "visualProfile":"otaku-v6-vertical",
        "backgroundMusic":{"src":"generated/otaku-v7-mesh/music-original.wav","volume":.12},
        "editorialProfile":"Otaku Multicena V7 mesh 8s review only"
    }
    props_path = REVIEW/"props-v7.json"
    props_path.write_text(json.dumps(props,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"original_source_run":ORIGINAL_RUN,
            "animation_method":"CPU bilinear deformable mesh; one authentic source RGBA",
            "grid_columns":GRID[0],"grid_rows":GRID[1],
            "mesh_fps":MESH_FPS,"video_fps":VIDEO_FPS,
            "source_images_reused":2,"mesh_frame_count":len(paths),
            "new_ai_image_calls":0,"separate_background":True,
            "whole_character_crossfade":False,"multiple_pose_identity_switch":False,
            "samples":samples,"original_character_sha256":SHA["pose-05-1.png"]}

def render(qa:dict) -> None:
    output = REVIEW/"Otaku_Multicena_V7_Malha2D_8s_Teste.mp4"
    proc = subprocess.run([
        "npm","run","render:master","--",str(output.resolve()),
        "--props",str((REVIEW/"props-v7.json").resolve()),
        "--concurrency","2","--codec","h264","--crf","19"
    ],cwd=ROOT/"motion-remotion",text=True,capture_output=True,timeout=3600)
    if proc.returncode:
        # Print only bounded editor stderr, never user secrets.
        print("[OTAKU V7] REMOTION_FAILED: "+proc.stderr[-1800:],file=sys.stderr)
        raise MeshBlocked("REMOTION_V7_RENDER_FAILED")
    if not output.is_file() or output.stat().st_size < 400_000:
        raise MeshBlocked("V7_MP4_MISSING")
    result = subprocess.run(["ffprobe","-v","error","-show_streams",
        "-show_format","-of","json",str(output)],text=True,
        capture_output=True,check=True)
    meta = json.loads(result.stdout)
    video = next((s for s in meta["streams"] if s["codec_type"]=="video"),None)
    sound = any(s["codec_type"]=="audio" for s in meta["streams"])
    duration = float(meta["format"]["duration"])
    if not video or video["width"] != 1080 or video["height"] != 1920 or not sound or abs(duration-SECONDS)>.25:
        raise MeshBlocked("V7_AV_FORMAT_MISMATCH")
    qa.update({"render_success":True,"video_duration_seconds":duration,
               "resolution":"1080x1920","audio_stream":sound,
               "video_sha256":digest(output),"video_bytes":output.stat().st_size,
               "uploaded_to_youtube":False,
               "reviewed_visually_by_human":False,
               "human_review_still_required":True})
    (REVIEW/"qa-v7.json").write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("[OTAKU V7] MESH_MP4_READY_FOR_HUMAN_REVIEW_NO_YOUTUBE",flush=True)

def main() -> int:
    try:
        row = preflight(os.environ)
        if len(sys.argv)>1 and sys.argv[1]=="--preflight":
            print("[OTAKU V7] ONE_REVIEW_AUTHORIZED_ZERO_PAID_IMAGE_CALLS")
            return 0
        qa = build(row)
        print("[OTAKU V7] 120 MESH_FRAMES_GENERATED_FROM_ONE_AUTHENTIC_RGBA",flush=True)
        render(qa)
        return 0
    except Exception as exc:
        if isinstance(exc,MeshBlocked):
            print("[OTAKU V7 BLOCKED] "+str(exc),file=sys.stderr)
        else:
            print("[OTAKU V7 BLOCKED] "+type(exc).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
