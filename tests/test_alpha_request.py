"""A API suporta pedir alpha; o proxy pode recusar. Nunca faz requisicao real."""
import base64
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from gerar_video_codex import request_image


def test_default_request_keeps_legacy_payload(monkeypatch):
    observed=[]
    content=base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"fake").decode()
    def fake_post(url,**kwargs):
        observed.append(kwargs["json"])
        return SimpleNamespace(ok=True,json=lambda:{"data":[{"b64_json":content}]})
    monkeypatch.setitem(sys.modules,"requests",SimpleNamespace(post=fake_post))
    assert request_image("demo","gpt-image-1.5","fake-key")==base64.b64decode(content)
    assert "background" not in observed[0]


def test_request_transparent_png(monkeypatch):
    observed=[]
    def fake_post(url,**kwargs):
        observed.append(kwargs["json"])
        return SimpleNamespace(ok=True,json=lambda:{"data":[{"b64_json":base64.b64encode(b"png").decode()}]})
    monkeypatch.setitem(sys.modules,"requests",SimpleNamespace(post=fake_post))
    request_image("isolated subject","gpt-image-2","fake",background="transparent")
    assert observed[0]["background"]=="transparent"
    assert observed[0]["output_format"]=="png"


def test_rejects_invalid_background_without_api(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError("should not call proxy")
    monkeypatch.setitem(sys.modules,"requests",SimpleNamespace(post=forbidden))
    with pytest.raises(ValueError):
        request_image("x","gpt-image-2","key",background="greenscreen")


def test_proxy_rejection_is_explicit(monkeypatch):
    def fake_post(*args,**kwargs):
        return SimpleNamespace(ok=False,status_code=400,text="unsupported parameter")
    monkeypatch.setitem(sys.modules,"requests",SimpleNamespace(post=fake_post))
    with pytest.raises(RuntimeError,match="Sem fallback verde"):
        request_image("subject","gpt-image-1.5","key",background="transparent")
