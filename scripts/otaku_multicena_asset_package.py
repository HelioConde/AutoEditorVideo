#!/usr/bin/env python3
"""Assemble production-ready FILE CHECKLISTS, not images or video.

Converts the ten-shot storyboard plan into an intentionally incomplete
quality-v3 manifest. It cannot pass the V3 validator until original art,
transparent poses, real TTS markers, hashes and documented licenses exist.
This module never contacts providers and never unlocks publication.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from otaku_multicena_ten_shot_plan import build_report

REQUIRED_ANIMATED_SHOTS={1:"pingpong",4:"once",6:"pingpong",9:"once"}
DEFAULT_POSE_FPS=5

class PackageBlocked(ValueError):
    pass

def template_for_plan(plan:dict)->dict:
    if (not isinstance(plan,dict) or
        plan.get("schema")!="autoeditorvideo/ten-shot-editorial-draft/v1" or
        len(plan.get("shots",[]))!=10):
        raise PackageBlocked("INVALID_EDITORIAL_STORY_PLAN")
    draft=[]
    needs=[]
    for raw in plan["shots"]:
        i=raw["shot_index"]
        bg=f"shot-{i:02d}-clean.png"
        shot={
            "start_phrase":raw["start_phrase_candidate"],
            "background":bg,
            "beat_role":raw["beat_role"],
            "shot_type":raw["shot_type"],
            "rights":{"type":None,"evidence":""},
            "reference_image_sha256":None,
            "draft_action":raw["source_action"],
            "draft_framing":raw["composition_direction"],
            "asset_status":"NOT_CREATED_OR_VERIFIED",
            "editorial_fact_check":False,
            "character_consistency_review":False,
        }
        needs.append({"filename":bg,"purpose":f"original clean plate shot {i}",
                      "source_storyboard_index":raw["source_storyboard_index"],
                      "license_required":True})
        if i in REQUIRED_ANIMATED_SHOTS:
            files=[f"shot-{i:02d}-pose-{j:02d}.png" for j in (1,2)]
            shot.update({"pose_frames":files,"pose_fps":DEFAULT_POSE_FPS,
                         "pose_playback":REQUIRED_ANIMATED_SHOTS[i],
                         "clean_plate_confirmed":False})
            for j,name in enumerate(files,1):
                needs.append({"filename":name,
                              "purpose":f"real transparent articulated pose {j} in shot {i}",
                              "license_required":True})
        draft.append(shot)
    needs.append({"filename":"voz-master.mp3",
                  "purpose":"genuine approved narration, not synthesized by this script",
                  "license_required":True})
    needs.append({"filename":"marcacoes-voz.json",
                  "purpose":"word-aligned TTS markers created by narrator",
                  "license_required":False})
    script=plan["narration_script"]
    return {
        "schema":"autoeditorvideo/quality-preview/v3",
        "template_status":"INCOMPLETE_ASSETS_AND_LICENSES_NO_GENERATION",
        "episode_id":plan["episode_id"],
        "episode_number":plan["episode_number"],
        "narration_script":script,
        "narration_sha256":sha256(script.encode("utf-8")).hexdigest(),
        "duration_frames":None,
        "voice":"voz-master.mp3",
        "voice_rights":{"type":None,"evidence":""},
        "manual_visual_review":False,
        "hook_text":plan["hook_phrase_candidate"],
        "payoff_text":plan["payoff_phrase_candidate"],
        "sha256":{},
        "shots":draft,
        "required_file_checklist":needs,
        "animation_target_shots":sorted(REQUIRED_ANIMATED_SHOTS),
        "animation_asset_count":8,
        "background_asset_count":10,
        "editorial_approval":False,
        "rights_review_completed":False,
        "publish_authorized":False,
        "instructions":[
            "Use real character reference approved by creator for every pose and scene.",
            "Scene backgrounds are CLEAN plates in animation shots, not duplicate painted characters.",
            "Prepare 1024x1536 PNGs; RGBA transparent articulated poses for shots 1,4,6,9.",
            "Verify anatomy and original visual style; a hash alone never proves character identity.",
            "Replace each empty right/evidence and reference only with genuine documented provenance.",
            "Create narration and word timings AFTER creator lifts generation pause, not in this workflow.",
            "Populate real SHA256 hashes and actual duration_frames from measured audio.",
            "Verify all frames before removing template_status, editorial_approval remains separate.",
            "No generated media or YouTube publication is authorized by this template."
        ]
    }

def package_plan(numbers:list[int])->dict:
    report=build_report(numbers)
    packages=[template_for_plan(p) for p in report["plans"]]
    return {
        "schema":"autoeditorvideo/otaku-quality-asset-package/v1",
        "status":"TEXT_ONLY_ASSET_LIST_NO_IMAGE_TTS_MP4_OR_UPLOAD",
        "episode_numbers":numbers,
        "packages":packages,
        "planned_background_files":10*len(packages),
        "planned_pose_files":8*len(packages),
        "files_generated":False,
        "video_generated":False,
        "youtube_uploads":0,
        "publication_paused":True,
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--numbers",type=int,nargs="+",default=[5,4,3,2,1])
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    report=package_plan(a.numbers)
    payload=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(payload,encoding="utf-8")
    else:
        print(payload,end="")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (PackageBlocked,ValueError,KeyError,OSError) as exc:
        raise SystemExit("[ASSET PACKAGE BLOCKED] "+str(exc)) from None
