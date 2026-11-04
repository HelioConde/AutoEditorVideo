"""Regressions: do not reveal Fofinho or future cast in frames 03/08."""
from __future__ import annotations
import io
import json
from pathlib import Path
import sys
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import serie_kids_emanuelly_v1 as maker
import kids_emanuelly_continuidade_v2 as guard


def fresh_photo(tmp_path):
    file = tmp_path / "assets" / "referencias-privadas" / "emanuelly-elenco.png"
    file.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1024, 1536), (80, 91, 120)).save(file)
    return file


def image_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (1024, 1536), (220, 170, 90)).save(buf, format="PNG")
    return buf.getvalue()


def extract_photo(tmp_path):
    path = fresh_photo(tmp_path)
    events = []
    def isolated_edit(source, prompt, model, key, *, transparent):
        events.append((source, prompt, model))
        return image_bytes()
    result = guard.prepare_isolated_references(
        path, budget=2, editor=isolated_edit, key_provider=lambda: "unused"
    )
    assert result["new_calls"] == 2
    assert all(entry[0] == path for entry in events)
    assert all(entry[2] == "gpt-image-2" for entry in events)
    assert "Only ONE child" in events[0][1]
    assert "EXACTLY TWO subjects" in events[1][1]
    for role in guard.REFERENCE_ROLES:
        iso, digest = guard.check_isolated_ref(path, role)
        assert iso.is_file() and digest == maker.sha(iso.read_bytes())
        assert iso != path
    return path


def test_every_frame_before_born_is_girl_only():
    parts = maker.load_parts()
    assert [guard.role_for(parts[0], b) for b in parts[0]["segments"]] == [
        "emanuelly-solo"
    ] * 9
    assert [guard.role_for(parts[1], b) for b in parts[1]["segments"]] == (
        ["emanuelly-solo"] * 5 + ["emanuelly-fofinho"] * 5
    )
    for part in parts[2:]:
        assert set(guard.role_for(part, b) for b in part["segments"]) == {
            "emanuelly-fofinho"
        }
    assert set(guard.CAST_LOCK) == {
        "fofinha-arco-iris", "fofinha-rosa", "raposo", "porco-espinho"
    }


def test_frame03_and_08_are_exactly_emanuelly_and_intact_egg():
    part = maker.load_parts()[0]
    for i in (3, 8):
        beat = part["segments"][i - 1]
        assert guard.allowed_characters(part, beat) == ("Emanuelly",)
        prompt = maker.frame_prompt(part, beat, i)
        assert "ONE CHARACTER" in prompt
        assert "no blue plush kitten" in prompt.lower()
        assert "Scene 08 must NOT show ANY second character" in prompt
        assert "SAME blue DRAGON EGG" in prompt
        assert "gpt-image-2" not in prompt  # Parser uses an actual model param, not prose.
    assert "Nenhuma pelúcia" in part["segments"][2]["visual_cue"]
    assert "Somente Emanuelly" in part["segments"][7]["visual_cue"]


def test_reference_isolation_is_mandatory_before_any_scene_generation(tmp_path):
    part = maker.load_parts()[0]
    original = fresh_photo(tmp_path)
    editor_called = []
    def illegal_editor(*_args, **_kwargs):
        editor_called.append(True)
        return image_bytes()
    with pytest.raises(FileNotFoundError, match="PrepararReferencias"):
        maker.make_images([part], reference=original, root=tmp_path, budget=9,
                          editor=illegal_editor, key_provider=lambda: "key")
    assert not editor_called


def test_budget_preflight_prevents_any_source_image_upload(tmp_path):
    path = fresh_photo(tmp_path)
    with pytest.raises(ValueError, match="nenhuma chamada"):
        guard.prepare_isolated_references(path, budget=1, editor=lambda *_args: image_bytes(),
                                          key_provider=lambda: "key")
    assert not guard.isolated_reference(path, "emanuelly-solo").exists()


def test_gpt_image_15_never_allowed_when_using_reference(tmp_path):
    part = maker.load_parts()[0]
    photo = fresh_photo(tmp_path)
    with pytest.raises(ValueError, match="gpt-image-2"):
        maker.make_images([part], reference=photo, root=tmp_path,
                          model="gpt-image-1.5", budget=100,
                          editor=lambda *_args: image_bytes())
    assert "choices=(MODEL,)" in (
        ROOT / "scripts" / "serie_kids_emanuelly_v1.py"
    ).read_text(encoding="utf-8")


def test_no_full_cast_sheet_sent_to_story_frame_and_cache_v1_invalid(tmp_path):
    reference = extract_photo(tmp_path)
    part = maker.load_parts()[0]
    calls = []
    def editor(ref, prompt, model, key, *, transparent):
        calls.append((ref, prompt, model))
        return image_bytes()
    result = maker.make_images([part], reference=reference, root=tmp_path,
                               budget=9, editor=editor, key_provider=lambda: "key")
    assert result["generated"] == 9
    assert all(c[0] != reference for c in calls)
    assert all(c[0] == guard.isolated_reference(reference, "emanuelly-solo") for c in calls)
    assert all(c[2] == "gpt-image-2" for c in calls)
    frame, marker = maker.frame_paths(part, part["segments"][7], root=tmp_path)
    meta = json.loads(marker.read_text(encoding="utf-8"))
    assert meta["allowed_characters"] == ["Emanuelly"]
    assert meta["continuity_policy"] == guard.POLICY
    assert maker.valid_frame(part, part["segments"][7], "gpt-image-2",
                             maker.reference_hash(reference), root=tmp_path)
    meta["schema"] = "kids-emanuelly/image-qa/v1"
    marker.write_text(json.dumps(meta), encoding="utf-8")
    assert not maker.valid_frame(part, part["segments"][7], "gpt-image-2",
                                maker.reference_hash(reference), root=tmp_path)


def test_part2_reference_unlocks_fofinho_only_after_hatching(tmp_path):
    ref = extract_photo(tmp_path)
    part = maker.load_parts()[1]
    event = []
    def editor(input_photo, prompt, model, key, *, transparent):
        event.append((input_photo.name, prompt))
        return image_bytes()
    maker.make_images([part], reference=ref, root=tmp_path,
                      budget=10, editor=editor, key_provider=lambda: "key")
    assert [e[0] for e in event] == [guard.SOLO] * 5 + [guard.DUO] * 5
    assert all("EXACTLY EMANUELLY and her BLUE PLUSH KITTEN" in prompt
               for _filename, prompt in event[5:])


def test_isolated_references_obsolete_after_cast_sheet_change(tmp_path):
    photo = extract_photo(tmp_path)
    Image.new("RGB", (1024, 1536), (7, 31, 70)).save(photo)
    with pytest.raises(ValueError, match="desatualizada"):
        guard.check_isolated_ref(photo, "emanuelly-solo")
