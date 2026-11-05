"""One-time Alchemy-only re-upload checks, no YouTube network calls."""
import ast,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/alchemy_v4_single_request_retry.py"
MARKER=ROOT/"conteudos/alchemy-v4-three-single-request-20261105.json"

def test_exact_three_and_no_gamer_channel():
 s=SCRIPT.read_text(encoding="utf-8")
 ast.parse(s)
 for episode in ("alchemy-001-chatgpt-gifs-v4","alchemy-002-images-26-consistencia-v4","alchemy-003-gif-animado-tutorial-v4"):
  assert '"'+episode+'"' in s
 assert '"games"' not in s
 assert 'get_youtube("alchemy"' in s
 assert 'KNOWN_IDS["alchemy"]' in s
 assert 'YOUTUBE_ALCHEMY_TOKEN_JSON' in s
 assert 'YOUTUBE_GAMES_TOKEN_JSON' not in s
 assert "resumable=False" in s
 assert ".execute(num_retries=0)" in s
 assert 'privacyStatus":"private"' in s
 assert "set_thumbnail(api,id,cover)" in s
 assert '"categoryId":"28"' in s

def test_explicit_three_video_approval():
 m=json.loads(MARKER.read_text(encoding="utf-8"))
 assert m["approved_by_creator"] is True
 assert m["channel"]=="alchemy"
 assert m["source_run"]==42074829801
 assert m["source_artifact_id"]==13439442112
 assert m["method"]=="single_request_non_resumable"
 assert m["expected_count"]==3
 assert m["visibility"]=="private"
 assert len(m["old_ids"])==3
 assert m["other_channels_unchanged"] is True
 assert m["no_new_images"] is True

def test_no_delete_no_public_release():
 s=SCRIPT.read_text()
 assert ".videos().delete(" not in s
 assert ".videos().update(" not in s
 assert 'privacyStatus":"public"' not in s
 assert "alchem" in s.lower()
