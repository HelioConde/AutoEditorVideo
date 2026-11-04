#!/usr/bin/env python3
"""Authorize a YouTube channel WITHOUT uploading videos.

Run only on the owner's PC: the OAuth browser redirect needs localhost.
Secrets stay in .secrets/, which is excluded from Git. No upload functions here.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / ".secrets" / "youtube-oauth-client.json"
SCOPES = (
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
)
TOKEN_PATHS = {
    "br": ".secrets/youtube-token.json",
    "en": ".secrets/youtube-en-token.json",
    "kids": ".secrets/youtube-kids-token.json",
}
CHANNEL_ID_PATTERN = re.compile(r"UC[A-Za-z0-9_-]{22}")


def token_path(channel: str, root: Path = ROOT) -> Path:
    if channel not in TOKEN_PATHS:
        raise ValueError("Canal desconhecido")
    return root / TOKEN_PATHS[channel]


def validate_channel(actual: list[dict], expected: str) -> str:
    """Only the selected channel may be authorized for later use."""
    if not CHANNEL_ID_PATTERN.fullmatch(expected):
        raise ValueError("Channel ID invalido; consulte YouTube Studio > Configuracoes > Canal > Avancado")
    if len(actual) != 1 or actual[0].get("id") != expected:
        raise ValueError("O canal autorizado nao corresponde ao Channel ID informado; nenhum token sera salvo")
    return str(actual[0].get("snippet", {}).get("title", ""))


def validate_client(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Falta .secrets/youtube-oauth-client.json (cliente OAuth Desktop do Google Cloud)")
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    app = obj.get("installed", {}) if isinstance(obj, dict) else {}
    if not isinstance(app, dict) or not app.get("client_id") or not app.get("client_secret"):
        raise ValueError("Cliente OAuth invalido: escolha App para computador no Google Cloud")


def save_token(path: Path, payload: str, *, replace: bool) -> None:
    """Backup before replacing an existing token; never print credentials."""
    path.parent.mkdir(exist_ok=True, parents=True)
    if path.is_symlink():
        raise ValueError("Nao salvar token em link simbolico")
    if path.exists() and not replace:
        raise FileExistsError("Token existente preservado; use --renovar se precisar reautorizar")
    if path.exists():
        hist = path.parent / "historico-oauth"
        hist.mkdir(exist_ok=True)
        backup = hist / (path.stem + "-anterior.json")
        if backup.exists():
            raise FileExistsError("Backup anterior existente; arquive-o em local seguro antes de renovar")
        shutil.copy2(path, backup)
    tmp = path.with_suffix(".partial")
    if tmp.exists() or tmp.is_symlink():
        raise FileExistsError("Arquivo temporario OAuth existente; confira manualmente")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def authorize(channel: str, expected: str, *, replace: bool = False, root: Path = ROOT):
    path = token_path(channel, root)
    client = root / ".secrets" / "youtube-oauth-client.json"
    validate_client(client)
    if not CHANNEL_ID_PATTERN.fullmatch(expected):
        raise ValueError("Channel ID invalido")
    if path.exists() and not replace:
        print("[INFO] Token existente preservado. Para refazer a autorizacao, use --renovar.")
        return {"status": "ja_existe", "canal": channel}
    # Only used for interactive authorization and a READ-ONLY channel lookup.
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    flow = InstalledAppFlow.from_client_secrets_file(str(client), list(SCOPES))
    credentials = flow.run_local_server(
        host="localhost", port=0, open_browser=True,
        access_type="offline", prompt="consent",
    )
    if not credentials.refresh_token:
        raise RuntimeError("Google nao forneceu refresh token; autorizacao nao foi salva")
    yt = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    actual = yt.channels().list(part="id,snippet", mine=True).execute().get("items", [])
    title = validate_channel(actual, expected)
    save_token(path, credentials.to_json(), replace=replace)
    print(f"[OK] Autorizacao para canal {channel}: {title} ({expected}). Nenhum video enviado.")
    return {"status": "autorizado", "canal": channel, "channel_id": expected}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Autoriza YouTube sem enviar videos")
    parser.add_argument("--canal", choices=list(TOKEN_PATHS), required=True)
    parser.add_argument("--channel-id", required=True, help="ID UC... mostrado no YouTube Studio")
    parser.add_argument("--renovar", action="store_true", help="Renovar um token existente com backup")
    args = parser.parse_args(argv)
    try:
        authorize(args.canal, args.channel_id, replace=args.renovar)
        return 0
    except (ImportError, OSError, ValueError, RuntimeError, FileExistsError) as exc:
        print(f"[FALHA] Autorizacao: {type(exc).__name__}. Confira cliente OAuth, canal e dependencias.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
