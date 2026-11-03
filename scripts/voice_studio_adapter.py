#!/usr/bin/env python3
"""VoiceStudio local TTS adapter: real word timestamps, independent provider cache.

Does not send a file to YouTube, download models, or fabricate subtitles.
Requires VoiceStudio's own TTS and ASR engines installed and running.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit
from difflib import SequenceMatcher

import requests


def _local_endpoint() -> str:
    raw = os.environ.get("OTAKU_VOICESTUDIO_URL", "http://127.0.0.1:3900").rstrip("/")
    url = urlsplit(raw)
    if (url.scheme != "http" or url.hostname not in ("localhost", "127.0.0.1", "::1")
            or url.username or url.password or url.query or url.fragment or url.path not in ("", "/")):
        raise ValueError("VoiceStudio deve usar HTTP local (http://127.0.0.1:3900), sem credenciais na URL")
    return raw


def _client() -> requests.Session:
    # Requests honors HTTP_PROXY by default, even for some loopback setups.
    # Never send the text/audio of a local VoiceStudio job through a proxy.
    client = requests.Session()
    client.trust_env = False
    return client


def _http_error_message(exc: requests.exceptions.HTTPError, stage: str) -> str:
    response = exc.response
    if response is None:
        return f"Falha HTTP do VoiceStudio na etapa {stage}: {exc}"
    status = response.status_code
    try:
        payload = response.json()
        payload = payload if isinstance(payload, dict) else {}
    except (ValueError, TypeError):
        payload = {}
    error = payload.get("error")
    error = error if isinstance(error, dict) else {}
    detail = payload.get("detail")
    detail_obj = detail if isinstance(detail, dict) else {}
    code = str(error.get("code") or detail_obj.get("code") or "").strip()
    message = str(error.get("message") or detail_obj.get("message") or
                  (detail if isinstance(detail, str) else "")).strip()
    # Keep diagnostics short and avoid dumping an API response or request text.
    message = re.sub(r"[\\r\\n\\t]+", " ", message)[:260]

    if status == 403 and code == "model_licence_required":
        models = detail_obj.get("models")
        names = [
            str(m.get("repo_id") or "") for m in models
            if isinstance(m, dict) and m.get("repo_id")
        ] if isinstance(models, list) else []
        suffix = f" Modelos: {', '.join(names[:4])}." if names else ""
        return (
            f"[LICENÇA PENDENTE] VoiceStudio recusou {stage} (HTTP 403, "
            "model_licence_required)." + suffix +
            " Abra Catálogo de modelos no VoiceStudio > Licença, leia e confirme "
            "somente os termos permitidos para seu uso. Não aceitamos licenças "
            "automaticamente. OmniVoice padrão pode ter restrição não comercial; "
            "não use para monetização sem autorização apropriada."
        )
    if status == 403:
        return (
            f"[ACESSO NEGADO] VoiceStudio recusou {stage} (HTTP 403). "
            f"Motivo informado: {message or code or 'sem detalhe'}. "
            "Use a API local em 127.0.0.1:3900, confira as permissões e "
            "as licenças na interface do VoiceStudio."
        )
    if status == 409 and stage == "transcrição ASR":
        return (
            "[MODELO ASR AUSENTE] VoiceStudio não está pronto para sincronizar "
            "legendas: configure um Whisper compatível com timestamps por palavra. "
            f"Resposta: {message or code or 'HTTP 409'}."
        )
    return f"VoiceStudio falhou em {stage} (HTTP {status}): {message or code or 'sem detalhe'}."


def _normalized(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", s))


def _words(payload: dict, source: str) -> list[dict]:
    raw = payload.get("words")
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("VoiceStudio ASR não retornou timestamps de palavras. Configure um modelo Whisper com word timestamps.")
    words = []
    prev = -1.0
    for item in raw:
        try:
            text = str(item.get("word") or "").strip()
            start, end = float(item["start"]), float(item["end"])
        except (TypeError, ValueError, KeyError) as exc:
            raise RuntimeError("VoiceStudio retornou alinhamento de palavras inválido") from exc
        if not text or not (math.isfinite(start) and math.isfinite(end)) or start < 0 or end <= start or start + 0.035 < prev:
            raise RuntimeError("VoiceStudio retornou palavras vazias, repetidas ou tempos inválidos")
        words.append({"text": text, "start": start, "end": end})
        prev = start
    if len(words) < max(4, int(len(source.split()) * 0.65)):
        raise RuntimeError("A transcrição omitiu muitas palavras do roteiro: teste bloqueado.")
    similar = SequenceMatcher(None, _normalized(source), _normalized(" ".join(w["text"] for w in words))).ratio()
    if similar < 0.71:
        raise RuntimeError(f"Transcrição diverge do roteiro ({similar:.0%} de semelhança); reveja pronúncia, ASR ou voz.")
    return words


def voice_paths(episode: dict, folder: Path) -> tuple[Path, Path, Path]:
    script = str(episode.get("script") or "").strip()
    model = os.environ.get("OTAKU_VOICESTUDIO_MODEL", "tts-1").strip()
    voice = os.environ.get("OTAKU_VOICESTUDIO_VOICE", "default").strip()
    if not script or not model or not voice:
        raise ValueError("Roteiro, modelo ou perfil de voz não informado")
    digest = hashlib.sha256(json.dumps(
        [script, model, voice, "pt"], ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return (folder / f"voz-voicestudio-{digest}.mp3",
            folder / f"legendas-voicestudio-{digest}.ass",
            folder / f"marcacoes-voicestudio-{digest}.json")


def ensure_voice_studio(episode: dict, folder: Path, *, create: bool = False) -> tuple[Path, Path]:
    script = str(episode.get("script") or "").strip()
    if not script or len(script) > 4096:
        raise ValueError("VoiceStudio requer roteiro entre 1 e 4096 caracteres")
    mp3, subtitles, marker = voice_paths(episode, folder)
    if mp3.is_file() and mp3.stat().st_size >= 1000 and subtitles.is_file() and marker.is_file():
        state = json.loads(marker.read_text(encoding="utf-8"))
        if (state.get("audio_sha256") == hashlib.sha256(mp3.read_bytes()).hexdigest()
                and state.get("script_sha256") == hashlib.sha256(script.encode("utf-8")).hexdigest()):
            return mp3, subtitles
    if not create:
        raise FileNotFoundError("Voz VoiceStudio e legendas não geradas. Rode o teste ou use --criar-voz.")

    base = _local_endpoint()
    model = os.environ.get("OTAKU_VOICESTUDIO_MODEL", "tts-1").strip()
    voice = os.environ.get("OTAKU_VOICESTUDIO_VOICE", "default").strip()
    stage = "geração TTS"
    try:
        with _client() as client:
            speech = client.post(base + "/v1/audio/speech",
                json={"model": model, "voice": voice, "input": script,
                      "language": "pt", "response_format": "mp3", "speed": 1.0},
                timeout=(10, 900))
            speech.raise_for_status()
            audio = speech.content
            if len(audio) < 1000 or "json" in speech.headers.get("Content-Type", "").lower():
                raise RuntimeError("VoiceStudio não retornou áudio MP3 válido")
            stage = "transcrição ASR"
            asr = client.post(base + "/v1/audio/transcriptions",
                data=[("model", "whisper-1"), ("language", "pt"),
                      ("response_format", "verbose_json"), ("timestamp_granularities[]", "word")],
                files={"file": ("narracao.mp3", audio, "audio/mpeg")},
                timeout=(10, 900))
            asr.raise_for_status()
            words = _words(asr.json(), script)
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(_http_error_message(exc, stage)) from exc
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(
            "VoiceStudio local indisponível ou não pronto. Abra VoiceStudio, instale "
            "um modelo TTS e um modelo ASR Whisper para timestamps; "
            "o Edge TTS original permanece disponível com -VozMotor edge. "
            f"Detalhe técnico: {exc}") from exc

    # Both speech and verified real word timestamps must exist before writing cache.
    from narracao_shorts import ass_dialogues
    ass = ass_dialogues(words)
    folder.mkdir(parents=True, exist_ok=True)
    temp_audio = mp3.with_suffix(".partial")
    temp_sub = subtitles.with_suffix(".partial")
    try:
        temp_audio.write_bytes(audio)
        temp_sub.write_text(ass, encoding="utf-8")
        temp_audio.replace(mp3)
        temp_sub.replace(subtitles)
        marker.write_text(json.dumps({
            "provider": "voicestudio", "model": model, "voice": voice,
            "source": "VoiceStudio ASR verified word timestamps",
            "script_sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
            "audio_sha256": hashlib.sha256(audio).hexdigest(), "words": words,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    finally:
        temp_audio.unlink(missing_ok=True)
        temp_sub.unlink(missing_ok=True)
    return mp3, subtitles
