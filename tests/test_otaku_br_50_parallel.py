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
