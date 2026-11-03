#!/usr/bin/env python3
"""Repara descricao UTF-8 e tenta enviar capa aprovada nos 5 Shorts JA publicados.

Nao faz videos.insert nem altera privacidade/titulo/categoria.
Usa um token OAuth separado, com escopo de edicao de metadados.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from metadata_shorts import MANIFEST, description_for, load_episodes

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "gerados" / "publicacao-youtube"
SECRET = ROOT / ".secrets" / "youtube-oauth-client.json"
REPAIR_TOKEN = ROOT / ".secrets" / "youtube-repair-token.json"
SCOPE = ["https://www.googleapis.com/auth/youtube.force-ssl"]
IDS = (
    "003-death-note-xadrez",
    "004-death-note-segundo-kira",
    "005-death-note-sangue",
    "006-death-note-shinigami",
    "007-death-note-maca",
)


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def validate_cover(path: Path) -> None:
    from PIL import Image
    if not path.is_file():
        raise FileNotFoundError(
            f"Capa aprovada nao encontrada: {path}. Gere com "
            ".\\gerar-shorts-master.ps1 -Id <ID> -SomenteCapa"
        )
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        width, height = im.size
        if im.format not in ("JPEG", "PNG"):
            raise ValueError(f"Capa invalida: formato {im.format}")
    if height < 640 or abs(width / height - 9 / 16) > .02:
        raise ValueError(f"Capa {path.name} nao esta em 9:16 ({width}x{height})")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError(f"Capa excede 50MB: {path}")


def plan_items(root: Path = ROOT, profile: str = "equilibrado") -> list[dict]:
    episodes = load_episodes(root / "conteudos" / "testes-animados-5.json")
    out = root / "assets" / "gerados" / "publicacao-youtube"
    planned = []
    used_ids = set()
    for episode_id in IDS:
        ep = episodes[episode_id]
        folder = root / "assets" / "gerados" / "shorts-animados" / episode_id
        video = folder / f"{episode_id}-master-multicenas-personagens-v3-{profile}.mp4"
        if not video.is_file():
            raise FileNotFoundError(f"MP4 original ausente: {video}")
        sha = digest_file(video)
        state_file = out / ("estado-upload-" + sha[:12] + ".json")
        if not state_file.is_file():
            raise FileNotFoundError(
                f"Registro do upload ausente: {state_file}. "
                "Nao adivinharemos o ID do video nem o reenviamos."
            )
        saved = read_json(state_file)
        video_id = str(saved.get("video_id") or "")
        if saved.get("video_sha256") != sha or not (
            6 <= len(video_id) <= 24 and all(c.isalnum() or c in "-_" for c in video_id)
        ):
            raise ValueError(f"Registro nao corresponde ao MP4 atual: {episode_id}")
        if video_id in used_ids:
            raise ValueError("Dois episodios apontam para o mesmo video do YouTube")
        used_ids.add(video_id)
        cover = folder / f"{episode_id}-master-capa.jpg"
        validate_cover(cover)
        planned.append({
            "id": episode_id, "video_id": video_id, "video": video,
            "cover": cover, "state_path": state_file, "state": saved,
            "description": description_for(ep),
        })
    return planned


def oauth_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    if not SECRET.is_file():
        raise FileNotFoundError(f"Credenciais OAuth ausentes: {SECRET}")
    credentials = None
    if REPAIR_TOKEN.is_file():
        credentials = Credentials.from_authorized_user_file(str(REPAIR_TOKEN), SCOPE)
        if not credentials.has_scopes(SCOPE):
            credentials = None
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            print("[OAUTH] Autorize a edicao das descricoes e capas no canal correto.", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPE)
            credentials = flow.run_local_server(port=0, host="localhost", open_browser=True)
        REPAIR_TOKEN.parent.mkdir(parents=True, exist_ok=True)
        REPAIR_TOKEN.write_text(credentials.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def build_snippet_update(remote: dict, new_description: str) -> dict:
    original = remote.get("snippet", {})
    title = original.get("title", "")
    category = str(original.get("categoryId", ""))
    if not title or not category:
        raise ValueError("O YouTube nao retornou titulo/categoria; nada sera alterado")
    snippet = {
        "title": title,
        "categoryId": category,
        "description": new_description,
    }
    for optional in ("tags", "defaultLanguage"):
        if optional in original:
            snippet[optional] = original[optional]
    return {"id": remote["id"], "snippet": snippet}


def update_one(youtube, item: dict, owner_id: str, *, send_cover: bool = True) -> dict:
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    video_id = item["video_id"]
    result = {
        "id": item["id"], "video_id": video_id,
        "url": f"https://youtu.be/{video_id}",
        "capa_arquivo": str(item["cover"]),
        "descricao_status": "pendente", "capa_status": "pendente",
    }
    try:
        remote_items = youtube.videos().list(part="snippet", id=video_id).execute().get("items", [])
        if len(remote_items) != 1:
            raise RuntimeError("Video nao encontrado pela API")
        remote = remote_items[0]
        if remote.get("snippet", {}).get("channelId") != owner_id:
            raise RuntimeError("Video nao pertence ao canal autenticado")
        wanted = item["description"]
        if remote["snippet"].get("description") == wanted:
            result["descricao_status"] = "ja_corrigida"
        else:
            youtube.videos().update(
                part="snippet", body=build_snippet_update(remote, wanted)
            ).execute()
            result["descricao_status"] = "corrigida"
        print(f"[DESCRICAO] {item['id']}: {result['descricao_status']}", flush=True)
    except HttpError as exc:
        result["descricao_status"] = f"erro_http_{exc.resp.status}"
        result["descricao_erro"] = str(exc)[:350]
    except Exception as exc:
        result["descricao_status"] = "erro"
        result["descricao_erro"] = str(exc)[:350]

    if not send_cover:
        result["capa_status"] = "nao_tentada"
        print(f"[CAPA] {item['id']}: sem nova chamada de upload; "
              f"arquivo local: {item['cover']}", flush=True)
        return result

    try:
        image_type = "image/png" if item["cover"].suffix.lower() == ".png" else "image/jpeg"
        media = MediaFileUpload(str(item["cover"]), mimetype=image_type, resumable=False)
        youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        result["capa_status"] = "aceita_pela_api"
        item["state"]["thumbnail_status"] = "success"
        item["state"]["thumbnail_file"] = str(item["cover"])
        write_json(item["state_path"], item["state"])
        print(f"[CAPA] {item['id']}: API aceitou a imagem. Confira no YouTube Studio.", flush=True)
    except HttpError as exc:
        code = int(exc.resp.status)
        result["capa_status"] = f"erro_http_{code}"
        result["capa_erro"] = str(exc)[:350]
        if code == 429:
            print(f"[CAPA] {item['id']}: limite de envios de miniaturas (HTTP 429). "
                  "Interrompendo novas tentativas de capa nesta execucao.", flush=True)
        else:
            print(f"[CAPA] {item['id']}: HTTP {code}; "
                  f"use o Studio: https://studio.youtube.com/video/{video_id}/edit",
                  flush=True)
    except Exception as exc:
        result["capa_status"] = "erro"
        result["capa_erro"] = str(exc)[:350]
        print(f"[CAPA] {item['id']}: {type(exc).__name__}; veja o relatorio.", flush=True)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repara somente uploads existentes, sem reenviar MP4")
    parser.add_argument("--aplicar", action="store_true", help="Envia as alteracoes a API do YouTube")
    parser.add_argument("--sem-capas", action="store_true",
                        help="Corrige somente as descricoes; nao tenta enviar capas")
    parser.add_argument("--perfil-personagens", choices=("equilibrado", "vivo", "ultrassutil"),
                        default="equilibrado")
    args = parser.parse_args(argv)
    planned = plan_items(profile=args.perfil_personagens)
    for item in planned:
        print(f"[LOCALIZADO] {item['id']} -> https://youtu.be/{item['video_id']} | "
              f"capa {item['cover'].name}", flush=True)
    if not args.aplicar:
        print("[PREVIA] Os cinco registros e capas estao prontos. "
              "Execute com --aplicar para corrigir o YouTube. Nao houve alteracoes.")
        return 0

    youtube = oauth_service()
    mine = youtube.channels().list(part="id", mine=True).execute().get("items", [])
    if len(mine) != 1 or not mine[0].get("id"):
        raise RuntimeError("Nao foi possivel determinar um unico canal autenticado")
    owner_id = mine[0]["id"]
    report = []
    uploads_allowed = not args.sem_capas
    for item in planned:
        row = update_one(youtube, item, owner_id, send_cover=uploads_allowed)
        report.append(row)
        if row["capa_status"] == "erro_http_429":
            uploads_allowed = False
        write_json(OUTPUT / "reparo-5-shorts.json", {
            "updated_at": datetime.now(timezone.utc).isoformat(), "resultados": report,
        })
    failed_descriptions = sum(
        1 for row in report
        if row["descricao_status"] not in ("corrigida", "ja_corrigida")
    )
    covers_pending = sum(
        1 for row in report if row["capa_status"] != "aceita_pela_api"
    )
    print(f"[RESUMO] Descricoes com erro: {failed_descriptions}; "
          f"capas pendentes: {covers_pending}. "
          f"Relatorio: {OUTPUT / 'reparo-5-shorts.json'}")
    if covers_pending:
        print("[CAPAS] O YouTube pode limitar uploads por canal. Nao repita "
              "o reparo imediatamente. Use YouTube Studio em um computador "
              "para enviar a capa 9:16 de cada Short.")
    print("[IMPORTANTE] Nenhum MP4 foi reenviado e nenhuma privacidade foi alterada.")
    # Miniaturas pendentes sao uma advertencia, nao falha da correcao das descricoes.
    return 1 if failed_descriptions else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        print("[ERRO] " + str(exc), file=sys.stderr)
        raise SystemExit(2)
