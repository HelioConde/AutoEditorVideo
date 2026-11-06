#!/usr/bin/env python3
"""Validate a finished generation-only MP4/cover cache before sequential upload.

This script uses only stdlib. It cannot upload, publish, regenerate media or
claim human visual review, and it never opens image-provider credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from otaku_br_50_reverso import OUTPUT, validate


class PreparedBlocked(ValueError):
    pass


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def require_file(path: Path, size: int = 1000) -> None:
    if not path.is_file() or path.stat().st_size < size:
        raise PreparedBlocked("MISSING_OR_SMALL_" + path.name)


def check(number: int) -> dict:
    if number not in range(1, 51):
        raise PreparedBlocked("SHORT_NUMBER_OUT_OF_RANGE")
    row = validate()[number - 1]
    folder = OUTPUT / row["id"]
    art = [folder / ("scene-%02d.png" % i) for i in range(1, 6)]
    for item in art:
        require_file(item, 30000)
    mp4 = folder / "preview-unreviewed.mp4"
    cover = folder / "thumb.jpg"
    voice = folder / "voz-master.mp3"
    for item, min_bytes in ((mp4, 200000), (cover, 10000), (voice, 10000)):
        require_file(item, min_bytes)
    files = {name: folder / name for name in (
        "qa.json", "metadata.json", "original-art-provenance.json",
        "props.json", "marcacoes-voz.json"
    )}
    for file in files.values():
        require_file(file)
    qa = json.loads(files["qa.json"].read_text(encoding="utf-8"))
    meta = json.loads(files["metadata.json"].read_text(encoding="utf-8"))
    provenance = json.loads(files["original-art-provenance.json"].read_text(encoding="utf-8"))
    if (meta.get("episode_id") != row["id"]
            or meta.get("channel_id") != row["channel_id"]
            or meta.get("title") != row["title"]
            or meta.get("description") != row["description"]
            or meta.get("tags") != row["tags"]
            or meta.get("containsSyntheticMedia") is not True
            or meta.get("requested_privacy") != "public_after_qa"):
        raise PreparedBlocked("METADATA_NOT_APPROVED_FOR_THIS_EPISODE")
    if (provenance.get("episode_id") != row["id"]
            or provenance.get("channel_id") != row["channel_id"]
            or provenance.get("model") != "gpt-image-2"
            or provenance.get("scene_count") != 5
            or provenance.get("art_original") is not True
            or provenance.get("human_visual_review") is not False):
        raise PreparedBlocked("ART_PROVENANCE_INVALID")
    img_hashes = [digest(path) for path in art]
    if img_hashes != provenance.get("scene_sha256") or img_hashes != qa.get("scene_sha256"):
        raise PreparedBlocked("ART_HASH_MISMATCH")
    if (qa.get("video_sha256") != digest(mp4)
            or qa.get("cover_sha256") != digest(cover)
            or qa.get("voice_sha256") != digest(voice)
            or qa.get("technical") != "preview_rendered_unreviewed"
            or qa.get("publication") != "not_performed"
            or qa.get("human_visual_review") is not False):
        raise PreparedBlocked("PREPARED_MEDIA_INTEGRITY_OR_QA_MISMATCH")
    return {"short": number, "episode_id": row["id"], "ready": True,
            "publication": False, "cached_media_verified": True}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--number", required=True, type=int)
    args = p.parse_args()
    try:
        print(json.dumps(check(args.number), ensure_ascii=False))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit("[PREPARED MEDIA BLOCKED] " + str(exc)) from None
