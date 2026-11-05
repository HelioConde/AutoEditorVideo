"""Offline security tests. No Secrets, no proxy, no YouTube, no generation."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import otaku_br_cloud_short as cloud


def good_env():
    return {
        "GITHUB_REPOSITORY": "HelioConde/AutoEditorVideo",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_EVENT_NAME": "push",
        "IMAGE_MODEL": "gpt-image-2",
        "PROXY_API_KEY": "only-a-synthetic-example-do-not-use",
    }


def test_authorized_single_br_episode_with_21_calls():
    cloud.validate_job_environment(good_env(), cloud.EPISODE, 21)


@pytest.mark.parametrize("changes,code", [
    ({"GITHUB_REPOSITORY": "other/repo"}, "WRONG_GITHUB_REPOSITORY"),
    ({"GITHUB_REF": "refs/heads/pr-1"}, "MAIN_ONLY"),
    ({"GITHUB_RUN_ATTEMPT": "2"}, "RERUN_NOT_AUTHORIZED"),
    ({"GITHUB_EVENT_NAME": "pull_request"}, "UNAUTHORIZED_EVENT"),
    ({"GITHUB_EVENT_NAME": "schedule"}, "UNAUTHORIZED_EVENT"),
    ({"IMAGE_MODEL": "gpt-image-1.5"}, "UNEXPECTED_IMAGE_MODEL"),
    ({"PROXY_API_KEY": ""}, "PROXY_SECRET_NOT_SET"),
])
def test_fails_closed_for_unsafe_action_environment(changes, code):
    env = good_env() | changes
    with pytest.raises(cloud.CloudBRBlocked, match=code):
        cloud.validate_job_environment(env, cloud.EPISODE, 21)


@pytest.mark.parametrize("budget", [-1, 22, 180, 999])
def test_unapproved_budget_never_triggers_generation(budget):
    with pytest.raises(cloud.CloudBRBlocked, match="IMAGE_BUDGET_EXCEEDS_21"):
        cloud.validate_job_environment(good_env(), cloud.EPISODE, budget)


def test_wrong_episode_never_generates():
    with pytest.raises(cloud.CloudBRBlocked, match="EPISODE_NOT_AUTHORIZED"):
        cloud.validate_job_environment(good_env(), "5001-black-clover", 21)


def test_zero_budget_is_safe_for_cached_render():
    env = good_env()
    env["PROXY_API_KEY"] = ""
    cloud.validate_job_environment(env, cloud.EPISODE, 0)


def test_review_fails_closed_without_complete_autoeditorvideo_output(tmp_path):
    with pytest.raises(cloud.CloudBRBlocked, match="MISSING_VIDEO"):
        cloud.prepare_review(tmp_path, cloud.EPISODE, tmp_path / "review")


def test_review_never_uploads_raw_scene_cache():
    src = Path(__file__).resolve().parents[1] / "scripts" / "otaku_br_cloud_short.py"
    text = src.read_text(encoding="utf-8")
    assert "fluxo_unico_short.py" in text
    assert "renderizar_master_remotion.py" in text
    assert '"--publicar"' not in text
    assert '"--tentativas", "1"' in text
    assert '"master-raw.png"' not in text
    assert '"accounts.json"' not in text
