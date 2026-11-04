"""No-network tests for image proxy URL and preflight."""
from __future__ import annotations

from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import proxy_endpoint as endpoint
import cloud_proxy_preflight as preflight
import master_scenes as master
import gerar_video_codex as video


def test_local_default_unchanged():
    assert endpoint.proxy_base_url({}) == "http://127.0.0.1:8080"
    assert endpoint.proxy_api_url("/v1/images/edits", {}) == master.EDIT_URL
    assert endpoint.proxy_api_url("/v1/images/generations", {}) == "http://127.0.0.1:8080/v1/images/generations"


def test_https_remote_accepts_optional_v1_suffix():
    assert endpoint.proxy_api_url("/v1/images/edits", {"PROXY_BASE_URL": "https://images.example.com/v1"}) == "https://images.example.com/v1/images/edits"
    assert endpoint.proxy_base_url({"PROXY_BASE_URL": "https://images.example.com/"}) == "https://images.example.com"


@pytest.mark.parametrize("url", [
    "http://images.example.com", "http://10.1.2.3:8080",
    "https://127.0.0.1.example.local", "https://10.1.2.3",
    "https://images.example.com@localhost:8080", "https://user:password@images.example.com",
    "ftp://images.example.com", "https://images.example.com/evil",
    "https://images.example.com/?token=bad", "https://images.example.com/#foo",
    "https://images.example.com\nAuthorization: x",
    "https://images.example.com:99999",
])
def test_insecure_remote_address_rejected(url):
    with pytest.raises(ValueError):
        endpoint.proxy_base_url({"PROXY_BASE_URL": url})


def test_missing_remote_and_key_reported():
    assert preflight.check({"PROXY_API_KEY": "unit-test-key-1234567", "GITHUB_ACTIONS": "true"}) == "REMOTE_ENDPOINT_NOT_CONFIGURED"
    assert preflight.check({"PROXY_BASE_URL": "https://images.example.com", "GITHUB_ACTIONS": "true"}) == "KEY_MISSING_OR_INVALID"


class Reply:
    def __init__(self, content=b"{}", status=200):
        self.content, self.status = content, status
    def read(self, n=-1):
        return self.content[:n]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def test_read_only_health_and_account_probe_never_exposes_secret(capsys):
    calls = []
    key = "unit-test-key-123456789"
    def fake(req, timeout):
        calls.append((req.full_url, req.get_header("Authorization")))
        if req.full_url.endswith("/health/live"):
            return Reply()
        if req.full_url.endswith("/admin/accounts"):
            return Reply(b'{"accounts":[{"eligible_now":true}]}')
        raise AssertionError("Unexpected request")
    env = {"PROXY_BASE_URL": "https://images.example.com", "PROXY_API_KEY": key, "GITHUB_ACTIONS": "true"}
    assert preflight.check(env, opener=fake) == "REMOTE_PROXY_READY"
    assert [x[0].split("/")[-1] for x in calls] == ["live", "accounts"]
    assert calls[0][1] is None
    assert calls[1][1] == "Bearer " + key
    assert capsys.readouterr().out == ""


def test_no_eligible_account_is_never_bypassed():
    def fake(req, timeout):
        if req.full_url.endswith("/health/live"):
            return Reply()
        return Reply(b'{"accounts":[{"eligible_now":false}]}')
    env = {"PROXY_BASE_URL": "https://images.example.com", "PROXY_API_KEY": "fake-test-key-123456789", "GITHUB_ACTIONS": "true"}
    assert preflight.check(env, opener=fake) == "NO_ELIGIBLE_ACCOUNT"


def test_hosted_runner_refuses_local_endpoint():
    env = {"PROXY_BASE_URL": "http://localhost:8080", "PROXY_API_KEY": "test-key-123456789", "GITHUB_ACTIONS": "true"}
    assert preflight.check(env) == "CLOUD_REQUIRES_HTTPS_REMOTE"


def test_real_image_call_uses_remote_only_when_explicit(monkeypatch):
    requests = pytest.importorskip("requests")
    calls = []
    class Response:
        ok = True
        def json(self):
            return {"data": [{"b64_json": "aW1hZ2U="}]}
    def fake_post(url, **kwargs):
        calls.append(url)
        return Response()
    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setenv("PROXY_BASE_URL", "https://images.example.com/v1")
    assert video.request_image("test", "gpt-image-2", "test-key-123456") == b"image"
    assert calls == ["https://images.example.com/v1/images/generations"]
