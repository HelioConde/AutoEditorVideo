"""Offline tests for safe no-upload YouTube OAuth setup."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import autorizar_youtube_canais as auth

CHANNEL_ID = "UC" + "a" * 22


def test_channels_have_isolated_token_files(tmp_path):
    assert auth.token_path("br", tmp_path).name == "youtube-token.json"
    assert auth.token_path("en", tmp_path).name == "youtube-en-token.json"
    assert auth.token_path("kids", tmp_path).name == "youtube-kids-token.json"
    with pytest.raises(ValueError):
        auth.token_path("unknown", tmp_path)


def test_channel_mismatch_does_not_approve_authorization():
    valid = [{"id": CHANNEL_ID, "snippet": {"title": "Teste"}}]
    assert auth.validate_channel(valid, CHANNEL_ID) == "Teste"
    with pytest.raises(ValueError, match="nao corresponde"):
        auth.validate_channel(valid, "UC" + "b" * 22)
    with pytest.raises(ValueError, match="invalido"):
        auth.validate_channel(valid, "some-text")


def test_client_must_be_a_real_desktop_format(tmp_path):
    path = tmp_path / "client.json"
    path.write_text(json.dumps({"web": {"client_id": "x", "client_secret": "y"}}))
    with pytest.raises(ValueError):
        auth.validate_client(path)
    path.write_text(json.dumps({"installed": {"client_id": "x", "client_secret": "y"}}))
    auth.validate_client(path)


def test_existing_token_never_overwritten_without_explicit_renewal(tmp_path):
    path = tmp_path / ".secrets" / "youtube-token.json"
    auth.save_token(path, '{"refresh_token":"unit-test-one"}', replace=False)
    with pytest.raises(FileExistsError):
        auth.save_token(path, '{"refresh_token":"unit-test-two"}', replace=False)
    assert "unit-test-one" in path.read_text()
    auth.save_token(path, '{"refresh_token":"unit-test-two"}', replace=True)
    assert "unit-test-two" in path.read_text()
    backup = path.parent / "historico-oauth" / "youtube-token-anterior.json"
    assert "unit-test-one" in backup.read_text()
    with pytest.raises(FileExistsError):
        auth.save_token(path, '{"refresh_token":"unit-test-three"}', replace=True)


def test_existing_token_no_browser_needed(tmp_path, capsys):
    p = tmp_path / ".secrets"
    p.mkdir()
    (p / "youtube-oauth-client.json").write_text(json.dumps(
        {"installed": {"client_id": "test-client", "client_secret": "test-secret"}}
    ))
    (p / "youtube-token.json").write_text('{"refresh_token":"test"}')
    result = auth.authorize("br", CHANNEL_ID, root=tmp_path)
    assert result["status"] == "ja_existe"
    assert "refresh_token" not in capsys.readouterr().out
