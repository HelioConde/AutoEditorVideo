"""Offline-only tests: one-call image test, safe logs, and in-memory PNG QA."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
import sys
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import fofinhos_one_image_cloud_probe as probe


def image_response(format="b64"):
    pic = Image.new("RGB", (1024, 1024), color=(180, 230, 255))
    buf = io.BytesIO()
    pic.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode()
    return json.dumps({"data": [{"b64_json": encoded}] if format=="b64" else
                               [{"url": "data:image/png;base64,"+encoded}]}).encode()


class FakeResponse:
    def __init__(self, value, status=200):
        self.value, self.status = value, status
    def read(self, n):
        return self.value[:n]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def test_one_valid_png_in_memory():
    assert probe.decode_image_response(image_response()) == (1024, 1024)
    assert probe.decode_image_response(image_response("url")) == (1024, 1024)


def test_one_http_post_no_retry_no_fallback():
    calls = []
    key = "synthetic-test-api-key-123456"
    def opener(req, timeout):
        calls.append((req, timeout))
        return FakeResponse(image_response())
    assert probe.request_single_image(key, opener=opener) == (1024, 1024)
    assert len(calls) == 1
    req, timeout = calls[0]
    assert req.full_url == "http://127.0.0.1:8080/v1/images/generations"
    assert req.get_method() == "POST"
    assert req.get_header("Authorization") == "Bearer " + key
    body = json.loads(req.data)
    assert body["model"] == "gpt-image-2"
    assert body["n"] == 1
    assert body["size"] == "1024x1024"
    assert body["background"] == "opaque"
    assert "Emanuelly" not in body["prompt"]
    assert "no people" in body["prompt"]


@pytest.mark.parametrize("bad", [
    b"{}",
    b"{unclosed",
    b'{"data":[]}',
    b'{"data":[{"url":"https://not-allowed.example/image.png"}]}',
    b'{"data":[{"b64_json":"not valid b64 !!!"}]}',
    json.dumps({"data":[{"b64_json":base64.b64encode(b"not-a-png").decode()}]}).encode(),
])
def test_malformed_or_remote_results_rejected_without_unsafe_fallback(bad):
    with pytest.raises(probe.ImageProbeError):
        probe.decode_image_response(bad)


def test_zero_budget_rejects_before_any_account_check(capsys):
    def forbidden(_):
        raise AssertionError("Should not call proxy")
    assert probe.run({"MAX_IMAGE_CALLS":"0","IMAGE_MODEL":"gpt-image-2"},
                     readiness=forbidden,generate=forbidden) == 1
    assert "BUDGET_NOT_EXACTLY_ONE" in capsys.readouterr().out


def test_wrong_model_rejects_before_any_account_check(capsys):
    assert probe.run({"MAX_IMAGE_CALLS":"1","IMAGE_MODEL":"gpt-image-1.5"},
                     readiness=lambda _: (_ for _ in ()).throw(AssertionError())) == 1
    assert "MODEL_NOT_APPROVED" in capsys.readouterr().out


def test_one_call_after_eligible_cache_and_no_secret_logging(capsys):
    checks, calls = [], []
    key = "synthetic-test-key-this-is-not-real"
    def ready(k):
        checks.append(k)
        return "ACCOUNT_RECORDS_LOADED_CACHED_ELIGIBLE"
    def generate(k):
        calls.append(k)
        return (1024, 1024)
    assert probe.run({"MAX_IMAGE_CALLS":"1","IMAGE_MODEL":"gpt-image-2","PROXY_API_KEY":key},
                     readiness=ready, generate=generate) == 0
    assert checks == [key] and calls == [key]
    out = capsys.readouterr().out
    assert "REAL_IMAGE_VALIDATED_PNG_1024x1024" in out
    assert key not in out


def test_ineligible_account_never_calls_image_generation():
    generated = []
    assert probe.run({"MAX_IMAGE_CALLS":"1","IMAGE_MODEL":"gpt-image-2",
                      "PROXY_API_KEY":"synthetic-key-1234567"},
                     readiness=lambda _: "ACCOUNT_RECORDS_LOADED_BUT_NOT_CACHED_ELIGIBLE",
                     generate=lambda _: generated.append(True)) == 1
    assert generated == []


def test_provider_errors_never_print_sensitive_body(capsys):
    key = "private-1234567890"
    def fake_req(k):
        raise RuntimeError(f"Sensitive secret {k}")
    assert probe.run({"MAX_IMAGE_CALLS":"1","IMAGE_MODEL":"gpt-image-2",
                      "PROXY_API_KEY":key},
                     readiness=lambda _: "ACCOUNT_RECORDS_LOADED_CACHED_ELIGIBLE",
                     generate=fake_req) == 1
    out = capsys.readouterr().out
    assert key not in out
    assert "Sensitive" not in out
    assert "UNKNOWN_FAILURE" in out
