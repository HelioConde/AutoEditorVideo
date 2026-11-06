"""Offline contract tests for the five-independent-Actions generation pilot."""
from pathlib import Path
import ast
import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_independent_generation_workflow_has_no_youtube_credentials():
    workflow = read(".github/workflows/otaku-br-parallel-one.yml")
    data = yaml.load(workflow, Loader=yaml.BaseLoader)
    assert "workflow_dispatch" in data["on"]
    jobs = data["jobs"]
    assert list(jobs) == ["prepare-one"]
    job = jobs["prepare-one"]
    assert job["environment"] == "image-generation"
    assert "YOUTUBE_BR_TOKEN_JSON" not in workflow
    assert "otaku_br_50_upload_public.py" not in workflow
    assert "otaku_br_50_validate_prepared.py" in workflow
    assert "actions/cache/save@v4" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert '[[ "$EPISODE_NUMBER" =~ ^(22|23|24|25|26)$ ]]' in workflow


def test_five_way_launcher_dispatches_five_separate_runs_not_matrix_jobs():
    workflow = read(".github/workflows/otaku-br-5-parallel-launch.yml")
    data = yaml.load(workflow, Loader=yaml.BaseLoader)
    assert "push" in data["on"]
    assert "otaku-br-5-parallel-test-20261106.json" in workflow
    assert "for number in 26 25 24 23 22" in workflow
    assert "gh workflow run otaku-br-parallel-one.yml" in workflow
    assert "confirm_generation=true" in workflow
    assert '.public_upload == true' in workflow
    assert "serial_existing_workflow_after_prior_receipts" in workflow
    assert "otaku-br-50-serial-public.yml" in workflow
    assert data["jobs"]["dispatch-five-generators"]["permissions"]["actions"] == "write"


def test_serial_queue_reuses_only_hash_validated_parallel_media():
    workflow = read(".github/workflows/otaku-br-50-serial-public.yml")
    data = yaml.load(workflow, Loader=yaml.BaseLoader)
    steps = data["jobs"]["generate-render-one"]["steps"]
    ids = [item.get("id") for item in steps]
    assert "prepared-cache" in ids
    assert "actions/cache/restore@v4" in workflow
    assert "scripts/otaku_br_50_validate_prepared.py --number" in workflow
    assert "steps.prepared-cache.outputs.cache-hit != 'true'" in workflow
    assert "otaku-br-50-prepared-v1-" in workflow
    assert "otaku-br-50-prepared-v1-" in read(".github/workflows/otaku-br-parallel-one.yml")


def test_validator_is_offline_and_compiles():
    code = read("scripts/otaku_br_50_validate_prepared.py")
    ast.parse(code)
    assert "sha256" in code
    assert "stage" not in code or "publication" in code
    assert "YOUTUBE_BR_TOKEN_JSON" not in code
    assert "gpt-image-2" in code


