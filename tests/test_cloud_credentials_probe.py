"""No-network tests for GitHub Actions credential validation."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cloud_credentials_probe as p


def test_refresh_token_and_client_match():
    client = {"installed": {"client_id": "test-client", "client_secret": "fake-secret"}}
    token = {"client_id": "test-client", "client_secret": "fake-secret", "refresh_token": "fake-token"}
    p.verify_client_match(client, token)
    token["client_secret"] = "other"
    with pytest.raises(ValueError, match="MISMATCH"):
        p.verify_client_match(client, token)


def test_upload_scope_alone_is_not_read_only():
    assert not p.has_read_scope({"scopes": ["https://www.googleapis.com/auth/youtube.upload"]})
    assert p.has_read_scope({"scopes": ["https://www.googleapis.com/auth/youtube.readonly"]})


def test_wrong_channel_is_detected():
    assert p.check_channel_id([{"id": p.EXPECTED_EN_CHANNEL}], p.EXPECTED_EN_CHANNEL)
    assert not p.check_channel_id([{"id": "UC" + "a" * 22}], p.EXPECTED_EN_CHANNEL)
    assert not p.check_channel_id([], p.EXPECTED_EN_CHANNEL)


def test_invalid_json_raises_sanitized_code_only():
    with pytest.raises(ValueError, match="INVALID_JSON") as e:
        p.parse_secret("YT", '{"invalid":"')
    assert '{"invalid":"' not in str(e.value)


def test_missing_secrets_cannot_authenticate(monkeypatch, capsys):
    monkeypatch.delenv("YOUTUBE_OAUTH_CLIENT_JSON", raising=False)
    assert p.run() == 1
    output = capsys.readouterr().out
    assert "[AUTH] CLIENT:MISSING" in output
    assert "NO_UPLOAD" not in output
