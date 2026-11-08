#!/usr/bin/env python3
"""Evidence-aware planning for future Otaku Multicena editorial experiments.

No schedule is submitted, no new MP4 is generated, and no YouTube API is used.
Assumptions about posting frequency and algorithmic delivery remain hypotheses.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from otaku_multicena_editorial_audit import normalized

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"conteudos/otaku-multicena-insights-editor-v2.json"

class StrategyBlocked(ValueError):
    pass

EXPERIMENTS=(
 {"key":"mystery_reveal","category":"Mistério e revelação","count":5,
  "reference":"Light caçou Kira SEM SABER que era ele mesmo",
  "creative_rule":"Prometa uma contradição específica e entregue a explicação antes do fim"},
 {"key":"emotional_choice","category":"Escolha emocional","count":5,
  "reference":"Blue Box: AMOR OU ESPORTE",
  "creative_rule":"Mostre desejo e custo da escolha; não invente detalhes do cânone"},
 {"key":"power_curiosity","category":"Curiosidade sobre habilidades","count":5,
  "reference":"Zenitsu luta melhor DORMINDO?",
  "creative_rule":"Comece por uma pergunta verificável; explique a mecânica sem exagerar"},
)

def analyze_title(title:str)->dict:
    """Quality prompts, not algorithmic or statistical performance predictions."""
    if not isinstance(title,str) or not title.strip():
        raise StrategyBlocked("EMPTY_TITLE")
    title=title.strip()
    words=title.split()
    cap=[w for w in words if len(re.sub(r"[^A-Za-zÀ-ÿ]","",w))>=3 and
         re.sub(r"[^A-Za-zÀ-ÿ]","",w).isupper()]
    has_question="?" in title
    has_contrast=bool(re.search(
        r"\b(sem|mas|mesmo|melhor|pior|contra|versus|vs|imposs[ií]vel|enganou|perdeu|por que|como)\b",
        normalized(title),re.IGNORECASE))
    checks={
        "reasonable_length":12<=len(title)<=70,
        "direct_promise":has_question or has_contrast,
        "not_all_caps":title != title.upper(),
        "single_emphasis_word":len(cap)<=2,
        "no_repeat_punctuation":"!!!" not in title and "???" not in title
    }
    return {"title":title,"checks":checks,"review_reasons":[k for k,v in checks.items() if not v],
            "human_factual_check_required":True,"predicted_views":None}

def experiment_plan(snapshot:dict)->dict:
    entries=snapshot.get("audit_snapshots",[])
    if not entries:
        raise StrategyBlocked("NO_AUDIT_SNAPSHOT")
    latest=entries[-1]
    top=latest.get("top_five",[])
    if len(top)!=5:
        raise StrategyBlocked("TOP_FIVE_MISSING")
    titles=[str(i.get("title","")) for i in top]
    if len(set(titles))!=5:
        raise StrategyBlocked("DUPLICATE_TOP_TITLES")
    death_note=sum(x.get("franchise")=="Death Note" for x in top)
    total=latest.get("views_total")
    videos=latest.get("video_count")
    if not isinstance(total,int) or not isinstance(videos,int) or videos<=0:
        raise StrategyBlocked("CHANNEL_METRICS_INVALID")
    from otaku_growth_autotune import load_policy
    adaptive=load_policy()
    plan={
        "schema":"otaku-multicena/strategy-experiments/v1",
        "adaptive_growth":({
            "status":"metric_grounded_experiments_only",
            "priority":adaptive["priority"],
            "viewed_vs_swiped_28d_percent":adaptive["inputs"]["views_vs_swiped_28d_percent"],
            "viewed_rate_target_is_experiment_not_prediction":adaptive["viewed_rate_aspirational_target_percent"],
            "content_variants":adaptive["production_rules"]["content"]["experiments"],
            "hook_first_seconds":adaptive["production_rules"]["hook"]["first_seconds"],
            "short_duration_range_seconds":adaptive["production_rules"]["duration"]["baseline_experiment_seconds"],
            "extended_duration_range_seconds":adaptive["production_rules"]["duration"]["extended_experiment_seconds"],
            "max_extended_test_share_pct":adaptive["production_rules"]["duration"]["extended_max_share_of_new_tests_percent"],
            "no_automatic_publication_or_length_change":True
        } if adaptive else None),
        "mode":"offline_only_generation_and_upload_paused",
        "top_five_death_note_count":death_note,
        "channel_views_per_video":round(total/videos,2),
        "reported_shorts_average":latest.get("shorts_view_average_reported"),
        "means_are_not_same_metric":True,
        "top_examples":[{"title":i["title"],"views":i["views"],
                         "title_review":analyze_title(i["title"])}
                        for i in top],
        "editorial_tests":list(EXPERIMENTS),
        "planned_total":sum(e["count"] for e in EXPERIMENTS),
        "cadence_hypotheses":[
            {"name":"A","shorts_per_day":2,
             "window":"observe each Short 48h from its publication"},
            {"name":"B","shorts_per_day":3,
             "window":"observe each Short 48h from its publication"}],
        "cadence_assumption":"Not evidence that YouTube penalizes more than 3 uploads/day",
        "success_measurements":[
            "viewed_vs_swiped_away","average_view_duration_seconds",
            "average_percentage_viewed","subscribers_per_1000_views",
            "48h_views","feed_exposure","shares_per_1000_views"],
        "story_requirements":[
            "first 3s show a specific, verifiable curiosity",
            "script answers its own hook without invented facts",
            "avoid unearned 10-second intro and filler",
            "scene boundary respects spoken sentence and action",
            "separate actual character/object animation from zoom-only motion",
            "copyright and rights review before any release"],
        "longform_idea":{
            "approved_for_production":False,
            "pilot_range_minutes":[8,12],
            "review_requirements":"fact-check and original script, independent visual QA",
            "note":"Do not auto-concatenate Shorts; no YouTube publication enabled"},
        "release":{"generated":False,"published":False,"resume_authorized":False}
    }
    return plan

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    data=json.loads(DATA.read_text(encoding="utf-8"))
    output=json.dumps(experiment_plan(data),ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding="utf-8")
    else:
        print(output,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
