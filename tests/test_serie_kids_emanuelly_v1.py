"""Emanuelly story pipeline: reference photo, finite image budget and no uploads."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import serie_kids_emanuelly_v1 as story
import organizar_videos_por_canal as archive
import kids_emanuelly_continuidade_v2 as continuity


def reference(tmp_path, *, color=(120, 70, 210)) -> Path:
    path = tmp_path / "assets/referencias-privadas/emanuelly-elenco.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1024, 1536), color).save(path)
    install_fake_isolated_references(path)
    for name in ("Wondertrail _Main Theme_.mp3", "Wondertrail _Main Theme_2.mp3"):
        (tmp_path / name).write_bytes(b"ID3" + b"\x00" * 120_000)
    return path


def install_fake_isolated_references(photo: Path):
    for role in continuity.REFERENCE_ROLES:
        target = continuity.isolated_reference(photo, role)
        Image.new("RGB", (1024, 1536), (20, 70, 155)).save(target)
        target.with_suffix(".json").write_text(json.dumps({
            "schema": continuity.POLICY,
            "model": continuity.MODEL,
            "reference_role": role,
            "source_sha256": story.sha(photo.read_bytes()),
            "derived_sha256": story.sha(target.read_bytes()),
            "prompt_signature": continuity.reference_signature(photo.read_bytes(), role),
        }), encoding="utf-8")



def fake_png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (1024, 1536), (180, 120, 210)).save(out, format="PNG")
    return out.getvalue()


def test_four_parts_serialized_and_no_upload():
    parts = story.load_parts()
    assert [p["part"] for p in parts] == [1, 2, 3, 4]
    assert sum(len(p["segments"]) for p in parts) == 37
    for p in parts:
        assert p["narration"].startswith(p["segments"][0]["spoken_text"])
        assert p["narration"].endswith(p["segments"][-1]["spoken_text"])
        episode = story.episode_for_tts(p)
        assert len(episode["scenes"]) == 5
        assert episode["script"] == p["narration"]
        assert len(episode["kids_pacing"]["segments"]) == len(p["segments"])
        assert [i["scene"] for i in episode["kids_pacing"]["segments"]] == sorted(
            i["scene"] for i in episode["kids_pacing"]["segments"]
        )
        assert all(i["pause_after_s"] >= 1.8 for i in episode["kids_pacing"]["segments"]
                   if i["cue"].endswith("-question"))


def test_reference_never_uploaded_to_github_or_used_as_static_final_frame(tmp_path):
    path = reference(tmp_path)
    installed = story.install_reference(path, tmp_path / "assets/referencias-privadas/canon.png")
    assert installed["github_upload"] is False
    assert installed["sha256"]
    assert (tmp_path / "assets/referencias-privadas/canon.png").is_file()
    assert "/assets/referencias-privadas/" in (ROOT / ".gitignore").read_text()
    assert "videos().insert" not in (ROOT / "scripts/serie_kids_emanuelly_v1.py").read_text()


def test_strict_missing_reference_and_budget_zero_do_not_call_ai(tmp_path):
    part = story.load_parts()[0]
    with pytest.raises(FileNotFoundError, match="Foto de referencia"):
        story.image_plan([part], tmp_path / "not-found.png", "gpt-image-2", tmp_path)
    photo = reference(tmp_path)
    called = []
    def editor(*args, **kwargs):
        called.append(True)
        return fake_png()
    with pytest.raises(ValueError, match="NENHUMA chamada"):
        story.make_images([part], reference=photo, budget=0, root=tmp_path,
                          editor=editor, key_provider=lambda: "private")
    assert not called


def test_reference_supplied_to_every_image_edit_and_cache_is_idempotent(tmp_path):
    part = story.load_parts()[0]
    photo = reference(tmp_path)
    observations = []
    def editor(reference_path, prompt, model, key, *, transparent):
        observations.append((reference_path, prompt, model, key, transparent))
        return fake_png()
    result = story.make_images([part], reference=photo, budget=9, root=tmp_path,
                               editor=editor, key_provider=lambda: "test-key")
    assert result["generated"] == 9
    assert len(observations) == 9
    assert all(item[0] == continuity.isolated_reference(photo, "emanuelly-solo")
               for item in observations)
    assert all("VISIBLE CAST: EXACTLY ONE CHARACTER" in item[1] for item in observations)
    assert all("Scene 08 must NOT show ANY second character" in item[1] for item in observations)
    assert all(item[2] == "gpt-image-2" and item[3] == "test-key"
               and item[4] is False for item in observations)
    assert all(story.valid_frame(part, beat, "gpt-image-2",
                                story.reference_hash(photo), root=tmp_path)
               for beat in part["segments"])
    again = story.make_images([part], reference=photo, budget=0, root=tmp_path,
                              editor=lambda *_a, **_kw: pytest.fail("Must be cached"),
                              key_provider=lambda: pytest.fail("No key needed"))
    assert again["generated"] == 0
    assert again["cached"] == 9
    assert not (tmp_path / "assets/gerados/kids-emanuelly" / part["id"] / "final.mp4").exists()


def test_reference_change_blocks_old_cache_until_explicit_rebuild(tmp_path):
    part = story.load_parts()[0]
    photo = reference(tmp_path)
    story.make_images([part], reference=photo, budget=9, root=tmp_path,
                      editor=lambda *_a, **_kw: fake_png(),
                      key_provider=lambda: "test-key")
    Image.new("RGB", (1024, 1536), (50, 130, 190)).save(photo)
    with pytest.raises(ValueError, match="outro roteiro/referencia"):
        story.make_images([part], reference=photo, budget=9, root=tmp_path,
                          editor=lambda *_a, **_kw: pytest.fail("No overwrite"))
    install_fake_isolated_references(photo)
    recreated = story.make_images([part], reference=photo, budget=9, root=tmp_path,
                                  regenerate=True,
                                  editor=lambda *_a, **_kw: fake_png(),
                                  key_provider=lambda: "test-key")
    assert recreated["generated"] == 9
    hist = tmp_path / "assets/gerados/kids-emanuelly" / part["id"] / "historico-imagens"
    assert len(list(hist.glob("*.png"))) == 9


def test_reference_install_requires_explicit_replace(tmp_path):
    first = reference(tmp_path)
    other = tmp_path / "new.png"
    Image.new("RGB", (1024, 1536), (85, 95, 105)).save(other)
    with pytest.raises(ValueError, match="SubstituirReferencia"):
        story.install_reference(other, first)
    assert story.reference_hash(first) != story.reference_hash(other)
    result = story.install_reference(other, first, replace=True)
    assert result["status"] == "instalada_localmente"
    assert len(list((first.parent / "historico").glob("*.png"))) == 1


def test_scene_props_align_with_cached_words_and_private_images(tmp_path, monkeypatch):
    part = story.load_parts()[0]
    photo = reference(tmp_path)
    story.make_images([part], reference=photo, budget=9, root=tmp_path,
                      editor=lambda *_a, **_kw: fake_png(),
                      key_provider=lambda: "test-key")
    episode = story.episode_for_tts(part)
    from kids_narracao_acolhedora_v1 import signature
    segments = []
    words = []
    clock = 0.0
    for index, beat in enumerate(episode["kids_pacing"]["segments"]):
        segments.append({
            **beat, "segment": index,
            "start_s": clock,
            "speech_end_s": clock + 3.75,
            "end_s": clock + 3.75 + beat["pause_after_s"],
        })
        words.extend([
            {"segment": index, "start": clock + .2, "end": clock + .5, "text": "Era"},
            {"segment": index, "start": clock + .7, "end": clock + 1.0, "text": "uma"},
            {"segment": index, "start": clock + 1.2, "end": clock + 1.5, "text": "vez"},
        ])
        clock += 3.75 + beat["pause_after_s"]
    directory = story.output_for(part, tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    sound = b"mock audio" * 2000
    (directory / "narracao.mp3").write_bytes(sound)
    (directory / "marcacoes-voz.json").write_text(json.dumps({
        "script_sha256": story.sha(part["narration"].encode()),
        "pacing_sha256": signature(episode["kids_pacing"]),
        "voice": story.VOICE, "rate": story.RATE,
        "mp3_sha256": story.sha(sound), "words": words,
        "segments": segments, "duration_s": clock,
    }), encoding="utf-8")
    monkeypatch.setattr(story, "audio_seconds", lambda _p: clock)
    props, location = story.build_props(part, reference=photo, root=tmp_path)
    assert location.is_file()
    assert props["madeForKids"] is True
    assert len(props["frames"]) == len(part["segments"])
    assert len(props["captions"]) == len(words) // 3
    assert all(a["endFrame"] == b["startFrame"]
               for a, b in zip(props["frames"], props["frames"][1:]))
    assert props["durationFrames"] <= 1800
    assert all("quadro-" in frame["image"] for frame in props["frames"])
    assert props["frames"][-1]["endFrame"] == props["durationFrames"]
    assert not any("referencias-privadas" in str(item) for item in props["frames"])


def test_existing_mp4_with_mismatched_voice_is_not_reused(tmp_path):
    part = story.load_parts()[0]
    photo = reference(tmp_path)
    folder = story.output_for(part, tmp_path)
    folder.mkdir(parents=True)
    (folder / "final.mp4").write_bytes(b"prior video" * 22000)
    (folder / "qa-local.json").write_text(json.dumps({
        "video_sha256": story.sha((folder / "final.mp4").read_bytes()),
        "script_sha256": story.sha(part["narration"].encode()),
        "reference_sha256": story.reference_hash(photo),
        "model": "gpt-image-2",
        "image_sha256": [], "voice_sha256": "old",
    }))
    with pytest.raises(ValueError, match="outro roteiro ou referencia"):
        story.render(part, root=tmp_path, reference=photo)


def test_new_story_videos_are_archived_under_kids(tmp_path):
    part = story.load_parts()[0]
    mp4 = story.output_for(part, tmp_path) / "final.mp4"
    mp4.parent.mkdir(parents=True)
    mp4.write_bytes(b"pretend mp4")
    file = archive.classify(mp4, root=tmp_path)
    assert file is not None and file.channel == "Kids"
    assert file.episode == part["id"]
    videos, unknown = archive.scan(tmp_path)
    assert len(videos) == 1 and videos[0].source == mp4
    assert not unknown
