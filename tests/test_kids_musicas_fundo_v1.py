"""Two supplied Kids MP3: safe local mixing metadata and cache invalidation."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from kids_musicas_fundo_v1 import (
    TRACKS, MUSIC_POLICY, MUSIC_VOLUME, choose_track,
    music_signature, prepare_kids_music,
)
import serie_kids_emanuelly_v1 as story


def fake_songs(root):
    for name, _target in TRACKS:
        (root / name).write_bytes(b"ID3" + b"\x00" * 120_000)


def test_real_music_sources_added_by_creator_to_main():
    # Tests run on a Git checkout. Do not open or redistribute these sources.
    assert len(TRACKS) == 2
    assert all((ROOT / name).is_file() for name, _ in TRACKS)


def test_tracks_are_used_in_kids_only_with_stable_rotation():
    assert [choose_track(p["id"])[0] for p in story.load_parts()] == [0, 1, 0, 1]
    assert choose_track("kids-001-estrela-azul")[0] == 0
    assert choose_track("kids-002-cinco-passarinhos")[0] == 1
    assert choose_track("kids-003-formas-casinha")[0] == 0
    with pytest.raises(ValueError, match="nao autorizada"):
        choose_track("game-001-minecraft-um-coracao")
    with pytest.raises(ValueError, match="nao autorizada"):
        choose_track("003-death-note-xadrez")


def test_music_copies_only_to_remotion_build_assets(tmp_path):
    fake_songs(tmp_path)
    s1 = prepare_kids_music(tmp_path, "kids-emanuelly-ep01-p01-ovo-azul")
    s2 = prepare_kids_music(tmp_path, "kids-emanuelly-ep01-p02-nascimento")
    assert s1["schema"] == s2["schema"] == MUSIC_POLICY
    assert s1["source_name"] != s2["source_name"]
    assert s1["audio"] != s2["audio"]
    assert s1["sha256"] == music_signature(tmp_path, "kids-emanuelly-ep01-p01-ovo-azul")
    assert s2["sha256"] == music_signature(tmp_path, "kids-emanuelly-ep01-p02-nascimento")
    assert s1["rights_review"] == "pending_before_publication"
    assert s1["volume"] == pytest.approx(.075)
    assert 0 < MUSIC_VOLUME <= .12
    for meta in (s1, s2):
        dest = tmp_path / "motion-remotion/public" / meta["audio"]
        assert dest.read_bytes()[:3] == b"ID3"
    assert all((tmp_path / name).is_file() for name, _ in TRACKS)


def test_update_source_music_replaces_only_public_copy(tmp_path):
    fake_songs(tmp_path)
    episode = "kids-emanuelly-ep01-p03-poder-agua"
    original = prepare_kids_music(tmp_path, episode)
    destination = tmp_path / "motion-remotion/public" / original["audio"]
    assert destination.is_file()
    name = choose_track(episode)[1]
    (tmp_path / name).write_bytes(b"ID3" + b"\x01" * 120_000)
    updated = prepare_kids_music(tmp_path, episode)
    assert updated["sha256"] != original["sha256"]
    assert destination.read_bytes() == (tmp_path / name).read_bytes()


def test_missing_song_blocks_kids_only(tmp_path):
    with pytest.raises(FileNotFoundError, match="Faixa Kids ausente"):
        prepare_kids_music(tmp_path, "kids-001-estrela-azul")


def test_copyright_status_and_volume_are_exposed_to_qa():
    music_code = (ROOT / "motion-remotion/src/kids-background-music.tsx").read_text(encoding="utf-8")
    assert "loop volume=" in music_code
    assert "fadeIn" in music_code and "fadeOut" in music_code
    assert "Math.min(0.12" in music_code
    en_code = (ROOT / "motion-remotion/src/emanuelly-short.tsx").read_text(encoding="utf-8")
    pilot_code = (ROOT / "motion-remotion/src/pilot-short.tsx").read_text(encoding="utf-8")
    assert "<KidsBackgroundMusic" in en_code
    assert "kids&&<KidsBackgroundMusic" in pilot_code
    main = (ROOT / "scripts/serie_kids_emanuelly_v1.py").read_text(encoding="utf-8")
    assert '"music_sha256": music_signature' in main
    assert '"music_rights_review": "pending_before_publication"' in main
