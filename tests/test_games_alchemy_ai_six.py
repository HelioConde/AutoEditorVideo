"""Offline safety and editorial coverage for AI-illustrated six-video pilot."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import games_alchemy_ai_six as renderer
import games_alchemy_ai_upload as uploader

def test_six_jobs_are_all_reserved_and_ai_only():
    job = renderer.load_manifest()
    assert len(job["batch"]) == 6
    assert sum(len(j["scenes"]) for j in job["batch"]) == 30
    assert all(j["ai_illustrations_only"] is True for j in job["batch"])
    assert all(j["footage_required"] is False for j in job["batch"])
    assert all(j["qa"]["youtube_uploaded"] is False for j in job["batch"])
    assert [j["channel"] for j in job["batch"]] == ["games"]*3+["alchemy"]*3

def test_two_channels_have_different_canonical_ids_and_tokens():
    from youtube_channel_registry import get_channel
    a,b = get_channel("games"),get_channel("alchemy")
    assert a["youtube_channel_id"] != b["youtube_channel_id"]
    assert a["oauth_token_secret_name"] == "YOUTUBE_GAMES_TOKEN_JSON"
    assert b["oauth_token_secret_name"] == "YOUTUBE_ALCHEMY_TOKEN_JSON"
    assert a["youtube_environment"] == b["youtube_environment"] == "youtube-private-upload"

def test_model_budget_and_no_image_generation_without_environment(monkeypatch):
    for k in ("GITHUB_REPOSITORY","GITHUB_REF","GITHUB_EVENT_NAME","GITHUB_RUN_ATTEMPT",
              "IMAGE_MODEL","MAX_IMAGE_CALLS","PROXY_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(renderer.PilotError, match="WRONG_REPOSITORY"):
        renderer.environment_guard()
    monkeypatch.setenv("GITHUB_REPOSITORY","HelioConde/AutoEditorVideo")
    monkeypatch.setenv("GITHUB_REF","refs/heads/main")
    monkeypatch.setenv("GITHUB_EVENT_NAME","push")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT","1")
    monkeypatch.setenv("IMAGE_MODEL","gpt-image-2")
    monkeypatch.setenv("MAX_IMAGE_CALLS","31")
    monkeypatch.setenv("PROXY_API_KEY","x"*24)
    with pytest.raises(renderer.PilotError, match="IMAGE_BUDGET_NOT_30"):
        renderer.environment_guard()

def test_upload_requires_approval_secrets_and_render_artifact():
    from youtube_channel_registry import get_channel
    env={"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo","GITHUB_REF":"refs/heads/main",
         "GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"1",
         "AI_SIX_PILOT_USER_APPROVED":"false","YOUTUBE_CLIENT_JSON":"dummy",
         "YOUTUBE_CHANNEL_TOKEN_JSON":"dummy",
         "GITHUB_WORKFLOW":"Gamer + Alchemy - private upload from completed AI render",
         "AI_SIX_PILOT_ORIGINAL_RUN_ID":"42044136670",
         "AI_SIX_PILOT_ORIGINAL_SHA":"a414b9aea8d778f27c765cfb3d45e94612d0ee05"}
    # Preserve prior workflow and exact-source provenance gates; the
    # approval test must exercise approval, not a missing unrelated field.
    rejected=dict(env,GITHUB_WORKFLOW="untrusted")
    with pytest.raises(uploader.UploadBlocked,match="UNEXPECTED_UPLOAD_WORKFLOW"):
        uploader.preflight("games",rejected)
    with pytest.raises(uploader.UploadBlocked,match="EXPLICIT_PILOT_APPROVAL_REQUIRED"):
        uploader.preflight("games",env)
    env["AI_SIX_PILOT_USER_APPROVED"]="true"
    env.pop("YOUTUBE_CLIENT_JSON")
    with pytest.raises(uploader.UploadBlocked,match="GITHUB_YOUTUBE_SECRETS_NOT_CONFIGURED"):
        uploader.preflight("alchemy",env)

def test_no_fake_gameplay_or_experiment_claims_in_first_six():
    m=renderer.load_manifest()
    for job in m["batch"]:
        text=job["title_draft"].lower()
        assert "testei" not in text
        assert "joguei" not in text
        assert "consegui" not in text
        assert job["description_draft"].find("🎨") >= 0
        for scene in job["scenes"]:
            prompt=scene["prompt_en"].lower()
            assert "no fake in-game hud" in prompt
            assert "no photoreal screenshot" in prompt
