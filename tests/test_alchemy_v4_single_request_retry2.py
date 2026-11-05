"""Validate single-purpose Alchemy retry V2 after initial draft-state mismatch."""
import ast,json
from pathlib import Path

R=Path(__file__).resolve().parents[1]
S=R/"scripts/alchemy_v4_single_request_retry2.py"
M=R/"conteudos/alchemy-v4-single-request-retry2-20261105.json"

def test_exact_scope_and_owner_check():
 s=S.read_text(encoding="utf-8")
 ast.parse(s)
 assert 'CHANNEL=KNOWN_IDS["alchemy"]' in s
 assert 'get_youtube("alchemy"' in s
 assert 'YOUTUBE_ALCHEMY_TOKEN_JSON' in s
 assert '"games"' not in s
 assert "resumable=False" in s
 assert "result=api.videos().insert(" in s
 assert ".execute(num_retries=0)" in s
 assert "state(api,id)" in s
 assert "seen=existing(api,eid,meta[" in s
 assert 'privacyStatus":"private"' in s
 assert s.count('("alchemy-')==3
 assert "set_thumbnail(api,id,cover)" in s
 assert "OUTPUT.write_text(" in s
 assert ".videos().delete(" not in s and ".videos().update(" not in s
 assert "state(api,old)" not in s

def test_authorized_once_with_old_ids_preserved():
 d=json.loads(M.read_text())
 assert d["approved_by_creator"] is True
 assert d["channel"]=="alchemy"
 assert d["visibility"]=="private"
 assert d["expected_count"]==3
 assert d["method"]=="single_request_non_resumable"
 assert d["no_new_images"] is True
 assert d["no_other_channel_changes"] is True
 assert d["previous_run"]==42093990295
 assert d["source_run"]==42074829801
