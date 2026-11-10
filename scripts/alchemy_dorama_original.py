#!/usr/bin/env python3
"""Isolated Alchemy original anime episode: Fofinho Part-3-style 2D layers.

Planejar: read-only; preparar: copy ONLY approved, hash-matching original
anchors and measured narration into Remotion props; renderizar: render to
local MP4. Never calls paid image models, uploads or changes Kids workflows.

Do not invoke the Fofinho CLI directly: its assets, madeForKids flag, music
and 60-second duration cap are specific to the children's series.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "canais/alchemy-lab/conteudos/conquiste-a-princesa-ou-morra"
BOARD = SERIES / "episodio-01.json"
MANIFEST = SERIES / "referencias-v1.json"
RESERVATIONS = ROOT / "conteudos/otaku-production-reservations.json"
SOURCE = ROOT / "assets/gerados/alchemy-dorama-original/ep01"
REFROOT = ROOT / "assets/gerados/alchemy-dorama-original/referencias"
PUBLIC = ROOT / "motion-remotion/public/generated/alchemy-dorama-original/ep01"
PROPS = ROOT / "motion-remotion/props-alchemy-dorama-ep01.json"
OUTPUT = SOURCE / "final-camadas.mp4"
FPS = 30
CHANNEL = "UCCTYFE5Cmz2aYZ37cJQ-wcg"
EPISODE = "alchemy-114-conquiste-princesa-ep01"
OWNER = "alchemy_dorama_original_20261110"
BACKGROUND = {"TRONO-01", "ACADEMIA-01", "ARQUIVO-01", "CORREDOR-01"}
ACTORS = {"REN-01", "ELARA-01", "VALDREN-01", "OREN-01", "LUVA-01"}
PROPS_IDS = {"PROP-01", "PROP-02", "PROP-03"}

POSITIONS = {
    "TRONO-01": {
        "REN-01": (.32, .74, .43, 30),
        "ELARA-01": (.78, .55, .35, 35),
        "VALDREN-01": (.50, .39, .39, 32),
        "OREN-01": (.13, .63, .29, 30),
        "PROP-02": (.58, .73, .12, 42),
        "PROP-03": (.13, .72, .19, 44),
    },
    "ACADEMIA-01": {
        "REN-01": (.39, .68, .55, 30),
    },
    "ARQUIVO-01": {
        "REN-01": (.35, .65, .46, 30),
        "OREN-01": (.77, .59, .34, 34),
        "LUVA-01": (.77, .55, .29, 45),
        "PROP-01": (.71, .71, .10, 44),
        "PROP-02": (.71, .71, .10, 44),
    },
}
# Motion applies to WHOLE approved cutout, never invented joints/faces.
MOTIONS = {
    (1, "REN-01"): "kneel",
    (2, "VALDREN-01"): "gesture",
    (3, "REN-01"): "walk",
    (4, "REN-01"): "react",
    (8, "OREN-01"): "walk",
    (9, "REN-01"): "react",
    (10, "REN-01"): "react",
    (11, "REN-01"): "react",
    (12, "REN-01"): "gesture",
    (13, "REN-01"): "point",
    (14, "ELARA-01"): "look",
    (15, "ELARA-01"): "walk",
    (16, "ELARA-01"): "look",
}
# Same Fofinho Part-3 strategy: different approved pose PNGs for each action.
# All derived images must prove lineage to a fixed canonical character SHA.
POSES_BY_SCENE = {
    "REN-01": {
        1:"REN-01-ajoelhado", 2:"REN-01-ajoelhado",
        3:"REN-01-treinando", 4:"REN-01-treinando",
        5:"REN-01-ajoelhado",
        6:"REN-01-trabalhando", 7:"REN-01-trabalhando", 8:"REN-01-trabalhando",
        9:"REN-01-ajoelhado", 10:"REN-01-assustado", 11:"REN-01-assustado",
        12:"REN-01-apontando", 13:"REN-01-apontando",
        14:"REN-01-ajoelhado", 15:"REN-01-ajoelhado", 16:"REN-01-assustado",
    },
    "ELARA-01": {
        2:"ELARA-01-observando", 9:"ELARA-01-observando",
        11:"ELARA-01-observando", 12:"ELARA-01-observando",
        14:"ELARA-01-observando", 15:"ELARA-01-firme", 16:"ELARA-01-firme",
    },
    "VALDREN-01": {
        1:"VALDREN-01-julgando", 2:"VALDREN-01-julgando",
        5:"VALDREN-01-julgando", 9:"VALDREN-01-julgando",
        12:"VALDREN-01-julgando", 15:"VALDREN-01-julgando",
    },
}


def selected_asset(number: int, anchor: str) -> str:
    return POSES_BY_SCENE.get(anchor, {}).get(number, anchor)


def needed_keys(board: dict) -> set[str]:
    needed: set[str] = set()
    for shot in board["scenes"]:
        needed.add(shot["background_anchor"])
        originals = shot["character_anchors"] + [
            x for x in shot["item_anchors"] if x not in {"UI-01", "UI-02"}]
        for anchor in originals:
            needed.add(anchor)
            needed.add(selected_asset(shot["number"], anchor))
    return needed


CAMERAS = {
    1: "slow-push", 3: "drift-right", 4: "slow-push",
    6: "slow-push", 7: "slow-push", 9: "slow-push",
    10: "still", 11: "still", 13: "slow-push",
    14: "slow-push", 16: "slow-push",
}
PANELS = {
    10: {"kind": "mission", "title": "MISSÃO PRINCIPAL",
         "message": "Conquiste o coração da princesa Elara em 30 dias. Falha: MORTE.",
         "counter": "30 DIAS"},
    11: {"kind": "emergency", "title": "MISSÃO DE EMERGÊNCIA",
         "message": "Faça a princesa suspender sua execução.",
         "counter": "01:30"},
    15: {"kind": "completed", "title": "MISSÃO CONCLUÍDA",
         "message": "Execução suspensa. Você sobreviveu."},
    16: {"kind": "anomaly", "title": "ANOMALIA DETECTADA",
         "message": "A PRINCESA CONHECE O SISTEMA."},
}


def read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def check_storyboard(data: dict) -> None:
    if data.get("channel") != "alchemy" or data.get("youtube_channel_id") != CHANNEL:
        raise ValueError("CHANNEL_MISMATCH")
    if data.get("episode_id") != EPISODE or data.get("reservation_owner") != OWNER:
        raise ValueError("EPISODE_OR_OWNER_MISMATCH")
    if not 150 <= data["duration_seconds_target"] <= 180:
        raise ValueError("EPISODE_DURATION_OUTSIDE_150_180")
    scenes = data["scenes"]
    if not scenes or scenes[0]["start_second"] != 0:
        raise ValueError("STORYBOARD_MISSING_START")
    for i, shot in enumerate(scenes):
        if shot["end_second"] <= shot["start_second"]:
            raise ValueError("EMPTY_SHOT")
        if i and scenes[i - 1]["end_second"] != shot["start_second"]:
            raise ValueError("SHOT_TIMELINE_GAP")
        if shot["background_anchor"] not in BACKGROUND:
            raise ValueError("UNKNOWN_BACKGROUND")
    if scenes[-1]["end_second"] != data["duration_seconds_target"]:
        raise ValueError("STORYBOARD_END_MISMATCH")
    ledger = read_json(RESERVATIONS)
    matches = [e for e in ledger["entries"]
               if e.get("channel") == "alchemy" and e.get("id") == EPISODE]
    if len(matches) != 1 or matches[0].get("reservation_owner") != OWNER:
        raise ValueError("NO_MATCHING_PRODUCTION_RESERVATION")
    if matches[0].get("status") != "reserved":
        raise ValueError("RESERVATION_NOT_READY")


def anchor_map(data: dict) -> dict:
    if data.get("channel") != "alchemy" or data.get("youtube_channel_id") != CHANNEL:
        raise ValueError("REFERENCE_CHANNEL_MISMATCH")
    refs = {item["id"]: item for item in data["entries"]}
    return refs


def inspect_assets(board: dict, refs: dict, ui: dict) -> list[str]:
    required = needed_keys(board)
    missing = []
    for key in sorted(required):
        item = refs.get(key)
        if not item:
            missing.append(key + ":not_in_manifest")
            continue
        location = (ROOT / item["file"]).resolve()
        if not location.is_relative_to(REFROOT.resolve()) or location.name != key + ".png":
            missing.append(key + ":unsafe_path")
            continue
        digest = item.get("sha256")
        if not item.get("approved") or not isinstance(digest, str) or len(digest) != 64:
            missing.append(key + ":not_approved_or_no_sha")
            continue
        if not location.is_file() or sha256(location) != digest:
            missing.append(key + ":missing_or_hash_mismatch")
            continue
        parent_id = item.get("source_id")
        if parent_id:
            parent = refs.get(parent_id)
            if (not parent or item.get("source_sha256") != parent.get("sha256")
                    or not parent.get("approved")):
                missing.append(key + ":parent_hash_or_approval_mismatch")
                continue
        if key not in BACKGROUND:
            try:
                from PIL import Image
                with Image.open(location) as im:
                    if im.mode != "RGBA" or im.getchannel("A").getextrema() == (255, 255):
                        missing.append(key + ":cutout_needs_real_alpha")
            except ImportError:
                missing.append(key + ":pillow_needed_to_validate_alpha")
    if not all(ui.get(k, {}).get("approved_visual") for k in ("UI-01", "UI-02")):
        missing.append("UI-01/UI-02:visual_approval_pending")
    return missing


def audio_status() -> tuple[Path | None, list[dict], list[str]]:
    audio = SOURCE / "narracao.mp3"
    timing_file = SOURCE / "legendas.json"
    errors = []
    captions: list[dict] = []
    if not audio.is_file():
        errors.append("narracao.mp3:missing")
    if not timing_file.is_file():
        errors.append("legendas.json:missing_real_voice_timestamps")
    else:
        captions = read_json(timing_file).get("captions", [])
        if not captions:
            errors.append("legendas.json:empty")
        for line in captions:
            if (not isinstance(line.get("text"), str) or not line["text"].strip()
                    or not 0 <= line["startFrame"] < line["endFrame"] <= 5250):
                errors.append("legendas.json:invalid_caption")
                break
    return (audio if audio.is_file() else None, captions, errors)


def plan() -> dict:
    board = read_json(BOARD)
    check_storyboard(board)
    ref_doc = read_json(MANIFEST)
    refs = anchor_map(ref_doc)
    missing = inspect_assets(board, refs, ref_doc.get("ui", {}))
    _audio, _caps, more = audio_status()
    return {"schema": "autoeditorvideo/alchemy-dorama-plan/v1",
            "episode": EPISODE, "channel": "alchemy",
            "renderer": "Remotion 2D separate sprite layers, adapted from Fofinho EP01 Part3",
            "duration_seconds_target": board["duration_seconds_target"],
            "scenes": len(board["scenes"]),
            "reference_ready": not missing, "missing": missing + more,
            "ready_to_prepare": not (missing + more),
            "youtube_uploads": 0, "paid_image_calls": 0}


def prepare() -> dict:
    current = plan()
    if not current["ready_to_prepare"]:
        raise ValueError("PREFLIGHT_BLOCKED: " + ", ".join(current["missing"]))
    board = read_json(BOARD)
    refs = anchor_map(read_json(MANIFEST))
    audio, captions, _ = audio_status()
    assert audio is not None

    # Audio must be real and must not be sped up to meet duration.
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise FileNotFoundError("FFPROBE_NOT_FOUND")
    p = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
                       capture_output=True, text=True, check=True)
    seconds = float(p.stdout.strip())
    if not (150 <= seconds <= board["duration_seconds_target"]):
        raise ValueError("AUDIO_DURATION_MUST_BE_150_TO_TARGET_SECONDS")
    last_caption_end = max(c["endFrame"] for c in captions)
    if last_caption_end > round(seconds * FPS) + FPS:
        raise ValueError("CAPTIONS_OUTSIDE_REAL_AUDIO")

    PUBLIC.mkdir(parents=True, exist_ok=True)
    required = needed_keys(board)
    for key in sorted(required):
        source = ROOT / refs[key]["file"]
        destination = PUBLIC / (key + ".png")
        if destination.exists() and sha256(destination) == refs[key]["sha256"]:
            continue
        shutil.copy2(source, destination)
    shutil.copy2(audio, PUBLIC / "narracao.mp3")

    def uri(key: str) -> str:
        return "generated/alchemy-dorama-original/ep01/" + key + ".png"

    last_time = None
    shots = []
    for scene in board["scenes"]:
        number = scene["number"]
        background = scene["background_anchor"]
        sprites = []
        ids = scene["character_anchors"] + [
            v for v in scene["item_anchors"] if v not in ("UI-01", "UI-02")]
        for key in ids:
            # Every sprite uses the ORIGINAL asset, never a newly invented face.
            pose_key = selected_asset(number, key)
            if key not in refs or pose_key not in refs:
                raise ValueError("MISSING_REFERENCE_OR_POSE: " + key)
            if key not in POSITIONS.get(background, {}):
                raise ValueError("MISSING_LAYOUT_FOR_" + background + "_" + key)
            x, y, width, z = POSITIONS[background][key]
            sprites.append({
                "anchorId": key, "poseAssetId": pose_key, "image": uri(pose_key),
                "x": x, "y": y, "width": width, "zIndex": z,
                "motion": MOTIONS.get((number, key), "still"),
            })
        flashback = scene["time_layer"] == "FLASHBACK"
        flash_label = ""
        if flashback and last_time != "FLASHBACK":
            flash_label = "7 DIAS ANTES" if number == 3 else "NAQUELA NOITE"
        shots.append({
            "number": number, "startFrame": scene["start_second"] * FPS,
            "endFrame": scene["end_second"] * FPS,
            "backgroundAnchor": background, "background": uri(background),
            "timeLayer": scene["time_layer"], "flashbackLabel": flash_label,
            "cameraMotion": CAMERAS.get(number, "still"),
            "sprites": sprites,
            "systemPanel": PANELS.get(number),
            "effect": "tension" if number in (1, 9, 16) else "none",
        })
        last_time = scene["time_layer"]
    props = {
        "episodeId": EPISODE, "title": board["episode_title"],
        "durationFrames": board["duration_seconds_target"] * FPS,
        "scenes": shots, "captions": captions,
        "audio": "generated/alchemy-dorama-original/ep01/narracao.mp3",
    }
    PROPS.parent.mkdir(parents=True, exist_ok=True)
    PROPS.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
    return {"prepared": True, "props": str(PROPS),
            "duration_frames": props["durationFrames"],
            "layers": sum(len(s["sprites"]) for s in shots),
            "reference_sha256": {key: refs[key]["sha256"] for key in sorted(required)},
            "youtube_uploads": 0, "paid_image_calls": 0}


def render() -> dict:
    meta = prepare()
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm:
        raise FileNotFoundError("NPM_NOT_FOUND")
    motion = ROOT / "motion-remotion"
    if not (motion / "node_modules").is_dir():
        raise FileNotFoundError("REMOTION_DEPENDENCIES_NOT_INSTALLED")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS: preserve old video; review before rerender")
    subprocess.run([npm, "run", "render:alchemy-dorama", "--",
                    str(OUTPUT.resolve()), "--props", str(PROPS.resolve()),
                    "--concurrency", "2"],
                   cwd=motion, check=True, timeout=3600)
    if not OUTPUT.is_file() or OUTPUT.stat().st_size < 10000:
        raise ValueError("RENDER_FAILED_OR_EMPTY")
    qa = {"episode": EPISODE, "rendered": True, "video": str(OUTPUT),
          "video_sha256": sha256(OUTPUT), "technical_review": "pending_ffprobe_and_visual",
          "visual_review": "pending", "youtube_uploads": 0,
          "music_rights": "no_kids_music_copied"}
    (SOURCE / "qa-camadas.json").write_text(json.dumps(qa, indent=2) + "\n",
                                           encoding="utf-8")
    return {"render": "local_preview_only", **meta, **qa}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acao", choices=("planejar", "preparar", "renderizar"),
                    default="planejar")
    args = ap.parse_args()
    result = plan() if args.acao == "planejar" else (
        prepare() if args.acao == "preparar" else render())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as e:
        print("[ALCHEMY DORAMA BLOQUEADO] " + str(e), file=sys.stderr)
        raise SystemExit(1)
