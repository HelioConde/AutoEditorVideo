"""Validated image proxy endpoint configuration.

Local by default; HTTPS required for remote endpoints. Never logs URLs or
credentials. Configured remote proxies must be approved and operated separately.
"""
from __future__ import annotations

import ipaddress
import os
from urllib.parse import urlsplit

LOCAL_DEFAULT = "http://127.0.0.1:8080"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def proxy_base_url(env: dict[str, str] | None = None) -> str:
    """Return a validated base URL without the optional /v1 path."""
    env = os.environ if env is None else env
    raw = env.get("PROXY_BASE_URL", "").strip() or LOCAL_DEFAULT
    if any(ord(ch) <= 32 or ord(ch) == 127 for ch in raw):
        raise ValueError("PROXY_BASE_URL contem caracteres invalidos")
    try:
        u = urlsplit(raw)
        hostname = u.hostname
        port = u.port
    except ValueError:
        raise ValueError("PROXY_BASE_URL invalido") from None
    if not hostname or not u.netloc or u.username or u.password:
        raise ValueError("PROXY_BASE_URL invalido (sem usuario ou senha embutidos)")
    if u.query or u.fragment or u.path.rstrip("/") not in ("", "/v1"):
        raise ValueError("PROXY_BASE_URL deve ser a raiz do servico ou /v1")
    host = hostname.lower()
    local = host in LOCAL_HOSTS
    if u.scheme not in ("http", "https"):
        raise ValueError("PROXY_BASE_URL exige HTTPS remoto ou localhost HTTP")
    if not local:
        if u.scheme != "https":
            raise ValueError("Proxy remoto deve usar HTTPS")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("Proxy remoto deve usar dominio HTTPS, nao IP literal")
        if "." not in host or host.endswith(".localhost") or host.endswith(".local"):
            raise ValueError("Dominio remoto nao autorizado")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Porta de proxy invalida")
    formatted_host = f"[{host}]" if ":" in host else host
    authority = formatted_host + (f":{port}" if port is not None else "")
    return f"{u.scheme}://{authority}"


def proxy_api_url(path: str, env: dict[str, str] | None = None) -> str:
    if path not in ("/v1/images/edits", "/v1/images/generations",
                    "/health/live", "/admin/accounts"):
        raise ValueError("Caminho nao permitido no proxy")
    return proxy_base_url(env) + path
