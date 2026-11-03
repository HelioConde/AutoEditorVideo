"""Offline tests: one-hour paced releases must not upload early or duplicate."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import publicar_recap_hourly as hourly

ID2 = "102-death-note-ep02"
ID3 = "103-death-note-ep03"


def record(id: str, at: datetime, privacy: str = "public") -> hourly.UploadRecord:
    return hourly.UploadRecord(id, f"vid_{id}", privacy, at)


def test_default_experiment_cycles_between_content_formats():
    ids = hourly.DEFAULT_IDS
    assert ids == (
        ID2, "201-death-note-rosto-nome",
        "301-death-note-voce-lembra-justica", ID3,
    )
    catalog = hourly.registered_episodes()
    assert all(i in catalog for i in ids)
    assert tuple(hourly.editorial_role(catalog[i]) for i in ids) == (
        "episodio", "curiosidade", "voce-lembra", "episodio",
    )
    assert hourly.DEFAULT_MINUTES == 60


def test_publication_is_explicit_with_default_off(monkeypatch):
    calls = []
    monkeypatch.setattr(hourly, "run_upload", lambda args: calls.append(args) or 0)
    monkeypatch.setattr(hourly, "existing_upload", lambda *args: None)
    assert hourly.main([]) == 0
    assert not calls


def test_existing_ep2_waits_until_exact_hour_for_ep3():
    start = datetime(2026, 11, 3, 10, 20, tzinfo=timezone.utc)
    ep2_at = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    current = [start]
    items = {ID2: record(ID2, ep2_at)}
    calls = []
    delays = []
    def reader(episode_id, profile):
        return items.get(episode_id)
    def executor(command):
        calls.append(command)
        items[ID3] = record(ID3, current[0])
        return 0
    def nap(seconds):
        assert 0 < seconds <= 60
        delays.append(seconds)
        current[0] += timedelta(seconds=seconds)
    results = hourly.process(
        [ID2, ID3], minutes=60, privacy="public",
        profile="equilibrado", model="gpt-image-1.5", budget=0,
        publish=True, reader=reader, execute=executor,
        clock=lambda: current[0], sleep=nap,
    )
    assert len(calls) == 1
    assert "-Id" in calls[0] and ID3 in calls[0]
    assert current[0] == ep2_at + timedelta(hours=1)
    assert sum(delays) == 40 * 60
    assert [r.episode_id for r in results] == [ID2, ID3]


def test_two_fresh_episodes_are_one_hour_apart():
    current = [datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)]
    published = {}
    uploads = []
    def reader(episode_id, _profile):
        return published.get(episode_id)
    def executor(command):
        episode_id = command[command.index("-Id") + 1]
        uploads.append((episode_id, current[0]))
        published[episode_id] = record(episode_id, current[0])
        return 0
    def nap(seconds):
        current[0] += timedelta(seconds=seconds)
    hourly.process(
        [ID2, ID3], minutes=60, privacy="public",
        profile="equilibrado", model="gpt-image-1.5", budget=45,
        publish=True, reader=reader, execute=executor,
        clock=lambda: current[0], sleep=nap,
    )
    assert [u[0] for u in uploads] == [ID2, ID3]
    assert uploads[1][1] - uploads[0][1] == timedelta(hours=1)


def test_no_duplicate_if_both_already_uploaded():
    t = datetime(2026, 11, 3, 11, 0, tzinfo=timezone.utc)
    items = {ID2: record(ID2, t), ID3: record(ID3, t + timedelta(hours=1))}
    def fail(*_args, **_kwargs):
        pytest.fail("A previously confirmed episode must not be uploaded again")
    rows = hourly.process(
        [ID2, ID3], minutes=60, privacy="public", profile="equilibrado",
        model="gpt-image-1.5", budget=0, publish=True,
        reader=lambda i, _: items.get(i), execute=fail, sleep=fail,
    )
    assert len(rows) == 2


def test_wrong_privacy_fails_before_next_video():
    t = datetime(2026, 11, 3, 11, 0, tzinfo=timezone.utc)
    with pytest.raises(hourly.SchedulingError, match="privacidade"):
        hourly.process(
            [ID2, ID3], minutes=60, privacy="public",
            profile="equilibrado", model="gpt-image-1.5", budget=0,
            publish=True, reader=lambda i, _: record(i, t, "private"),
            execute=lambda *_: pytest.fail("Must not upload"),
        )


def test_failed_ep2_stops_entire_sequence():
    now = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    attempts = []
    def execute(command):
        attempts.append(command)
        return 1
    with pytest.raises(hourly.SchedulingError, match="Sequencia interrompida"):
        hourly.process(
            [ID2, ID3], minutes=60, privacy="public", profile="equilibrado",
            model="gpt-image-1.5", budget=45, publish=True,
            reader=lambda *_: None, execute=execute, clock=lambda: now,
            sleep=lambda *_: pytest.fail("Should never wait after failure"),
        )
    assert len(attempts) == 1


def test_rejects_short_interval_duplicate_ids_and_unknown_episode():
    base = dict(privacy="public", profile="equilibrado", model="gpt-image-1.5",
                budget=45, publish=False)
    with pytest.raises(hourly.SchedulingError, match="60 minutos"):
        hourly.process([ID2, ID3], minutes=59, **base)
    with pytest.raises(hourly.SchedulingError, match="distintos"):
        hourly.process([ID2, ID2], minutes=60, **base)
    with pytest.raises(hourly.SchedulingError, match="nao cadastrado"):
        hourly.process([ID2, "104-death-note-ep04"], minutes=60, **base)


def test_uploaded_state_requires_matching_mp4_hash_and_timestamp(tmp_path, monkeypatch):
    clips = tmp_path / "videos"
    logs = tmp_path / "logs"
    monkeypatch.setattr(hourly, "SHORTS", clips)
    monkeypatch.setattr(hourly, "PUBLICATIONS", logs)
    video = hourly.video_file(ID2, "equilibrado")
    video.parent.mkdir(parents=True)
    video.write_bytes(b"fake video bytes")
    assert hourly.existing_upload(ID2, "equilibrado") is None
    sha = hashlib.sha256(video.read_bytes()).hexdigest()
    state_file = logs / f"estado-upload-{sha[:12]}.json"
    logs.mkdir()
    state = {
        "video_sha256": sha,
        "video_id": "abc1234",
        "enviado_em": "2026-11-03T10:00:00+00:00",
        "privacidade_solicitada": "public",
    }
    state_file.write_text(json.dumps(state), encoding="utf-8")
    found = hourly.existing_upload(ID2, "equilibrado")
    assert found.youtube_url == "https://youtu.be/abc1234"
    assert found.published_at.tzinfo is not None
    state["video_sha256"] = "wrong"
    state_file.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(hourly.SchedulingError, match="hash"):
        hourly.existing_upload(ID2, "equilibrado")


def test_new_content_has_original_scripts_and_correct_youtube_metadata():
    from metadata_shorts import publisher_episode
    from roteiro_para_storyboard import select_episode, build_storyboard
    for episode_id, role in (
        ("201-death-note-rosto-nome", "curiosidade"),
        ("301-death-note-voce-lembra-justica", "voce-lembra"),
    ):
        item = select_episode(episode_id)
        assert item["format_type"] == role
        assert item["series"] == "Death Note"
        assert "Inscreva-se" in item["script"] or "inscreva-se" in item["script"]
        assert 80 <= len(item["script"].split()) <= 135
        assert item["cover"] and len(item["cover"]) >= 8
        meta = publisher_episode(item)
        assert meta["titulo_youtube"] == item["title"]
        assert "geradas por IA" in meta["descricao_youtube"]
        assert "#Shorts" in meta["descricao_youtube"]
        scenes = build_storyboard(item, max_hold=6)["scenes"]
        assert 2 <= len(scenes) <= 60


def test_full_editorial_cycle_publishes_four_formats_in_order_with_hourly_intervals():
    beginning = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    current = [beginning]
    published = {}
    uploads = []
    def reader(episode_id, profile):
        return published.get(episode_id)
    def execute(command):
        episode_id = command[command.index("-Id") + 1]
        uploads.append((episode_id, current[0]))
        published[episode_id] = record(episode_id, current[0])
        return 0
    def nap(seconds):
        current[0] += timedelta(seconds=seconds)
    results = hourly.process(
        list(hourly.DEFAULT_IDS), minutes=60, privacy="public",
        profile="equilibrado", model="gpt-image-1.5", budget=45,
        publish=True, reader=reader, execute=execute,
        clock=lambda: current[0], sleep=nap,
    )
    assert [row[0] for row in uploads] == list(hourly.DEFAULT_IDS)
    assert [row.episode_id for row in results] == list(hourly.DEFAULT_IDS)
    assert all(
        uploads[i+1][1] - uploads[i][1] >= timedelta(hours=1)
        for i in range(len(uploads)-1)
    )


def test_no_reordering_if_old_schedule_already_published_episode_three():
    t = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)
    published = {ID2: record(ID2, t), ID3: record(ID3, t + timedelta(hours=1))}
    with pytest.raises(hourly.SchedulingError, match="fora de ordem"):
        hourly.process(
            list(hourly.DEFAULT_IDS), minutes=60, privacy="public",
            profile="equilibrado", model="gpt-image-1.5", budget=45,
            publish=True, reader=lambda i, _: published.get(i),
            execute=lambda *_: pytest.fail("No uploads after prior EP03 publication"),
        )
