#!/usr/bin/env python3
"""Read-only editorial PLAN quality score for the 90s Otaku Multicena test.

A 9/10 score means NINE DOCUMENTATION/PLAN checks were met, NOT a prediction
of YouTube retention nor an approval of factual lore, media rights or MP4.
The tenth requires actual media and human review and cannot pass offline.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json
from urllib.parse import urlsplit

from otaku_multicena_duration_90 import load,PLAN,CURATION,PAUSE,ROLES,word_count,validate_result_only

class PlanBlocked(ValueError):
    pass

def check_record(row: dict, matching_catalog: dict) -> dict:
    if row.get("rank") != matching_catalog.get("rank") or row.get("title") != matching_catalog.get("new_short_title_proposal"):
        raise PlanBlocked("CATALOG_AND_PILOT_TITLE_NOT_ALIGNED")
    report=row.get("story_quality_v5",{})
    parts=row.get("story_segments",[])
    script=row.get("narration_script") or ""
    micro=report.get("micro_reveals",[])
    visuals=report.get("visual_shots",[])
    claims=report.get("canon_claims",[])
    audio=report.get("narration",{})
    rights=report.get("editorial_safety",{})
    pair=report.get("experiment_pair",{})
    evidence_domains=("hbomax.com","jojo-portal.com","jojo-portal-anime.com",
                      "demonslayer-anime.com","media.netflix.com","viz.com",
                      "crunchyroll.com","anime.com")
    def sourced(claim:dict)->bool:
        try:
            url=urlsplit(claim.get("source_url",""))
            valid_host=url.hostname and (url.hostname in evidence_domains or
                      any(url.hostname.endswith("."+domain) for domain in evidence_domains))
            return bool(valid_host and url.scheme=="https" and url.path.startswith("/") and
                        isinstance(claim.get("claim"),str) and len(claim["claim"])>24 and
                        claim.get("human_verified") is False)
        except (TypeError,ValueError,AttributeError):
            return False
    beat_times=[m.get("approx_second") for m in micro]
    shot_times=[s.get("approx_second") for s in visuals]
    checks={
      "short_specific_hook":bool(parts and parts[0].get("role")=="hook" and
         parts[0].get("word_count",100)<=8 and
         isinstance(report.get("core_promise"),str) and
         "?" in report["core_promise"]),
      "sourced_canon_claims":len(claims)>=3 and all(sourced(c) for c in claims),
      "six_beats_and_story_length":(
          [p.get("role") for p in parts]==list(ROLES) and
          190<=word_count(script)<=225 and
          script==" ".join(p["text"] for p in parts)),
      "four_unique_mid_story_discoveries":(
          len(micro)==4 and beat_times==[15,31,51,70] and
          len({m.get("anchor") for m in micro})==4 and
          all(isinstance(m.get("anchor"),str) and script.count(m["anchor"])==1
              and m["anchor"] in parts[i+1]["text"] and
              m.get("actual_audio_second") is None for i,m in enumerate(micro))),
      "final_result_without_cta":False,
      "ten_original_visual_beats":(
          len(visuals)==10 and shot_times==[0,4,12,19,29,40,50,61,71,81] and
          len({v.get("shot_type") for v in visuals})>=5 and
          all(v.get("shot_number")==i and v.get("asset_ready") is False and
              v.get("rights_checked") is False and
              isinstance(v.get("visual_instruction"),str) and
              len(v["visual_instruction"])>14
              for i,v in enumerate(visuals,1))),
      "human_narration_direction":(
          audio.get("locale")=="pt-BR" and
          isinstance(audio.get("style"),str) and len(audio["style"])>=35 and
          len(audio.get("segment_tones",[]))==6 and
          len(audio.get("names_to_pronounce",[]))>=2 and
          audio.get("pronunciation_reviewed") is False and
          audio.get("measured_tts_seconds") is None),
      "rights_spoiler_and_review_gates":(
          rights.get("spoilers_level") in ("baixo","moderado","alto") and
          rights.get("spoilers_approved") is False and
          rights.get("canon_human_verified") is False and
          rights.get("rights_verified") is False and
          row.get("ready_to_render") is False and
          row.get("no_auto_upload") is True),
      "matched_40s_vs_90s_protocol":(
          pair.get("short_duration_seconds")==40 and pair.get("long_duration_seconds")==90
          and pair.get("control_script_ready") is False
          and pair.get("both_no_cta") is True
          and pair.get("no_duplicate_visual_assets") is True
          and pair.get("matched_48h") is True
          and pair.get("no_publication_authorized") is True),
      "measured_media_and_human_approval":False,
    }
    try:
        checks["final_result_without_cta"]=validate_result_only(row)=="result_only_verified_offline"
    except ValueError:
        checks["final_result_without_cta"]=False
    if row.get("script_status")!="canon_grounded_draft_needs_human_fact_check":
        raise PlanBlocked("PILOT_MUST_REMAIN_UNAPPROVED_EDITORIAL_DRAFT")
    score=sum(bool(value) for value in checks.values())
    return {
        "rank":row["rank"],"anime":row["anime"],"title":row["title"],
        "planning_score":score,"out_of":10,"checks":checks,
        "editorial_gate":"BLOCKED_UNTIL_ACTUAL_TTS_VISUAL_CANON_AND_RIGHTS_REVIEW",
        "real_audio_measured":False,"published":False
    }

def audit()->dict:
    plan=load(PLAN);catalog=load(CURATION);pause=load(PAUSE)
    if not (pause.get("pause_requested") is True and
            pause.get("authorized_public") is False and
            pause.get("maintenance_complete") is False and
            pause.get("resume_authorized_after_maintenance") is False):
        raise PlanBlocked("CREATOR_PAUSE_NOT_ENFORCED")
    items=plan.get("items",[])
    if len(items)!=50 or len(catalog.get("items",[]))!=50:
        raise PlanBlocked("FIFTY_TOPICS_REQUIRED")
    if plan.get("editorial_v5",{}).get("target_planning_score")!=9:
        raise PlanBlocked("NINE_POINT_PLAN_NOT_CONFIGURED")
    if plan.get("editorial_v5",{}).get("paused_generation") is not True or plan["editorial_v5"].get("paused_publication") is not True:
        raise PlanBlocked("EDITORIAL_PLAN_IS_NOT_OFFLINE")
    drafts=[check_record(r,catalog["items"][i]) for i,r in enumerate(items) if r.get("narration_script")]
    if len(drafts)!=5 or len({d["anime"] for d in drafts})!=5:
        raise PlanBlocked("FIVE_UNIQUE_90S_PILOTS_REQUIRED")
    if any(d["planning_score"]!=9 for d in drafts):
        raise PlanBlocked("PILOT_PLANNING_SCORE_BELOW_NINE")
    if any(d["checks"]["measured_media_and_human_approval"] for d in drafts):
        raise PlanBlocked("OFFLINE_PLANNING_CANNOT_CLAIM_MEDIA_APPROVAL")
    if any(r.get("narration_script") for r in items[5:]):
        raise PlanBlocked("FUTURE_UNREVIEWED_SCRIPTS_CANNOT_BE_MARKED_READY")
    return {
      "schema":"otaku-multicena/editorial-planning-score/v1",
      "scope":"five scripted pilots, NOT all 50 anime, not videos",
      "score":9,"out_of":10,
      "pending_tenth_item":"real TTS, human canon/visual review, music and media rights, finished MP4",
      "published_short_count_from_this_plan":0,
      "generation_or_upload_authorized":False,
      "unwritten_anime_stories":45,
      "pilot_results":drafts,
      "fair_experiment_warning":"No measured improvement until 40s vs 90s videos actually exist, pass rights QA and reach comparable 48h age.",
    }

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=audit()
    serialized=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(serialized,encoding="utf-8")
    else:
        print(serialized,end="")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except (PlanBlocked,ValueError,TypeError,KeyError,OSError) as error:
        raise SystemExit("[EDITORIAL PLANNING BLOCKED] "+str(error)) from None
