"""Ensure 50-anime editorial V4 never removes published franchises or restarts uploads.

Tests only read repo catalog/receipts and do not generate files, media or network requests.
"""
from pathlib import Path
import json
import re
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
CATALOG=ROOT/"conteudos/otaku-multicena-animes-50-curadoria-v4.json"
GRADES=(
    ROOT/"conteudos/otaku-multicena-grade-50-a.json",
    ROOT/"conteudos/otaku-multicena-grade-50-b.json"
)
BATCH=ROOT/"conteudos/otaku-multicena-br-50-inéditos-reverso-20261106.json"
RESERVATIONS=ROOT/"conteudos/otaku-production-reservations.json"
RECEIPTS=ROOT/"dados/otaku-br-50-reverso-recibos"
PAUSE=ROOT/"conteudos/otaku-br-50-serial-launch-20261106.json"

def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def anime_id(name):
    key=unicodedata.normalize("NFKC",name).casefold().replace("×","x")
    return re.sub(r"\s+"," ",key).strip()

def sources():
    result=load(CATALOG)
    grade=[e for path in GRADES for e in load(path)["episodes"]]
    published_rows=[e for e in load(BATCH)["episodes"]
                    if (RECEIPTS/(e["id"]+".json")).exists()]
    registry=load(RESERVATIONS)["entries"]
    published_earlier=[e for e in registry if e.get("channel")=="br"
                       and e.get("status")=="published"]
    by_id={e["id"]:e for e in grade}
    protected={anime_id(x["series"]) for x in published_rows}
    protected.update(anime_id(by_id[e["id"]]["series"])
                     for e in published_earlier if e["id"] in by_id)
    return result,grade,published_rows,published_earlier,protected,registry

def test_new_curation_has_fifty_distinct_anime_and_title_candidates():
    doc,*_=sources()
    rows=doc["items"]
    assert doc["schema"]=="otaku-multicena/50-unique-anime-editorial-v4"
    assert len(rows)==doc["series_total"]==50
    assert doc["unique_series"] is True
    assert [r["rank"] for r in rows]==list(range(1,51))
    assert len({anime_id(x["anime"]) for x in rows})==50
    assert len({x["new_short_title_proposal"].casefold() for x in rows})==50
    assert all(len(x["new_short_title_proposal"])>=20 for x in rows)
    assert all(x["fact_check_status"]=="requires_canon_review" for x in rows)
    assert all(x["spoiler_review"]=="required" for x in rows)

def test_all_published_anime_survive_reordering():
    doc,_,published_rows,previous_published,published,_=sources()
    selected={anime_id(r["anime"]) for r in doc["items"]}
    assert len(published_rows)==45
    assert len(previous_published)==7
    assert len(published)==17
    assert published<=selected
    assert doc["preserved_published_series_count"]==17
    assert doc["previous_batch_verified_public_receipts"]==45
    assert {anime_id(x) for x in doc["preserved_published_series"]}==published
    assert all(r["franchise_state"]=="already_published_franchise"
               for r in doc["items"] if anime_id(r["anime"]) in published)
    assert doc["published_records_immutable"] is True

def test_six_exclusions_are_not_published_and_old_files_are_preserved():
    doc,grade,_,_,published,_=sources()
    old={anime_id(x["series"]) for x in grade}
    new={anime_id(x["anime"]) for x in doc["items"]}
    excluded={anime_id(x["anime"]) for x in doc["exclude_from_new_50_only"]}
    added={anime_id(x) for x in doc["added_to_new_50"]}
    assert len(old)==len(new)==50
    assert len(excluded)==len(added)==6
    assert old-new==excluded
    assert new-old==added
    assert not excluded.intersection(published)
    assert doc["old_sources_not_deleted"] is True
    assert all(path.is_file() for path in GRADES)

def test_unpublished_legacy_batch_entries_remain_pending_without_reassignment():
    doc,*_=sources()
    pending=doc["previous_batch_pending_episodes"]
    assert {e["position"] for e in pending}==set(range(1,6))
    assert all(e["status"]=="unchanged_pending_paused" for e in pending)
    assert all(e["id"].startswith("610") for e in pending)
    assert all(not e["queue_enabled"] and not e["publication_authorized"]
               and not e["images_generated"] and not e["voice_generated"]
               for e in doc["items"])

def test_existing_in_production_and_reserved_episodes_untouched():
    doc,*_=sources()
    by_name={r["anime"]:r for r in doc["items"]}
    assert by_name["Aoashi"]["franchise_state"]=="in_production_protected"
    assert by_name["Overgeared"]["franchise_state"]=="in_production_protected"
    assert by_name["Gachiakuta"]["franchise_state"]=="reserved_protected"
    assert by_name["Bleach: Thousand-Year Blood War"]["franchise_state"]=="existing_assets_protected"
    assert doc["upload_queue_modified"] is False
    assert doc["generation_paused"] is True
    assert doc["youtube_publication_paused"] is True
    pause=load(PAUSE)
    assert pause["pause_requested"] is True
    assert pause["authorized_public"] is False
    assert pause["resume_authorized_after_maintenance"] is False
    assert pause["maintenance_complete"] is False

def test_curated_markdown_shows_all_titles_and_preservation_warning():
    doc,*_=sources()
    content=(ROOT/"docs/OTAKU-MULTICENA-50-ANIMES-CURADORIA-V4.md").read_text(encoding="utf-8")
    assert "45 publicações com comprovantes" in content
    assert "17 animes diferentes" in content
    for row in doc["items"]:
        assert row["new_short_title_proposal"] in content
    assert "Não substituir roteiros/MP4s" in content


def test_unverified_channel_history_does_not_count_as_definite_exclusion():
    doc,*_=sources()
    assert doc["live_channel_inventory_complete"] is False
    assert doc["exclusions_are_non_destructive"] is True
    assert all(x["restore_if_found_published"] is True
               for x in doc["exclude_from_new_50_only"])
    assert all(x["publication_check"]=="not_seen_in_available_repository_evidence_not_exhaustive"
               for x in doc["exclude_from_new_50_only"])
