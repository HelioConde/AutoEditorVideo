"""Proxy preflight is read-only, preserves cached Shorts and reuses old kit credentials."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fluxo_unico_short as flow
import gerar_video_codex as video_codex
import estado_codex_proxy as codex_status


def test_missing_proxy_fails_fast_before_image_requests():
    with pytest.raises(flow.PipelineError, match="offline") as failure:
        flow.assert_image_provider_ready(
            status_fn=lambda: {"state": "offline", "eligible": 0}
        )
    assert "Docker" in str(failure.value)
    assert "Nenhuma chamada" in str(failure.value)


def test_no_eligible_account_is_never_bypassed():
    with pytest.raises(flow.PipelineError, match="sem_conta_elegivel") as failure:
        flow.assert_image_provider_ready(
            status_fn=lambda: {
                "state": "sem_conta_elegivel", "eligible": 0
            }
        )
    assert "nao contorne" in str(failure.value)


def test_connected_proxy_allows_generation():
    status = {"state": "conectado", "eligible": 1}
    assert flow.assert_image_provider_ready(status_fn=lambda: status) is status


def test_legacy_env_works_without_reinstalling_proxy(tmp_path, monkeypatch):
    missing = tmp_path / "new" / ".env"
    legacy = tmp_path / "arquivo-otaku-kit" / "chatgpt-codex-proxy" / ".env"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("PROXY_API_KEY=valid-legacy-test-1234567\n", encoding="utf-8")
    monkeypatch.setattr(video_codex, "PROXY_ENV", missing)
    monkeypatch.setattr(codex_status, "credentials_file", lambda root: legacy)
    assert video_codex.proxy_key(missing) == "valid-legacy-test-1234567"
    with pytest.raises(RuntimeError, match="Credenciais"):
        video_codex.proxy_key(tmp_path / "explicit" / ".env")


def test_existing_current_proxy_env_takes_precedence(tmp_path, monkeypatch):
    modern = tmp_path / "new" / ".env"
    modern.parent.mkdir()
    modern.write_text("PROXY_API_KEY=valid-current-test-123456\n", encoding="utf-8")
    monkeypatch.setattr(video_codex, "PROXY_ENV", modern)
    monkeypatch.setattr(
        codex_status, "credentials_file",
        lambda root: pytest.fail("Should not search legacy credentials when current exists"),
    )
    assert video_codex.proxy_key(modern) == "valid-current-test-123456"


def test_unconfigured_proxy_never_invents_or_logs_credentials(tmp_path, monkeypatch):
    missing = tmp_path / "missing.env"
    monkeypatch.setattr(video_codex, "PROXY_ENV", missing)
    monkeypatch.setattr(codex_status, "credentials_file", lambda root: None)
    with pytest.raises(RuntimeError, match="Credenciais Codex Proxy nao encontradas"):
        video_codex.proxy_key(missing)


def test_actions_secret_key_takes_precedence_without_printing(tmp_path, monkeypatch, capsys):
    old_env = tmp_path / "proxy.env"
    old_env.write_text("PROXY_API_KEY=valid-old-local-1234567890\n", encoding="utf-8")
    monkeypatch.setattr(video_codex, "PROXY_ENV", old_env)
    monkeypatch.setenv("PROXY_API_KEY", "valid-github-actions-secret-12345")
    assert video_codex.proxy_key(old_env) == "valid-github-actions-secret-12345"
    assert capsys.readouterr().out == ""


def test_invalid_actions_secret_never_silently_falls_back(tmp_path, monkeypatch):
    old_env = tmp_path / "proxy.env"
    old_env.write_text("PROXY_API_KEY=valid-old-local-1234567890\n", encoding="utf-8")
    monkeypatch.setattr(video_codex, "PROXY_ENV", old_env)
    monkeypatch.setenv("PROXY_API_KEY", "change-me-insecure")
    with pytest.raises(RuntimeError, match="configurada mas invalida"):
        video_codex.proxy_key(old_env)
