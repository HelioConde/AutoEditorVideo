#!/usr/bin/env python3
"""Run an Otaku Multicena BR Short with the REAL AutoEditorVideo engine in Actions.

No external compositor, no upload, no copyright assets from video footage.
This runner delegates the actual work to fluxo_unico_short.py, which uses the
canonical storyboard, Codex Proxy scene layers, Edge TTS and Remotion.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EPISODE = "5008-firefly-wedding"
MAX_ALLOWED_CALLS = 21
REVIEW = ROOT / "cloud-br-review"


class CloudBRBlocked(ValueError):
    pass


def validate_job_environment(env: dict[str, str], episode_id: str,
                             image_budget: int) -> None:
    """Fail closed before ANY image, voice or publication requests."""
    if episode_id != EPISODE:
        raise CloudBRBlocked("EPISODE_NOT_AUTHORIZED")
    if not isinstance(image_budget, int) or not 0 <= image_budget <= MAX_ALLOWED_CALLS:
        raise CloudBRBlocked("IMAGE_BUDGET_EXCEEDS_21")
    if env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo":
        raise CloudBRBlocked("WRONG_GITHUB_REPOSITORY")
    if env.get("GITHUB_REF") != "refs/heads/main":
        raise CloudBRBlocked("MAIN_ONLY")
    if env.get("GITHUB_RUN_ATTEMPT") != "1":
        raise CloudBRBlocked("RERUN_NOT_AUTHORIZED")
    if env.get("GITHUB_EVENT_NAME") not in ("push", "workflow_dispatch"):
        raise CloudBRBlocked("UNAUTHORIZED_EVENT")
    if env.get("IMAGE_MODEL") != "gpt-image-2":
        raise CloudBRBlocked("UNEXPECTED_IMAGE_MODEL")
    # Availability and actual OAuth account are checked by the ORIGINAL engine.
    # Secrets must never be printed or passed as CLI arguments.
    if image_budget and not env.get("PROXY_API_KEY"):
        raise CloudBRBlocked("PROXY_SECRET_NOT_SET")


def private_review_files(root: Path, episode_id: str) -> dict[str, Path]:
    folder = root / "assets" / "gerados" / "shorts-animados" / episode_id
    return {
        "video": folder / f"{episode_id}-master-multicenas-personagens-v3-equilibrado.mp4",
        "cover": folder / f"{episode_id}-master-capa.jpg",
        "qa": folder / "qa-master-multicenas.json",
        "metadata": root / "assets" / "gerados" / "publicacao-youtube" / "episodios" / f"{episode_id}.json",
    }


def prepare_review(root: Path, episode_id: str, target: Path) -> dict:
    """Publish ONLY one final MP4, cover, metadata and safe QA; never private state."""
    if episode_id != EPISODE:
        raise CloudBRBlocked("EPISODE_NOT_AUTHORIZED")
    paths = private_review_files(root, episode_id)
    for kind, path in paths.items():
        if not path.is_file():
            raise CloudBRBlocked(f"MISSING_{kind.upper()}")
        if path.stat().st_size == 0:
            raise CloudBRBlocked(f"EMPTY_{kind.upper()}")
    qa = json.loads(paths["qa"].read_text(encoding="utf-8"))
    if qa.get("id") != episode_id or qa.get("status") != "renderizado-aguardando-revisao":
        raise CloudBRBlocked("QA_DID_NOT_AUTHORIZE_REVIEW")
    if qa.get("published") is not False:
        raise CloudBRBlocked("PUBLISHED_FLAG_NOT_FALSE")
    if qa.get("animation_mode") != "cinematica":
        raise CloudBRBlocked("WRONG_RENDERER_MODE")
    if not isinstance(qa.get("visual_shots"), int) or qa["visual_shots"] < 5:
        raise CloudBRBlocked("NOT_ENOUGH_VISUAL_SHOTS")
    from shorts_duration import validate_video
    seconds = validate_video(paths["video"], stage="Cloud BR preview")
    if seconds > 60:
        raise CloudBRBlocked("DURATION_EXCEEDS_SHORT")
    if paths["video"].stat().st_size > 450_000_000:
        raise CloudBRBlocked("VIDEO_ARTIFACT_TOO_LARGE")
    with Image.open(paths["cover"]) as im:
        im.load()
        if im.format != "JPEG" or abs(im.width / im.height - 9/16) > .02:
            raise CloudBRBlocked("INVALID_VERTICAL_COVER")
    if target.exists():
        raise CloudBRBlocked("REVIEW_OUTPUT_ALREADY_EXISTS")
    target.mkdir(parents=True, mode=0o700)
    dest_names = {
        "video": f"{episode_id}-autoeditorvideo-BR.mp4",
        "cover": f"{episode_id}-cover.jpg",
        "qa": f"{episode_id}-qa.json",
        "metadata": f"{episode_id}-metadata.json",
    }
    for kind, source in paths.items():
        shutil.copyfile(source, target / dest_names[kind])
    summary = {
        "schema": "autoeditorvideo/cloud-br-preview/v1",
        "episode": episode_id,
        "render_origin": "AutoEditorVideo/scripts/fluxo_unico_short.py -> renderizar_master_remotion.py",
        "duration_seconds": round(seconds, 2),
        "visual_shots": qa["visual_shots"],
        "made_with_proxy_scene_layers": True,
        "automatic_technical_qa": True,
        "manual_artistic_review_required": True,
        "publication": "none",
        "notice": "GitHub public-repository Action artifacts can be read by people with repository read access; no child or private photos.",
    }
    (target / "review-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", default=EPISODE)
    ap.add_argument("--max-image-calls", required=True, type=int)
    ap.add_argument("--only-package", action="store_true")
    args = ap.parse_args(argv)
    try:
        validate_job_environment(os.environ, args.id, args.max_image_calls)
        if not args.only_package:
            from master_scenes import production_storyboard, read_storyboard, estimate
            # Predict cost before voice synthesis or starting paid generation.
            plan = read_storyboard(production_storyboard(args.id, 6))
            pending = len(estimate(plan, plan["scenes"], "gpt-image-2"))
            print(f"[CLOUD BR] STORYBOARD_{len(plan['scenes'])}_SHOTS")
            print(f"[CLOUD BR] EXPECTED_IMAGE_REQUESTS_{pending}")
            if pending > args.max_image_calls:
                raise CloudBRBlocked("UNAPPROVED_IMAGE_BUDGET")
            cmd = [
                sys.executable, str(ROOT / "scripts" / "fluxo_unico_short.py"),
                "--id", args.id, "--modelo", "gpt-image-2",
                "--voz-motor", "edge", "--perfil", "equilibrado",
                "--max-chamadas", str(args.max_image_calls),
                "--tentativas", "1", "--privacidade", "private",
            ]
            # NEVER add --publicar, and do not pass credentials on command line.
            print("[CLOUD BR] REAL_AUTOEDITORVIDEO_PIPELINE_START_NO_YOUTUBE_UPLOAD")
            subprocess.run(cmd, cwd=ROOT, check=True)
        summary = prepare_review(ROOT, args.id, REVIEW)
        print(f"[CLOUD BR] MP4_READY_DURATION_{summary['duration_seconds']}s")
        print(f"[CLOUD BR] FRAMES_{summary['visual_shots']}_SCENES")
        print("[CLOUD BR] REVIEW_ARTIFACT_ONLY_NO_YOUTUBE_UPLOAD")
        return 0
    except CloudBRBlocked as exc:
        print("[CLOUD BR] BLOCKED_" + str(exc), file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        # Do NOT stringify downstream errors because untrusted upstream responses
        # and paths can contain sensitive account data.
        print("[CLOUD BR] PIPELINE_OR_TECHNICAL_QA_FAILED", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
