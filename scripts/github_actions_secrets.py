"""Read GitHub Actions Secrets safely; never contact providers or print values.

The manual check only verifies structure. Optional staging creates files ignored
by Git, for a future explicitly authorized YouTube workflow. No uploads.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

PROXY_SECRET = "PROXY_API_KEY"
CLIENT_SECRET = "YOUTUBE_OAUTH_CLIENT_JSON"
CHANNEL_TOKENS = {
    "br": "YOUTUBE_BR_TOKEN_JSON",
    "en": "YOUTUBE_EN_TOKEN_JSON",
    "kids": "YOUTUBE_KIDS_TOKEN_JSON",
}
REQUIRED = (PROXY_SECRET, CLIENT_SECRET, CHANNEL_TOKENS["br"], CHANNEL_TOKENS["en"])


def _valid(name: str, value: str) -> bool:
    if not value or not value.strip():
        return False
    if name == PROXY_SECRET:
        key = value.strip()
        return len(key) >= 15 and not key.lower().startswith("change-me")
    try:
        doc = json.loads(value)
    except (ValueError, TypeError):
        return False
    if not isinstance(doc, dict):
        return False
    if name == CLIENT_SECRET:
        installed = doc.get("installed")
        return isinstance(installed, dict) and all(
            isinstance(installed.get(k), str) and installed[k].strip()
            for k in ("client_id", "client_secret")
        )
    if name in CHANNEL_TOKENS.values():
        return all(
            isinstance(doc.get(k), str) and doc[k].strip()
            for k in ("client_id", "client_secret", "refresh_token")
        )
    return False


def check(env: dict[str, str] | None = None) -> bool:
    """Print only secret NAMES and outcomes; never lengths, values or JSON."""
    env = os.environ if env is None else env
    good = True
    for name in (PROXY_SECRET, CLIENT_SECRET, *CHANNEL_TOKENS.values()):
        value = env.get(name, "")
        status = "PENDENTE" if not value.strip() else (
            "OK" if _valid(name, value) else "INVALIDO"
        )
        print(f"[{status}] {name}")
        if name in REQUIRED and status != "OK":
            good = False
        if status == "INVALIDO":
            good = False
    print("[RESULTADO] Estrutura de credenciais conferida SEM acessar proxy/YouTube.")
    return good


def _write_private(path: Path, content: str) -> None:
    """Write a new private file without allowing replacement of a symlink."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def stage_youtube(channel: str, root: Path, env: dict[str, str] | None = None) -> tuple[Path, Path]:
    """Stage one channel's OAuth files for *later*, never publish anything.

    Existing files are never overwritten. Use only in trusted, manually
    authorized workflows. The BR and EN scripts have different token names.
    """
    env = os.environ if env is None else env
    if channel not in CHANNEL_TOKENS:
        raise ValueError("Canal nao suportado")
    client, token = CLIENT_SECRET, CHANNEL_TOKENS[channel]
    if not _valid(client, env.get(client, "")) or not _valid(token, env.get(token, "")):
        raise ValueError("Credenciais OAuth ausentes ou em formato invalido")
    folder = root / ".secrets"
    path_client = folder / "youtube-oauth-client.json"
    token_name = {
        "br": "youtube-token.json",
        "en": "youtube-en-token.json",
        "kids": "youtube-kids-token.json",
    }[channel]
    path_token = folder / token_name
    if path_client.exists() or path_client.is_symlink() or path_token.exists() or path_token.is_symlink():
        raise FileExistsError("Arquivo OAuth local ja existe. Nao sobrescrever.")
    _write_private(path_client, env[client])
    try:
        _write_private(path_token, env[token])
    except BaseException:
        path_client.unlink(missing_ok=True)
        raise
    return path_client, path_token


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica Actions Secrets sem rede ou upload")
    parser.add_argument("--check", action="store_true", help="Valida apenas estrutura e presenca")
    parser.add_argument("--stage-channel", choices=tuple(CHANNEL_TOKENS),
                        help="Cria arquivos OAuth temporarios para um canal, sem upload")
    args = parser.parse_args(argv)
    if args.stage_channel:
        root = Path(__file__).resolve().parents[1]
        try:
            stage_youtube(args.stage_channel, root)
        except (ValueError, OSError) as exc:
            print(f"[FALHA] Preparacao de credenciais: {type(exc).__name__}", file=sys.stderr)
            return 1
        print(f"[OK] Arquivos privados preparados para canal {args.stage_channel}; nenhum envio.")
        return 0
    return 0 if check() else 1


if __name__ == "__main__":
    raise SystemExit(main())
