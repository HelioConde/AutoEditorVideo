#!/usr/bin/env python3
"""Plan a factual-review-first 90-second Shorts duration experiment, OFFLINE.

The 50 anime stories are targeted at 1:30, but ONLY FIVE already have full
draft scripts. Real duration can be confirmed ONLY after real TTS narration.
Does not generate voices, images, videos or YouTube uploads.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/"conteudos/otaku-multicena-teste-90s-v1.json"
CURATION=ROOT/"conteudos/otaku-multicena-animes-50-curadoria-v4.json"
PAUSE=ROOT/"conteudos/otaku-br-50-serial-launch-20261106.json"
TARGET=90
TOLERANCE=3
ROLES=("hook","contexto","tensao","virada","resposta","fechamento")
MIN_WORDS=190
MAX_WORDS=225

class DurationBlocked(ValueError):
    pass

def load(path:Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def word_count(script:str)->int:
    return len(script.strip().split()) if script.strip() else 0

def verify_record(plan:dict,story:dict)->dict:
    if (plan.get("schema")!="otaku-multicena/shorts-90s-editorial-test/v1"
        or story.get("rank") not in range(1,51)
        or story.get("target_duration_seconds")!=90
        or story.get("duration_profile")!="short_90s_test"
        or story.get("duration_tolerance_seconds")!=3
        or story.get("ready_to_render") is not False
        or story.get("factual_review") is not False
        or story.get("narration_generated") is not False
        or story.get("rendered") is not False
        or story.get("no_auto_upload") is not True):
        raise DurationBlocked("INVALID_UNAPPROVED_90S_STORY_PROFILE")
    result={
        "rank":story["rank"],"anime":story["anime"],
        "title":story["title"],"target_seconds":90,
        "duration_profile":"short_90s_test",
        "actual_audio_seconds":None,"audio_measured":False,
        "story_status":story.get("script_status"),
        "reviewed":False,"safe_to_render":False,
    }
    segments=story.get("story_segments",[])
    if segments:
        if [s.get("role") for s in segments]!=list(ROLES):
            raise DurationBlocked("SIX_DISTINCT_STORY_BEATS_REQUIRED")
        for segment in segments:
            if not isinstance(segment.get("text"),str) or not segment["text"].strip():
                raise DurationBlocked("EMPTY_NARRATIVE_SEGMENT")
            if segment.get("word_count") != word_count(segment["text"]):
                raise DurationBlocked("SEGMENT_WORD_COUNT_MISMATCH")
        script=" ".join(s["text"] for s in segments)
        words=word_count(script)
        if story.get("narration_script")!=script or story.get("word_count")!=words:
            raise DurationBlocked("NARRATION_CONTENT_INTEGRITY_ERROR")
        if not MIN_WORDS<=words<=MAX_WORDS:
            raise DurationBlocked("SCRIPT_NOT_TARGETED_FOR_NINETY_SECONDS")
        # Just an estimate, not a fake promise of TTS or MP4 duration.
        result.update({
            "word_count":words,
            "speech_estimate_at_150wpm_seconds":round(words*60/150,1),
            "needs_actual_tts_duration":True,
            "story_status":"PILOT_TEXT_DRAFT_NEEDS_FACT_CHECK_AND_REAL_VOICE",
        })
    else:
        if story.get("narration_script") is not None or story.get("word_count")!=0:
            raise DurationBlocked("OUTLINE_CANNOT_PRETEND_TO_BE_FINISHED_SCRIPT")
        result.update({"word_count":0,"needs_full_script":True})
    return result

def verify_catalog()->dict:
    plan=load(PLAN)
    cur=load(CURATION)
    control=load(PAUSE)
    if not (control.get("pause_requested") is True
            and control.get("authorized_public") is False
            and control.get("maintenance_complete") is False
            and control.get("resume_authorized_after_maintenance") is False):
        raise DurationBlocked("CREATOR_PAUSE_MUST_REMAIN_ACTIVE")
    rows=plan.get("items")
    if not isinstance(rows,list) or len(rows)!=50 or len(cur.get("items",[]))!=50:
        raise DurationBlocked("FIFTY_ANIME_REQUIRED")
    if plan.get("target_seconds")!=TARGET or plan.get("actual_duration_must_be_measured_from_tts") is not True:
        raise DurationBlocked("NINETY_SECOND_CONTRACT_MISSING")
    for a,b in zip(rows,cur["items"]):
        if (a.get("rank"),a.get("anime"),a.get("title")) != (
            b["rank"],b["anime"],b["new_short_title_proposal"]):
            raise DurationBlocked("NEW_90S_STORY_MISMATCHES_PROTECTED_CURATION")
    results=[verify_record(plan,row) for row in rows]
    ready_drafts=[x for x in results if x["word_count"]>0]
    if len(ready_drafts)!=5:
        raise DurationBlocked("FIVE_CONTROLLED_PILOTS_EXPECTED")
    return {
        "schema":"otaku-multicena/90s-experiment-readonly-report/v1",
        "total_anime":50,
        "target_duration_seconds":90,
        "allowed_audio_duration_seconds":[87,93],
        "fully_drafted_pilots_needing_review":len(ready_drafts),
        "outlines_without_complete_scripts":len(results)-len(ready_drafts),
        "no_actual_audio_measured":True,
        "no_videos_generated":True,"no_upload":True,"creator_pause_enforced":True,
        "editorial_test_comparison":{
            "control_duration_seconds":[35,45],
            "experiment_duration_seconds":[87,93],
            "matched_metrics":["views_48h","feed_exposures_48h",
                               "viewed_vs_swiped_away","average_watch_seconds",
                               "percentage_viewed","subscribers_per_1000_views"],
            "warning":"5-video pilot cannot establish causality; use matched topics and upload windows."
        },
        "stories":results,
    }

def validate_measured_seconds(seconds:float)->float:
    if not 87<=seconds<=93:
        raise DurationBlocked("TTS_AUDIO_OUTSIDE_ALLOWED_87_TO_93_SECONDS")
    return round(seconds,3)

def measure_audio_seconds(path:Path)->float:
    if not path.is_file() or path.suffix.lower() not in (".mp3",".wav"):
        raise DurationBlocked("REAL_AUDIO_FILE_REQUIRED_FOR_DURATION_CHECK")
    try:
        process=subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1",str(path)],
            capture_output=True,text=True,check=False,timeout=25)
        if process.returncode!=0:
            raise DurationBlocked("TTS_AUDIO_PROBE_FAILED")
        seconds=float(process.stdout.strip())
    except (OSError,ValueError,subprocess.TimeoutExpired):
        raise DurationBlocked("AUDIO_DURATION_UNAVAILABLE") from None
    return validate_measured_seconds(seconds)

def main()->int:
    parser=argparse.ArgumentParser(description="Only plan 90s scripts and measure existing audio; no media generation")
    parser.add_argument("--output",type=Path)
    parser.add_argument("--audio",type=Path,help="Previously generated TTS audio, never synthesized by this command")
    parser.add_argument("--rank",type=int,help="Required when checking a particular audio file")
    args=parser.parse_args()
    data=verify_catalog()
    if args.audio:
        if args.rank is None or not 1<=args.rank<=50:
            raise DurationBlocked("AUDIO_MEASUREMENT_REQUIRES_EPISODE_RANK")
        sec=measure_audio_seconds(args.audio)
        data["audio_check"]={"rank":args.rank,"measured_seconds":sec,
                             "approved_for_upload":False,
                             "meaning":"Measured source audio, not a rendered video or editorial approval."}
        data["no_actual_audio_measured"]=False
    payload=json.dumps(data,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(payload,encoding="utf-8")
    else:
        print(payload,end="")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (DurationBlocked,ValueError,OSError,TypeError) as exc:
        raise SystemExit("[90S EDITORIAL BLOCKED] "+str(exc)) from None
