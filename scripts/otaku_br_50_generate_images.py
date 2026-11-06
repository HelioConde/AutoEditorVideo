#!/usr/bin/env python3
"""Generate exactly FIVE original illustrated frames for ONE reserved Otaku BR Short.

This job never has YouTube OAuth, never uploads, and never marks human visual
review completed. Fail closed if the image provider or validation fails.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageOps, ImageStat

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from otaku_br_50_reverso import OUTPUT, validate
from gerar_video_codex import proxy_key, check_proxy_accounts, request_image

MODEL="gpt-image-2"
SIZE=(1024,1536)
CHANNEL_ID="UCXGYTuBYn-0Ziqin5ajKhOw"

class ImageBlocked(ValueError):
    pass

def sha(file:Path)->str:
    return hashlib.sha256(file.read_bytes()).hexdigest()

def stage_check(number:int)->dict:
    if os.getenv("GITHUB_REPOSITORY")!="HelioConde/AutoEditorVideo":
        raise ImageBlocked("WRONG_REPOSITORY")
    if os.getenv("GITHUB_REF")!="refs/heads/main" or os.getenv("GITHUB_RUN_ATTEMPT")!="1":
        raise ImageBlocked("MAIN_AND_FIRST_ATTEMPT_ONLY")
    if os.getenv("GITHUB_EVENT_NAME") not in ("push","workflow_dispatch"):
        raise ImageBlocked("UNAUTHORIZED_EVENT")
    if os.getenv("IMAGE_MODEL")!=MODEL or os.getenv("MAX_IMAGE_CALLS")!="5":
        raise ImageBlocked("WRONG_MODEL_OR_IMAGE_BUDGET")
    if number not in range(1,51):
        raise ImageBlocked("INVALID_EPISODE_NUMBER")
    item=validate()[number-1]
    if item.get("channel_id")!=CHANNEL_ID or item["position"]!=number:
        raise ImageBlocked("CHANNEL_OR_QUEUE_MISMATCH")
    return item

# This one story's original action includes an extreme self-sacrifice near
# tremendous heat. The image provider rejected a prompt with HTTP 400.
# Use non-graphic, editorial storytelling instead of depicting injuries or
# burning people. The separately approved narration remains untouched.
# This is a single prompt revision, NOT an automated retry/guardrail bypass.
ARMIN_SAFE_SHOTS=(
    "An original 2D editorial anime illustration: a blonde young fantasy scout, "
    "Armin, quietly studying a tactical sketch beside a window. A colossal distant "
    "silhouette appears across the misty city skyline. Emphasize thoughtful determination.",
    "Armin and his dark-haired ally Eren point at a hand-drawn tactical map in "
    "a stone tower while luminous mist drifts outside. Emphasize the clever distraction plan.",
    "A tiny distant scout silhouette creates a distraction with a bright beam of "
    "reflected daylight on a city rooftop, drawing the attention of a very large "
    "shadow in the distance. Keep all figures safe, unharmed, and fully clothed.",
    "Eren notices an opening beyond the drifting vapor while the scout's "
    "carefully chosen route on the city map aligns with the view outside. "
    "Focus on strategic consequences and a tense, cinematic expression.",
    "Close with Armin's marked-up tactical map held gently by Eren and a "
    "hopeful sunlight-lit skyline. Symbolize courage and personal cost through "
    "a quiet, thoughtful face, without injuries or distressing scenes.",
)

def safe_scene_override(row:dict,index:int)->str|None:
    # Do not edit unrelated videos or the spoken narration.
    if row.get("position")!=37 or row.get("id")!="6137-multicena-experimento-novembro":
        return None
    if index not in range(1,6):
        raise ImageBlocked("INVALID_SCENE_INDEX")
    return (
        "Create ONE ORIGINAL non-graphic, hand-painted 2D fantasy anime editorial "
        "illustration, portrait 2:3 1024x1536. It is analysis artwork, not "
        "a screenshot or a recreation of existing animation frames. "
        "This is a family-friendly, peaceful visual retelling focused on "
        "planning, meaningful gestures, maps and hopeful character reactions. "
        "Use atmospheric mist and warm backlighting. "
        "Maintain stable characters and scenery across the five different images. "
        "Keep the bottom 22 percent uncluttered for narration captions. "
        "No lettering, captions, logos, brands, watermarks or panels. "
        "Keep all objects and characters completely within the image. "
        f"Distinct image {index} of 5: {ARMIN_SAFE_SHOTS[index-1]}"
    )


# The Erwin episode concerns a high-risk command decision. Keep the same
# approved factual narration while telling its visual story through maps,
# cavalry staging and thoughtful faces, not harm or combat outcomes.
# Episode-specific safe ART direction; never retry a refused graphic prompt.
ERWIN_SAFE_SHOTS=(
    "Erwin, an adult blond commander wearing a green exploration cape, quietly "
    "studies an original hand-painted tactical map in a sunlit command tent. "
    "A peaceful field and distant horses are visible beyond the canvas doorway.",
    "Erwin uses a pencil to trace two routes across a parchment terrain map. "
    "Beside him a small brass horse figurine marks an approaching formation, "
    "with a second route highlighted for his dark-haired ally Levi.",
    "Several fully clothed adult scouts stand beside calm horses at the edge of "
    "a wide green plain. The commander gestures towards the distant horizon; "
    "focus on solemn preparation, not an attack or anyone in danger.",
    "A close-up of the commander's thoughtful expression and a gloved hand "
    "resting on the folded parchment plan. Two figures exchange a nod of "
    "understanding. Strong cinematic lighting suggests the gravity of a decision.",
    "Levi studies the same map with a steady expression while an unoccupied "
    "sunlit grassy field stretches towards the horizon. Close on the route "
    "marker and a folded green cape, symbolizing responsibility and courage.",
)

def erwin_safe_scene_override(row:dict,index:int)->str|None:
    if row.get("position")!=34 or row.get("id")!="6134-multicena-experimento-novembro":
        return None
    if index not in range(1,6):
        raise ImageBlocked("INVALID_SCENE_INDEX")
    return (
        "Draw one ORIGINAL 2D hand-painted editorial fantasy anime illustration, "
        "portrait 2:3 at 1024x1536. The video examines a commander's strategy "
        "and ethical dilemma through peaceful planning scenes. All adults are "
        "fully clothed, safe and unharmed. Use only maps, horses at rest, quiet "
        "teamwork, respectful expressions, sunlight and atmospheric landscapes. "
        "Do not depict an attack, injuries, blood, distressing scenes, or weapons "
        "in use. Do not reproduce a copyrighted animation frame. Maintain "
        "the same character designs and props in all five distinct images. "
        "Preserve the bottom 22 percent for external timed captions. "
        "No words, titles, logos, graphic symbols or watermarks. "
        "Show each complete subject and main prop inside the frame. "
        f"Unique scene {index} of 5: {ERWIN_SAFE_SHOTS[index-1]}"
    )


# Episode 32: provider refused a generic storyboard image (HTTP 400) at
# scene four. Use distinct, peaceful, originally designed illustrations
# without copying copyrighted character designs. Not a blind retry.
STORYTELLER_SAFE_SHOTS=(
    "A cheerful young coastal villager wearing a simple linen vest tells a "
    "playful tall tale to friends near brightly colored wooden fishing boats.",
    "The same imaginative storyteller draws a fanciful sea creature in sand "
    "while three amused friends listen near the village marketplace.",
    "Under a cloudy sky, the young storyteller gently comforts a worried "
    "friend beside a seaside path, with the village visible in the distance.",
    "At the village harbor, the storyteller stands confidently alongside "
    "friends, holding a small handmade wooden slingshot at rest; nobody "
    "is threatened, and the emphasis is on friendship and quiet courage.",
    "The friends share a warm laugh at sunset by the calm harbor as the "
    "storyteller gestures toward paper drawings of imaginary adventures.",
)

def storyteller_safe_scene_override(row:dict,index:int)->str|None:
    if row.get("position")!=32 or row.get("id")!="6132-multicena-experimento-novembro":
        return None
    if index not in range(1,6):
        raise ImageBlocked("INVALID_SCENE_INDEX")
    return (
        "Create one ORIGINAL 2D editorial fantasy illustration, vertical "
        "portrait 2:3 at 1024x1536. Five distinct scenes depict the same "
        "fictional seaside storyteller, with consistent clothing, friends "
        "and cheerful maritime village; use an original character design, "
        "not a screenshot or recognizable reproduction of any anime figure. "
        "Wholesome, nonviolent, family-friendly visual storytelling: "
        "friendship, imagination, quiet bravery and humorous expressions. "
        "Everyone is safe and fully clothed, with no combat, threats, "
        "injuries or graphic content. No franchise names, logos, letters, "
        "captions, watermarks or panels. Keep the bottom 22 percent clear "
        "for external timed subtitles and all subjects inside the frame. "
        f"Illustration {index} of five: {STORYTELLER_SAFE_SHOTS[index-1]}"
    )

# Short 31: the provider refused the fourth general storyboard prompt (HTTP 400).
# Visualize the nautical weather expertise without peril or combat. This
# single, explicit editorial revision preserves the original narration.
NAVIGATOR_SAFE_SHOTS=(
    "A skilled adult red-haired fantasy navigator in a practical blue jacket "
    "studies wind direction and a brass compass on a peaceful wooden sailboat deck. "
    "Distant clouds drift across the horizon, no storm damage.",
    "The same navigator marks a route on a hand-drawn sea chart beside a simple "
    "barometer, while two fully clothed adult crewmates listen attentively.",
    "A calm panoramic seascape shows sunlight through layered clouds and a "
    "turning weather vane on the ship. The navigator observes weather signs "
    "and points toward a clear path.",
    "The navigator helps a crewmate adjust the ship's route on a tabletop map "
    "to avoid distant gray rain clouds, using a brass compass and a pencil. "
    "Everyone remains safe; emphasize clever preparation and teamwork.",
    "Golden afternoon light illuminates a safe harbor as the navigator and crew "
    "smile while checking the completed sailing route, reflecting the value "
    "of navigation knowledge.",
)

def navigator_safe_scene_override(row:dict,index:int)->str|None:
    if row.get("position")!=31 or row.get("id")!="6131-multicena-experimento-novembro":
        return None
    if index not in range(1,6):
        raise ImageBlocked("INVALID_SCENE_INDEX")
    return (
        "Produce ONE ORIGINAL hand-painted 2D editorial fantasy anime illustration, "
        "vertical 2:3 portrait, 1024x1536. Five distinct peaceful scenes tell "
        "the story of a skilled sea navigator using knowledge of weather, "
        "wind and charts. Characters are adult, fully clothed, safe and unharmed. "
        "No violence, battle, disasters, injuries, blood or danger. Use original "
        "character artwork, not frames from any existing animation. "
        "Keep consistent costumes, map and ship across the five scenes. "
        "Cinematic atmosphere, clear props and expressive calm gestures. "
        "Keep the lower 22 percent clear for timed external subtitles; no "
        "written text, logos, watermarks, borders or panels. "
        "Every subject must fit completely inside the image. "
        f"Specific illustration {index} of 5: {NAVIGATOR_SAFE_SHOTS[index-1]}"
    )

def prompt_for(row:dict,index:int)->str:
    # Editorial stills are explicitly specified for the two sensitive
    # strategy-focused storylines. Never regenerate on a provider refusal.
    override=navigator_safe_scene_override(row,index)
    if override is not None:
        return override
    override=storyteller_safe_scene_override(row,index)
    if override is not None:
        return override
    override=erwin_safe_scene_override(row,index)
    if override is None:
        override=safe_scene_override(row,index)
    if override is not None:
        return override
    scene=row["storyboard"][index-1]
    common=(
        "Create ONE ORIGINAL hand-painted 2D anime editorial illustration, "
        "vertical 2:3 1024x1536, to be composited in an original Brazilian "
        "YouTube anime ANALYSIS video. High-quality hand-drawn cel animation "
        "aesthetic, cohesive character designs, crisp anatomy, natural hands, "
        "bold cinematic lighting, expressive faces, vivid background depth, "
        "clear action frozen at an impactful moment. Not a still from the anime; "
        "NOT a screenshot, no existing animation frames, no title, captions, "
        "logos, watermarks, UI, lettering, borders, panels or collage. "
        "All characters and important objects fully in frame, keep the "
        "bottom 22 percent relatively uncluttered for real Remotion captions. "
        "Match costumes, props, scene geography and lighting consistently "
        "throughout the five scenes of THIS same short. "
    )
    return (common+
        f"Franchise and story context: {row['series']}. "
        f"Story to faithfully visualize: {row['narration_script']} "
        f"Unique shot {index}/5; direction: {scene['action']} "
        f"Emphasize this image's DIFFERENT action and camera perspective: {scene['camera']}. "
        f"Episode visual object cues: {row['cover_text']}. "
        "Do not invent new characters or scenes unrelated to the narrated story. "
        "Avoid excessive text, gore or graphic violence.")

def generate(number:int)->dict:
    row=stage_check(number)
    folder=OUTPUT/row["id"]
    folder.mkdir(parents=True,exist_ok=True)
    art=[folder/f"scene-{i:02d}.png" for i in range(1,6)]
    if (folder/"original-art-provenance.json").exists() or any(p.exists() for p in art):
        raise ImageBlocked("EXISTING_ART_REQUIRES_RECONCILIATION_NO_REGENERATION")
    key=proxy_key()
    check_proxy_accounts(key)
    hashes=[]
    try:
        for i,dest in enumerate(art,1):
            # Safe per-scene progress markers expose no prompts, accounts,
            # credentials, or provider response bodies in public CI logs.
            print(f"[OTAKU BR IMAGE] REQUESTED_SCENE={i:02d}/05",flush=True)
            raw=request_image(prompt_for(row,i),MODEL,key,"1024x1536")
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                if image.width<512 or image.height<768:
                    raise ImageBlocked("IMAGE_TOO_SMALL")
                canvas=ImageOps.pad(image.convert("RGB"),SIZE,
                                    method=Image.Resampling.LANCZOS,color=(10,12,24))
                if max(ImageStat.Stat(canvas.resize((64,96))).stddev)<15:
                    raise ImageBlocked("IMAGE_VISUALLY_BLANK")
                canvas.save(dest,"PNG",optimize=True)
            hashes.append(sha(dest))
            print(f"[OTAKU BR IMAGE] VERIFIED_SCENE={i:02d}/05",flush=True)
        if len(set(hashes))!=5:
            raise ImageBlocked("DUPLICATE_OR_REPEATED_IMAGES")
        report={
          "episode_id":row["id"],"channel_id":CHANNEL_ID,
          "model":MODEL,"art_original":True,
          "visual_qa":"automated_technical_checks_only",
          "rights_qa":"AI_generated_no_imported_media",
          "human_visual_review":False,
          "scene_count":5,"scene_sha256":hashes,
          "production_order":number,"publication":"not_performed",
          "limitations":"Automated checks do not establish narrative/anatomy/rights quality."
        }
        (folder/"original-art-provenance.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        return {"number":number,"scenes":5,"status":"generated_unreviewed",
                "upload_attempts":0}
    except Exception:
        # Do not mistake partial images for a complete episode on a retry.
        for p in art: p.unlink(missing_ok=True)
        raise

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--number",type=int,required=True)
    args=ap.parse_args()
    print(json.dumps(generate(args.number),ensure_ascii=False))
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ImageBlocked,ValueError,OSError,RuntimeError) as exc:
        raise SystemExit("[OTAKU BR IMAGE BLOCKED] "+str(exc)) from None
