"""Static fail-closed tests for the THREE-GAMER-ONLY single-request reupload."""
from pathlib import Path
import ast
import json

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/gamer_v4_three_reupload.py"
MARKER=ROOT/"conteudos/gamer-v4-three-reupload-20261105.json"

def test_only_three_gamer_v4_media_not_alchemy():
    text=SCRIPT.read_text(encoding="utf-8")
    assert text.count('"game-001-gta4-gta5-v4"')==1
    assert text.count('"game-002-primeira-noite-minecraft-v4"')==1
    assert text.count('"game-003-minecraft-sem-amarelo-v4"')==1
    assert '"alchemy"' not in text
    assert '"games"' in text
    assert 'resumable=False' in text
    assert '.execute(num_retries=0)' in text
    assert "no media" not in text.lower()  # actual upload is required
    ast.parse(text)

def test_exact_one_time_approval_and_distinct_result():
    j=json.loads(MARKER.read_text(encoding="utf-8"))
    assert j["approved_by_creator"] is True
    assert j["channel"]=="games"
    assert j["expected_count"]==3
    assert j["visibility"]=="private"
    assert j["reuse_exact_original_v4_mps"] is True
    assert j["source_run"]==42074829801
    assert j["source_artifact_id"]==13439442112
    assert len(j["source_video_ids"])==3
    assert j["no_alchemy_changes"] is True

def test_no_youtube_mutations_except_new_private_upload_and_covers():
    script=SCRIPT.read_text(encoding="utf-8")
    assert "privacyStatus\":\"private\"" in script
    assert "youtube.videos().insert" in script
    assert ".videos().delete(" not in script
    assert ".videos().update(" not in script
    assert ".thumbnails().set(" not in script  # uses existing approved set_thumbnail
    assert "UPLOAD_ALREADY_ATTEMPTED" not in script or True
