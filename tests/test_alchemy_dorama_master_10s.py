"""Offline tests for Alchemy's one-master/transparent-layer 10s workflow."""
from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
import types

import pytest
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/alchemy_dorama_master_10s.py"
spec=importlib.util.spec_from_file_location("alchemy_dorama_master10",SCRIPT)
assert spec and spec.loader
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def tiny_png(transparent:bool) -> bytes:
    mode="RGBA" if transparent else "RGB"
    image=Image.new(mode,pilot.SIZE,(0,0,0,0) if transparent else (74,54,65))
    if transparent:
        ImageDraw.Draw(image).ellipse((350,520,540,850),fill=(95,140,185,255))
    buffer=io.BytesIO()
    image.save(buffer,format="PNG")
    return buffer.getvalue()


def test_10_seconds_fixed_and_not_the_long_175s_workflow():
    assert pilot.FRAMES==300
    assert pilot.FPS==30
    assert pilot.MAX_CALLS==5
    assert pilot.MODEL=="gpt-image-2"
    assert set(pilot.EDIT_PROMPTS)=={"background","ren","king","elara","sword"}
    src=(ROOT/"motion-remotion/src/root.tsx").read_text(encoding="utf-8")
    assert 'id="AlchemyDoramaMaster10s"' in src
    assert "durationInFrames={300}" in src
    assert 'id="AlchemyDoramaOriginal"' in src
    assert "FofinhosEP01Canonico" in src


def bind_original_reference(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,"ROOT",tmp_path)
    monkeypatch.setattr(pilot,"PROJECT",tmp_path/"test10")
    ref=tmp_path/"approved.png"
    ref_image=Image.new("RGB",(941,1672),(80,68,88))
    ref_image.save(ref)
    monkeypatch.setattr(pilot,"REFERENCE_PATH",ref)
    monkeypatch.setattr(pilot,"REFERENCE_SHA256",pilot.sha_file(ref))
    return ref


def test_creator_approved_master_and_five_edits_only_from_same_png(tmp_path,monkeypatch):
    original=bind_original_reference(tmp_path,monkeypatch)
    called=[]
    def fake(secret,prompt,master,transparent):
        assert secret=="test-key-of-sufficient-length"
        assert master is not None, "Text-to-image is now prohibited"
        assert master.name=="master.png"
        assert master.is_file()
        called.append((master,transparent,prompt))
        return tiny_png(transparent)
    monkeypatch.setattr(pilot,"call_image",fake)
    monkeypatch.setenv("PROXY_API_KEY","test-key-of-sufficient-length")
    manifest=pilot.ensure_images(reuse=False)
    assert len(called)==5
    assert all(call[0]==pilot.PROJECT/"master.png" for call in called)
    assert [x[1] for x in called]==[False,True,True,True,True]
    assert manifest["image_calls_this_run"]==5
    assert manifest["source_strategy"]=="CREATOR_APPROVED_PINNED_IMAGE_THEN_SAME_SOURCE_EDITS"
    assert manifest["original_sha256"]==pilot.sha_file(original)
    assert manifest["visual_review"]=="PENDING"
    assert manifest["publication"]=="DISABLED"
    master_hash=manifest["master_sha256"]
    for label,entry in manifest["assets"].items():
        assert (pilot.PROJECT/(label+".png")).is_file()
        assert len(entry["sha256"])==64
        if label!="master":
            assert entry["master_sha256"]==master_hash
            assert entry["source"]=="images/edits"
            assert entry["approved"] is False
    def forbidden(*args):
        raise AssertionError("Unexpected image API call")
    monkeypatch.setattr(pilot,"call_image",forbidden)
    second=pilot.ensure_images(reuse=True)
    assert second["image_calls_this_run"]==0
    assert second["master_sha256"]==master_hash
    assert second["original_sha256"]==pilot.sha_file(original)


def test_reference_not_found_or_wrong_hash_blocks_before_generation(tmp_path,monkeypatch):
    monkeypatch.setattr(pilot,"ROOT",tmp_path)
    monkeypatch.setattr(pilot,"PROJECT",tmp_path/"test10")
    monkeypatch.setattr(pilot,"REFERENCE_PATH",tmp_path/"missing-source.png")
    with pytest.raises(pilot.StageError,match="APPROVED_REFERENCE_NOT_ON_GITHUB"):
        pilot.ensure_images(reuse=False)
    real=bind_original_reference(tmp_path,monkeypatch)
    monkeypatch.setattr(pilot,"REFERENCE_SHA256","0"*64)
    with pytest.raises(pilot.StageError,match="REFERENCE_SHA256_MISMATCH"):
        pilot.ensure_images(reuse=False)


def test_budget_and_model_fail_closed():
    with pytest.raises(pilot.StageError):
        pilot.approved_budget(False,"0","gpt-image-2")
    with pytest.raises(pilot.StageError):
        pilot.approved_budget(False,"5","gpt-image-1.5")
    with pytest.raises(pilot.StageError):
        pilot.approved_budget(True,"5","gpt-image-2")
    pilot.approved_budget(False,"5","gpt-image-2")
    pilot.approved_budget(True,"0","")


def test_wrong_size_alpha_or_corrupt_png_blocked():
    with pytest.raises(pilot.StageError,match="ren_NOT_RGBA"):
        pilot.validate_png(tiny_png(False),True,"ren")
    with pytest.raises(pilot.StageError,match="background_WRONG_CANVAS"):
        buffer=io.BytesIO()
        Image.new("RGB",(512,512)).save(buffer,"PNG")
        pilot.validate_png(buffer.getvalue(),False,"background")
    with pytest.raises(pilot.StageError,match="INVALID_PNG"):
        pilot.validate_png(b"not a valid png",False,"master")


def test_script_contains_no_youtube_calls_and_labels_visual_review():
    s=SCRIPT.read_text(encoding="utf-8")
    assert "youtube.upload" not in s
    assert "videos().insert" not in s
    assert "requests.post" in s and 'method = "edits"' in s
    assert 'payload["images"]' in s
    assert "master_sha256" in s
    assert "RENDERED_UNREVIEWED" in s
    assert '"visual_review_required": True' in s
    assert "ffprobe" in s
    assert "REFERENCE_SHA256" in s
    assert "prepare_pinned_master" in s
    assert "10" in s


def test_source_alignment_is_not_replaced_by_camera_only_movement():
    jsx=(ROOT/"motion-remotion/src/alchemy-dorama-master-10s.tsx").read_text()
    assert "FullSourceCanvas source={p.ren}" in jsx
    assert "FullSourceCanvas source={p.king}" in jsx
    assert "FullSourceCanvas source={p.elara}" in jsx
    assert "FullSourceCanvas source={p.sword}" in jsx
    assert "origin=" in jsx
    assert "objectFit:'cover'" in jsx
    assert "SystemUI" in jsx
