#!/usr/bin/env python3
"""Expand five canonical storyboard beats into a TEN-SHOT editorial PRE-PRODUCTION plan.

Read-only work: no images, voices, MP4, image providers, tokens or YouTube.
This creates descriptions to review, not V3-ready artwork or fictitious approval.
The original narration and the creator pause are never changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from otaku_br_50_reverso import validate
from otaku_multicena_quality_v3 import words

ROOT=Path(__file__).resolve().parents[1]

# Every shot has a distinct framing and function rather than ten identical
# pans over the same five originals. Source beats remain editorial reference.
CHOREOGRAPHY=(
    ("hook", "reaction",0,"Start with a readable expression and a clear object connected to the hook."),
    ("setup","wide",1,"Establish the physical environment and spatial relationships."),
    ("setup","detail",1,"Show the important object or clue in its actual context."),
    ("detail","medium",2,"Show the character taking the described action."),
    ("detail","close",2,"Make the consequence or an object interaction legible."),
    ("rehook","reaction",2,"Use a distinct reaction angle to renew curiosity."),
    ("twist","wide",3,"Reveal how the environment makes the contradiction possible."),
    ("answer","detail",3,"Show the evidence for the explanation, not an unrelated image."),
    ("answer","reaction",3,"Show a meaningful reaction to the story's actual payoff."),
    ("cta","final",4,"End on the resolved visual evidence without a new unsupported event."),
)

class StoryboardBlocked(ValueError):
    pass

def balanced_positions(number_of_words:int, number_of_shots:int)->list[int]:
    if number_of_shots != 10 or number_of_words < 45:
        raise StoryboardBlocked("TEN_SHOTS_REQUIRE_45_OR_MORE_SPOKEN_WORDS")
    cuts=[round(number_of_words*i/number_of_shots) for i in range(number_of_shots+1)]
    if cuts[0]!=0 or cuts[-1]!=number_of_words or any(
            b-a<4 for a,b in zip(cuts,cuts[1:])):
        raise StoryboardBlocked("INSUFFICIENT_UNIQUE_SPOKEN_MATERIAL")
    return cuts

def unique_phrase(tokens:list[str],start:int)->str:
    if not 0<=start<len(tokens):
        raise StoryboardBlocked("SHOT_ANCHOR_OUTSIDE_SCRIPT")
    for size in range(3,min(9,len(tokens)-start)+1):
        cue=tokens[start:start+size]
        occurrences=sum(tokens[i:i+size]==cue for i in range(len(tokens)-size+1))
        if occurrences==1:
            return " ".join(cue)
    raise StoryboardBlocked("SHOT_CUE_NOT_UNIQUE_IN_NARRATION")

def plan_one(row:dict)->dict:
    board=row.get("storyboard")
    script=row.get("narration_script")
    if not isinstance(board,list) or len(board)!=5 or not isinstance(script,str):
        raise StoryboardBlocked("REQUIRES_FIVE_CANONICAL_STORY_BEATS")
    tokens=words(script)
    cuts=balanced_positions(len(tokens),len(CHOREOGRAPHY))
    shots=[]
    for i,(beat,shot_type,source_index,direction) in enumerate(CHOREOGRAPHY):
        original=board[source_index]
        action=original.get("action", "")
        if not isinstance(action,str) or len(action.strip())<45:
            raise StoryboardBlocked("CANONICAL_ACTION_MISSING")
        start,end=cuts[i:i+2]
        spoken_excerpt=" ".join(tokens[start:end])
        cue=unique_phrase(tokens,start)
        shots.append({
            "shot_index":i+1,
            "beat_role":beat,
            "shot_type":shot_type,
            "start_phrase_candidate":cue,
            "estimated_word_start":start,
            "estimated_word_end":end,
            "spoken_excerpt_reference":spoken_excerpt,
            "source_storyboard_index":source_index+1,
            "source_action":action,
            "composition_direction":direction,
            "draft_original_image_prompt":(
                "Create a NEW original vertical editorial anime-style illustration, "
                "not a screenshot or reproduction of an existing episode frame. "
                f"Anime: {row['series']}. Story moment: {spoken_excerpt}. "
                f"Visual facts to preserve: {action} "
                f"Distinct visual framing: {shot_type}. {direction} "
                "Use established character appearance and consistent setting; "
                "do not invent a new event or show injuries. "
                "Leave safe space for subtitles in the lower third."
            ),
            "needs_fact_check":True,
            "artwork_exists":False,
            "pose_frames_exist":False,
        })
    # These are candidate anchors, NOT verification of semantic story payoff.
    return {
        "schema":"autoeditorvideo/ten-shot-editorial-draft/v1",
        "status":"PREPRODUCTION_ONLY_REQUIRES_EDITORIAL_AND_RIGHTS_REVIEW",
        "episode_id":row["id"],
        "episode_number":row["position"],
        "title":row["title"],
        "series":row["series"],
        "narration_script":script,
        "narration_word_count":len(tokens),
        "planned_shot_count":len(shots),
        "hook_phrase_candidate":shots[0]["start_phrase_candidate"],
        "payoff_phrase_candidate":shots[7]["start_phrase_candidate"],
        "shots":shots,
        "guidance":(
            "Shot times are approximate word indices, not timings; use real "
            "TTS markers once available. Edit all visual prompts for canon, "
            "character consistency, title truthfulness and originality."
        ),
        "rights_checked":False,
        "media_generated":False,
        "rendered":False,
        "youtube_uploaded":False,
        "youtube_authorized":False,
    }

def build_report(numbers:list[int])->dict:
    if not isinstance(numbers,list) or not numbers or len(numbers)!=len(set(numbers)):
        raise StoryboardBlocked("UNIQUE_EPISODE_NUMBERS_REQUIRED")
    if any(not isinstance(n,int) or not 1<=n<=50 for n in numbers):
        raise StoryboardBlocked("EPISODE_OUTSIDE_1_TO_50")
    rows=validate()
    planned=[plan_one(rows[n-1]) for n in numbers]
    return {
        "schema":"autoeditorvideo/editorial-shot-plan-batch/v1",
        "status":"OFFLINE_EDITORIAL_DRAFTS_NOT_PRODUCTION",
        "planned_episode_numbers":numbers,
        "plans":planned,
        "files_created":False,
        "videos_generated":False,
        "youtube_uploads":0,
        "creator_pause_preserved":True,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--numbers",type=int,nargs="+",default=[5,4,3,2,1])
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    report=build_report(a.numbers)
    output=json.dumps(report,ensure_ascii=False,indent=2)+"\n"
    if a.output:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(output,encoding="utf-8")
    else:
        print(output,end="")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (StoryboardBlocked,ValueError,KeyError,OSError) as exc:
        raise SystemExit("[OFFLINE PLAN BLOCKED] "+str(exc)) from None
