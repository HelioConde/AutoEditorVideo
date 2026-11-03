#!/usr/bin/env python3
"""TikTok Content Posting API (official) for already rendered Arquivo Otaku Shorts.

No scraping, browser session hijack, video generation, or automatic public posting.
The user must explicitly authorize a TikTok account and confirm each batch.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import requests

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "conteudos" / "testes-animados-5.json"
APP_PATH = ROOT / ".secrets" / "tiktok-app.json"
TOKEN_PATH = ROOT / ".secrets" / "tiktok-token.json"
OUT = ROOT / "assets" / "gerados" / "publicacao-tiktok"
STATE = OUT / "envios.json"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
API = "https://open.tiktokapis.com/v2/post/publish/"
MODES = {"rascunho": "video.upload", "direto": "video.publish"}
PRIVACY = ("SELF_ONLY", "PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR")
PROFILES = ("equilibrado", "vivo", "ultrassutil")
MAX_BYTES = 4_000_000_000


class TikTokError(RuntimeError):
    pass


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def app_config() -> dict:
    if not APP_PATH.is_file():
        raise TikTokError(
            f"Credenciais ausentes: {APP_PATH}. Configure client_key, client_secret "
            "e redirect_uri do aplicativo TikTok for Developers."
        )
    data = read_json(APP_PATH)
    for name in ("client_key", "client_secret", "redirect_uri"):
        if not isinstance(data.get(name), str) or not data[name].strip():
            raise TikTokError(f"Campo {name} ausente em tiktok-app.json")
    parsed = urlparse(data["redirect_uri"])
    if (parsed.scheme != "http" or parsed.hostname not in ("localhost", "127.0.0.1")
            or not parsed.port or parsed.query or parsed.fragment or not parsed.path):
        raise TikTokError("Use redirect_uri http://127.0.0.1:8731/callback/ e cadastre-a no TikTok")
    return data


def auth_url(config: dict, scope: str, state: str, challenge: str) -> str:
    params = {
        "client_key": config["client_key"],
        "response_type": "code",
        "scope": "user.info.basic," + scope,
        "redirect_uri": config["redirect_uri"],
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return AUTH_URL + "?" + urlencode(params)


def exchange_token(config: dict, payload: dict) -> dict:
    response = requests.post(TOKEN_URL, data={
        "client_key": config["client_key"],
        "client_secret": config["client_secret"],
        **payload,
    }, timeout=35)
    response.raise_for_status()
    data = response.json()
    if "access_token" not in data or "refresh_token" not in data:
        raise TikTokError("TikTok nao devolveu tokens validos: " + str(data.get("error", "unknown")))
    data["expires_at"] = int(time.time()) + int(data.get("expires_in", 7200))
    save_json(TOKEN_PATH, data)
    return data


def connect(scope: str) -> None:
    config = app_config()
    parsed = urlparse(config["redirect_uri"])
    state = secrets.token_urlsafe(28)
    verifier = secrets.token_urlsafe(64)
    # TikTok Desktop PKCE requires lowercase hexadecimal SHA256.
    challenge = hashlib.sha256(verifier.encode("ascii")).hexdigest()
    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            url = urlparse(self.path)
            if url.path != parsed.path:
                self.send_error(404)
                return
            params = parse_qs(url.query)
            if params.get("state", [""])[0] != state:
                self.send_error(403, "Invalid OAuth state")
                captured["error"] = "state_invalido"
                return
            if params.get("error"):
                captured["error"] = params["error"][0]
            elif params.get("code"):
                captured["code"] = params["code"][0]
            else:
                captured["error"] = "codigo_ausente"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Autorizacao recebida. Pode fechar esta aba.")

    server = HTTPServer((parsed.hostname, parsed.port), Handler)
    server.timeout = 180
    print("[OAUTH] Abrindo autorizacao TikTok. Escolha a conta correta.", flush=True)
    print("[OAUTH] Se o navegador nao abrir, use:\n" + auth_url(config, scope, state, challenge))
    webbrowser.open(auth_url(config, scope, state, challenge))
    try:
        server.handle_request()
    finally:
        server.server_close()
    if not captured.get("code"):
        raise TikTokError("OAuth incompleto: " + captured.get("error", "timeout_ou_cancelado"))
    token = exchange_token(config, {
        "code": captured["code"],
        "grant_type": "authorization_code",
        "redirect_uri": config["redirect_uri"],
        "code_verifier": verifier,
    })
    granted = scopes(token)
    if scope not in granted:
        raise TikTokError(f"Conta conectada, mas nao autorizou {scope}; confira seu app e permissões.")
    print("[OK] Conta TikTok autorizada. Open ID final: ..." + str(token.get("open_id", ""))[-6:])


def scopes(token: dict) -> set[str]:
    value = token.get("scope", "")
    return {s.strip() for s in value.split(",") if s.strip()} if isinstance(value, str) else set(value)


def get_token(required_scope: str) -> dict:
    if not TOKEN_PATH.is_file():
        raise TikTokError("Conta nao conectada. Execute -Acao conectar -Modo rascunho/direto primeiro.")
    token = read_json(TOKEN_PATH)
    if required_scope not in scopes(token):
        raise TikTokError(
            f"Token sem permissao {required_scope}. Reconecte usando -Acao conectar -Modo correspondente."
        )
    if int(token.get("expires_at", 0)) - time.time() < 300:
        if not token.get("refresh_token"):
            raise TikTokError("Refresh token ausente. Conecte novamente.")
        token = exchange_token(app_config(), {
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        })
    if not token.get("open_id"):
        raise TikTokError("TikTok nao retornou o ID da conta; conecte novamente.")
    return token


def api_post(route: str, token: str, payload: dict) -> dict:
    response = requests.post(
        API + route, headers={"Authorization": f"Bearer {token}",
                              "Content-Type": "application/json; charset=UTF-8"},
        json=payload, timeout=40,
    )
    if response.status_code == 429:
        raise TikTokError("Limite da API TikTok (HTTP 429). Sem tentativa automatica adicional.")
    response.raise_for_status()
    body = response.json()
    error = body.get("error", {})
    if error.get("code") != "ok":
        raise TikTokError("TikTok recusou a operacao: " + str(error.get("code")) +
                          " - " + str(error.get("message", ""))[:150])
    return body.get("data", {})


def creator_info(access_token: str) -> dict:
    return api_post("creator_info/query/", access_token, {})


def ffprobe_video(path: Path) -> dict:
    cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        output = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=45)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TikTokError("FFprobe nao conseguiu analisar " + str(path)) from exc
    info = json.loads(output.stdout)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise TikTokError("MP4 precisa conter video e audio: " + str(path))
    width, height = int(video["width"]), int(video["height"])
    if min(width, height) < 360 or abs(width / height - 9 / 16) > 0.03:
        raise TikTokError("O video precisa estar na vertical 9:16: " + str(path))
    if video.get("codec_name") not in ("h264", "hevc", "vp8", "vp9"):
        raise TikTokError("Codec nao aceito no TikTok: " + str(video.get("codec_name")))
    numer, denom = map(int, video.get("r_frame_rate", "0/1").split("/"))
    fps = numer / denom if denom else 0
    if not 23 <= fps <= 60:
        raise TikTokError("FPS fora de 23 a 60: " + str(fps))
    duration = float(info.get("format", {}).get("duration", 0))
    if not 1 <= duration <= 600:
        raise TikTokError("Duracao invalida para TikTok: " + str(duration))
    return {"duration": duration, "width": width, "height": height, "fps": fps}


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def caption(episode: dict) -> str:
    title = str(episode.get("title", "")).replace("#Shorts", "").strip()
    value = title + "\n\n#DeathNote #Anime #ArquivoOtaku #AnimeBrasil"
    if len(value.encode("utf-16-le")) // 2 > 2200:
        raise TikTokError("Legenda longa demais para TikTok")
    if "Ã§" in value or "Ã¡" in value or "\ufffd" in value:
        raise TikTokError("Legenda corrompida")
    return value


def episode_items(profile: str, wanted: str = "", limit: int = 5) -> list[dict]:
    data = read_json(MANIFEST)
    items = data["episodes"]
    if wanted:
        items = [ep for ep in items if ep["id"] == wanted]
        if not items:
            raise TikTokError("ID nao encontrado no manifesto: " + wanted)
    else:
        items = items[:limit]
    result = []
    for ep in items:
        video = ROOT / "assets" / "gerados" / "shorts-animados" / ep["id"] / (
            ep["id"] + "-master-multicenas-personagens-v3-" + profile + ".mp4"
        )
        if not video.is_file():
            raise TikTokError("MP4 ausente: " + str(video))
        size = video.stat().st_size
        if size < 100_000 or size > MAX_BYTES:
            raise TikTokError("MP4 incompleto ou acima de 4GB: " + str(video))
        metrics = ffprobe_video(video)
        result.append({"id": ep["id"], "video": video, "size": size,
                       "digest": digest_file(video), "caption": caption(ep), **metrics})
    return result


def chunk_plan(size: int) -> tuple[int, list[tuple[int, int]]]:
    if size <= 64_000_000:
        return size, [(0, size)]
    chunk_size = 10_000_000
    n = size // chunk_size
    if not 1 <= n <= 1000:
        raise TikTokError("Numero de partes nao suportado")
    chunks = [(i * chunk_size, chunk_size) for i in range(n)]
    chunks[-1] = (chunks[-1][0], size - chunks[-1][0])
    return chunk_size, chunks


def validate_upload_url(url: str) -> None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not (
        host == "tiktokapis.com" or host.endswith(".tiktokapis.com")
    ):
        raise TikTokError("TikTok retornou URL de upload fora de dominio confiavel")


def transfer(video: Path, upload_url: str, size: int, chunks: list[tuple[int, int]]) -> None:
    validate_upload_url(upload_url)
    with video.open("rb") as stream:
        for i, (start, length) in enumerate(chunks, 1):
            stream.seek(start)
            data = stream.read(length)
            if len(data) != length:
                raise TikTokError("Erro ao ler MP4. Upload interrompido.")
            response = requests.put(upload_url, data=data, headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(length),
                "Content-Range": f"bytes {start}-{start + length - 1}/{size}",
            }, timeout=(15, 240), allow_redirects=False)
            if response.status_code not in (201, 206):
                raise TikTokError(f"Falha ao transferir parte {i}/{len(chunks)}: HTTP {response.status_code}")
            print(f"[UPLOAD] Parte {i}/{len(chunks)} enviada ({response.status_code}).", flush=True)


def key_for(item: dict, open_id: str, mode: str) -> str:
    return hashlib.sha256((open_id + "/" + mode + "/" + item["digest"]).encode()).hexdigest()


def send_one(item: dict, mode: str, privacy: str, token: dict,
             info: dict | None, saved: dict) -> dict:
    key = key_for(item, token["open_id"], mode)
    previous = saved["items"].get(key)
    if previous:
        print(f"[CACHE] {item['id']}: existe envio anterior {previous['status']}. "
              "Use -Acao status para consultar; nao duplicando.")
        return previous
    if mode == "direto":
        if not info or privacy not in info.get("privacy_level_options", []):
            raise TikTokError(f"Privacidade {privacy} indisponivel na conta TikTok")
        if item["duration"] > int(info.get("max_video_post_duration_sec", 0)):
            raise TikTokError(f"Video {item['id']} excede duracao permitida pela conta")
    chunk_size, chunks = chunk_plan(item["size"])
    payload: dict = {"source_info": {
        "source": "FILE_UPLOAD", "video_size": item["size"],
        "chunk_size": chunk_size, "total_chunk_count": len(chunks),
    }}
    if mode == "direto":
        payload["post_info"] = {
            "title": item["caption"],
            "privacy_level": privacy,
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
            "is_aigc": True,
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        }
    route = "video/init/" if mode == "direto" else "inbox/video/init/"
    response = api_post(route, token["access_token"], payload)
    publish_id, upload_url = response.get("publish_id"), response.get("upload_url")
    if not isinstance(publish_id, str) or not isinstance(upload_url, str):
        raise TikTokError("TikTok nao retornou publish_id/upload_url; confira a conta antes de repetir")
    record = {
        "id": item["id"], "sha256": item["digest"], "mode": mode,
        "open_id": token["open_id"], "publish_id": publish_id,
        "privacy_requested": privacy if mode == "direto" else None,
        "status": "iniciado", "created_at": int(time.time()),
    }
    # Persist immediately after init: an upload failure must NOT trigger a second init.
    saved["items"][key] = record
    save_json(STATE, saved)
    try:
        transfer(item["video"], upload_url, item["size"], chunks)
        record["status"] = "transferido_aguardando_processamento"
    except Exception as exc:
        record["status"] = "transferencia_interrompida_verifique_status"
        save_json(STATE, saved)
        raise TikTokError(
            "Envio ja iniciado no TikTok; nao rode -Acao enviar outra vez. "
            "Consulte -Acao status. Detalhe: " + str(exc)
        ) from exc
    save_json(STATE, saved)
    return record


def check_status(token: dict, saved: dict, mode: str, selected_id: str = "") -> None:
    found = 0
    for record in saved.get("items", {}).values():
        if record.get("open_id") != token["open_id"] or record.get("mode") != mode:
            continue
        if selected_id and record.get("id") != selected_id:
            continue
        result = api_post("status/fetch/", token["access_token"],
                          {"publish_id": record["publish_id"]})
        status = result.get("status", "DESCONHECIDO")
        record["remote_status"] = status
        record["last_checked_at"] = int(time.time())
        if status in ("PUBLISH_COMPLETE", "FAILED", "SEND_TO_USER_INBOX"):
            record["status"] = status
        if status == "FAILED":
            record["fail_reason"] = result.get("fail_reason", "sem detalhe")
        save_json(STATE, saved)
        print(f"[STATUS] {record['id']}: {status}" +
              (" (abrir TikTok para finalizar)" if status == "SEND_TO_USER_INBOX" else ""))
        found += 1
    if not found:
        print("[STATUS] Nenhum envio conhecido nessa conta/modo.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Arquivo Otaku: publicador oficial TikTok")
    parser.add_argument("--acao", choices=("diagnostico", "conectar", "preparar", "enviar", "status"),
                        default="diagnostico")
    parser.add_argument("--modo", choices=tuple(MODES), default="rascunho")
    parser.add_argument("--privacidade", choices=PRIVACY, default="SELF_ONLY")
    parser.add_argument("--id", default="")
    parser.add_argument("--limite", type=int, default=1)
    parser.add_argument("--perfil", choices=PROFILES, default="equilibrado")
    parser.add_argument("--confirmar", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.limite <= 5:
        parser.error("--limite precisa ficar entre 1 e 5")
    scope = MODES[args.modo]
    if args.acao == "diagnostico":
        print("[LOCAL] App TikTok:", "configurado" if APP_PATH.is_file() else "pendente")
        print("[LOCAL] Token TikTok:", "existente" if TOKEN_PATH.is_file() else "pendente")
        print("[LOCAL] Arquivos prontos: execute -Acao preparar.")
        print("[MODO] Rascunho requer concluir no TikTok; direto exige video.publish e app auditado.")
        return 0
    if args.acao == "conectar":
        connect(scope)
        return 0
    saved = read_json(STATE) if STATE.is_file() else {"schema": "arquivo-otaku/tiktok/v1", "items": {}}
    if args.acao == "status":
        token = get_token(scope)
        check_status(token, saved, args.modo, args.id)
        return 0
    items = episode_items(args.perfil, args.id, args.limite)
    for item in items:
        print(f"[VIDEO] {item['id']} | {item['duration']:.1f}s | "
              f"{item['width']}x{item['height']} | {item['size']//1024} KiB")
        print("[LEGENDA]", item["caption"].replace("\n", " "))
    if args.acao == "preparar":
        print("[PREVIA] Nenhum arquivo enviado ao TikTok.")
        return 0
    if not args.confirmar:
        raise TikTokError("Envio bloqueado. Revise os videos e execute novamente com -ConfirmarEnvio.")
    token = get_token(scope)
    info = creator_info(token["access_token"]) if args.modo == "direto" else None
    if info:
        print(f"[CONTA] @{info.get('creator_username', 'desconhecida')} | "
              f"privacidade disponivel: {info.get('privacy_level_options', [])}")
    print(f"[ENVIO] Conta autorizada ...{token['open_id'][-6:]} | modo: {args.modo} "
          f"| privacidade: {args.privacidade if args.modo == 'direto' else 'escolhida no TikTok'}")
    for item in items:
        send_one(item, args.modo, args.privacidade, token, info, saved)
    print("[FINALIZADO] Transferencias solicitadas. Use -Acao status para confirmar o resultado.")
    if args.modo == "rascunho":
        print("[TIKTOK] Abra o aplicativo e conclua as publicacoes pela notificacao da caixa de entrada.")
    else:
        print("[TIKTOK] Publicacao direta sujeita a revisao, permissao e restricoes de auditoria.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (TikTokError, ValueError, OSError, requests.RequestException,
            subprocess.SubprocessError) as exc:
        print("[ERRO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
