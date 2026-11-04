"""Published BR -> native English V3 migration: strict offline safety tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preparar_publicados_en_v3 as prepare
import renderizar_shorts_en as render
import publicar_shorts_en as upload


def test_snapshot_18_public_splits_ready_existing_and_unmapped():
    snapshot = prepare._read(prepare.SNAPSHOT)
    prepare.validate_snapshot(snapshot)
    counts = {status: sum(r["status"] == status for r in snapshot["videos"])
              for status in ("ready", "already_on_english", "source_unconfirmed")}
    assert counts == {"ready": 13, "already_on_english": 1, "source_unconfirmed": 4}
    assert snapshot["verified_en_preexisting"]["101-death-note-ep01"] == "tPurNjxbnx0"
    assert snapshot["verified_en_preexisting"]["201-death-note-rosto-nome"] == "gZt7V7L5L9c"


def test_published_manifest_native_english_and_stable_provenance(tmp_path):
    manifest, report = prepare.build_manifest()
    assert report["br_public_count"] == 18
    assert report["ready_to_plan"] == len(manifest["episodes"]) == 13
    assert len(report["unmatched_source"]) == 4
    assert report["uploads_executed"] == 0
    assert manifest["target_channel_id"] == "UCBoNbQjaMYdpJqPLRZAFkvQ"
    assert manifest["source_br_channel_id"] == "UCXGYTuBYn-0Ziqin5ajKhOw"
    assert "101-death-note-ep01" not in {e["id"] for e in manifest["episodes"]}
    assert "201-death-note-rosto-nome" not in {e["id"] for e in manifest["episodes"]}
    for e in manifest["episodes"]:
        assert e["channel"] == "Otaku Reframe"
        assert e["source_br_video_id"]
        assert len(e["hook_options"]) == 5
        assert len(set(e["hook_options"])) == 5
        assert e["script"].startswith(e["selected_hook"])
        assert e["source_visual_check"] == "requires_full_english_video_review"
        assert 50 <= len(e["script"].split()) <= 145
        assert "#OtakuReframe" in e["description"]
        assert e["source_pt_script_sha256"]
    written = tmp_path / "en.json"
    written.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    parsed = render.load_english(written)
    assert len(parsed) == 13


def test_sources_are_exactly_existing_pt_episodes_and_not_only_title_matches():
    manifest, _ = prepare.build_manifest()
    pt = prepare.load_episodes(include_recaps=True)
    for e in manifest["episodes"]:
        assert e["id"] in pt
        expected = hashlib.sha256(pt[e["id"]]["script"].encode("utf-8")).hexdigest()
        assert e["source_pt_script_sha256"] == expected
        assert e["script"] != pt[e["id"]]["script"]


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(target_channel_id="UCXGYTuBYn-0Ziqin5ajKhOw"),
    lambda d: d["episodes"][0].update(source_br_video_id="11111111111"),
    lambda d: d["episodes"][0].update(source_pt_script_sha256="f" * 64),
    lambda d: d["episodes"][0].update(script="Truncated unrelated text"),
])
def test_render_manifest_rejects_wrong_channel_wrong_pt_or_mismatched_narration(tmp_path, mutate):
    manifest, _ = prepare.build_manifest()
    mutate(manifest)
    file = tmp_path / "en.json"
    file.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        render.load_english(file)


def test_snapshot_refuses_unverified_new_video_and_missing_source():
    snapshot = prepare._read(prepare.SNAPSHOT)
    snapshot["videos"][0]["status"] = "source_unconfirmed"
    with pytest.raises(ValueError, match="divergente"):
        prepare.build_manifest(snapshot=snapshot)
    with pytest.raises(ValueError, match="nao elegivel"):
        prepare.build_manifest(only_ids=["mP34eFfMIRI"])
    with pytest.raises(ValueError, match="nao elegivel"):
        prepare.build_manifest(only_ids=["101-death-note-ep01"])


def test_cli_prepares_local_only_and_uses_one_episode(tmp_path, capsys):
    file = tmp_path / "english-manifest.json"
    assert prepare.main(["--acao", "preparar", "--id", "5001-black-clover",
                         "--saida", str(file)]) == 0
    data = json.loads(file.read_text(encoding="utf-8"))
    assert len(data["episodes"]) == 1
    assert data["episodes"][0]["id"] == "5001-black-clover"
    assert "uploads_executed" in capsys.readouterr().out
    report_rows = prepare.check_local_assets(data, root=tmp_path)
    assert report_rows[0]["blocking_if_missing_cache"] is True
    assert report_rows[0]["visual_quality_approved"] is False
    assert report_rows[0]["en_render_complete"] is False


def test_rendered_reuse_requires_matching_signed_qa_before_upload(tmp_path, monkeypatch):
    manifest, _ = prepare.build_manifest(only_ids=["5001-black-clover"])
    file = tmp_path / "english.json"
    file.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    item = manifest["episodes"][0]
    folder = tmp_path / item["id"] / "en-US"
    folder.mkdir(parents=True)
    video = folder / f"{item['id']}-en-US-master-multicenas-personagens-v3-equilibrado.mp4"
    video.write_bytes(b"LOCAL EN VIDEO TEST" * 15000)
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    qa = {
        "status": "renderizado_aguardando_revisao", "language": "en-US",
        "render_origin": "AutoEditorVideo/local/remotion",
        "video_sha256": digest,
        "source_br_video_id": item["source_br_video_id"],
        "source_pt_script_sha256": item["source_pt_script_sha256"],
    }
    (folder / "qa-en-US.json").write_text(json.dumps(qa), encoding="utf-8")
    monkeypatch.setattr(upload, "OUT", tmp_path)
    monkeypatch.setattr(upload, "validate_mp4", lambda path: None)
    rows = upload.candidates("equilibrado", item["id"], 1, file)
    assert len(rows) == 1 and rows[0]["sha"] == digest
    qa["source_br_video_id"] = "bad_source"
    (folder / "qa-en-US.json").write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="rastreabilidade"):
        upload.candidates("equilibrado", item["id"], 1, file)


def test_wrong_local_en_channel_blocks_before_login_or_upload(monkeypatch, tmp_path):
    manifest, _ = prepare.build_manifest(only_ids=["5001-black-clover"])
    path = tmp_path / "en.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(upload, "candidates", lambda *_args: [
        {"id": "5001-black-clover", "sha": "test", "meta": {"titulo": "OK"}}
    ])
    monkeypatch.setattr(upload, "STATE", tmp_path / "state.json")
    monkeypatch.setattr(upload, "expected_channel",
                        lambda: "UCXGYTuBYn-0Ziqin5ajKhOw")
    monkeypatch.setattr(upload, "channel_auth",
                        lambda: pytest.fail("OAuth must not run for mismatched EN channel"))
    with pytest.raises(RuntimeError, match="CANAL EN INCORRETO"):
        upload.main(["--acao", "enviar", "--manifesto", str(path),
                     "--id", "5001-black-clover", "--confirmar"])


def test_five_legacy_scripts_still_unchanged():
    original = {item["id"]: item for item in render.load_english()}
    combined, _ = prepare.build_manifest()
    matched = {item["id"]: item for item in combined["episodes"]}
    for id in original:
        assert matched[id]["script"] == original[id]["script"]
        assert matched[id]["title"] == original[id]["title"]
        assert "Otaku Reframe" in matched[id]["tags"]


def test_no_runtime_upload_in_preparer_and_wrapper_has_no_upload_flag():
    script = (ROOT / "scripts" / "preparar_publicados_en_v3.py").read_text(encoding="utf-8")
    ps = (ROOT / "preparar-publicados-en.ps1").read_text(encoding="utf-8")
    assert "videos().insert" not in script
    assert "MediaFileUpload" not in script
    assert "youtube-en-token.json" not in script
    assert "ConfirmarEnvio" not in ps


def test_english_motion_report_never_confuses_camera_with_character_animation():
    props = {"scenes": [
        {"id": "01", "subject": "personagens", "motionCapability": "camera-only",
         "movableCharacterLayers": 0},
        {"id": "02", "subject": "objeto", "motionCapability": "camera-only",
         "movableCharacterLayers": 0},
        {"id": "03", "subject": "personagens", "motionCapability": "character-layer",
         "movableCharacterLayers": 1},
    ]}
    report = render.assess_character_motion(props)
    assert report["character_scenes"] == 2
    assert report["character_layer_scenes"] == 1
    assert report["camera_only_character_scene_ids"] == ["01"]
    assert report["character_motion_verified"] is False
    with pytest.raises(ValueError, match="Zoom de camera"):
        render.assess_character_motion(props, strict=True)
    assert render.assess_character_motion({
        "scenes": [props["scenes"][2]]
    }, strict=True)["character_motion_verified"] is True