def test_small_valid_json_receipts_do_not_block_parallel_cache(tmp_path, monkeypatch):
    """Regression: provenance/metadata JSON is naturally <1KB."""
    import hashlib
    import importlib
    import json

    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    validator = importlib.import_module("otaku_br_50_validate_prepared")
    number = 26
    row = {
        "id": "6126-multicena-experimento-novembro",
        "channel_id": "UCXGYTuBYn-0Ziqin5ajKhOw",
        "title": "Short de teste",
        "description": "Descricao do teste",
        "tags": ["short", "anime"],
    }
    monkeypatch.setattr(validator, "validate", lambda: [row] * 50)
    monkeypatch.setattr(validator, "OUTPUT", tmp_path)
    folder = tmp_path / row["id"]
    folder.mkdir()

    def write(name, data):
        path = folder / name
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    image_hashes = [
        write(f"scene-{i:02}.png", bytes([i]) * 32000)
        for i in range(1, 6)
    ]
    video_hash = write("preview-unreviewed.mp4", b"mp4" * 70000)
    cover_hash = write("thumb.jpg", b"jpeg" * 3000)
    voice_hash = write("voz-master.mp3", b"mp3" * 4000)
    write("props.json", b'{"scenes": []}')
    write("marcacoes-voz.json", b'{"words": []}')

    def jsonfile(name, value):
        content = json.dumps(value, ensure_ascii=False).encode("utf-8")
        (folder / name).write_bytes(content)
        return len(content)

    jsonfile("metadata.json", {
        **row, "episode_id": row["id"],
        "containsSyntheticMedia": True,
        "requested_privacy": "public_after_qa",
    })
    prov_len = jsonfile("original-art-provenance.json", {
        "episode_id": row["id"],
        "channel_id": row["channel_id"],
        "model": "gpt-image-2",
        "scene_count": 5,
        "art_original": True,
        "human_visual_review": False,
        "scene_sha256": image_hashes,
    })
    jsonfile("qa.json", {
        "video_sha256": video_hash,
        "cover_sha256": cover_hash,
        "voice_sha256": voice_hash,
        "scene_sha256": image_hashes,
        "technical": "preview_rendered_unreviewed",
        "publication": "not_performed",
        "human_visual_review": False,
    })
    assert prov_len < 1000
    assert (folder / "metadata.json").stat().st_size < 1000
    assert validator.check(number)["cached_media_verified"] is True


def test_cache_fallback_reuses_validated_prepared_media_after_new_prompt_override():
    for path in (
        ".github/workflows/otaku-br-parallel-one.yml",
        ".github/workflows/otaku-br-50-serial-public.yml",
    ):
        src=read(path)
        assert "cache-matched-key == ''" in src
        assert "restore-keys: |" in src
        assert "otaku-br-50-prepared-v1-" in src
        assert "otaku_br_50_validate_prepared.py --number" in src


def test_short_31_safe_navigation_images_do_not_change_other_short_scripts():
    source=read("scripts/otaku_br_50_generate_images.py")
    tree=ast.parse(source)
    nodes=[
        node for node in tree.body
        if (isinstance(node,ast.Assign) and any(
            isinstance(target,ast.Name) and target.id=="NAVIGATOR_SAFE_SHOTS"
            for target in node.targets
        )) or (isinstance(node,ast.FunctionDef) and
                node.name=="navigator_safe_scene_override")
    ]
    assert len(nodes)==2
    ns={"ImageBlocked":ValueError}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"short31", "exec"),ns)
    fun=ns["navigator_safe_scene_override"]
    row={"position":31,"id":"6131-multicena-experimento-novembro"}
    prompts=[fun(row,i) for i in range(1,6)]
    assert all(isinstance(p,str) and "No violence" in p for p in prompts)
    assert len(set(prompts))==5
    assert fun({"position":26,"id":"6126-multicena-experimento-novembro"},4) is None
    assert "override=navigator_safe_scene_override(row,index)" in source


def test_short_30_comic_wayfinding_visuals_are_nonviolent_and_episode_scoped():
    source=read("scripts/otaku_br_50_generate_images.py")
    tree=ast.parse(source)
    nodes=[
        node for node in tree.body
        if (isinstance(node,ast.Assign) and any(
            isinstance(target,ast.Name) and target.id=="LOST_WAYFINDER_SAFE_SHOTS"
            for target in node.targets))
        or (isinstance(node,ast.FunctionDef) and
            node.name=="lost_wayfinder_safe_scene_override")
    ]
    assert len(nodes)==2
    ns={"ImageBlocked":ValueError}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"short30", "exec"),ns)
    fn=ns["lost_wayfinder_safe_scene_override"]
    target={"position":30,"id":"6130-multicena-experimento-novembro"}
    prompts=[fn(target,i) for i in range(1,6)]
    assert len(set(prompts))==5
    assert all("No battles, violence" in p for p in prompts)
    assert all("original character" in p for p in prompts)
    assert fn({"position":31,"id":"6131-multicena-experimento-novembro"},3) is None
    assert fn({"position":26,"id":"6126-multicena-experimento-novembro"},3) is None
    assert "override=lost_wayfinder_safe_scene_override(row,index)" in source
