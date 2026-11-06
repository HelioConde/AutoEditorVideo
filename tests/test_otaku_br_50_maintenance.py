"""Maintenance and manual-resume security tests for the Otaku BR batch."""
import importlib
import json
from pathlib import Path
import sys
import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
gate=importlib.import_module("otaku_br_50_maintenance_gate")
CONTROL=ROOT/"conteudos/otaku-br-50-serial-launch-20261106.json"

def future_authorized():
    return {
        "schema": gate.SCHEMA,
        "channel_id": gate.CHANNEL,
        "pause_requested": False,
        "authorized_public": True,
        "maintenance_complete": True,
        "resume_authorized_after_maintenance": True,
    }

def test_maintenance_requires_all_four_independent_authorizations():
    accepted=future_authorized()
    assert gate.check_authorization(accepted)
    for key in ("pause_requested","authorized_public","maintenance_complete","resume_authorized_after_maintenance"):
        bad=dict(accepted)
        bad.pop(key)
        with pytest.raises(gate.MaintenanceBlocked):
            gate.check_authorization(bad)
        bad=dict(accepted)
        bad[key]=not accepted[key]
        with pytest.raises(gate.MaintenanceBlocked):
            gate.check_authorization(bad)

def test_wrong_channel_and_missing_authorization_never_pass():
    for data in ({}, {"schema":gate.SCHEMA}, dict(future_authorized(),channel_id="other")):
        with pytest.raises(gate.MaintenanceBlocked):
            gate.check_authorization(data)

def test_creator_requested_pause_is_recorded_in_current_control():
    data=json.loads(CONTROL.read_text(encoding="utf-8"))
    assert data["pause_requested"] is True
    assert data["authorized_public"] is False
    assert data["maintenance_complete"] is False
    assert data["resume_authorized_after_maintenance"] is False
    with pytest.raises(gate.MaintenanceBlocked,match="CREATOR_PAUSED"):
        gate.check_authorization(data)

def test_serial_workflow_checks_live_main_before_image_or_upload_dispatch():
    src=(ROOT/".github/workflows/otaku-br-50-serial-public.yml").read_text(encoding="utf-8")
    wf=yaml.load(src,Loader=yaml.BaseLoader)
    jobs=wf["jobs"]
    queue=jobs["queue-and-contract"]["steps"]
    assert any("otaku_br_50_maintenance_gate.py" in str(s.get("run","")) for s in queue)
    generate=jobs["generate-render-one"]["steps"]
    provider=next(s for s in generate if "Generate one video's FIVE images" in s.get("name",""))
    assert "otaku_br_50_maintenance_gate.py" in provider["run"]
    assert provider["run"].index("otaku_br_50_maintenance_gate.py") < provider["run"].index("proxy_accounts_private_stage.py")
    dispatch=jobs["launch-next-only-after-covered-publication"]["steps"][-1]
    assert dispatch["run"].index("otaku_br_50_maintenance_gate.py") < dispatch["run"].index("gh workflow run")
    assert any(s.get("uses","").startswith("actions/checkout") for s in jobs["launch-next-only-after-covered-publication"]["steps"])
    upload=(ROOT/"scripts/otaku_br_50_upload_public.py").read_text(encoding="utf-8")
    assert upload.count("ensure_unpaused_live()") >= 2
    assert upload.index("ensure_unpaused_live()") < upload.index("youtube.videos().insert(")

def test_manual_workflow_dispatch_cannot_override_creator_pause():
    wf=(ROOT/".github/workflows/otaku-br-50-serial-public.yml").read_text(encoding="utf-8")
    # Queue checks the current control even when manual authorized_public is true.
    assert "Enforce LIVE creator maintenance pause" in wf
    assert "GH_TOKEN: ${{ github.token }}" in wf
    assert "pause_requested" in (ROOT/"scripts/otaku_br_50_maintenance_gate.py").read_text(encoding="utf-8")
