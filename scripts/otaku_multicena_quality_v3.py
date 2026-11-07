#!/usr/bin/env python3
"""Build an offline QUALITY V3 Remotion preview from approved scene assets.

Input: 8-12 distinct, rights-tracked shots and real TTS word-boundary captions.
Optional character animation REQUIRES transparent pose frames plus an authored
clean background plate. A static source cannot silently become "rigged".
NO image calls, NO TTS calls, NO video render, NO YouTube API or uploads.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import unicodedata

from PIL import Image
from otaku_multicena_pose_qa import inspect_poses

WIDTH, HEIGHT = 1024, 1536
FPS = 30
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{4,100}$")
FILE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}\.(?:png|mp3|wav)$")
ALLOWED_LICENSES = {"creator_original", "public_domain_verified", "properly_licensed"}
ALLOWED_BEATS = {"hook", "setup", "detail", "rehook", "answer", "twist", "cta"}
ALLOWED_SHOTS = {"wide", "medium", "reaction", "detail", "close", "final"}

class QualityBlocked(ValueError):
    pass

def words(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.casefold())
    return re.findall(r"[a-z0-9]+", "".join(
        c for c in text if not unicodedata.combining(c)))

def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def check_manifest_path(folder: Path, filename: str, hashes: dict) -> Path:
    if not isinstance(filename, str) or not FILE_RE.fullmatch(filename):
        raise QualityBlocked("INVALID_ASSET_FILENAME")
    path = folder / filename
    # No symlink imports from outside the approved scene directory.
    if path.is_symlink() or path.resolve().parent != folder.resolve():
        raise QualityBlocked("ASSET_SYMLINK_OR_EXTERNAL_PATH_FORBIDDEN")
    if not path.is_file():
        raise QualityBlocked("MISSING_ASSET_" + filename)
    expected = hashes.get(filename)
    if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
        raise QualityBlocked("MISSING_ASSET_SHA256_" + filename)
    if digest(path) != expected:
        raise QualityBlocked("ASSET_HASH_CHANGED_" + filename)
    return path

def verify_image(path: Path, *, pose: bool = False) -> str:
    if path.suffix.lower() != ".png":
        raise QualityBlocked("SCENE_REQUIRES_PNG")
    with Image.open(path) as img:
        img.load()
        if img.size != (WIDTH, HEIGHT):
            raise QualityBlocked("SCENE_DIMENSIONS_NOT_1024x1536")
        if pose:
            if img.mode != "RGBA":
                raise QualityBlocked("POSE_MUST_HAVE_REAL_ALPHA")
            alpha = img.getchannel("A")
            extrema = alpha.getextrema()
            if extrema[0] == 255 or extrema[1] == 0:
                raise QualityBlocked("POSE_ALPHA_EMPTY_OR_OPAQUE")
            bounds = alpha.getbbox()
            if not bounds:
                raise QualityBlocked("POSE_ALPHA_EMPTY")
            covered = sum(n for index, n in enumerate(alpha.histogram()) if index > 16)
            if not .003 < covered / (WIDTH * HEIGHT) < .75:
                raise QualityBlocked("POSE_ALPHA_COVERAGE_UNSAFE")
        elif img.getbbox() is None:
            raise QualityBlocked("EMPTY_BACKGROUND_IMAGE")
        return sha256(img.convert("RGBA").tobytes()).hexdigest()

def decode_captions(data: object, duration_frames: int) -> list[dict]:
    captions = data.get("captions") if isinstance(data, dict) else data
    if not isinstance(captions, list) or len(captions) < 10:
        raise QualityBlocked("REAL_CAPTIONS_REQUIRED")
    uttered: list[dict] = []
    last = -1
    for caption in captions:
        start = caption.get("startFrame") if isinstance(caption, dict) else None
        end = caption.get("endFrame") if isinstance(caption, dict) else None
        entries = caption.get("words", []) if isinstance(caption, dict) else []
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= duration_frames:
            raise QualityBlocked("INVALID_CAPTION_BOUNDS")
        if not isinstance(entries, list) or not entries:
            raise QualityBlocked("MISSING_WORD_MARKERS")
        for word in entries:
            if not isinstance(word, dict):
                raise QualityBlocked("INVALID_WORD_MARKER")
            first, last_frame, txt = word.get("startFrame"), word.get("endFrame"), word.get("text")
            if not isinstance(first, int) or not isinstance(last_frame, int) or not isinstance(txt, str):
                raise QualityBlocked("INVALID_WORD_MARKER")
            if not 0 <= first < last_frame <= duration_frames or first < last:
                raise QualityBlocked("WORDS_OUT_OF_AUDIO_ORDER")
            last = first
            pieces = words(txt)
            if len(pieces) != 1:
                raise QualityBlocked("AMBIGUOUS_WORD_BOUNDARY")
            uttered.append({"text": pieces[0], "startFrame": first, "endFrame": last_frame})
    if uttered[-1]["endFrame"] < duration_frames * .85:
        raise QualityBlocked("VOICE_END_DOES_NOT_MATCH_CAPTIONS")
    return uttered

def phrase_position(markers: list[dict], text: str) -> int:
    phrase = words(text)
    if len(phrase) < 2 or len(phrase) > 9:
        raise QualityBlocked("SCENE_CUE_MUST_BE_2_TO_9_WORDS")
    candidates = [i for i in range(len(markers) - len(phrase) + 1)
                  if [m["text"] for m in markers[i:i+len(phrase)]] == phrase]
    if len(candidates) != 1:
        raise QualityBlocked("SCENE_CUE_NOT_UNIQUE_IN_VOICE")
    return candidates[0]

def validate_rights(item: dict, filename: str) -> None:
    rights = item.get("rights", {}) if isinstance(item, dict) else {}
    if (rights.get("type") not in ALLOWED_LICENSES or
        not isinstance(rights.get("evidence"), str) or
        len(rights["evidence"].strip()) < 12):
        raise QualityBlocked("ASSET_RIGHTS_EVIDENCE_REQUIRED_" + filename)

def build_preview(manifest_path: Path, captions_path: Path, public_root: Path,
                  *, output_path: Path | None = None) -> dict:
    manifest_path = Path(manifest_path)
    folder = manifest_path.parent
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != "autoeditorvideo/quality-preview/v3":
        raise QualityBlocked("WRONG_QUALITY_SCHEMA")
    episode = doc.get("episode_id")
    if not isinstance(episode, str) or not ID_RE.fullmatch(episode):
        raise QualityBlocked("INVALID_EPISODE_IDENTIFIER")
    if doc.get("manual_visual_review") is not False:
        raise QualityBlocked("PREVIEW_CANNOT_CLAIM_HUMAN_APPROVAL")
    duration = doc.get("duration_frames")
    # The 90-second experiment is explicitly opt-in. The legacy 20-60s
    # limits and old published content remain unchanged.
    duration_profile=doc.get("duration_profile", "legacy_short")
    if duration_profile=="short_90s_test":
        if not isinstance(duration, int) or not 87 * FPS <= duration <= 93 * FPS:
            raise QualityBlocked("NINETY_SECOND_PROFILE_REQUIRES_MEASURED_87_TO_93S")
    elif duration_profile=="legacy_short":
        if not isinstance(duration, int) or not 20 * FPS <= duration <= 60 * FPS:
            raise QualityBlocked("VIDEO_DURATION_OUT_OF_RANGE")
    else:
        raise QualityBlocked("UNKNOWN_DURATION_PROFILE")
    catalog = doc.get("sha256", {})
    shots = doc.get("shots", [])
    if not isinstance(catalog, dict) or not isinstance(shots, list) or not 8 <= len(shots) <= 12:
        raise QualityBlocked("REQUIRE_8_TO_12_EDITORIAL_SHOTS")
    narration = doc.get("narration_script")
    if not isinstance(narration, str) or len(words(narration)) < 40:
        raise QualityBlocked("INVALID_STORY")
    caps = json.loads(Path(captions_path).read_text(encoding="utf-8"))
    marker_words = decode_captions(caps, duration)
    if words(narration) != [m["text"] for m in marker_words]:
        raise QualityBlocked("CAPTIONS_DIFFER_FROM_STORY")
    if phrase_position(marker_words, doc.get("hook_text", "")) > 9:
        raise QualityBlocked("OPENING_HOOK_IS_TOO_LATE")
    payoff_position = phrase_position(marker_words, doc.get("payoff_text", ""))
    if payoff_position < len(marker_words) * .50:
        raise QualityBlocked("PAYOFF_MUST_BE_IN_SECOND_HALF")
    if not isinstance(doc.get("voice"), str):
        raise QualityBlocked("VOICE_SOURCE_MISSING")
    voice = check_manifest_path(folder, doc["voice"], catalog)
    if voice.suffix.lower() != ".mp3":
        raise QualityBlocked("VOICE_MUST_BE_MP3")
    # This stage verifies bytes/hashes, not codec or audible speech. Media QA is separate.
    if voice.stat().st_size < 100:
        raise QualityBlocked("VOICE_TOO_SMALL_FOR_PREVIEW")
    for file in (doc["voice"],):
        validate_rights({"rights": doc.get("voice_rights", {})}, file)

    locations = []
    background_hashes = []
    cue_indexes = []
    pose_scene_count = 0
    pose_geometry_reports: list[dict] = []
    assets: dict[str, Path] = {doc["voice"]: voice}
    for shot in shots:
        if not isinstance(shot, dict) or shot.get("beat_role") not in ALLOWED_BEATS:
            raise QualityBlocked("INVALID_STORY_BEAT")
        if shot.get("shot_type") not in ALLOWED_SHOTS:
            raise QualityBlocked("INVALID_SHOT_TYPE")
        cue = shot.get("start_phrase", "")
        pos = phrase_position(marker_words, cue)
        cue_indexes.append(pos)
        background_name = shot.get("background")
        bg = check_manifest_path(folder, background_name, catalog)
        bg_pixel_hash = verify_image(bg)
        background_hashes.append(bg_pixel_hash)
        validate_rights(shot, background_name)
        assets[background_name] = bg
        pose_names = shot.get("pose_frames", [])
        if not isinstance(pose_names, list) or len(pose_names) > 12:
            raise QualityBlocked("POSE_FRAME_LIST_INVALID")
        if pose_names:
            if (len(pose_names) < 2 or
                shot.get("clean_plate_confirmed") is not True or
                not isinstance(shot.get("pose_fps"), int) or
                not 4 <= shot["pose_fps"] <= 12):
                raise QualityBlocked("POSES_REQUIRE_CLEAN_PLATE_AND_FPS")
            playback = shot.get("pose_playback", "pingpong")
            if playback not in ("pingpong", "once", "loop"):
                raise QualityBlocked("UNKNOWN_POSE_PLAYBACK")
            pose_scene_count += 1
            pixel_hashes = []
            pose_paths = []
            for filename in pose_names:
                image = check_manifest_path(folder, filename, catalog)
                pixel_hashes.append(verify_image(image, pose=True))
                pose_paths.append(image)
                validate_rights(shot, filename)
                assets[filename] = image
            if len(set(pixel_hashes)) < 2:
                raise QualityBlocked("POSE_FRAMES_NOT_ACTUALLY_DIFFERENT")
            pose_geometry_reports.append({"shot_index":len(locations)+1,
                                         **inspect_poses(pose_paths)})
        locations.append({"shot":shot,"pose":pose_names})
    if len(set(cue_indexes)) != len(cue_indexes) or cue_indexes != sorted(cue_indexes):
        raise QualityBlocked("STORY_SCENES_OUT_OF_SEQUENCE")
    if cue_indexes[0] != 0:
        raise QualityBlocked("FIRST_SCENE_MUST_START_WITH_FIRST_WORD")
    # A repeated background is only meaningful with independently moving poses.
    if len(set(background_hashes)) != len(background_hashes):
        for i, hashed in enumerate(background_hashes):
            if background_hashes.count(hashed) > 1 and not locations[i]["pose"]:
                raise QualityBlocked("DUPLICATE_STATIC_BACKGROUND_HOLD")
    cuts = [0] + [marker_words[i]["startFrame"] for i in cue_indexes[1:]] + [duration]
    if any(b-a < 45 for a, b in zip(cuts, cuts[1:])):
        raise QualityBlocked("SHOTS_TOO_SHORT_FOR_READABILITY")
    # 90s episodes use up to twelve shots; holding every shot below 7s
    # would make a full 90s programme mathematically impossible with ten.
    max_hold=12 * FPS if duration_profile=="short_90s_test" else 7 * FPS
    if any(b-a > max_hold for a, b in zip(cuts, cuts[1:])):
        raise QualityBlocked("SHOT_HELD_TOO_LONG_FOR_DURATION_PROFILE")
    root = Path(public_root)
    relative = f"generated/otaku-quality-v3/{episode}"
    scene_items = []
    for i, ref in enumerate(locations):
        shot = ref["shot"]
        bkg = f"{relative}/{shot['background']}"
        item = {"id": f"{i+1:02d}", "subject": "personagens",
                "startFrame": cuts[i], "endFrame": cuts[i+1],
                "background": bkg,
                "foreground": bkg,
                "renderMode": "master_static", "shotType": shot["shot_type"],
                "beatRole": shot["beat_role"],
                "transitionStyle": "hard" if shot["beat_role"] in
                    ("hook", "rehook", "twist", "answer") else "crossfade"}
        if ref["pose"]:
            paths = [f"{relative}/{name}" for name in ref["pose"]]
            item["renderMode"] = "multilayer"
            item["foreground"] = paths[0]
            item["layers"] = [{
                "id": f"{i+1:02d}-character", "role": "character",
                "src": paths[0], "z": 10,
                "rigFrames": {"fps": shot["pose_fps"],
                              "frames": paths,
                              "playback": shot.get("pose_playback", "pingpong")}
            }]
        scene_items.append(item)
    sound_cues = []
    for i, ref in enumerate(locations):
        for cue in ref["shot"].get("sound_effects", []):
            if not isinstance(cue, dict):
                raise QualityBlocked("INVALID_SOUND_EFFECT")
            fname = cue.get("file")
            path = check_manifest_path(folder, fname, catalog)
            validate_rights(cue, fname)
            if path.suffix.lower() not in (".wav", ".mp3"):
                raise QualityBlocked("UNSUPPORTED_AUDIO_CUE")
            assets[fname] = path
            offset = cue.get("offset_seconds")
            length = cue.get("duration_seconds")
            volume = cue.get("volume")
            if (not isinstance(offset, (int, float)) or isinstance(offset, bool) or
                not isinstance(length, (int, float)) or isinstance(length, bool) or
                not isinstance(volume, (int, float)) or isinstance(volume, bool) or
                not 0 <= offset <= 6 or not .1 <= length <= 5 or
                not 0 <= volume <= .4):
                raise QualityBlocked("SOUND_TIMING_OR_VOLUME_UNSAFE")
            start = cuts[i] + round(offset * FPS)
            end = min(cuts[i+1], start + round(length * FPS))
            if end <= start:
                raise QualityBlocked("SOUND_STARTS_OUTSIDE_SCENE")
            sound_cues.append({"src": f"{relative}/{fname}", "startFrame": start,
                               "endFrame": end, "volume": float(volume)})
    music = None
    if doc.get("music"):
        soundtrack = doc["music"]
        if not isinstance(soundtrack, dict):
            raise QualityBlocked("MUSIC_CONFIGURATION_INVALID")
        name = soundtrack.get("file")
        path = check_manifest_path(folder, name, catalog)
        validate_rights(soundtrack, name)
        volume = soundtrack.get("volume")
        if not isinstance(volume, (float, int)) or isinstance(volume, bool) or not 0 < volume <= .2:
            raise QualityBlocked("MUSIC_TOO_LOUD")
        if path.suffix.lower() not in (".wav", ".mp3"):
            raise QualityBlocked("MUSIC_FORMAT_INVALID")
        assets[name] = path
        music = {"src": f"{relative}/{name}", "volume": float(volume)}

    props = {"id": episode, "durationFrames": duration, "audio": f"{relative}/{doc['voice']}",
             "scenes": scene_items, "captions": caps["captions"] if isinstance(caps, dict) else caps,
             "hook": doc["hook_text"], "animationMode": "esqueleto2d" if pose_scene_count else "cinematica",
             "characterPreset": "equilibrado", "visualProfile": "original",
             "editorialProfile": "otaku-quality-v3-unreviewed",
             "soundCues": sound_cues, "backgroundMusic": music}
    report = {
        "schema": "autoeditorvideo/quality-preview-qa/v3",
        "episode_id": episode,
        "shot_count": len(shots),
        "pose_animated_shots": pose_scene_count,
        "static_shots": len(shots) - pose_scene_count,
        "sound_effect_count": len(sound_cues),
        "pose_geometry_checks": pose_geometry_reports,
        "shot_start_frames": cuts,
        "duration_profile": duration_profile,
        "target_seconds": 90 if duration_profile=="short_90s_test" else None,
        "actual_seconds_from_tts_markers": round(duration/FPS,3),
        "asset_sha256": {name: digest(path) for name, path in assets.items()},
        "technical_preflight": "assets_and_voice_markers_checked",
        "human_visual_review": False,
        "rendered_video": False, "youtube_upload": False, "publish_authorized": False,
    }
    if output_path is not None:
        target = root / relative
        target.mkdir(parents=True, exist_ok=True)
        for name, src in assets.items():
            out = target / name
            if out.exists():
                if digest(out) != digest(src):
                    raise QualityBlocked("DESTINATION_ASSET_COLLISION_" + name)
            else:
                shutil.copy2(src, out)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(props, ensure_ascii=False, indent=2)+"\n",
                               encoding="utf-8")
        output_path.with_name(output_path.stem+"-qa.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return {"props": props, "qa": report}

def main() -> int:
    parser = argparse.ArgumentParser(description="Only builds offline Remotion props; never renders or uploads")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--captions", type=Path, required=True)
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(build_preview(args.manifest, args.captions,
                                   args.public_root, output_path=args.output)["qa"],
                     ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit("[QUALITY V3 BLOCKED] "+str(exc)) from None
