#!/usr/bin/env python3
"""Safe YouTube uploader for a separate English-language channel.

No channel creation by API. All uploads require explicit local OAuth, verified
channel ID, separate tokens, and human review. Never touches PT upload state.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from renderizar_shorts_en import load_english, english_metadata, OUT, ROOT

CLIENT = ROOT / ".secrets" / "youtube-oauth-client.json"
TOKEN = ROOT / ".secrets" / "youtube-en-token.json"
CHANNEL_FILE = ROOT / ".secrets" / "youtube-en-channel-id.txt"
STATE = ROOT / "assets" / "gerados" / "publicacao-youtube-en" / "estado.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def expected_channel() -> str:
    if not CHANNEL_FILE.is_file():
        raise RuntimeError(
            "Falta ID do segundo canal em .secrets/youtube-en-channel-id.txt; "
            "crie o canal no YouTube Studio e copie o Channel ID verdadeiro."
        )
    val = CHANNEL_FILE.read_text(encoding="utf-8-sig").strip()
    if not re.fullmatch(r"UC[A-Za-z0-9_-]{22}", val):
        raise ValueError("ID do canal em ingles invalido; deve ser o Channel ID com prefixo UC")
    return val


def verify_channel_identity(actual: list[dict], channel_id: str) -> str:
    """Refuse to upload if OAuth is linked to any different YouTube channel."""
    if len(actual) != 1 or actual[0].get("id") != channel_id:
        raise RuntimeError(
            "CONTA ERRADA. O OAuth nao corresponde ao Channel ID do canal em ingles. "
            "Nenhum video foi enviado. Revise a identidade escolhida no navegador; "
            "para reconectar, exclua SOMENTE .secrets/youtube-en-token.json."
        )
    return str(actual[0].get("snippet", {}).get("title", ""))


def channel_auth():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not CLIENT.is_file():
        raise RuntimeError("Faltam as credenciais OAuth do Google Cloud em .secrets/youtube-oauth-client.json")
    channel_id = expected_channel()
    credential = None
    if TOKEN.is_file():
        credential = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
        if not credential.has_scopes(SCOPES):
            credential = None
    if not credential or not credential.valid:
        if credential and credential.expired and credential.refresh_token:
            credential.refresh(Request())
        else:
            print("[OAUTH EN] Escolha a identidade do SEGUNDO canal na autorizacao do Google.")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
            credential = flow.run_local_server(port=0, host="localhost", open_browser=True)
        TOKEN.parent.mkdir(parents=True, exist_ok=True)
        TOKEN.write_text(credential.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=credential, cache_discovery=False)
    actual = youtube.channels().list(part="id,snippet", mine=True).execute().get("items", [])
    title = verify_channel_identity(actual, channel_id)
    print(f"[CANAL EN VERIFICADO] {title}: {channel_id}")
    return youtube


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda: f.read(1024 * 1024), b""):
            h.update(piece)
    return h.hexdigest()


def validate_mp4(path: Path) -> None:
    if not path.is_file() or path.stat().st_size < 100000:
        raise FileNotFoundError("Video ingles ausente ou incompleto: " + str(path))
    command = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        data = json.loads(subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=45
        ).stdout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("FFprobe falhou para: " + str(path)) from exc
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video or not any(s.get("codec_type") == "audio" for s in streams):
        raise ValueError("O Short precisa de trilhas de video e de audio")
    width, height = int(video["width"]), int(video["height"])
    if abs(width / height - 9 / 16) > 0.03:
        raise ValueError("Short ingles deve ser 9:16")
    if float(data.get("format", {}).get("duration", 0)) <= 1:
        raise ValueError("Duracao invalida")


def candidates(profile: str, episode_id: str, limit: int) -> list[dict]:
    episodes = load_english()
    if episode_id:
        episodes = [x for x in episodes if x["id"] == episode_id]
        if not episodes:
            raise ValueError("Episodio nao encontrado no manifesto ingles")
    else:
        episodes = episodes[:limit]
    result = []
    for ep in episodes:
        folder = OUT / ep["id"] / "en-US"
        path = folder / f"{ep['id']}-en-US-master-multicenas-personagens-v3-{profile}.mp4"
        validate_mp4(path)
        report_file = folder / "qa-en-US.json"
        if not report_file.is_file():
            raise ValueError(f"QA em ingles ausente: {ep['id']}. Reprocesse e revise.")
        qa = read_json(report_file)
        if qa.get("status") != "renderizado_aguardando_revisao":
            raise ValueError("QA invalido para " + ep["id"])
        title = english_metadata(ep)["titulo"]
        if not 1 <= len(title) <= 100:
            raise ValueError("Titulo em ingles invalido")
        result.append({"id": ep["id"], "path": path, "sha": sha256(path),
                       "meta": english_metadata(ep)})
    return result


def upload(youtube, row: dict, privacy: str, saved: dict) -> dict:
    key = row["sha"]
    previous = saved["items"].get(key)
    if previous:
        print(f"[EN CACHE] {row['id']}: registro anterior {previous['status']}; "
              "nao reenviando; confira o Studio.")
        return previous
    meta = row["meta"]
    record = {
        "id": row["id"], "sha256": key, "status": "iniciado_ou_ambiguo",
        "requested_privacy": privacy, "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    saved["items"][key] = record
    save_json(STATE, saved)
    # If the process crashes after videos.insert, do not blindly repeat.
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(row["path"]), mimetype="video/mp4",
                            chunksize=4 * 1024 * 1024, resumable=True)
    command = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": meta["titulo"], "description": meta["descricao"],
                "tags": meta["tags"], "categoryId": meta["categoria"],
                "defaultLanguage": meta["idioma"],
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=media,
    )
    response = None
    while response is None:
        progress, response = command.next_chunk()
        if progress:
            print(f"[EN UPLOAD] {row['id']}: {progress.progress()*100:.1f}%", flush=True)
    video_id = response.get("id")
    if not video_id:
        raise RuntimeError("API nao retornou ID. Confira Studio antes de repetir!")
    record.update(status="enviado", video_id=video_id,
                  link="https://youtu.be/" + video_id)
    save_json(STATE, saved)
    print(f"[EN PUBLICADO] {row['id']}: https://youtu.be/{video_id} ({privacy})")
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YouTube English channel - publication separated from PT")
    parser.add_argument("--acao", choices=("verificar", "conectar", "enviar"), default="verificar")
    parser.add_argument("--id", default="")
    parser.add_argument("--limite", type=int, default=1)
    parser.add_argument("--perfil", choices=("equilibrado", "vivo", "ultrassutil"),
                        default="equilibrado")
    parser.add_argument("--privacidade", choices=("private", "unlisted", "public"), default="private")
    parser.add_argument("--confirmar", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limite <= 5:
        parser.error("Limite: 1 a 5")
    if args.acao == "conectar":
        channel_auth()
        return 0
    rows = candidates(args.perfil, args.id, args.limite)
    saved = read_json(STATE) if STATE.is_file() else {"schema": "arquivo-otaku/youtube-en/v1", "items": {}}
    for row in rows:
        existing = saved["items"].get(row["sha"], {})
        print(f"[EN PRONTO] {row['id']} | {row['meta']['titulo']} | "
              f"{'ja enviado' if existing.get('video_id') else 'pendente'}")
    if args.acao == "verificar":
        print("[PREVIA] Nenhum upload; selecione canal e revise os MP4s antes de enviar.")
        return 0
    if not args.confirmar:
        raise RuntimeError("Envio desabilitado. Revise e passe -ConfirmarEnvio.")
    youtube = channel_auth()  # strict channel check BEFORE any videos.insert
    for row in rows:
        upload(youtube, row, args.privacidade, saved)
    print("[EN PRONTO] Confira os videos no Studio do novo canal.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
        print("[EN ERRO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
