"""Security tests for a main-only GitHub Environment with temporary Go state.

Purely synthetic fixtures. Never load or store the user's real OAuth tokens.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import proxy_accounts_private_stage as state
import image_env_policy_guard as guard
import image_session_readonly_probe as probe


def fake_state():
    return json.dumps({"records": [{
        "id": "synthetic-id",
        "token": {
            "access_token": "fake-token-for-unit-test-only",
            "refresh_token": "fake-refresh-for-unit-test-only",
            "expires_at": "2099-01-01T00:00:00Z",
        },
    }], "rotation_strategy": "least_used"})


def test_json_validated_and_restored_to_mode_0600(tmp_path):
    data_dir = tmp_path / "data"
    count = state.stage_private_state(fake_state(), data_dir)
    assert count == 1
    saved = data_dir / "accounts.json"
    assert json.loads(saved.read_text())["records"][0]["id"] == "synthetic-id"
    if os.name != "nt":
        assert stat.S_IMODE(saved.stat().st_mode) == 0o600
        assert stat.S_IMODE(data_dir.stat().st_mode) == 0o700
    with pytest.raises(FileExistsError):
        state.stage_private_state(fake_state(), data_dir)


@pytest.mark.parametrize("raw,expected", [
    ("", "MISSING_SECRET"),
    ("{broken", "INVALID_JSON"),
    (json.dumps({"records": []}), "RECORDS_NOT_FOUND"),
    (json.dumps({"records": [{"token": {}}]}), "TOKEN_FIELDS_MISSING"),
    ("x" * (45 * 1024 + 1), "SECRET_TOO_LARGE"),
])
def test_bad_private_state_fails_closed(raw, expected):
    with pytest.raises(state.InvalidPrivateState, match=expected):
        state.validate_state(raw)


def test_main_only_environment_is_accepted():
    env = {"name": "image-generation",
           "deployment_branch_policy": {
               "custom_branch_policies": True,
               "protected_branches": False}}
    rule = {"branch_policies": [{"name": "main", "type": "branch"}],
            "total_count": 1}
    guard.strict_environment_policy(env, rule)


@pytest.mark.parametrize("rules", [
    {"branch_policies": [], "total_count": 0},
    {"branch_policies": [{"name": "*", "type": "branch"}], "total_count": 1},
    {"branch_policies": [{"name": "main"}, {"name": "dev"}], "total_count": 2},
    {"branch_policies": [{"name": "main"}], "total_count": 2},
    {"branch_policies": [{"name": "main", "type": "tag"}], "total_count": 1},
])
def test_policy_guard_rejects_unsafe_branches(rules):
    env = {"name": "image-generation",
           "deployment_branch_policy": {
               "custom_branch_policies": True,
               "protected_branches": False}}
    with pytest.raises(guard.InvalidEnvironment):
        guard.strict_environment_policy(env, rules)


def test_missing_custom_policy_is_not_accepted():
    env = {"name": "image-generation",
           "deployment_branch_policy": {
               "custom_branch_policies": False,
               "protected_branches": True}}
    with pytest.raises(guard.InvalidEnvironment):
        guard.strict_environment_policy(env, {
            "branch_policies": [{"name": "main"}], "total_count": 1})


def test_policy_guard_checks_only_two_fixed_read_only_urls():
    with pytest.raises(guard.InvalidEnvironment, match="UNEXPECTED_API_URL"):
        guard.fetch_json("https://attacker.example/steal")


class Response:
    status = 200
    def __init__(self, body):
        self.body = json.dumps(body).encode()
    def read(self, _limit):
        return self.body
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False


def test_policy_guard_works_with_mocked_public_github_api():
    visited = []
    def fake(req, timeout):
        visited.append(req.full_url)
        if req.full_url == guard.API_BASE:
            return Response({"name": guard.ENV_NAME, "deployment_branch_policy": {
                "protected_branches": False, "custom_branch_policies": True}})
        return Response({"branch_policies": [{"name": "main", "type": "branch"}], "total_count": 1})
    guard.check("fake-github-token", opener=fake)
    assert visited == [guard.API_BASE, guard.API_BASE + "/deployment-branch-policies?per_page=100"]


def test_readonly_session_does_not_call_image_endpoints():
    accessed = []
    def fake(req, timeout):
        accessed.append(req.full_url)
        if req.full_url.endswith("/health/live"):
            return Response({"status": "ok"})
        if req.full_url.endswith("/admin/accounts"):
            return Response({"accounts": [{"eligible_now": True}]})
        raise AssertionError("Unexpected endpoint: " + req.full_url)
    assert probe.check("synthetic-password-more-than-15", opener=fake) == (
        "ACCOUNT_RECORDS_LOADED_CACHED_ELIGIBLE")
    assert accessed == [probe.URL + "/health/live", probe.URL + "/admin/accounts"]
    assert all("/v1/images" not in url for url in accessed)


def test_readonly_no_account_is_not_claimed_successful():
    def fake(req, timeout):
        if req.full_url.endswith("/health/live"):
            return Response({"status": "ok"})
        return Response({"accounts": []})
    with pytest.raises(probe.ReadOnlyProbeError, match="NO_AUTHORIZED_ACCOUNTS"):
        probe.check("synthetic-password-more-than-15", opener=fake)
