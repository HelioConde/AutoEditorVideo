#!/usr/bin/env python3
"""Fila editorial ciclica: episodio, curiosidade, nostalgia, proximo episodio.

Este programa e executado LOCALMENTE no Windows. Nao usa GitHub Actions
como relogio, nao envia arquivos para o GitHub e nunca faz upload sem
--publicar. O tempo e contado pela confirmacao de upload no registro local,
nao pelo inicio da renderizacao. A sequencia para ao primeiro erro.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "conteudos" / "death-note-recaps-60s.json"
FORMATS_CATALOG = ROOT / "conteudos" / "death-note-formatos-60s.json"
PUBLICATIONS = ROOT / "assets" / "gerados" / "publicacao-youtube"
SHORTS = ROOT / "assets" / "gerados" / "shorts-animados"
# The published EP01 is not republished. Start with EP02, then alternate
# content formats before returning to the next episode.
DEFAULT_IDS = (
    "102-death-note-ep02",
    "201-death-note-rosto-nome",
    "301-death-note-voce-lembra-justica",
    "103-death-note-ep03",
)
EDITORIAL_CYCLE = ("episodio", "curiosidade", "voce-lembra")
DEFAULT_MINUTES = 60


class SchedulingError(RuntimeError):
    pass


@dataclass(frozen=True)
class UploadRecord:
    episode_id: str
    video_id: str
    privacy: str
    published_at: datetime

    @property
    def youtube_url(self) -> str:
        return f"https://youtu.be/{self.video_id}"


def registered_episodes() -> dict[str, dict]:
    items: dict[str,dict] = {}
    for source in (CATALOG, FORMATS_CATALOG):
        document = json.loads(source.read_text(encoding="utf-8-sig"))
        for episode in document["episodes"]:
            episode_id = episode["id"]
            if episode_id in items:
                raise SchedulingError("ID duplicado nos catalogos: " + episode_id)
            items[episode_id] = episode
    return items


def editorial_role(episode: dict) -> str:
    return "episodio" if episode.get("episode_number") else episode.get("format_type", "")


def verify_default_cycle(catalog: dict[str, dict]) -> None:
    expected = ("episodio", "curiosidade", "voce-lembra", "episodio")
    roles = tuple(editorial_role(catalog[episode_id]) for episode_id in DEFAULT_IDS)
    if roles != expected:
        raise SchedulingError(
            "A fila padrao deve respeitar episodio -> curiosidade -> voce-lembra "
            f"-> episodio. Detectado: {roles!r}"
        )


def video_file(episode_id: str, profile: str) -> Path:
    return SHORTS / episode_id / (
        f"{episode_id}-master-multicenas-personagens-v3-{profile}.mp4"
    )


def existing_upload(episode_id: str, profile: str) -> UploadRecord | None:
    """Look up existing upload by *actual MP4 SHA*, not just title or episode."""
    path = video_file(episode_id, profile)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    digest_hex = digest.hexdigest()
    state_file = PUBLICATIONS / f"estado-upload-{digest_hex[:12]}.json"
    if not state_file.is_file():
        return None
    state = json.loads(state_file.read_text(encoding="utf-8-sig"))
    if state.get("video_sha256") != digest_hex:
        raise SchedulingError(
            f"Registro inconsistente para {episode_id}: hash do MP4 nao confere."
        )
    video_id = str(state.get("video_id") or "").strip()
    if not video_id:
        raise SchedulingError(
            f"Upload sem confirmacao de video_id em {state_file}. "
            "Confirme no YouTube Studio antes de repetir."
        )
    instant = str(state.get("enviado_em") or "")
    if not instant:
        raise SchedulingError(f"Registro sem horario de envio: {state_file}")
    try:
        when = datetime.fromisoformat(instant.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SchedulingError(f"Horario invalido no registro: {state_file}") from exc
    if when.tzinfo is None:
        raise SchedulingError(f"Horario sem fuso no registro: {state_file}")
    return UploadRecord(
        episode_id=episode_id,
        video_id=video_id,
        privacy=str(state.get("privacidade_solicitada") or ""),
        published_at=when.astimezone(timezone.utc),
    )


def upload_command(episode_id: str, *, privacy: str, profile: str,
                   model: str, budget: int) -> list[str]:
    return [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(ROOT / "criar-publicar-short.ps1"),
        "-Id", episode_id,
        "-Modelo", model,
        "-Perfil", profile,
        "-MaxChamadas", str(budget),
        "-Publicar", "-Privacidade", privacy,
    ]


def run_upload(parts: list[str]) -> int:
    return subprocess.run(parts, cwd=ROOT, check=False).returncode


def wait_until(target: datetime, *,
               clock: Callable[[], datetime],
               sleep: Callable[[float], None]) -> None:
    while True:
        remaining = (target - clock()).total_seconds()
        if remaining <= 0:
            return
        print(f"[INTERVALO] Aguardando {remaining / 60:.1f} minuto(s) "
              f"ate {target.astimezone().strftime('%H:%M:%S')} para o proximo upload.",
              flush=True)
        sleep(min(60.0, remaining))


def process(
    episode_ids: list[str], *, minutes: int, privacy: str,
    profile: str, model: str, budget: int, publish: bool,
    reader: Callable[[str, str], UploadRecord | None] = existing_upload,
    execute: Callable[[list[str]], int] = run_upload,
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    sleep: Callable[[float], None] = time.sleep,
) -> list[UploadRecord]:
    catalog = registered_episodes()
    verify_default_cycle(catalog)
    if not episode_ids or len(set(episode_ids)) != len(episode_ids):
        raise SchedulingError("Selecione episodios distintos, em ordem.")
    for episode_id in episode_ids:
        if episode_id not in catalog:
            raise SchedulingError(f"Episodio nao cadastrado: {episode_id}")
    if minutes < 60:
        raise SchedulingError(
            "O experimento exige no minimo 60 minutos entre uploads confirmados."
        )

    # Do not start an earlier missing slot if a later slot is already public.
    # This protects a previously run EP02 -> EP03 queue from silently adding
    # curiosity/nostalgia out of order after EP03.
    existing = [reader(item, profile) for item in episode_ids]
    later_already_sent = False
    for item, recorded in zip(reversed(episode_ids), reversed(existing)):
        if recorded is not None:
            later_already_sent = True
        elif later_already_sent:
            raise SchedulingError(
                f"A fila esta fora de ordem: {item} ainda nao foi enviado, "
                "mas um video posterior ja foi publicado. "
                "Revise a ordem manualmente; nenhum upload sera iniciado."
            )

    previous_at: datetime | None = None
    results: list[UploadRecord] = []
    for index, episode_id in enumerate(episode_ids, 1):
        record = reader(episode_id, profile)
        if record is not None:
            if record.privacy != privacy:
                raise SchedulingError(
                    f"{episode_id} ja enviado com privacidade {record.privacy!r}, "
                    f"mas o experimento solicita {privacy!r}. Ajuste no YouTube Studio."
                )
            print(f"[JA PUBLICADO] {episode_id} | {record.youtube_url} | "
                  f"{record.published_at.isoformat()}", flush=True)
            if previous_at is not None and (
                record.published_at < previous_at + timedelta(minutes=minutes)
            ):
                print(
                    "[ATENCAO] Os uploads ja existentes estao mais proximos "
                    "do que o intervalo configurado. Nao apagar nem reenviar.",
                    flush=True,
                )
            results.append(record)
            previous_at = record.published_at
            continue

        if not publish:
            date = (
                previous_at + timedelta(minutes=minutes)
                if previous_at is not None else None
            )
            when = (date.isoformat() if date is not None else "a partir de agora")
            print(f"[PLANO {index}/{len(episode_ids)}] {episode_id} | "
                  f"proximo horario elegivel: {when} | SEM UPLOAD", flush=True)
            continue

        if previous_at is not None:
            wait_until(
                previous_at + timedelta(minutes=minutes),
                clock=clock, sleep=sleep,
            )
        command = upload_command(
            episode_id, privacy=privacy, profile=profile,
            model=model, budget=budget,
        )
        print(f"[PUBLICAR {index}/{len(episode_ids)}] {episode_id} | "
              f"{clock().isoformat()}", flush=True)
        result = execute(command)
        if result != 0:
            raise SchedulingError(
                f"Falhou o episodio {episode_id}, codigo {result}. "
                "Sequencia interrompida; nenhum outro video sera enviado "
                "automaticamente. Verifique os logs e o YouTube Studio."
            )
        confirmed = reader(episode_id, profile)
        if confirmed is None or not confirmed.video_id:
            raise SchedulingError(
                f"Sem comprovante local de upload de {episode_id}. "
                "Sequencia interrompida para evitar duplicacao."
            )
        if confirmed.privacy != privacy:
            raise SchedulingError(
                f"Privacidade inesperada em {episode_id}: {confirmed.privacy!r}."
            )
        if previous_at is not None and (
            confirmed.published_at < previous_at + timedelta(minutes=minutes)
        ):
            raise SchedulingError(
                f"O registro de {episode_id} nao respeita o intervalo configurado."
            )
        print(f"[CONFIRMADO] {episode_id}: {confirmed.youtube_url} | "
              f"{confirmed.published_at.isoformat()}", flush=True)
        results.append(confirmed)
        previous_at = confirmed.published_at
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Publica EP02, curiosidade, nostalgia e EP03 com intervalo >=1h; ou planeja offline"
    )
    parser.add_argument("--ids", nargs="+", default=list(DEFAULT_IDS))
    parser.add_argument("--intervalo-minutos", type=int, default=DEFAULT_MINUTES)
    parser.add_argument("--privacidade", choices=("public", "private", "unlisted"),
                        default="public")
    parser.add_argument("--perfil", choices=("equilibrado", "vivo", "ultrassutil"),
                        default="equilibrado")
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"),
                        default="gpt-image-1.5")
    parser.add_argument("--max-chamadas", type=int, default=45)
    parser.add_argument("--publicar", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.max_chamadas <= 180:
        parser.error("O orcamento deve ser de 0 a 180 chamadas por video")
    records = process(
        args.ids, minutes=args.intervalo_minutos,
        privacy=args.privacidade, profile=args.perfil, model=args.modelo,
        budget=args.max_chamadas, publish=args.publicar,
    )
    print(f"[CONCLUIDO] {len(records)} registro(s) de publicacao. "
          "O experimento usa horarios confirmados, nao estimativas.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SchedulingError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("[INTERROMPIDO] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
