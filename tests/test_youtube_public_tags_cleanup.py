"""Offline QA: remove only internal uploader markers, preserve real vidIQ tags."""
from pathlib import Path
import ast,sys,json
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/"scripts"))
from youtube_public_tags import public_tags,internal_tags,is_internal_tag
from cleanup_six_youtube_internal_tags import EXPECTED,preserved_snippet,preflight,TagCleanupBlocked
import pytest

def test_screenshot_keywords_remain_and_machine_markers_are_removed():
    raw=["Hélio Conde","Minecraft","Minecraft Brasil","Minecraft nostalgia",
         "Minecraft sobrevivência",
         "autoeditorvideo-gamer-v4-reupload-once-20261105",
         "autoeditorvideo-id-game-002-primeira-noite-minecraft-v4",
         "creeper","games Brasil","primeira noite Minecraft","você lembra?"]
    assert public_tags(raw)==[x for x in raw if not x.startswith("autoeditorvideo-")]
    assert len(internal_tags(raw))==2
    assert all(not is_internal_tag(x) for x in public_tags(raw))

def test_snippet_update_preserves_description_title_category_language():
    old={"title":"Primeira noite Minecraft","description":"Texto original com CTA 🎨",
         "categoryId":"20","defaultLanguage":"pt-BR","tags":["Minecraft","autoeditorvideo-id-a"]}
    updated=preserved_snippet(old,public_tags(old["tags"]))
    for field in ("title","description","categoryId","defaultLanguage"):
        assert updated[field]==old[field]
    assert updated["tags"]==["Minecraft"]

def test_only_six_exact_latest_processed_shorts_and_two_channels():
    assert EXPECTED["games"]==("GPJa03DRf5Y","BCqrEmJa77E","j7_cAomsPvM")
    assert EXPECTED["alchemy"]==("WNlK9OYe1jc","bk433QOIdK0","iKlsUANJ8og")
    assert len(set(EXPECTED["games"])|set(EXPECTED["alchemy"]))==6

def test_requires_single_approved_main_workflow(monkeypatch):
    for k in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME",
              "GITHUB_RUN_ATTEMPT","GITHUB_WORKFLOW","REMOVE_INTERNAL_TAGS_APPROVED"):
        monkeypatch.delenv(k,raising=False)
    with pytest.raises(TagCleanupBlocked):
        preflight("games")

def test_no_publication_upload_or_deletion():
    source=(R/"scripts/cleanup_six_youtube_internal_tags.py").read_text(encoding="utf-8")
    assert ".videos().insert(" not in source
    assert ".videos().delete(" not in source
    assert ".thumbnails().set(" not in source
    assert ".videos().update(" in source
    assert 'part="snippet"' in source
    assert 'get("privacyStatus") not in ("private","unlisted","public")' in source
    assert 'after.get("status",{}).get("privacyStatus")!=before.get("status",{}).get("privacyStatus")' in source
    ast.parse(source)
