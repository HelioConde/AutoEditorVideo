"""Guards against the invalid-YAML mistake that created no-job failed runs.

This offline test uses only Python's stdlib and cannot invoke YouTube or Actions.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/batch15-public-existing-after-oauth-20261108.yml"
PUBLISHER = ROOT / "scripts/batch15_publicize_reviewed_20261108.py"


def test_step_names_with_colons_are_quoted():
    source = WORKFLOW.read_text(encoding="utf-8")
    for raw in source.splitlines():
        match = re.match(r"^\s*- name:\s*(.+)$", raw)
        if not match:
            continue
        name = match.group(1)
        if ": " in name:
            assert name.startswith(("'", '"')), "Unquoted colon in Actions step name invalidates YAML: " + name
            assert name.endswith(name[0]), "Unclosed quote on Actions step name: " + name


def test_existing_video_publication_requires_explicit_dispatch():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "\non:\n  workflow_dispatch:\n" in source
    assert "\n  push:" not in source
    assert "\n  workflow_run:" not in source
    assert "required: true" in source
    assert "type: string" in source
    assert "PUBLICAR-9-SEM-DUPLICAR" in source
    assert "environment: youtube-private-upload" in source


def test_no_insert_delete_or_image_generation_in_public_workflow():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    publisher = PUBLISHER.read_text(encoding="utf-8")
    assert "scripts/batch15_publicize_reviewed_20261108.py" in workflow
    assert "scripts/five_channel_fifteen_20261108.py --action render" not in workflow
    assert "videos().insert(" not in publisher
    assert "videos().delete(" not in publisher
    assert "videos().update(" in publisher
