"""Offline metadata quality; no YouTube, network, image provider or upload."""
import importlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
audit=importlib.import_module("otaku_multicena_editorial_audit")

def example():
    return {"position":1,"series":"Death Note",
            "title":"Light enganou L com um pacote de BATATAS!",
            "hook":"Light enganou a vigilancia de L!",
            "narration_script":"Light Yagami e Kira sao investigados por L. Light e Ryuk conhecem o Death Note.",
            "cover_text":"Light VS L","storyboard":[{}]*5,
            "tags":["Death Note","Light Yagami","Kira","otaku multicena"]}

def test_only_tags_grounded_in_this_specific_short_are_suggested():
    terms=[
        "Death Note","Light Yagami","Kira","anime facts",
        "The Great Gatsby","booktuber","santos x palmeiras",
        "misa amane","Shin Animes 心","Death Note","caught on camera",
        "the apothecary diaries","otaku multicena",
    ]
    review=audit.review_candidates(example(),terms)
    accepted=[audit.normalized(x) for x in review["accepted"]]
    assert accepted==[
        "death note","light yagami","kira","anime facts","otaku multicena"
    ]
    reasons={audit.normalized(x["tag"]):x["reason"] for x in review["rejected"]}
    assert reasons["the great gatsby"]=="OFF_TOPIC_OR_COMPETITOR"
    assert reasons["shin animes"]=="OFF_TOPIC_OR_COMPETITOR"
    assert reasons["misa amane"]=="NOT_IN_THIS_EPISODE"
    assert reasons["death note"]=="DUPLICATE"
    assert reasons["the apothecary diaries"]=="NOT_IN_THIS_EPISODE"

def test_case_accents_and_limits_are_enforced_without_spam():
    row=example()
    terms=["análise de anime","analise de anime","anime em português","shorts",
           "anime psicológico","Kira","otaku","Death Note","Light Yagami"]
    review=audit.review_candidates(row,terms,max_tags=4,max_chars=100)
    assert len(review["accepted"])<=4
    assert len(review["accepted"])==len({audit.normalized(x) for x in review["accepted"]})
    assert all(x["reason"] in ("DUPLICATE","TAG_BUDGET_EXCEEDED")
               for x in review["rejected"])
    assert review["character_count"]<=100

def test_audit_is_explicitly_offline_and_keeps_the_real_catalog_intact():
    report=audit.audit_catalog()
    assert report["catalog_size"]==50
    assert report["no_video_generated"] is True
    assert report["no_youtube_actions"] is True
    assert len(report["audit"])==50
    assert all(x["status"]=="offline_editorial_review_only" for x in report["audit"])
    assert {x["number"] for x in report["audit"]}==set(range(1,51))
    assert report["review_counts"]["rejected_catalog_tags"]>=0

def test_competitor_names_are_not_keyword_stuffing():
    row=example()
    names=["Shin Animes 心","Animakai KAI","D+ANIMES","Mavua Animes",
           "Anime Voz BR","Sabia Geek"]
    review=audit.review_candidates(row,names)
    assert review["accepted"]==[]
    assert all(x["reason"]=="OFF_TOPIC_OR_COMPETITOR"
               for x in review["rejected"])
