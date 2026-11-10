"""No external API and no YouTube upload: Alchemy anime Part-3-style layers."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import types

import pytest
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/alchemy_dorama_original.py"
spec = importlib.util.spec_from_file_location("alchemy_dorama_original", MODULE)
assert spec and spec.loader
dorama = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dorama)


def test_alchemy_storyboard_is_unique_and_150_to_180_seconds():
    board = dorama.read_json(dorama.BOARD)
    dorama.check_storyboard(board)
    assert board["episode_id"] == dorama.EPISODE
    assert len(board["scenes"]) == 16
    assert board["duration_seconds_target"] == 175
    assert board["youtube_channel_id"] == dorama.CHANNEL
    assert board["upload_authorized"] is False
    assert {shot["time_layer"] for shot in board["scenes"]} == {
        "PRESENTE", "FLASHBACK"
    }
    assert sum(s["time_layer"] == "FLASHBACK" for s in board["scenes"]) == 5


def test_wrong_channel_or_different_runtime_is_blocked():
    original = dorama.read_json(dorama.BOARD)
    changed = {**original, "youtube_channel_id": "fake"}
    with pytest.raises(ValueError, match="CHANNEL_MISMATCH"):
        dorama.check_storyboard(changed)
    changed = {**original, "duration_seconds_target": 60}
    with pytest.raises(ValueError, match="EPISODE_DURATION_OUTSIDE_150_180"):
        dorama.check_storyboard(changed)


def test_preflight_is_fail_closed_and_does_not_generate_images(tmp_path, monkeypatch):
    board = dorama.read_json(dorama.BOARD)
    manifest = dorama.read_json(dorama.MANIFEST)
    monkeypatch.setattr(dorama, "ROOT", tmp_path)
    monkeypatch.setattr(dorama, "REFROOT",
                        tmp_path / "assets/gerados/alchemy-dorama-original/referencias")
    monkeypatch.setattr(dorama, "SOURCE",
                        tmp_path / "assets/gerados/alchemy-dorama-original/ep01")
    result = dorama.inspect_assets(board, dorama.anchor_map(manifest), manifest["ui"])
    assert result and "UI-01/UI-02:visual_approval_pending" in result
    assert all("gpt-image" not in r for r in result)


def test_prepared_props_reuse_canonical_hashes_and_2d_independent_layers(
        tmp_path, monkeypatch):
    board = dorama.read_json(dorama.BOARD)
    doc = dorama.read_json(dorama.MANIFEST)
    needed = set()
    for shot in board["scenes"]:
        needed.add(shot["background_anchor"])
        needed.update(shot["character_anchors"])
        needed.update(a for a in shot["item_anchors"] if a not in {"UI-01", "UI-02"})
    root = tmp_path
    for item in doc["entries"]:
        if item["id"] not in needed:
            continue
        target = root / item["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if item["id"] in dorama.BACKGROUND:
            image = Image.new("RGB", (64, 96), (100, 85, 105))
        else:
            image = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
            ImageDraw.Draw(image).rectangle((12, 15, 50, 75), fill=(80, 95, 180, 255))
        image.save(target)
        item["sha256"] = dorama.sha256(target)
        item["approved"] = True
    doc["ui"]["UI-01"]["approved_visual"] = True
    doc["ui"]["UI-02"]["approved_visual"] = True
    manifest = root / "references.json"
    manifest.write_text(json.dumps(doc), encoding="utf-8")
    source = root / "assets/gerados/alchemy-dorama-original/ep01"
    source.mkdir(parents=True)
    (source / "narracao.mp3").write_bytes(b"ID3" + b"test-audio")
    (source / "legendas.json").write_text(json.dumps({"captions": [
        {"startFrame": 0, "endFrame": 250, "text": "Inicio"},
        {"startFrame": 4000, "endFrame": 4900, "text": "Final"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(dorama, "ROOT", root)
    monkeypatch.setattr(dorama, "REFROOT",
                        root / "assets/gerados/alchemy-dorama-original/referencias")
    monkeypatch.setattr(dorama, "MANIFEST", manifest)
    monkeypatch.setattr(dorama, "SOURCE", source)
    monkeypatch.setattr(dorama, "PUBLIC", root / "motion-remotion/public/generated/alchemy-dorama-original/ep01")
    monkeypatch.setattr(dorama, "PROPS", root / "motion-remotion/props-alchemy-dorama-ep01.json")
    monkeypatch.setattr(dorama.shutil, "which",
                        lambda program: "/usr/bin/ffprobe" if program == "ffprobe" else None)
    monkeypatch.setattr(dorama.subprocess, "run",
                        lambda *args, **kwargs: types.SimpleNamespace(stdout="169.0"))
    prepared = dorama.prepare()
    props = json.loads(dorama.PROPS.read_text(encoding="utf-8"))
    assert prepared["prepared"] is True
    assert prepared["youtube_uploads"] == 0
    assert prepared["paid_image_calls"] == 0
    assert props["durationFrames"] == 5250
    assert len(props["scenes"]) == 16
    assert props["scenes"][0]["backgroundAnchor"] == "TRONO-01"
    assert any(s["anchorId"] == "REN-01" for s in props["scenes"][0]["sprites"])
    assert props["scenes"][2]["flashbackLabel"] == "7 DIAS ANTES"
    assert props["scenes"][3]["flashbackLabel"] == ""
    assert props["scenes"][5]["flashbackLabel"] == "NAQUELA NOITE"
    assert props["scenes"][9]["systemPanel"]["kind"] == "mission"
    assert props["scenes"][10]["systemPanel"]["kind"] == "emergency"
    assert props["scenes"][15]["systemPanel"]["kind"] == "anomaly"
    assert not any("emanuelly" in s["background"] for s in props["scenes"])
    assert all(s["endFrame"] > s["startFrame"] for s in props["scenes"])
    assert all(a["endFrame"] == b["startFrame"] for a, b in
               zip(props["scenes"], props["scenes"][1:]))


def test_no_private_kids_material_or_upload_code_imported():
    script = MODULE.read_text(encoding="utf-8")
    assert "videos().insert" not in script
    assert "YOUTUBE_KIDS_TOKEN_JSON" not in script
    assert "KidsBackgroundMusic" not in script
    root_tsx = (ROOT / "motion-remotion/src/root.tsx").read_text(encoding="utf-8")
    assert "AlchemyDoramaOriginal" in root_tsx
    assert "EmanuellySerieV1" in root_tsx
    assert "FofinhosEP01Canonico" in root_tsx
