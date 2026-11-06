#!/usr/bin/env python3
"""Offline editorial/metadata audit; NEVER generates media or contacts YouTube.

Candidate tags are treated as untrusted search suggestions, not as a mandate to
copy whatever a competitor or keyword explorer recommends. Existing approved
publication records and rendered media are immutable.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"conteudos/otaku-multicena-br-50-inéditos-reverso-20261106.json"

GENERAL_TAGS={
    "shorts","youtube shorts","youtubeshorts","shorts de anime","anime",
    "anime facts","anime theory","anime theories","anime em portugues",
    "curiosidades anime","curiosidades de anime","analise de anime",
    "otaku multicena","otaku","anime brasileiro","anime psicologico",
    "anime aventura","anime shonen","anime fantasia","misterio anime",
    "estrategia anime","animes","anime curiosidades",
}
# Competitor names are for comparisons and research, NOT metadata piggybacking.
COMPETITORS={
    "shin animes","animakai kai","d+animes","mavua animes",
    "anime voz br","sabia geek",
}
# Clear unrelated suggestions observed in a keyword dump. The relevance
# rule below also rejects unknown strings that don't match this episode.
OFF_TOPIC={
    "the great gatsby","great gatsby summary","lord of the flies",
    "a court of thorns and roses","acotar","book recommendations",
    "booktuber","beyblade caseiro","santos x palmeiras",
    "vasco x flamengo","gremio","stf","investimentos",
    "enem","resenha rentavel","palmeiras","futebol s2h",
    "caught on camera","incredible things caught on camera",
    "you won't believe your eyes","viral moments","amazing moments",
    "unbelievable moments","online lessons","machineplays",
    "youtubeshorts viral moments","corrida das blogueiras",
}
FRANCHISE_ALIASES={
    "death note": {"death note","death note anime","death note manga"},
    "the apothecary diaries": {
        "the apothecary diaries","diarios de uma apotecaria","kusuriya no hitorigoto"
    },
    "black clover":{"black clover"},
    "jujutsu kaisen":{"jujutsu kaisen","jjk"},
    "naruto":{"naruto"},
    "one piece":{"one piece"},
    "attack on titan":{"attack on titan","shingeki no kyojin"},
    "fullmetal alchemist: brotherhood":{
        "fullmetal alchemist","fullmetal alchemist brotherhood"
    },
    "demon slayer":{"demon slayer","kimetsu no yaiba"},
    "hunter x hunter":{"hunter x hunter","hunter hunter"},
    "code geass":{"code geass"},
    "frieren: beyond journey's end":{"frieren","frieren beyond journeys end"},
}
# Known characters are allowed only if the short actually discusses them.
EPISODE_CHARACTERS={
    "death note":{"light yagami":"light","l lawliet":"l","ryuk":"ryuk",
                  "misa amane":"misa","kira":"kira"},
    "the apothecary diaries":{"maomao":"maomao","jinshi":"jinshi"},
    "black clover":{"asta":"asta","yuno":"yuno"},
    "demon slayer":{"zenitsu":"zenitsu","tanjiro":"tanjiro"},
    "hunter x hunter":{"kurapika":"kurapika","killua":"killua"},
    "one piece":{"nami":"nami","luffy":"luffy","zoro":"zoro","usopp":"usopp"},
}

def normalized(value:str)->str:
    raw=unicodedata.normalize("NFKD",value.casefold())
    folded="".join(ch for ch in raw if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",folded)).strip()

def contains_phrase(haystack:str,needle:str)->bool:
    if not needle:return False
    return (" "+normalized(needle)+" ") in (" "+normalized(haystack)+" ")

OFF_TOPIC_NORMALIZED={normalized(x) for x in OFF_TOPIC | COMPETITORS}

def review_candidates(row:dict,candidates:list[str],max_tags:int=12,max_chars:int=260)->dict:
    """Propose only topical metadata; never edit uploaded records in place."""
    series=normalized(row.get("series",""))
    aliases=next((items for key,items in FRANCHISE_ALIASES.items()
                  if normalized(key)==series),{series})
    aliases={normalized(a) for a in aliases}
    story=" ".join(str(row.get(k,"")) for k in
                   ("series","title","hook","narration_script","cover_text"))
    selected=[]
    rejected=[]
    seen=set()
    total=0
    for original in candidates:
        if not isinstance(original,str):
            rejected.append({"tag":str(original),"reason":"NOT_STRING"})
            continue
        tag=original.strip().lstrip("#").strip()
        norm=normalized(tag)
        if not tag or not norm:
            rejected.append({"tag":original,"reason":"EMPTY"})
            continue
        if norm in seen:
            rejected.append({"tag":tag,"reason":"DUPLICATE"})
            continue
        seen.add(norm)
        if norm in OFF_TOPIC_NORMALIZED:
            rejected.append({"tag":tag,"reason":"OFF_TOPIC_OR_COMPETITOR"})
            continue
        if len(tag)>55 or len(tag.split())>7:
            rejected.append({"tag":tag,"reason":"TOO_BROAD_OR_LONG"})
            continue
        characters=EPISODE_CHARACTERS.get(series,{})
        topical=(norm in GENERAL_TAGS or norm in aliases
                 or any(norm == name and contains_phrase(story,anchor)
                        for name,anchor in characters.items())
                 or contains_phrase(story,tag))
        if not topical:
            rejected.append({"tag":tag,"reason":"NOT_IN_THIS_EPISODE"})
            continue
        next_len=total+len(tag)+(1 if selected else 0)
        if len(selected)>=max_tags or next_len>max_chars:
            rejected.append({"tag":tag,"reason":"TAG_BUDGET_EXCEEDED"})
            continue
        selected.append(tag)
        total=next_len
    return {"accepted":selected,"rejected":rejected,"character_count":total}

def audit_episode(row:dict)->dict:
    tags=review_candidates(row,row.get("tags",[]))
    hook=row.get("hook","")
    story=row.get("narration_script","")
    hook_words=len(hook.split())
    story_words=len(story.split())
    issues=[]
    if not (6<=hook_words<=22):
        issues.append("HOOK_LENGTH_REVIEW")
    if len(row.get("title",""))>70:
        issues.append("TITLE_TOO_LONG_REVIEW")
    if story_words<50 or story_words>140:
        issues.append("SCRIPT_DURATION_REVIEW")
    if tags["rejected"]:
        issues.append("METADATA_REQUIRES_REVIEW")
    if len(row.get("storyboard",[]))!=5:
        issues.append("VISUAL_BEATS_REQUIRE_REVIEW")
    return {"number":row.get("position"),"series":row.get("series"),
            "title":row.get("title"),"hook_words":hook_words,
            "narration_words":story_words,
            "tags_suggested":tags["accepted"],
            "tags_rejected":tags["rejected"],
            "review_flags":issues,
            "status":"offline_editorial_review_only"}

def audit_catalog()->dict:
    data=json.loads(CATALOG.read_text(encoding="utf-8-sig"))
    episodes=data["episodes"]
    report=[audit_episode(row) for row in episodes]
    return {
        "schema":"otaku-multicena/editorial-audit/v2",
        "catalog_size":len(episodes),
        "no_video_generated":True,
        "no_youtube_actions":True,
        "audit":report,
        "review_counts":{
          "episodes_flagged":sum(bool(r["review_flags"]) for r in report),
          "rejected_catalog_tags":sum(len(r["tags_rejected"]) for r in report),
        },
        "guidance":[
          "Treat 69.45% retention / 28s average on the Light Short as a benchmark, not a guarantee.",
          "Test 35-45s versus other lengths after listening to real narration.",
          "Hook in first 1-3s, value early, meaningful action instead of zoom-only.",
          "Monitor watch time and 48-hour subscriptions, not vidIQ SEO score alone.",
          "No public upload before creator resumes after maintenance.",
        ]
    }

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=None)
    args=parser.parse_args()
    result=audit_catalog()
    serialized=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(serialized,encoding="utf-8")
    else:print(serialized)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
