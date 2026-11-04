"""Offline tests: GitHub secrets never leak and cannot trigger uploads."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import github_actions_secrets as secrets

CLIENT = json.dumps({"installed": {
    "client_id": "example.invalid.apps.googleusercontent.com",
    "client_secret": "unit-test-not-a-real-secret",
}})
TOKEN = json.dumps({
    "client_id": "example.invalid.apps.googleusercontent.com",
    "client_secret": "unit-test-not-a-real-secret",
    "refresh_token": "unit-test-not-a-real-refresh-token",
})


def env():
    return {
        "PROXY_API_KEY": "unit-test-proxy-key-only",
        "YOUTUBE_OAUTH_CLIENT_JSON": CLIENT,
        "YOUTUBE_BR_TOKEN_JSON": TOKEN,
        "YOUTUBE_EN_TOKEN_JSON": TOKEN,
    }


def test_presence_check_never_prints_secret_values(capsys):
    values = env()
    assert secrets.check(values)
    stdout = capsys.readouterr().out
    assert "[OK] PROXY_API_KEY" in stdout
    assert "[PENDENTE] YOUTUBE_KIDS_TOKEN_JSON" in stdout
    for value in values.values():
        assert value not in stdout
    assert "unit-test" not in stdout


def test_missing_and_invalid_required_secret_fails_without_reveal(capsys):
    values = env()
    values["YOUTUBE_EN_TOKEN_JSON"] = "{bad-secret-contents"
    assert not secrets.check(values)
    stdout = capsys.readouterr().out
    assert "[INVALIDO] YOUTUBE_EN_TOKEN_JSON" in stdout
    assert "{bad-secret-contents" not in stdout
    del values["PROXY_API_KEY"]
    assert not secrets.check(values)


def test_stage_one_channel_and_refuse_overwrite(tmp_path):
    client, token = secrets.stage_youtube("en", tmp_path, env())
    assert client.relative_to(tmp_path).as_posix() == ".secrets/youtube-oauth-client.json"
    assert token.relative_to(tmp_path).as_posix() == ".secrets/youtube-en-token.json"
    assert client.read_text() == CLIENT
    assert token.read_text() == TOKEN
    with pytest.raises(FileExistsError):
        secrets.stage_youtube("en", tmp_path, env())
    assert token.read_text() == TOKEN


def test_no_staging_without_valid_token(tmp_path):
    values = env()
    values["YOUTUBE_BR_TOKEN_JSON"] = "not-json"
    with pytest.raises(ValueError):
        secrets.stage_youtube("br", tmp_path, values)
    assert not (tmp_path / ".secrets").exists()


def test_channel_isolation(tmp_path):
    values = env()
    with pytest.raises(ValueError):
        secrets.stage_youtube("kids", tmp_path, values)
    assert not list(tmp_path.rglob("*.json"))
