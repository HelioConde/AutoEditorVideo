"""No-network regression tests: HTTP400 recovery must preserve REAL input reference."""
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import gamer_v2_edit_recovery as fix
import nine_visual_replacements_v2_20261108 as batch

def sample():
    row=batch.validate("games")[0]
    return row,row["scenes"][7],row["character_identity_bible"]

def anchor(tmp_path):
    p=tmp_path/"anchor-builder.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n"+b"\x01"*31000)
    return p

def test_compact_has_same_character_and_real_story_scene():
    row,scene,chars=sample()
    standard=fix.compact_scene_prompt(row,scene,chars,fallback=False)
    short=fix.compact_scene_prompt(row,scene,chars,fallback=True)
    assert "Minecraft Builder" in standard
    assert "blocky cabin" in standard and "blocky cabin" in short
    assert "REFERENCE IMAGE" in standard and "REFERENCE IMAGE" in short
    assert len(short)<len(standard)
    assert all(word not in short for word in ("OFFICIAL screenshot", "generic substitute"))

def test_only_one_new_request_on_http400_with_exact_same_anchor(tmp_path):
    img=anchor(tmp_path)
    row,scene,chars=sample()
    budget=[6]
    observed=[]
    def fake_edit(ref,prompt,model,key,*,transparent):
        observed.append((ref,prompt,model,transparent))
        if len(observed)==1:raise RuntimeError("Proxy recusou images/edits (HTTP 400).")
        return b"successful_edit"
    blob,strategy=fix.edit_with_bounded_http400_repair(
        img,row,scene,chars,"gpt-image-2","fake",fake_edit,budget)
    assert blob==b"successful_edit"
    assert strategy=="short_reference_edit_after_http400"
    assert len(observed)==2
    assert observed[0][0]==img and observed[1][0]==img
    assert observed[0][1]!=observed[1][1]
    assert all(x[2]=="gpt-image-2" and x[3] is False for x in observed)
    assert budget==[5]

def test_non_400_is_not_retried(tmp_path):
    row,scene,chars=sample()
    seen=[]
    def fake(*a,**kw):
        seen.append(1)
        raise RuntimeError("HTTP 403")
    with pytest.raises(RuntimeError,match="403"):
        fix.edit_with_bounded_http400_repair(anchor(tmp_path),row,scene,chars,
                                            "gpt-image-2","fake",fake,[6])
    assert len(seen)==1

def test_repeated_http400_fails_closed_without_third_call(tmp_path):
    row,scene,chars=sample()
    attempts=[]
    def fake(*args,**kw):
        attempts.append(1)
        raise RuntimeError("HTTP 400")
    with pytest.raises(RuntimeError,match="400"):
        fix.edit_with_bounded_http400_repair(anchor(tmp_path),row,scene,chars,
                                            "gpt-image-2","fake",fake,[6])
    assert len(attempts)==2

def test_budget_exhaustion_refuses_retry(tmp_path):
    row,scene,chars=sample()
    observed=[]
    def fake(*a,**kw):
        observed.append(1)
        raise RuntimeError("HTTP 400")
    with pytest.raises(fix.GamerEditBlocked,match="EXHAUSTED"):
        fix.edit_with_bounded_http400_repair(anchor(tmp_path),row,scene,chars,
                                            "gpt-image-2","fake",fake,[0])
    assert len(observed)==1

def test_not_allowed_to_apply_gamer_fix_to_anime_or_kids(tmp_path):
    row,scene,chars=sample()
    row={**row,"channel":"en"}
    with pytest.raises(fix.GamerEditBlocked):
        fix.compact_scene_prompt(row,scene,chars,fallback=True)
    with pytest.raises(fix.GamerEditBlocked):
        fix.edit_with_bounded_http400_repair(anchor(tmp_path),row,scene,chars,
                                            "gpt-image-1.5","fake",lambda *a,**k:b"",[6])

def test_source_guard_never_uploads_public_or_deletes_old():
    code=(ROOT/"scripts"/"nine_visual_replacements_v2_upload_20261108.py").read_text()
    assert 'HTTP400_WORKFLOW="AutoEditorVideo - Gamer V2 fix HTTP400 and private upload"' in code
    assert 'and _gamer_fix_launch()' in code
    assert '33 if channel=="games"' in code
    assert '"privacyStatus"!="private"' in code
    assert "videos().delete(" not in code
    assert "videos().update(" not in code
