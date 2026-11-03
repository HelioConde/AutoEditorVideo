"""Regression: 24-content rotation and safe native YouTube scheduling (offline)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import agendar_24_shorts as batch
import publicar_arquivo_otaku as publisher
from roteiro_para_storyboard import select_episode, build_storyboard
from metadata_shorts import publisher_episode


def test_24_original_scripts_have_exactly_8_of_each_type():
    slots = batch.all_slots()
    assert len(slots) == 24
    assert len({s["id"] for s in slots}) == 24
    for kind in batch.ROLE_ORDER:
        assert sum(x["format"] == kind for x in slots) == 8
    assert [r["format"] for r in slots] == list(batch.ROLE_ORDER)*8
    assert slots[0]["id"] == "102-death-note-ep02"
    assert slots[-1]["id"] == "308-death-note-lembra-universidade"
    assert "101-death-note-ep01" not in [r["id"] for r in slots]


def test_hooks_ctas_voices_and_metadata_have_plausible_length():
    for slot in batch.all_slots():
        ep = select_episode(slot["id"])
        batch.validate_hook_and_cta(ep)
        assert ep["script"].startswith(ep["hook"])
        assert ep["script"].endswith(ep["cta"])
        assert ep["hook"] not in ep["script"][len(ep["hook"]):]
        assert "Inscreva-se" in ep["cta"] or "inscreva-se" in ep["cta"]
        assert 70 <= len(ep["script"].split()) <= 135
        metadata = publisher_episode(ep)
        assert metadata["titulo_youtube"] == ep["title"]
        assert "#Shorts" in metadata["descricao_youtube"]
        assert metadata["capa_texto"] == ep["cover"]
        # Storyboards are deterministic, offline and must preserve content.
        story = build_storyboard(ep, max_hold=6)
        assert story["scenes"] and story["script"] == ep["script"]


def test_brasilia_first_hour_9_am_and_24_continuous_hourly_slots():
    slots = batch.all_slots()
    times = batch.timestamps(date(2026, 11, 5), "09:00", 60, slots)
    assert len(times) == 24
    assert times[0] == datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)
    assert times[23] == datetime(2026, 11, 6, 11, 0, tzinfo=timezone.utc)
    assert all(times[i+1]-times[i] == timedelta(hours=1) for i in range(23))
    plan = batch.create_plan(slots, times, start_day=date(2026, 11, 5),
                             hour="09:00", interval=60, profile="equilibrado")
    assert plan["slots"][0]["publish_at_brasilia"].startswith("2026-11-05T09:00:")
    assert plan["slots"][-1]["publish_at_brasilia"].startswith("2026-11-06T08:00:")


def test_first_date_defaults_to_two_days_for_rendering_and_upload():
    now = datetime(2026, 11, 3, 11, 23, tzinfo=timezone.utc)
    assert batch.initial_date("", now=now) == date(2026, 11, 5)
    assert batch.initial_date("2026-11-07", now=now) == date(2026, 11, 7)
    with pytest.raises(batch.ScheduleError, match="Data invalida"):
        batch.initial_date("amanha", now=now)


def test_preview_has_zero_uploads():
    slots = batch.all_slots()
    times = batch.timestamps(date(2026, 11, 5), "09:00", 60, slots)
    plan = batch.create_plan(slots, times, start_day=date(2026, 11, 5),
                             hour="09:00", interval=60, profile="equilibrado")
    called = []
    outcome = batch.process(
        plan, agendar=False, max_new=24,
        model="gpt-image-1.5", profile="equilibrado", budget=45,
        reader=lambda *_: None,
        execute=lambda command: called.append(command),
    )
    assert len(outcome["planned"]) == 24
    assert not outcome["confirmed"] and outcome["new_uploads"] == 0
    assert called == []


def test_native_scheduling_is_private_and_requires_a_future_time():
    target = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    assert publisher.schedule_status("private", target, now=now) == {
        "privacyStatus": "private", "publishAt": "2026-11-05T12:00:00Z"
    }
    assert publisher.confirmed_schedule(
        {"status": {"privacyStatus": "private", "publishAt": "2026-11-05T12:00:00.000Z"}},
        target
    )
    assert not publisher.confirmed_schedule(
        {"status": {"privacyStatus": "public", "publishAt": "2026-11-05T12:00:00Z"}},
        target
    )
    with pytest.raises(ValueError, match="private"):
        publisher.schedule_status("public", target, now=now)
    with pytest.raises(ValueError, match="15 minutos"):
        publisher.schedule_status("private", now, now=now)
    with pytest.raises(ValueError, match="fuso"):
        publisher.parse_publish_at("2026-11-05T09:00:00")
    assert publisher.parse_publish_at("2026-11-05T09:00:00-03:00") == target


def test_schedule_only_three_new_videos_then_safe_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "UPLOADS", tmp_path)
    slots = batch.all_slots()
    times = batch.timestamps(date(2026, 11, 5), "09:00", 60, slots)
    plan = batch.create_plan(slots, times, start_day=date(2026, 11, 5),
                             hour="09:00", interval=60, profile="equilibrado")
    scheduled = {}
    calls = []
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    def read(id, profile):
        return scheduled.get(id)
    def upload(command):
        calls.append(command)
        episode_id = command[command.index("-Id") + 1]
        target = command[command.index("-AgendarEm") + 1]
        scheduled[episode_id] = {
            "video_id": "test_" + episode_id,
            "agendado_para": target,
            "privacidade_solicitada": "private",
            "agendamento_confirmado": True,
        }
        return 0
    first = batch.process(
        plan, agendar=True, max_new=3,
        model="gpt-image-1.5", profile="equilibrado", budget=20,
        clock=lambda: now, reader=read, execute=upload,
    )
    assert first["new_uploads"] == 3
    assert len(first["planned"]) == 21
    assert len(first["confirmed"]) == 3
    assert len(calls) == 3
    assert all("-Publicar" in x and "-Privacidade" in x for x in calls)
    assert all(x[x.index("-Privacidade")+1] == "private" for x in calls)
    second = batch.process(
        plan, agendar=True, max_new=24,
        model="gpt-image-1.5", profile="equilibrado", budget=20,
        clock=lambda: now, reader=read, execute=upload,
    )
    assert second["new_uploads"] == 21
    assert len(second["confirmed"]) == 24
    assert len(calls) == 24
    assert len(list((tmp_path / "lote24-comprovantes").glob("*.json"))) == 24
    third = batch.process(
        plan, agendar=True, max_new=24,
        model="gpt-image-1.5", profile="equilibrado", budget=20,
        clock=lambda: now, reader=read, execute=upload,
    )
    assert third["new_uploads"] == 0
    assert len(calls) == 24


def test_wrong_schedule_and_existing_public_video_block_uploads():
    slots = batch.all_slots()
    times = batch.timestamps(date(2026, 11, 5), "09:00", 60, slots)
    plan = batch.create_plan(slots, times, start_day=date(2026, 11, 5),
                             hour="09:00", interval=60, profile="equilibrado")
    wrong = {
        "video_id": "already_public",
        "agendado_para": "2026-11-05T12:00:00Z",
        "privacidade_solicitada": "public",
        "agendamento_confirmado": True,
    }
    with pytest.raises(batch.ScheduleError, match="NAO com o agendamento"):
        batch.process(
            plan, agendar=True, max_new=24, model="gpt-image-1.5",
            profile="equilibrado", budget=30,
            clock=lambda: datetime(2026, 11, 3, 12, tzinfo=timezone.utc),
            reader=lambda *args: wrong,
            execute=lambda command: pytest.fail("must not upload duplicates"),
        )


def test_expired_slot_stops_without_publishing():
    slots = batch.all_slots()
    times = batch.timestamps(date(2026, 11, 5), "09:00", 60, slots)
    plan = batch.create_plan(slots, times, start_day=date(2026, 11, 5),
                             hour="09:00", interval=60, profile="equilibrado")
    with pytest.raises(batch.ScheduleError, match="vencido"):
        batch.process(
            plan, agendar=True, max_new=24, model="gpt-image-1.5",
            profile="equilibrado", budget=30,
            clock=lambda: datetime(2026, 11, 5, 11, 55, tzinfo=timezone.utc),
            reader=lambda *_: None,
            execute=lambda command: pytest.fail("must not upload close to slot"),
        )


def test_invalid_count_and_interval_fail_before_any_upload():
    slots = batch.all_slots()
    with pytest.raises(batch.ScheduleError, match="60 minutos"):
        batch.timestamps(date(2026, 11, 5), "09:00", 59, slots)
    with pytest.raises(batch.ScheduleError, match="Hora invalida"):
        batch.timestamps(date(2026, 11, 5), "25:00", 60, slots)


def test_receipt_survives_deleted_mp4_and_prevents_duplicate_id(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "UPLOADS", tmp_path)
    monkeypatch.setattr(batch, "CLIPS", tmp_path / "clips")
    episode_id = "102-death-note-ep02"
    record = {
        "video_id": "youtube_abc123",
        "agendamento_confirmado": True,
        "privacidade_solicitada": "private",
        "agendado_para": "2026-11-05T12:00:00Z",
    }
    batch.save_episode_record(episode_id, record)
    assert batch.read_state(episode_id, "equilibrado") == record
    other = dict(record, video_id="other_video")
    with pytest.raises(batch.ScheduleError, match="Conflito de video_id"):
        batch.save_episode_record(episode_id, other)


def test_invalid_record_name_cannot_escape_schedule_folder():
    with pytest.raises(batch.ScheduleError, match="inseguro"):
        batch.episode_record("../../secrets")
