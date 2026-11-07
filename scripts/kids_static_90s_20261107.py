#!/usr/bin/env python3
"""One-shot Kids 90-120 second AutoEditorVideo renderer. NO Fofinhos assets or uploads.

Only the 3 previously reserved original, independent kids scripts can run.
Produces original AI art, real Edge WordBoundary narration and STATIC Remotion
scenes. No mesh, pin, rig, motion brush, puppet or character interpolation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from narracao_shorts import ensure_voice
from legendas_precisas import captions_from_markers
from capa_cinematografica import render_cover

PLAN = ROOT / "conteudos" / "lote-12-estatico-90s-20261107.json"
OUT = ROOT / "cloud-kids-static-20261107"
MOTION = ROOT / "motion-remotion"
OWNER = "lote12_static_original_20261107"
IDS = (
    "kids-101-elefantinho-agua-escondida",
    "kids-102-quiz-sombras-animais",
    "kids-103-dinos-segredos-incriveis",
)
CHANNEL_ID = "UCxEzVW2Uy44OUVurTQSg_Eg"
FPS = 30
IMAGE_MODEL = "gpt-image-2"
IMAGE_BUDGET = 24

class KidsBlocked(ValueError):
    pass

def digest(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def check_manifest() -> list[dict]:
    d = json.loads(PLAN.read_text(encoding="utf-8"))
    if d.get("schema") != "autoeditorvideo/lote-12-estatico-90s/v1":
        raise KidsBlocked("MANIFEST_SCHEMA_MISMATCH")
    if d.get("production_owner") != OWNER or d.get("target_total") != 12:
        raise KidsBlocked("PRODUCTION_OWNER_OR_TOTAL_MISMATCH")
    if d.get("excluded_channels") != ["br"] or len(d.get("episodes", [])) != 12:
        raise KidsBlocked("OTHER_CHANNEL_EXCLUSION_MISSING")
    kids = [e for e in d["episodes"] if e.get("channel") == "kids"]
    if [e.get("id") for e in kids] != list(IDS):
        raise KidsBlocked("ONLY_THREE_STANDALONE_KIDS_EPISODES_PERMITTED")
    if KNOWN_IDS.get("kids") != CHANNEL_ID:
        raise KidsBlocked("KIDS_REGISTRY_ID_MISMATCH")
    for row in kids:
        assert_reserved("kids", row["id"], OWNER)
        if row.get("channel_id") != CHANNEL_ID or row.get("made_for_kids") is not True:
            raise KidsBlocked("KIDS_DESTINATION_OR_AUDIENCE_MISMATCH")
        if row.get("production_state", {}).get("upload") != "not_started":
            raise KidsBlocked("POSSIBLE_PREVIOUS_UPLOAD")
        text = " ".join([row.get("title", ""), row.get("narration_script", ""),
                         " ".join(s.get("visual_instruction", "") for s in row.get("scenes", []))])
        if any(x in text.lower() for x in ("fofinhos", "fofinho", "emanuelly e fofinho")):
            raise KidsBlocked("FOFINHOS_SERIES_IS_SEPARATE")
        if len(row.get("scenes", [])) != 8 or len(row["narration_script"].split()) < 240:
            raise KidsBlocked("SCRIPT_OR_SCENES_INCOMPLETE")
        if not row.get("cover_text") or len(row["cover_text"]) > 42:
            raise KidsBlocked("KIDS_COVER_TEXT_INVALID")
        if not row.get("description") or len(row.get("title", "")) > 100:
            raise KidsBlocked("SEO_MISSING")
        if sum(map(len, row.get("tags", []))) > 500:
            raise KidsBlocked("SEO_TAGS_TOO_LONG")
    return kids

def run(argv: list[str], *, cwd: Path = ROOT, timeout: int = 3600) -> str:
    p = subprocess.run(argv, cwd=cwd, text=True, capture_output=True,
                       check=False, timeout=timeout)
    if p.returncode:
        raise KidsBlocked("MEDIA_SUBPROCESS_FAILED_" + str(p.returncode))
    return p.stdout

def probe(path: Path) -> dict:
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", str(path)], timeout=40))

def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])

def safe_environment() -> None:
    env = os.environ
    if (env.get("GITHUB_REPOSITORY") != "HelioConde/AutoEditorVideo"
            or env.get("GITHUB_REF") != "refs/heads/main"
            or env.get("GITHUB_EVENT_NAME") != "push"
            or env.get("GITHUB_RUN_ATTEMPT") != "1"):
        raise KidsBlocked("FIRST_MAIN_PUSH_ONLY")
    if env.get("GITHUB_WORKFLOW") != "Emanuelly Kids - 3 original static 90s Shorts private upload":
        raise KidsBlocked("WRONG_WORKFLOW")
    if env.get("KIDS_BATCH_AUTHORIZED") != "yes" or env.get("IMAGE_MODEL") != IMAGE_MODEL:
        raise KidsBlocked("BATCH_OR_MODEL_NOT_AUTHORIZED")
    if env.get("MAX_IMAGE_CALLS") != str(IMAGE_BUDGET):
        raise KidsBlocked("IMAGE_CREDIT_BUDGET_MISMATCH")
    if env.get("YOUTUBE_CHANNEL_TOKEN_JSON") or env.get("YOUTUBE_BR_TOKEN_JSON"):
        raise KidsBlocked("YOUTUBE_SECRETS_FORBIDDEN_IN_IMAGE_JOB")

def tts(row: dict, ep_dir: Path) -> tuple[Path, float, list[dict]]:
    import narracao_shorts as ns
    from narracao_shorts import _spoken_words
    script = row["narration_script"]
    rate = 0
    for attempt in range(4):
        ns.RATE = "%+d%%" % rate
        take = ep_dir / ("tts-%d" % (attempt + 1))
        mp3, _ = ensure_voice({"script": script}, take, create=True,
                              engine="edge", voice="pt-BR-FranciscaNeural")
        sec = duration(mp3)
        if not (50 <= sec <= 200):
            raise KidsBlocked("TTS_DURATION_IMPLAUSIBLE")
        print("KIDS_TTS_%s_TAKE_%s_SECONDS_%.2f" % (row["id"], attempt + 1, sec),
              flush=True)
        if 90 <= sec <= 120:
            marker = json.loads((take / "marcacoes-voz.json").read_text(encoding="utf-8"))
            words = marker["words"]
            if len(words) < 200:
                raise KidsBlocked("REAL_WORD_MARKERS_INCOMPLETE")
            captions = captions_from_markers(mp3, script, sec, fps=FPS)
            if not captions or len(captions) < 35:
                raise KidsBlocked("ALIGNED_SUBTITLES_MISSING")
            return mp3, sec, words
        if attempt == 3:
            break
        # Re-synthesize naturally; never time-stretch or pad with fake silence.
        next_rate = round(((1 + rate / 100) * (sec / 105) - 1) * 100)
        if abs(next_rate - rate) < 2:
            next_rate = rate + (4 if sec > 120 else -4)
        rate = max(-25, min(30, next_rate))
    raise KidsBlocked("VOICE_NOT_IN_90_TO_120_SECONDS")

def art_prompt(row: dict, scene: dict) -> str:
    base = (
        "Generate exactly ONE original vertical 1024x1536 premium pastel 2D "
        "storybook illustration for a Brazilian children's YouTube video ages 4-8. "
        "Safe, cheerful, gentle, bright, clean natural anatomy, no frightening faces. "
        "A beautiful composed STILL FRAME, not a screenshot, not an existing cartoon. "
        "Consistent character anatomy across the eight scenes. Center the main subjects "
        "away from top 22% and lower 24% to leave space for titles and captions. "
        "Do not include any writing, numbers, logos, watermark, real child, photograph "
        "or franchise character. Never include Emanuelly, Fofinho or Fofinhos. "
        "No warped limbs, duplicated faces, merged animals, cut-off heads or props. "
    )
    if row["id"] == IDS[0]:
        base += ("Character bible: Tito is ONE small friendly light-gray elephant "
                 "with round ears and brown eyes, Bela is a WHITE rabbit, Lilo is a "
                 "SMALL YELLOW bird; keep their appearances and sizes the same. ")
    elif row["id"] == IDS[1]:
        base += ("Quiz layout: if featuring an animal, present ONE DISTINCT species "
                 "centrally against a clean calm solid pastel background, natural full-body silhouette. "
                 "No animal names in the art and no visual answer-label text. ")
    else:
        base += ("Scientifically recognizable dinosaurs, no people, Jurassic and Cretaceous "
                 "species must not be represented as contemporary real-life companions. ")
    return base + "Exact story beat: " + scene["visual_instruction"]

def image_scenes(row: dict, ep_dir: Path, key: str) -> list[Path]:
    from PIL import Image, ImageOps
    from gerar_video_codex import request_image
    images = []
    for i, scene in enumerate(row["scenes"], 1):
        name = ep_dir / ("scene-%02d.png" % i)
        if name.exists():
            raise KidsBlocked("UNVERIFIED_EXISTING_IMAGE")
        raw = request_image(art_prompt(row, scene), IMAGE_MODEL, key, "1024x1536")
        with Image.open(io.BytesIO(raw)) as img:
            img.load()
            if img.width < 512 or img.height < 768:
                raise KidsBlocked("LOW_RESOLUTION_IMAGE")
            ImageOps.pad(img.convert("RGB"), (1024, 1536),
                         method=Image.Resampling.LANCZOS,
                         color=(247, 247, 239)).save(name, "PNG")
        if name.stat().st_size < 30_000:
            raise KidsBlocked("EMPTY_ARTWORK")
        images.append(name)
        print("KIDS_ORIGINAL_ART_%s_%02d_OF_08" % (row["id"], i), flush=True)
    if len({digest(p) for p in images}) != 8:
        raise KidsBlocked("DUPLICATE_ARTWORK")
    return images

def story_cuts(row: dict, words: list[dict], sec: float) -> list[int]:
    counts = [len(s["editorial_beat"].split()) for s in row["scenes"]]
    if len(counts) != 8 or not all(counts):
        raise KidsBlocked("SCENE_WORD_COUNT_INVALID")
    cuts = [0]
    running_count = 0
    total = sum(counts)
    for amount in counts[:-1]:
        running_count += amount
        idx = min(len(words) - 1, round(len(words) * running_count / total))
        cuts.append(round(float(words[idx]["start"]) * FPS))
    cuts.append(round(sec * FPS))
    if len(cuts) != 9 or any(b - a < FPS * 4 for a, b in zip(cuts, cuts[1:])):
        raise KidsBlocked("SCENE_TIMES_INVALID")
    return cuts

def render_one(row: dict, ep_dir: Path, audio: Path, sec: float,
               words: list[dict], images: list[Path]) -> dict:
    from PIL import Image
    ns = "kids-static-20261107/" + row["id"]
    static = MOTION / "public" / "generated" / ns
    if static.exists():
        raise KidsBlocked("RENDER_NAMESPACE_ALREADY_EXISTS")
    static.mkdir(parents=True, exist_ok=False)
    for i, img in enumerate(images, 1):
        shutil.copy2(img, static / ("scene-%02d.png" % i))
    shutil.copy2(audio, static / "voz-master.mp3")
    captions = captions_from_markers(audio, row["narration_script"], sec, fps=FPS)
    if not captions:
        raise KidsBlocked("REAL_CAPTIONS_MISSING")
    cuts = story_cuts(row, words, sec)
    scenes = []
    for i in range(8):
        source = "generated/" + ns + "/scene-%02d.png" % (i + 1)
        scenes.append({"id": "%02d" % (i + 1), "subject": "objeto",
                       "startFrame": cuts[i], "endFrame": cuts[i + 1],
                       "background": source, "foreground": source,
                       "renderMode": "master_static",
                       "shotType": "wide" if i % 2 == 0 else "detail",
                       "transitionStyle": "hard" if i == 0 else "crossfade",
                       "beatRole": "setup" if i < 2 else "answer"})
    props = {"id": row["id"], "durationFrames": round(sec * FPS),
             "audio": "generated/" + ns + "/voz-master.mp3",
             "scenes": scenes, "captions": captions,
             "hook": "", "animationMode": "desligada",
             "characterPreset": "equilibrado", "visualProfile": "original",
             "editorialProfile": "kids-original-stills-no-character-rig",
             "soundCues": []}
    (ep_dir / "props.json").write_text(json.dumps(props, ensure_ascii=False,
                                                   indent=2) + "\n", encoding="utf-8")
    mp4 = ep_dir / "final.mp4"
    run(["npm", "run", "render:master", "--", str(mp4.resolve()), "--props",
         str((ep_dir / "props.json").resolve()), "--concurrency", "2",
         "--codec", "h264", "--crf", "22"], cwd=MOTION, timeout=6000)
    cover = ep_dir / "thumb.jpg"
    with Image.open(images[0]) as img:
        cover_info = render_cover(img, row["cover_text"], cover,
                                  zoom=1.0, focus_x=.5, focus_y=.4,
                                  template="kids-pastel")
    if cover_info["size"] != [1080, 1920]:
        raise KidsBlocked("INVALID_CANONICAL_COVER")
    streams = probe(mp4)
    video = [s for s in streams["streams"] if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams["streams"] if s.get("codec_type") == "audio"]
    seconds = float(streams["format"]["duration"])
    if (not (90 <= seconds <= 121) or abs(seconds - sec) > 2
            or len(video) != 1 or not audio_streams
            or video[0].get("width") != 1080 or video[0].get("height") != 1920
            or mp4.stat().st_size < 300_000):
        raise KidsBlocked("FINAL_MP4_DURATION_OR_MEDIA_INVALID")
    with Image.open(cover) as img:
        if img.size != (1080, 1920) or img.format != "JPEG":
            raise KidsBlocked("COVER_NOT_1080X1920_JPEG")
    qa = {
        "schema": "autoeditorvideo/kids-static-90s-qa/v1",
        "channel": "kids", "channel_id": CHANNEL_ID, "episode_id": row["id"],
        "real_voice_seconds": round(sec, 3), "real_mp4_seconds": round(seconds, 3),
        "dimensions": [1080, 1920], "fps": FPS,
        "original_static_illustrations": len(images),
        "image_sha256": [digest(img) for img in images],
        "voice_sha256": digest(audio), "mp4_sha256": digest(mp4),
        "cover_sha256": digest(cover),
        "word_boundary_captions": True, "mesh_warp_puppet_disabled": True,
        "manual_visual_review": False, "youtube_privacy": "private",
        "automated_technical_qa": "passed", "youtube_upload": "not_performed"
    }
    meta = {
        "channel": "kids", "channel_id": CHANNEL_ID, "id": row["id"],
        "title": row["title"], "description": row["description"],
        "tags": row["tags"], "categoryId": "1", "defaultLanguage": "pt-BR",
        "selfDeclaredMadeForKids": True, "containsSyntheticMedia": True,
        "privacyStatus": "private", "mp4_sha256": qa["mp4_sha256"],
        "cover_sha256": qa["cover_sha256"]
    }
    (ep_dir / "qa.json").write_text(json.dumps(qa, ensure_ascii=False,
                                                indent=2) + "\n", encoding="utf-8")
    (ep_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False,
                                                      indent=2) + "\n", encoding="utf-8")
    print("KIDS_RENDERED_QA_PASSED_" + row["id"], flush=True)
    return {"id": row["id"], "video": row["id"] + "/final.mp4",
            "cover": row["id"] + "/thumb.jpg", "mp4_sha256": qa["mp4_sha256"],
            "cover_sha256": qa["cover_sha256"], "duration": round(seconds, 2)}

def render_all() -> None:
    rows = check_manifest()
    safe_environment()
    from gerar_video_codex import proxy_key, check_proxy_accounts
    if OUT.exists():
        raise KidsBlocked("OUTPUT_ALREADY_EXISTS_NO_REGENERATION")
    # Make real speech before spending up to 24 image requests.
    OUT.mkdir(parents=True, exist_ok=False)
    ready = []
    for row in rows:
        folder = OUT / row["id"]
        folder.mkdir()
        voice, sec, words = tts(row, folder)
        ready.append((row, folder, voice, sec, words))
    key = proxy_key()
    check_proxy_accounts(key)
    report = {"schema": "autoeditorvideo/kids-static-90s-batch/v1",
              "owner": OWNER, "target_channel": CHANNEL_ID,
              "render_engine": "AutoEditorVideo original Remotion MasterShort",
              "media_state": "rendered_private_upload_not_yet_performed",
              "videos": []}
    for row, folder, voice, sec, words in ready:
        images = image_scenes(row, folder, key)
        report["videos"].append(render_one(row, folder, voice, sec, words, images))
        # Keep upload artifact small; QA contains image hashes, not reference photos.
        for img in images:
            img.unlink()
        for take in folder.glob("tts-*"):
            if take.is_dir():
                shutil.rmtree(take)
    if len(report["videos"]) != 3:
        raise KidsBlocked("PARTIAL_BATCH_NOT_UPLOADED")
    (OUT / "summary.json").write_text(json.dumps(report, ensure_ascii=False,
                                                  indent=2) + "\n", encoding="utf-8")
    print("ALL_THREE_KIDS_STATIC_MP4_READY_FOR_PRIVATE_UPLOAD", flush=True)

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--action", choices=("validate", "render"), default="validate")
    args = p.parse_args()
    try:
        if args.action == "validate":
            ids = [x["id"] for x in check_manifest()]
            print("KIDS_STANDALONE_RESERVED_VALIDATED_" + ",".join(ids))
        else:
            render_all()
        return 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, KidsBlocked) else type(exc).__name__
        print("KIDS_RENDER_BLOCKED_" + message, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
