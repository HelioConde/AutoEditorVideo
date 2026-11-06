#!/usr/bin/env python3
"""Render one or more already-provided ORIGINAL anime editorial illustrations.

Uses AutoEditorVideo voice, real word-aligned captions, Remotion MasterShort
and original cover generator. Does not generate copyrighted footage or upload.
By default renders only number 50. Requires pre-existing original images
and source provenance; NEVER substitutes other episodes' images.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from otaku_br_50_reverso import OUTPUT, validate
from narracao_shorts import ensure_voice
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover, STYLE as COVER_STYLE

MOTION = ROOT / "motion-remotion"
FPS = 30


class RenderBlocked(RuntimeError):
    pass


def digest(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def call(argv: list[str], *, cwd: Path = ROOT, timeout: int = 2400) -> None:
    result = subprocess.run(argv, cwd=cwd, check=False, timeout=timeout,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True)
    if result.returncode:
        # Avoid dumping a log containing possibly private paths/credentials.
        raise RenderBlocked("AUTOEDITOR_SUBPROCESS_FAILED_" + str(result.returncode))


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_format",
                        "-show_streams", "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=50, check=True)
    return json.loads(r.stdout)


def size_ok(path: Path) -> bool:
    from PIL import Image
    with Image.open(path) as im:
        return im.size == (1024, 1536)


def preflight(row: dict) -> tuple[Path, list[Path]]:
    folder = OUTPUT / row["id"]
    if not folder.exists():
        raise RenderBlocked("ART_NOT_CREATED_FOR_" + row["id"])
    originals = [folder / ("scene-%02d.png" % i) for i in range(1, 6)]
    if not all(p.is_file() and p.stat().st_size > 30000 for p in originals):
        raise RenderBlocked("FIVE_ORIGINAL_SCENE_IMAGES_NOT_READY_" + row["id"])
    if not all(size_ok(p) for p in originals):
        raise RenderBlocked("ORIGINAL_ILLUSTRATIONS_REQUIRE_1024x1536")
    source = folder / "original-art-provenance.json"
    if not source.is_file():
        raise RenderBlocked("MISSING_SOURCE_RIGHTS_AND_CHARACTER_QA")
    data = json.loads(source.read_text(encoding="utf-8"))
    if (data.get("episode_id") != row["id"]
            or data.get("channel_id") != row["channel_id"]
            or data.get("model") != "gpt-image-2"
            or data.get("art_original") is not True
            or data.get("visual_qa") != "automated_technical_checks_only"
            or data.get("rights_qa") != "AI_generated_no_imported_media"
            or data.get("scene_count") != 5):
        raise RenderBlocked("ORIGINAL_ART_TECHNICAL_PROVENANCE_MISSING")
    hashes = data.get("scene_sha256")
    if hashes != [digest(p) for p in originals]:
        raise RenderBlocked("IMAGE_CHECKSUM_OR_EPISODE_MISMATCH")
    if folder.joinpath("youtube-upload-receipt.json").exists():
        raise RenderBlocked("ALREADY_HAS_UPLOAD_RECEIPT_DO_NOT_RENDER_OR_REUPLOAD")
    return folder, originals


def render_one(row: dict, *, force: bool = False) -> dict:
    from PIL import Image
    folder, art = preflight(row)
    mp4 = folder / "final.mp4"
    if mp4.exists() and not force:
        raise RenderBlocked("MP4_ALREADY_EXISTS_USE_EXISTING_ARTIFACT_OR_EXPLICIT_REVIEW")
    audio, subtitle = ensure_voice({"script": row["narration_script"]},
                                   folder, create=True, engine="edge")
    info = probe(audio)
    seconds = float(info["format"]["duration"])
    if not 20 <= seconds <= 59.2:
        raise RenderBlocked("NARRATION_OUTSIDE_20_TO_59_2_SECONDS")
    captions = captions_from_markers(audio, row["narration_script"], seconds, fps=FPS)
    if not captions or len(captions) < 10 or any(len(c["words"]) > 3 for c in captions):
        raise RenderBlocked("NATIVE_CAPTION_ALIGNMENT_INVALID")
    if captions[-1]["endFrame"] < FPS * seconds * .88:
        raise RenderBlocked("FINAL_CAPTION_ENDS_TOO_EARLY")
    namespace = "otaku-br-50/" + row["id"]
    static = MOTION / "public" / "generated" / namespace
    static.mkdir(parents=True, exist_ok=True)
    frames = math.ceil(FPS * seconds)
    cuts = [round(frames * i / len(art)) for i in range(len(art) + 1)]
    scenes = []
    for i, file in enumerate(art):
        img = static / ("scene-%02d.png" % (i + 1))
        shutil.copy2(file, img)
        # Foreground is transparent until a separately reviewed RGBA cast is available.
        fg = static / ("scene-%02d-foreground.png" % (i + 1))
        Image.new("RGBA", (1024, 1536), (0, 0, 0, 0)).save(fg)
        if cuts[i + 1] <= cuts[i]:
            raise RenderBlocked("ZERO_LENGTH_SCENE")
        scenes.append({
            "id": "%02d" % (i + 1), "subject": "personagens",
            "startFrame": cuts[i], "endFrame": cuts[i+1],
            "background": "generated/" + namespace + "/" + img.name,
            "foreground": "generated/" + namespace + "/" + fg.name,
            "renderMode": "master_static",
            "transitionStyle": "hard" if i == 0 or i == 3 else "crossfade",
            "shotType": "detail" if i in (1, 3) else "medium",
            "beatRole": ["hook", "setup", "detail", "answer", "cta"][i],
        })
    shutil.copy2(audio, static / "voz-master.mp3")
    props = {
        "id": row["id"], "durationFrames": frames,
        "audio": "generated/" + namespace + "/voz-master.mp3",
        "scenes": scenes, "captions": captions,
        "hook": row["cover_text"], "animationMode": "cinematica",
        "characterPreset": "equilibrado", "visualProfile": "original",
        "editorialProfile": "otaku-br-experimento-50"
    }
    prop_file = folder / "props.json"
    prop_file.write_text(json.dumps(props, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    video = folder / "preview-unreviewed.mp4"
    call(["npm", "run", "render:master", "--", str(video.resolve()),
          "--props", str(prop_file.resolve()), "--concurrency", "2"], cwd=MOTION)
    if not video.is_file() or video.stat().st_size < 200000:
        raise RenderBlocked("REMOTION_DID_NOT_CREATE_VALID_VIDEO")
    with Image.open(art[0]) as im:
        cover = render_cover(im, row["cover_text"], folder / "thumb.jpg",
                             zoom=1.02, focus_x=.5, focus_y=.35)
    if cover.get("style") != COVER_STYLE or cover.get("size") != [1080, 1920]:
        raise RenderBlocked("OFFICIAL_AUTOEDITOR_THUMBNAIL_FAILED")
    metadata = {"channel": "br", "channel_id": row["channel_id"],
                "episode_id": row["id"], "title": row["title"],
                "description": row["description"], "tags": row["tags"],
                "language": "pt-BR", "category_id": "1",
                "self_declared_made_for_kids": False,
                "containsSyntheticMedia": True,
                "requested_privacy": "public_after_qa"}
    (folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    qa = {"video_sha256": digest(video),
          "cover_sha256": digest(folder / "thumb.jpg"),
          "voice_sha256": digest(audio),
          "scene_sha256": [digest(p) for p in art],
          "technical": "preview_rendered_unreviewed",
          "editorial_review": "manifest_approved_by_creator_not_individual_video",
          "human_visual_review": False,
          "rights_review": "no_imported_media_automated_check_only",
          "youtube_upload": "not_performed",
          "publication": "not_performed"}
    (folder / "qa.json").write_text(json.dumps(qa, indent=2)+"\n",encoding="utf-8")
    return {"number":row["position"],"status":"rendered_unreviewed_preview",
            "file":str(video.relative_to(ROOT)),
            "upload_attempts":0,"youtube_publication":False}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--number", type=int, default=50)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--action", choices=("preflight", "render"), default="preflight")
    a = ap.parse_args()
    if a.number not in range(1,51):
        ap.error("Number must be 01..50")
    rows = validate()
    row = rows[a.number - 1]
    if a.action == "preflight":
        folder, art = preflight(row)
        print(json.dumps({"status":"original_art_preflight_passed", "number":a.number,
                          "image_count":len(art),"output":str(folder)},ensure_ascii=False))
        return 0
    print(json.dumps(render_one(row,force=a.force),ensure_ascii=False,indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RenderBlocked, ValueError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit("[BLOQUEADO AUTOEDITOR BR] "+str(exc))
