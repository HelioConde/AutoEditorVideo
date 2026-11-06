#!/usr/bin/env python3
"""Offline queue validator/planner for Otaku Multicena's 50 original Shorts.

No generation, uploads, OAuth, public release, or token reads.
Original video art and reviewed MP4s are NOT present in the repository.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "conteudos" / "otaku-multicena-br-50-inéditos-reverso-20261106.json"
RESERVATIONS = ROOT / "conteudos" / "otaku-production-reservations.json"
OUTPUT = ROOT / "assets" / "gerados" / "otaku-multicena-experimento-50"
OWNER = "otaku_multicena_br_50_reverso_20261106"
CHANNEL_ID = "UCXGYTuBYn-0Ziqin5ajKhOw"
CODES = ("autoeditorvideo-", "autoeditorvideo_", "autoeditorvideo:")

class PreflightError(ValueError):
    pass


def load() -> tuple[dict, dict]:
    return (json.loads(PLAN.read_text(encoding="utf-8-sig")),
            json.loads(RESERVATIONS.read_text(encoding="utf-8-sig")))


def validate() -> list[dict]:
    manifest, registry = load()
    if manifest.get("schema") != "autoeditorvideo/otaku-br-experimento-50-reverso/v1":
        raise PreflightError("SCHEMA_MISMATCH")
    if manifest.get("channel") != "br" or manifest.get("channel_id") != CHANNEL_ID:
        raise PreflightError("WRONG_YOUTUBE_CHANNEL")
    if manifest.get("reservation_owner") != OWNER:
        raise PreflightError("WRONG_RESERVATION_OWNER")
    if manifest.get("publication_state") != "none_generated_or_uploaded":
        raise PreflightError("UNEXPECTED_PUBLICATION_STATE")
    if manifest.get("upload_order") != list(range(50, 0, -1)):
        raise PreflightError("UPLOAD_ORDER_NOT_REVERSE")
    rows = manifest.get("episodes")
    if not isinstance(rows, list) or len(rows) != 50:
        raise PreflightError("EXPECTED_FIFTY_UNIQUE_SHORTS")
    reserved = {(e["channel"], e["id"]): e for e in registry["entries"]}
    seen_titles = set()
    seen_hooks = set()
    seen_ids = set()
    for idx, row in enumerate(rows, 1):
        key = ("br", row.get("id"))
        if row.get("position") != idx or key != ("br", str(6100 + idx) + "-multicena-experimento-novembro"):
            raise PreflightError("EPISODE_ORDER_OR_ID_INVALID")
        if key in seen_ids:
            raise PreflightError("REUSED_EPISODE_ID")
        seen_ids.add(key)
        item = reserved.get(key)
        if not item or item.get("status") != "reserved" or item.get("reservation_owner") != OWNER:
            raise PreflightError("EPISODE_NOT_RESERVED_IN_MAIN_" + str(idx))
        if item.get("publication_target") != "public_after_complete_individual_QA":
            raise PreflightError("UNSAFE_PUBLICATION_GATE")
        title = row.get("title", "").strip()
        if not (12 <= len(title) <= 100):
            raise PreflightError("BAD_TITLE_" + str(idx))
        if title.casefold() in seen_titles:
            raise PreflightError("DUPLICATE_TITLE")
        seen_titles.add(title.casefold())
        hook = row.get("hook", "").strip()
        if hook.casefold() in seen_hooks:
            raise PreflightError("DUPLICATE_HOOK")
        seen_hooks.add(hook.casefold())
        desc = row.get("description", "")
        if not 75 <= len(desc) <= 5000 or "#Shorts" not in desc:
            raise PreflightError("DESCRIPTION_INVALID_" + str(idx))
        if "geradas por IA" not in desc:
            raise PreflightError("MISSING_ORIGINAL_ILLUSTRATION_DISCLOSURE")
        tags = row.get("tags")
        if (not isinstance(tags, list) or len(tags) < 7
                or any(not isinstance(t, str) or not t.strip() for t in tags)):
            raise PreflightError("BAD_TAGS_" + str(idx))
        if len(", ".join(tags)) > 500:
            raise PreflightError("TAG_LIMIT_EXCEEDED")
        if len({t.casefold() for t in tags}) != len(tags):
            raise PreflightError("REPEATED_TAGS")
        if any(t.casefold().startswith(CODES) or re.match(r"^\\d{4}-", t) for t in tags):
            raise PreflightError("INTERNAL_TAG_LEAK")
        words = row.get("narration_script", "").split()
        if not 50 <= len(words) <= 120 or row.get("script_words") != len(words):
            raise PreflightError("BAD_NARRATION_" + str(idx))
        story = row.get("storyboard")
        if not isinstance(story, list) or len(story) < 5:
            raise PreflightError("MINIMUM_FIVE_DISTINCT_STORY_BEATS")
        if [shot.get("index") for shot in story] != list(range(1, len(story) + 1)):
            raise PreflightError("SCENE_SEQUENCE_MISMATCH")
        if any(len(shot.get("action", "").strip()) < 50 for shot in story):
            raise PreflightError("SCENE_WITHOUT_DETAILED_ACTION")
        if row.get("expected_order") != 51 - idx:
            raise PreflightError("UPLOAD_ORDER_MISMATCH")
    return rows


def ordered(rows: list[dict]) -> list[dict]:
    return list(reversed(rows))


def candidates(rows: list[dict], limit: int) -> list[dict]:
    if limit == 0:
        return ordered(rows)
    return ordered(rows)[:limit]


def file_report(row: dict, root: Path = OUTPUT) -> dict:
    folder = root / row["id"]
    media = [folder / ("scene-%02d.png" % i) for i in range(1, 6)]
    files = {
        "original_art": media,
        "narration": [folder / "voz-master.mp3", folder / "marcacoes-voz.json"],
        "captions": [folder / "legendas.ass"],
        "thumbnail": [folder / "thumb.jpg"],
        "video": [folder / "final.mp4"],
        "qa": [folder / "qa.json"],
    }
    missing = [str(path.relative_to(root)) for group in files.values()
               for path in group if not path.is_file()]
    qa_file = files["qa"][0]
    qa = json.loads(qa_file.read_text(encoding="utf-8")) if qa_file.is_file() else {}
    review = qa.get("editorial_review") == "approved" and qa.get("technical_review") == "approved"
    copyright_clear = qa.get("rights_review") == "approved"
    return {"position": row["position"], "id": row["id"], "title": row["title"],
            "missing_artifacts": missing, "qa_approved": review,
            "rights_approved": copyright_clear,
            "ready_for_publication": not missing and review and copyright_clear}


def prepare(rows: list[dict], limit: int) -> list[dict]:
    output = []
    for row in candidates(rows, limit):
        folder = OUTPUT / row["id"]
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / "production-plan.json"
        # This is a DRAFT plan, not evidence of rendering or approval.
        if not file.exists():
            payload = {"status": "production_plan_only", "channel": "br",
                       "channel_id": CHANNEL_ID, "publication_target": "public_after_QA",
                       "source": str(PLAN.relative_to(ROOT)),
                       "title": row["title"], "description": row["description"],
                       "tags": row["tags"], "narration_script": row["narration_script"],
                       "cover_text": row["cover_text"], "storyboard": row["storyboard"],
                       "original_art_required": ["scene-%02d.png" % i for i in range(1, 6)],
                       "thumbnail_engine": "scripts/capa_cinematografica.py",
                       "voice_engine": "scripts/narracao_shorts.py",
                       "caption_engine": "scripts/legendas_precisas.py",
                       "render_engine": "motion-remotion/src/master-short.tsx"}
            file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        output.append({"position": row["position"], "plan_path": str(file.relative_to(OUTPUT))})
    return output


def main() -> int:
    p = argparse.ArgumentParser(description="Otaku BR 50 Shorts: plano reverso, nenhuma publicacao")
    p.add_argument("--action", choices=("validate", "list", "plan", "status"), default="validate")
    p.add_argument("--limit", type=int, default=0,
                   help="0=todos. Valores positivos selecionam a partir do 50.")
    args = p.parse_args()
    if not 0 <= args.limit <= 50:
        p.error("--limit precisa estar entre 0 e 50")
    rows = validate()
    target = candidates(rows, args.limit)
    if args.action == "validate":
        result = {"status": "validated_editorial_metadata_only", "titles": len(rows),
                  "shorts": len(rows), "first": target[0]["position"] if target else None,
                  "last": target[-1]["position"] if target else None,
                  "upload_attempts": 0, "generated_videos": 0}
    elif args.action == "list":
        result = [{"order": 51 - row["position"], "number": row["position"],
                   "anime": row["series"], "title": row["title"]}
                  for row in target]
    elif args.action == "plan":
        result = {"planned": prepare(rows, args.limit), "uploaded": False, "public": 0}
    else:
        result = {"status": "checking_actual_local_artifacts_no_api_calls",
                  "files": [file_report(row) for row in target],
                  "upload_attempts": 0}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as exc:
        raise SystemExit("[BLOQUEADO OTaku BR 50] " + str(exc))
