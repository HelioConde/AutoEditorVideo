"""Zero-cost regression tests for canonical named anime characters and reference edits."""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import types

from PIL import Image
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import otaku_br_character_v2_20261108 as v2
import otaku_br_three_public_20261107 as legacy
from otaku_character_identity_policy import (
    IdentityBlocked,load_policy,verify_manifest_identity,anchor_prompt,edit_prompt
)

def test_policy_cannot_be_silently_weakened():
    p=load_policy()
    assert p["lock"]=="requires_explicit_new_creator_authorization_to_change"
    assert p["scope_channels"]==["br","en"]
    assert p["required_rules"]["scene_generation_requires_anchor_image_edit"]
    assert p["required_rules"]["never_change_policy_without_explicit_owner_instruction"]
    agents=(ROOT/"AGENTS.md").read_text(encoding="utf-8")
    assert "REGRA PRIORITÁRIA E PERMANENTE" in agents
    assert "config/otaku-character-identity-policy.json" in agents

def test_exact_new_reserved_v2_episodes_and_reference_budget():
    rows=v2.validate()
    assert tuple(r["id"] for r in rows)==v2.IDS
    assert sum(8+len(r["character_identity_bible"]) for r in rows)==28
    for r in rows:
        characters=verify_manifest_identity(r)
        assert len(r["scenes"])==8
        assert all(s["character_keys"] for s in r["scenes"])
        assert all("identity" in anchor_prompt(c,r["visual_bible"]).lower() for c in characters)
        assert all("reference" in edit_prompt(r,s,characters).lower() for s in r["scenes"])
        assert "generic athlete" not in r["visual_bible"].lower()
        assert "not copied exactly" not in r["visual_bible"].lower()

def test_previous_unanchored_br_workflow_is_permanently_blocked():
    with pytest.raises(legacy.BRBlocked):
        legacy.art_prompt({}, {})
    with pytest.raises(legacy.BRBlocked):
        legacy.create_art({},Path("/dev/null"),"")

def test_canonical_v2_generates_anchor_then_edits_no_independent_frames(tmp_path,monkeypatch):
    calls={"anchors":[],"edits":[]}
    def png(color):
        im=Image.effect_noise((1024,1536),25).convert("RGB")
        im=Image.blend(im,Image.new("RGB",(1024,1536),color),0.5)
        buf=io.BytesIO()
        im.save(buf,format="PNG")
        return buf.getvalue()
    def fake_image(prompt,model,key,size):
        calls["anchors"].append(prompt)
        assert model=="gpt-image-2" and size=="1024x1536"
        return png((25,80+10*len(calls["anchors"]),110))
    def fake_edit(master,prompt,model,key,*,transparent):
        calls["edits"].append((master,prompt))
        assert "reference" in prompt.lower()
        assert model=="gpt-image-2" and transparent is False
        return png((110+len(calls["edits"]),60,170))
    monkeypatch.setitem(sys.modules,"gerar_video_codex",
                        types.SimpleNamespace(request_image=fake_image))
    monkeypatch.setitem(sys.modules,"master_scenes",
                        types.SimpleNamespace(request_edit=fake_edit))
    row=v2.validate()[0]
    folder=tmp_path/row["id"]
    folder.mkdir()
    images,state=v2.generate_anchored_art(row,folder,"FAKE_NEVER_NETWORK")
    assert len(calls["anchors"])==2
    assert len(calls["edits"])==8
    assert len(images)==8
    assert state["scene_edit_generations"]==8
    assert state["independent_text_to_image_scene_generations"]==0
    assert state["editorial_visual_review_status"]=="pending"
    assert state["publication_allowed"] is False
    assert len(state["anchors_sha256"])==2
    assert len(state["scenes"])==8
    assert all(s["generation_endpoint"]=="images/edits" for s in state["scenes"])

def test_missing_or_generic_identity_is_fail_closed():
    row={**v2.validate()[1]}
    row["scenes"]=[dict(s) for s in row["scenes"]]
    row["scenes"][0]["visual_instruction"]="generic athlete in blue football stadium, totally different face"
    with pytest.raises(IdentityBlocked):
        verify_manifest_identity(row)

def test_artistic_approval_not_falsely_claimed_in_render_source():
    text=(ROOT/"scripts"/"otaku_br_character_v2_20261108.py").read_text()
    assert '"editorial_visual_review_status":"pending"' in text
    assert '"publication_allowed":False' in text
    assert "request_edit(composite" in text
    assert "request_image(anchor_prompt" in text
    assert "videos().insert(" not in text
    assert "videos().delete(" not in text
