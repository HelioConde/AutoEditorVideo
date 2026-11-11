#!/usr/bin/env python3
"""New 15-video batch: 3 each BR/EN/Gamer/Alchemy/Kids, one-shot private-first.

Builds genuine TTS + WordBoundary captions + original 8 editorial images + Remotion
MP4 and official 1080x1920 cover. A separate upload job verifies exact owner and
channel, hashes and existing uploads. The script never opens YouTube OAuth.
No anime frames, real gameplay, false app demos, hidden private family images.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import remaining_static_90s_20261107 as engine
from production_reservations import assert_reserved
from youtube_channel_registry import KNOWN_IDS
from kids_static_90s_20261107 import digest

MANIFEST = ROOT / "conteudos" / "lote-15-canais-20261108.json"
OUTPUT_ROOT = ROOT / "cloud-lote-15-canais-20261108"
WORKFLOW = "AutoEditorVideo - 15 new Shorts BR EN Gamer Kids Alchemy private-first"
OWNER = "lote15_novos_20261108"
IMAGE_MODEL = "gpt-image-2"
CHANNELS = ("br", "en", "games", "kids", "alchemy")
IMAGE_BUDGET = 24
EXPECTED = {
    "br": ("5015-jujutsu-kaisen-dominio","5016-dungeon-meshi-masmorra","5017-attack-on-titan-muralhas"),
    "en": ("7014-fullmetal-troca-equivalente","7015-one-piece-poneglyphs","7016-hunter-nen-restricoes"),
    "games": ("game-104-terraria-primeira-noite","game-105-stardew-estacoes","game-106-celeste-dificuldade"),
    "kids": ("kids-104-abelhinha-e-as-cores","kids-105-tartaruguinha-e-a-chuva","kids-106-estrelinhas-contam"),
    "alchemy": ("alchemy-104-automacao-gatilhos","alchemy-105-agentes-supervisao","alchemy-106-ia-checagem-fontes"),
}
TOKENS = {
    "br": "YOUTUBE_BR_TOKEN_JSON",
    "en": "YOUTUBE_EN_TOKEN_JSON",
    "games": "YOUTUBE_GAMES_TOKEN_JSON",
    "kids": "YOUTUBE_KIDS_TOKEN_JSON",
    "alchemy": "YOUTUBE_ALCHEMY_TOKEN_JSON",
}
CATEGORY = {"br":"24","en":"24","games":"20","kids":"1","alchemy":"28"}
STYLES = {
    "br": "Premium original anime editorial art, emotionally legible plot objects and dramatic environments; conceptual, no official anime frames or unreferenced imitation of named characters.",
    "en": "Premium original Japanese fantasy editorial art, symbolism and coherent fantasy settings, never a copied anime frame or fake canonical character.",
    "games": "Premium original game-inspired concept illustrations with accurate themed worlds, no gameplay recording, UI, logos, or claim to have played.",
    "kids": "Gentle original 2D preschool storybook with consistent cute animals, friendly eyes, safe proportions, clear bright color palette and calm scenes. No real child reference or private photographs.",
    "alchemy": "Premium original technology education diagram illustration with conceptual elements, no fabricated screenshot, results or actual application testing.",
}

engine.VOICES.update({"br":"pt-BR-AntonioNeural","en":"en-US-AriaNeural",
                      "games":"pt-BR-AntonioNeural","kids":"pt-BR-FranciscaNeural",
                      "alchemy":"pt-BR-FranciscaNeural"})
engine.CATEGORY.update(CATEGORY)
engine.PROFILE.update({"br":"original","en":"original",
                       "games":"gamer-alchemy-reference","kids":"original",
                       "alchemy":"gamer-alchemy-reference"})
engine.COVER.update({"br":"default","en":"default",
                     "games":"gamer-alchemy-reference","kids":"default",
                     "alchemy":"gamer-alchemy-reference"})
engine.OUTPUT_ROOT=OUTPUT_ROOT
engine.IMAGE_MODEL=IMAGE_MODEL

class BatchBlocked(ValueError):
    pass

def output(channel:str)->Path:
    return OUTPUT_ROOT / channel

def validate(channel:str)->list[dict]:
    if channel not in CHANNELS:
        raise BatchBlocked("UNKNOWN_CHANNEL")
    d=json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (d.get("schema")!="autoeditorvideo/new-15-five-channels-editorial-v1"
            or d.get("production_owner")!=OWNER or d.get("requested_total")!=15
            or d.get("per_channel")!=3 or d.get("default_visibility")!="private"):
        raise BatchBlocked("MANIFEST_CHANGED")
    rows=[r for r in d["episodes"] if r.get("channel")==channel]
    if tuple(r.get("id") for r in rows)!=EXPECTED[channel]:
        raise BatchBlocked("WRONG_EPISODES_ORDER_OR_DUPLICATE")
    for row in rows:
        assert_reserved(channel,row["id"],OWNER)
        if (row.get("channel_id")!=KNOWN_IDS[channel]
                or row.get("language")!=("en-US" if channel=="en" else "pt-BR")
                or row.get("made_for_kids") is not (channel=="kids")
                or row.get("visibility_intent")!="private_first_after_QA"
                or row.get("production_state",{}).get("upload")!="not_started"
                or row.get("production_state",{}).get("youtube_id") is not None):
            raise BatchBlocked("UNAUTHORIZED_CHANNEL_OR_PREVIOUS_UPLOAD")
        if (len(row.get("scenes",[]))!=8
                or [x.get("number") for x in row["scenes"]]!=list(range(1,9))
                or len(row.get("narration_script","").split())<240
                or len(row["narration_script"].split())>360
                or row["narration_script"]!=" ".join(x["editorial_beat"] for x in row["scenes"])):
            raise BatchBlocked("NARRATION_NOT_ALIGNED_WITH_8_BEATS")
        if (not all(len(str(x.get("visual_instruction","")))>30 for x in row["scenes"])
                or not 8<=len(row.get("title",""))<=100
                or not 5<=len(row.get("cover_text",""))<=42
                or not row.get("description") or not row.get("tags")
                or len(",".join(row["tags"]))>500):
            raise BatchBlocked("SCENE_SEO_OR_COVER_INVALID")
        if channel=="kids" and row.get("series")!="standalone_children_story_not_fofinhos":
            raise BatchBlocked("KIDS_STANDALONE_ONLY")
        if channel=="games" and "não são capturas de gameplay" not in row["description"].lower():
            raise BatchBlocked("NO_GAMEPLAY_DISCLOSURE")
        if channel=="alchemy" and not any(s in row["description"].lower() for s in ("conceitual","conceituais")):
            raise BatchBlocked("NO_FABRICATED_APP_DEMONSTRATION")
    return rows

def guard(channel:str)->None:
    e=os.environ
    if (e.get("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo"
            or e.get("GITHUB_EVENT_NAME")!="push"
            or e.get("GITHUB_REF")!="refs/heads/main"
            or e.get("GITHUB_RUN_ATTEMPT")!="1"
            or e.get("GITHUB_WORKFLOW")!=WORKFLOW
            or e.get("BATCH15_CHANNEL")!=channel
            or e.get("BATCH15_RENDER_AUTHORIZED")!="yes"
            or e.get("IMAGE_MODEL")!=IMAGE_MODEL
            or e.get("MAX_IMAGE_CALLS")!=str(IMAGE_BUDGET)):
        raise BatchBlocked("MAIN_ONE_SHOT_IMAGE_BUDGET_OR_OWNER_GUARD")
    if any(e.get(n) for n in ("YOUTUBE_CLIENT_JSON","YOUTUBE_CHANNEL_TOKEN_JSON",
                             "YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON",
                             "YOUTUBE_KIDS_TOKEN_JSON","YOUTUBE_GAMES_TOKEN_JSON",
                             "YOUTUBE_ALCHEMY_TOKEN_JSON")):
        raise BatchBlocked("YOUTUBE_OAUTH_FORBIDDEN_IN_RENDER")

def art_prompt(row:dict,scene:dict,channel:str)->str:
    # Targeted recovery: the provider repeatedly rejected this one volleyball
    # positioning illustration. Keep the original story action, but remove all
    # named-series and extended narration context from its image payload.
    if (channel=="br" and row["id"]=="5103-haikyuu-time"
            and scene["number"]==7):
        return (
            "Create one original premium cinematic illustration, vertical 1024x1536. "
            "An indoor school volleyball gym during team practice, warm wooden floor "
            "with clear volleyball court boundary lines and a net. Six distinct "
            "athletes are positioned across the court, communicating about where "
            "to pass the ball; coordinated body language, supportive teamwork, "
            "a lively but realistic action moment, warm light, dark blue and "
            "sunny orange sports outfits, cohesive professional editorial art. "
            "No brand names, celebrity or copyrighted characters, no writing, "
            "numbers, lettering, symbols or interface; no split composition. "
            "The full team must fit inside the center of the portrait frame."
        )
    if (channel=="br" and row["id"]=="5103-haikyuu-time"
            and scene["number"]==8):
        return (
            "One original high-quality cinematic editorial illustration, "
            "portrait 1024x1536. An indoor volleyball court after a friendly "
            "practice match, warm overhead lighting and polished wood floor. "
            "A group of adult fictional volleyball athletes in coherent "
            "navy and orange sportswear gathers happily by the net, smiling "
            "and celebrating their team cooperation. Expressive but natural "
            "poses, balanced perspective, pleasing color composition, clear "
            "separated faces and hands, realistic anatomy. "
            "No logos, text, numbers, existing fictional characters or brands. "
            "Keep the group within the central frame."
        )
    title=row["title"]
    original_theme=STYLES[channel]
    # All frames are independent illustrations. No claim of animation,
    # screenshots, reproductions or visually approved canonical likeness.
    return (
        "Generate ONE entirely new vertical 1024x1536 carefully composed STILL "
        "illustration for educational YouTube story narration. "
        +original_theme+" "
        "Episode: "+title+". "
        "Scene number: "+str(scene["number"])+". "
        "Illustrate the SPECIFIC story action: "+scene["visual_instruction"]+". "
        "Voice context: "+scene["editorial_beat"]+". "
        "Keep identity, color and geography consistent within this story. "
        "No writing, labels, fake user interface, official screenshots, watermarks, "
        "blurred faces, bad anatomy, visual glitches or split screen. "
        "All key shapes inside safe vertical crop. Original dramatic coherent image."
    )

engine.prompt=art_prompt

def verify_previous_finished_episode(row:dict,folder:Path,channel:str)->dict:
    """Fail closed when recovering the two MP4s from the immutable failed run.

    Their source is the pinned artifact in workflow run 42957295592, and they
    must independently pass on-disk integrity, dimensions and metadata checks.
    """
    from PIL import Image
    media=folder/"final.mp4"
    thumb=folder/"thumb.jpg"
    qa_path=folder/"qa.json"
    meta_path=folder/"metadata.json"
    paths=(media,thumb,qa_path,meta_path)
    if not all(p.is_file() and not p.is_symlink() for p in paths):
        raise BatchBlocked("RECOVERY_PRIOR_VIDEO_FILES_INVALID_"+row["id"])
    qa=json.loads(qa_path.read_text(encoding="utf-8"))
    meta=json.loads(meta_path.read_text(encoding="utf-8"))
    if (qa.get("schema")!="autoeditorvideo/remaining-static-original-90s-qa/v1"
            or qa.get("episode_id")!=row["id"]
            or qa.get("channel")!=channel or qa.get("channel_id")!=KNOWN_IDS[channel]
            or qa.get("image_count")!=8
            or qa.get("automated_technical_qa")!="passed"
            or qa.get("word_boundaries_synced") is not True
            or qa.get("character_warp_mesh_animation") is not False
            or qa.get("youtube_upload")!="not_performed"
            or qa.get("manual_visual_review") is not False
            or qa.get("publication_allowed") is not False):
        raise BatchBlocked("RECOVERY_PRIOR_VIDEO_QA_INVALID_"+row["id"])
    if (meta.get("id")!=row["id"] or meta.get("channel")!=channel
            or meta.get("channel_id")!=KNOWN_IDS[channel]
            or meta.get("title")!=row["title"]
            or meta.get("description")!=row["description"]
            or meta.get("tags")!=row["tags"]
            or meta.get("privacyStatus")!="private"
            or meta.get("selfDeclaredMadeForKids") is not False):
        raise BatchBlocked("RECOVERY_PRIOR_VIDEO_METADATA_INVALID_"+row["id"])
    if (qa.get("mp4_sha256")!=engine.digest(media)
            or qa.get("cover_sha256")!=engine.digest(thumb)
            or meta.get("mp4_sha256")!=qa.get("mp4_sha256")
            or meta.get("cover_sha256")!=qa.get("cover_sha256")):
        raise BatchBlocked("RECOVERY_PRIOR_MP4_OR_COVER_HASH_MISMATCH_"+row["id"])
    image_hashes=qa.get("image_sha256")
    if not isinstance(image_hashes,list) or len(image_hashes)!=8:
        raise BatchBlocked("RECOVERY_PRIOR_IMAGE_DIGESTS_MISSING_"+row["id"])
    for n in range(1,9):
        image=folder/("scene-%02d.png"%n)
        if not image.is_file() or image.is_symlink() or engine.digest(image)!=image_hashes[n-1]:
            raise BatchBlocked("RECOVERY_PRIOR_SCENE_HASH_MISMATCH_"+row["id"])
        with Image.open(image) as im:
            im.verify()
        with Image.open(image) as im:
            if im.format!="PNG" or im.size!=(1024,1536):
                raise BatchBlocked("RECOVERY_PRIOR_SCENE_FORMAT_INVALID_"+row["id"])
    if len(set(image_hashes))!=8:
        raise BatchBlocked("RECOVERY_PRIOR_DUPLICATE_SCENE_"+row["id"])
    with Image.open(thumb) as im:
        if im.format!="JPEG" or im.size!=(1080,1920):
            raise BatchBlocked("RECOVERY_PRIOR_THUMB_INVALID_"+row["id"])
    inspected=engine.probe(media)
    seconds=float(inspected["format"]["duration"])
    streams=inspected["streams"]
    video=[x for x in streams if x.get("codec_type")=="video"]
    audio=[x for x in streams if x.get("codec_type")=="audio"]
    if (not 90<=seconds<=121 or len(video)!=1 or not audio
            or video[0].get("width")!=1080 or video[0].get("height")!=1920
            or media.stat().st_size<300_000):
        raise BatchBlocked("RECOVERY_PRIOR_VIDEO_TECHNICAL_QA_INVALID_"+row["id"])
    print("BATCH15_REUSED_VERIFIED_PRIOR_MP4_"+row["id"],flush=True)
    return {"id":row["id"],"duration":round(seconds,2),
            "mp4_sha256":qa["mp4_sha256"],
            "cover_sha256":qa["cover_sha256"]}


def produce(channel:str)->None:
    guard(channel)
    rows=validate(channel)
    out=output(channel)
    recovering=(channel=="br" and
                os.environ.get("BATCH15_BR_SCENE_CACHE_FROM_42959933980")=="yes")
    if recovering:
        if not out.is_dir() or out.is_symlink():
            raise BatchBlocked("VERIFIED_BR_RECOVERY_CACHE_REQUIRED")
        if any(p.name not in {r["id"] for r in rows} or not p.is_dir() or p.is_symlink()
               for p in out.iterdir()):
            raise BatchBlocked("RECOVERY_CACHE_UNEXPECTED_CONTENTS")
        # These exact counts are from the known failed run. Two finished
        # stories have full image sets and QA; Haikyuu lacks scenes 7 and 8.
        for idx,row in enumerate(rows):
            folder=out/row["id"]
            expected_count=(8,8,7)[idx]
            if not folder.is_dir() or len(list(folder.glob("scene-*.png")))!=expected_count:
                raise BatchBlocked("RECOVERY_CACHE_SCENE_COUNT_MISMATCH_"+row["id"])
            if (folder/"qa.json").is_file() is not (idx<2):
                raise BatchBlocked("RECOVERY_CACHE_QA_PROVENANCE_MISSING_"+row["id"])
            if (folder/"youtube-private-receipts.json").exists():
                raise BatchBlocked("RECOVERY_CACHE_MAY_CONTAIN_PREVIOUS_UPLOAD")
            # Exactly two previously completed videos may be reused only with
            # their own QA, metadata, thumbnails and validated original images.
            finished=(folder/"final.mp4").is_file()
            if finished is not (idx<2):
                raise BatchBlocked("RECOVERY_CACHE_COMPLETED_VIDEO_SET_MISMATCH")
            if finished and not (folder/"metadata.json").is_file():
                raise BatchBlocked("RECOVERY_CACHE_METADATA_MISSING_"+row["id"])
            if finished and not (folder/"thumb.jpg").is_file():
                raise BatchBlocked("RECOVERY_CACHE_THUMB_MISSING_"+row["id"])
    else:
        if out.exists():
            raise BatchBlocked("EXISTING_OUTPUT_REFUSE_DUPLICATE_GENERATION")
        out.mkdir(parents=True,exist_ok=False)
    ready=[]
    for row in rows:
        folder=out/row["id"]
        folder.mkdir(parents=True,exist_ok=recovering)
        if recovering and (folder/"final.mp4").is_file():
            ready.append((row,folder,None,None,None))
        else:
            voice,sec,words=engine.voice_takes(row,folder,channel)
            ready.append((row,folder,voice,sec,words))
    from gerar_video_codex import proxy_key,check_proxy_accounts
    key=proxy_key()
    check_proxy_accounts(key)
    summary={"schema":"autoeditorvideo/remaining-three-static-original-90s-batch/v1",
             "owner":OWNER,"channel":channel,"target_channel_id":KNOWN_IDS[channel],
             "artifact_state":"rendered_upload_not_performed",
             "render_engine":"AutoEditorVideo/ArquivoOtakuMaster",
             "video_count":3,"videos":[]}
    for row,folder,voice,sec,words in ready:
        if recovering and voice is None:
            summary["videos"].append(verify_previous_finished_episode(row,folder,channel))
            continue
        try:
            arts=engine.images(row,folder,key,channel,reuse_verified_cache=recovering)
        except Exception as exc:
            # Public Actions logs must not expose proxy responses or credentials.
            # Identify the failing episode and stage without consuming extra image calls.
            completed=len(list(folder.glob("scene-*.png")))
            stage=("SCENE_%02d"%(completed+1)) if completed<8 else "POST_IMAGE_QA"
            http=re.search(r"\bHTTP\s+([1-5][0-9]{2})\b",str(exc))
            reason=("HTTP_"+http.group(1)) if http else type(exc).__name__
            print("BATCH15_IMAGE_FAILED_%s_%s_%s_%s" %
                  (channel,row["id"],stage,reason),file=sys.stderr,flush=True)
            raise
        video=engine.render_one(row,folder,voice,sec,words,arts,channel)
        qa_file=folder/"qa.json"
        meta_file=folder/"metadata.json"
        qa=json.loads(qa_file.read_text(encoding="utf-8"))
        qa.update({"batch":"lote15_20261108","manual_visual_review":False,
                   "visual_review_status":"pending","publication_allowed":False,
                   "original_artwork_only":True,"no_actual_gameplay":channel=="games"})
        qa_file.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        meta=json.loads(meta_file.read_text(encoding="utf-8"))
        meta["selfDeclaredMadeForKids"]=(channel=="kids")
        meta_file.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        summary["videos"].append(video)
        for tts_dir in folder.glob("tts-*"):
            if tts_dir.is_dir():shutil.rmtree(tts_dir)
        (folder/"props.json").unlink(missing_ok=True)
    if len(summary["videos"])!=3:
        raise BatchBlocked("PARTIAL_RENDER_DO_NOT_UPLOAD")
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("BATCH15_RENDERED_THREE_PRIVATE_READY_"+channel,flush=True)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--channel",choices=CHANNELS,required=True)
    ap.add_argument("--action",choices=("validate","render"),default="validate")
    args=ap.parse_args()
    try:
        if args.action=="validate":
            rows=validate(args.channel)
            print("BATCH15_VALIDATED_"+args.channel+"_"+",".join(x["id"] for x in rows))
        else:
            produce(args.channel)
        return 0
    except Exception as exc:
        msg=str(exc) if isinstance(exc,BatchBlocked) else type(exc).__name__
        print("BATCH15_RENDER_BLOCKED_"+msg,file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
