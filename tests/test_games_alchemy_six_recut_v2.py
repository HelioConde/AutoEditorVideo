"""Offline tests of six revised narration scripts and thumbnail layout."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import games_alchemy_six_recut_v2 as recut

def test_six_revised_episodes_reserved_with_ctas():
    data=recut.validate_manifest()
    assert len(data["projects"])==6
    assert [p["source_episode_id"] for p in data["projects"]]==recut.ORDER
    assert all(p["revised_episode_id"].endswith("-v2") for p in data["projects"])
    assert all(p["thumbnail"]["style"].endswith("top_center") for p in data["projects"])

def test_no_audible_disclosure_and_no_claims_of_gameplay():
    for p in recut.validate_manifest()["projects"]:
        script=p["narration"].lower()
        assert "se inscreve" in script
        assert not any(s in script for s in recut.PROHIBITED_SPOKEN)
        assert "não é gameplay" not in script
        assert "não é uma gravação" not in script
        assert "ilustrações geradas" not in script
        assert "🎨" in p["description"]  # transparency stays in metadata
        assert p["origin_video_id"] # old version stays safely private
        assert len(p["narration"].split())>=65

def test_one_shot_renderer_not_allowed_to_run_without_explicit_environment(monkeypatch):
    for k in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME","GITHUB_RUN_ATTEMPT","RECUT_V2_APPROVED","SOURCE_RUN_ID"):
        monkeypatch.delenv(k,raising=False)
    with pytest.raises(recut.RecutError,match="WRONG_REPOSITORY"):
        recut.guard_render()

def test_subtitle_wrapping_protects_horizontal_safe_area(tmp_path):
    # Fake WordBoundary timestamps: no TTS call or files required.
    parts="Já existem muitos detalhes que ajudam você a se inscrever no canal e acompanhar mais vídeos".split()
    words=[{"start":i*.35,"end":i*.35+.27,"text":w} for i,w in enumerate(parts)]
    path=tmp_path/"captions.ass"
    recut.write_safe_subtitles(words,path,25.0)
    text=path.read_text(encoding="utf-8-sig")
    lines=[x for x in text.splitlines() if x.startswith("Dialogue:")]
    assert lines
    for row in lines:
        caption=row.split(",,",1)[1]
        for line in caption.split(r"\N"):
            assert len(line)<=24
    assert "MarginL" in text and "260" in text
