#!/usr/bin/env python3
"""Prepara e agenda 24 Shorts no YouTube (8 recaps, 8 curiosidades, 8 nostalgias).

O agendamento verdadeiro usa YouTube videos.insert.status.publishAt,
NAO um processo que aguarda a hora de publicar. Nenhum upload/geracao
sem a flag --agendar. O script roda na maquina Windows com OAuth.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MANIFEST = ROOT / "conteudos" / "lote-24-shorts.json"
UPLOADS = ROOT / "assets" / "gerados" / "publicacao-youtube"
CLIPS = ROOT / "assets" / "gerados" / "shorts-animados"
PLAN = UPLOADS / "lote-24-agendamento.json"
BRASILIA = timezone(timedelta(hours=-3))  # America/Sao_Paulo, sem horário de verão em nov/2026.
UTC = timezone.utc
ROLE_ORDER = ("episodio", "curiosidade", "voce-lembra")
MIN_ADVANCE = timedelta(minutes=15)


class ScheduleError(RuntimeError):
    pass


def all_slots() -> list[dict]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    slots = data.get("slots", [])
    if len(slots) != 24 or len({x["id"] for x in slots}) != 24:
        raise ScheduleError("Lote exige 24 IDs diferentes (8 de cada formato).")
    from roteiro_para_storyboard import select_episode
    for index, row in enumerate(slots):
        expected_role = ROLE_ORDER[index % 3]
        if row["position"] != index + 1 or row["cycle"] != index // 3 + 1:
            raise ScheduleError("Ordem/numero do ciclo invalido: " + repr(row))
        if row["format"] != expected_role:
            raise ScheduleError(f"Ordem editorial invalida na posicao {index + 1}")
        ep = select_episode(row["id"])
        actual_role = "episodio" if ep.get("episode_number") else ep.get("format_type")
        if actual_role != expected_role:
            raise ScheduleError(f"Formato divergente no catalogo: {row['id']}")
        validate_hook_and_cta(ep)
    return slots


def validate_hook_and_cta(ep: dict) -> None:
    script = ep.get("script", "").strip()
    hook = ep.get("hook", "").strip()
    cta = ep.get("cta", "").strip()
    if not script or not hook or not cta:
        raise ScheduleError(f"Falta roteiro, gancho ou CTA em {ep.get('id')}")
    if not script.startswith(hook):
        raise ScheduleError(f"Gancho precisa ser as primeiras palavras: {ep['id']}")
    if not script.endswith(cta):
        raise ScheduleError(f"Inscricao deve fechar o roteiro: {ep['id']}")
    if "inscreva-se" not in cta.lower():
        raise ScheduleError(f"CTA final nao pede inscricao: {ep['id']}")
    words = len(script.split())
    if not 70 <= words <= 135:
        raise ScheduleError(
            f"Roteiro de {ep['id']} com {words} palavras. "
            "Revise a narracao para caber em 60 segundos."
        )


def initial_date(raw: str, *, now: datetime) -> date:
    if raw:
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise ScheduleError("Data invalida. Use AAAA-MM-DD, ex. 2026-11-05") from exc
    # For an expensive 24-video batch, prefer two full preparation days.
    return now.astimezone(BRASILIA).date() + timedelta(days=2)


def timestamps(start_day: date, hour: str, interval_minutes: int,
               slots: list[dict]) -> list[datetime]:
    if not 60 <= interval_minutes <= 7 * 24 * 60:
        raise ScheduleError("Intervalo deve ser de pelo menos 60 minutos.")
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", hour):
        raise ScheduleError("Hora invalida; use HH:MM, por exemplo 09:00.")
    hh, mm = map(int, hour.split(":"))
    start = datetime.combine(start_day, time(hh, mm), tzinfo=BRASILIA)
    return [(start + timedelta(minutes=i*interval_minutes)).astimezone(UTC)
            for i in range(len(slots))]


def episode_record(episode_id: str) -> Path:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", episode_id):
        raise ScheduleError("ID inseguro para nome de arquivo")
    return UPLOADS / "lote24-comprovantes" / f"{episode_id}.json"


def save_episode_record(episode_id: str, state: dict) -> None:
    """Protect against duplicate uploads if render/cache MP4 changes later."""
    target = episode_record(episode_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file():
        existing = json.loads(target.read_text(encoding="utf-8-sig"))
        if existing.get("video_id") != state.get("video_id"):
            raise ScheduleError(
                f"Conflito de video_id de {episode_id}; confira YouTube Studio."
            )
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def read_state(episode_id: str, profile: str) -> dict | None:
    marker = episode_record(episode_id)
    if marker.is_file():
        recorded = json.loads(marker.read_text(encoding="utf-8-sig"))
        if not recorded.get("video_id"):
            raise ScheduleError(
                f"Comprovante sem video_id de {episode_id}; verifique Studio."
            )
        return recorded
    path = CLIPS / episode_id / (
        f"{episode_id}-master-multicenas-personagens-v3-{profile}.mp4"
    )
    if not path.is_file():
        return None
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024*1024), b""):
            sha.update(block)
    state = UPLOADS / f"estado-upload-{sha.hexdigest()[:12]}.json"
    if not state.exists():
        return None
    stored = json.loads(state.read_text(encoding="utf-8-sig"))
    if stored.get("video_sha256") != sha.hexdigest() or not stored.get("video_id"):
        raise ScheduleError(
            f"Registro inconsistente/ambíguo de {episode_id}. Confira o YouTube Studio."
        )
    return stored


def confirmed_state(stored: dict, when: datetime, episode_id: str) -> None:
    from publicar_arquivo_otaku import parse_publish_at
    raw = str(stored.get("agendado_para") or "")
    if (stored.get("privacidade_solicitada") != "private"
            or stored.get("agendamento_confirmado") is not True
            or not raw
            or parse_publish_at(raw) != when):
        raise ScheduleError(
            f"{episode_id} ja foi enviado, mas NAO com o agendamento esperado. "
            "Nao duplicar nem sobrescrever; confira o video no YouTube Studio."
        )


def create_plan(slots: list[dict], times: list[datetime], *,
                start_day: date, hour: str, interval: int, profile: str) -> dict:
    return {
        "schema": "arquivo-otaku/youtube-native-24-schedules/v1",
        "start_date": start_day.isoformat(),
        "start_time": hour,
        "timezone": "America/Sao_Paulo",
        "interval_minutes": interval,
        "profile": profile,
        "slots": [
            {**row,
             "publish_at_utc": moment.isoformat().replace("+00:00", "Z"),
             "publish_at_brasilia": moment.astimezone(BRASILIA).isoformat()}
            for row, moment in zip(slots, times)
        ],
    }


def atomic_plan(value: dict) -> None:
    PLAN.parent.mkdir(parents=True, exist_ok=True)
    temporary = PLAN.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(PLAN)


def run_pipeline(parts: list[str]) -> int:
    return subprocess.run(parts, cwd=ROOT, check=False).returncode


def process(plan: dict, *, agendar: bool, max_new: int, model: str,
            profile: str, budget: int,
            clock: Callable[[], datetime] = lambda: datetime.now(UTC),
            reader: Callable[[str, str], dict | None] = read_state,
            execute: Callable[[list[str]], int] = run_pipeline) -> dict:
    if not 1 <= max_new <= 24:
        raise ScheduleError("Limite de uploads por execução: entre 1 e 24.")
    rows = plan["slots"]
    if len(rows) != 24:
        raise ScheduleError("Plano incompleto; nao agendar.")
    summary = {"confirmed": [], "planned": [], "new_uploads": 0}
    for row in rows:
        when = datetime.fromisoformat(row["publish_at_utc"].replace("Z", "+00:00"))
        episode_id = row["id"]
        local = when.astimezone(BRASILIA).strftime("%d/%m/%Y %H:%M")
        existing = reader(episode_id, profile)
        if existing:
            confirmed_state(existing, when, episode_id)
            if agendar:
                save_episode_record(episode_id, existing)
            print(f"[JA AGENDADO] {local} | {episode_id} | "
                  f"https://youtu.be/{existing['video_id']}", flush=True)
            summary["confirmed"].append(episode_id)
            continue
        if not agendar:
            print(f"[PLANO {row['position']:02d}/24] {local} | "
                  f"{row['format']} | {episode_id}", flush=True)
            summary["planned"].append(episode_id)
            continue
        if summary["new_uploads"] >= max_new:
            print(f"[PROXIMO LOTE] {local} | {episode_id}", flush=True)
            summary["planned"].append(episode_id)
            continue
        if when <= clock().astimezone(UTC) + MIN_ADVANCE:
            raise ScheduleError(
                f"Horario {local} esta vencido ou muito proximo para {episode_id}. "
                "Nenhum upload deste video foi feito. Nao altere horarios em um "
                "lote ja parcialmente publicado; confira os anteriores no Studio."
            )
        command = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(ROOT / "criar-publicar-short.ps1"),
            "-Id", episode_id, "-Modelo", model, "-Perfil", profile,
            "-MaxChamadas", str(budget),
            "-Publicar", "-Privacidade", "private",
            "-AgendarEm", row["publish_at_utc"],
        ]
        print(f"[PRODUZIR E AGENDAR {row['position']:02d}/24] {local} | "
              f"{episode_id}", flush=True)
        if execute(command) != 0:
            raise ScheduleError(
                f"Falhou producao/agendamento de {episode_id}; fila interrompida. "
                "Confira o YouTube Studio antes de tentar novamente."
            )
        verified = reader(episode_id, profile)
        if not verified:
            raise ScheduleError(
                f"Sem comprovante do upload {episode_id}. "
                "Interrompido para evitar duplicata."
            )
        confirmed_state(verified, when, episode_id)
        save_episode_record(episode_id, verified)
        print(f"[YOUTUBE AGENDOU] {local} | "
              f"https://youtu.be/{verified['video_id']}", flush=True)
        summary["confirmed"].append(episode_id)
        summary["new_uploads"] += 1
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="24 Shorts: 8 episodios, 8 curiosidades, 8 nostalgias, "
                    "agendamento nativo YouTube às 09:00 horario de Brasilia"
    )
    parser.add_argument("--data-inicio", default="",
                        help="AAAA-MM-DD; sem valor escolhe dois dias a frente")
    parser.add_argument("--hora-inicio", default="09:00")
    parser.add_argument("--intervalo-minutos", type=int, default=60)
    parser.add_argument("--limite", type=int, default=24,
                        help="quantidade maxima de uploads novos nesta execucao")
    parser.add_argument("--modelo", choices=("gpt-image-1.5", "gpt-image-2"),
                        default="gpt-image-1.5")
    parser.add_argument("--perfil", choices=("equilibrado", "vivo", "ultrassutil"),
                        default="equilibrado")
    parser.add_argument("--max-chamadas", type=int, default=45)
    parser.add_argument("--agendar", action="store_true",
                        help="AUTORIZACAO EXPLICITA para gerar IA, enviar e agendar")
    args = parser.parse_args(argv)
    if not 0 <= args.max_chamadas <= 180:
        parser.error("--max-chamadas deve estar entre 0 e 180 por video")
    slots = all_slots()
    now = datetime.now(UTC)
    saved = (json.loads(PLAN.read_text(encoding="utf-8-sig"))
             if PLAN.is_file() else None)
    if saved is not None:
        if (saved.get("schema") != "arquivo-otaku/youtube-native-24-schedules/v1"
                or len(saved.get("slots", [])) != 24):
            raise ScheduleError("Plano anterior invalido: revise antes de continuar.")
        if args.data_inicio and args.data_inicio != saved["start_date"]:
            raise ScheduleError("Plano existente usa outra data; nao remarcar videos publicados.")
        if args.hora_inicio != saved["start_time"] or args.intervalo_minutos != saved["interval_minutes"]:
            raise ScheduleError("Data/hora ou intervalo diferentes do plano existente.")
        if args.perfil != saved["profile"]:
            raise ScheduleError("Perfil diferente do lote em andamento.")
        if [r["id"] for r in saved["slots"]] != [r["id"] for r in slots]:
            raise ScheduleError("Catalogo editorial alterado apos iniciar a fila.")
        plan = saved
    else:
        day = initial_date(args.data_inicio, now=now)
        times = timestamps(day, args.hora_inicio, args.intervalo_minutos, slots)
        plan = create_plan(
            slots, times, start_day=day, hour=args.hora_inicio,
            interval=args.intervalo_minutos, profile=args.perfil
        )
    print(f"[LOTE 24] Inicio: {plan['start_date']} {plan['start_time']} "
          f"America/Sao_Paulo | a cada {plan['interval_minutes']} minutos", flush=True)
    if args.agendar:
        if not (ROOT / ".secrets" / "youtube-oauth-client.json").is_file():
            raise ScheduleError(
                "OAuth do canal ausente. Configure .secrets/youtube-oauth-client.json "
                "antes de gerar videos ou consumir cota de IA."
            )
        if saved is None:
            if datetime.fromisoformat(plan["slots"][0]["publish_at_utc"].replace("Z","+00:00")) <= now + MIN_ADVANCE:
                raise ScheduleError("Primeiro horario muito proximo. Escolha outra data.")
            atomic_plan(plan)
            print(f"[PLANO FIXADO] {PLAN}. Nao alterar o agendamento ao retomar.",
                  flush=True)
    else:
        print("[PREVIA] Nao produz, nao envia e nao agenda; sem gasto de IA.", flush=True)
    result = process(
        plan, agendar=args.agendar, max_new=args.limite,
        model=args.modelo, profile=args.perfil, budget=args.max_chamadas
    )
    print(f"[RESUMO] Confirmados: {len(result['confirmed'])}/24 | "
          f"Novos uploads nesta execucao: {result['new_uploads']} | "
          f"Restantes: {len(result['planned'])}.", flush=True)
    if result["planned"] and args.agendar:
        print("[ACAO] Para continuar, execute o MESMO comando e mesma data. "
              "Os videos confirmados serao reconhecidos e ignorados.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ScheduleError, ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print("[BLOQUEADO] " + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
