"""Check experiment accounting without model calls or paid services."""
import json

import pytest

from tools.codex_aux import benchmark as bench
from tools.codex_aux.context import digest


def test_missing_live_model_never_claims_c_measurement(monkeypatch):
    monkeypatch.setattr(bench, "git", lambda *_: b"simulation")
    monkeypatch.setattr(bench, "chatgpt_login", lambda: pytest.fail("unexpected login"))
    assert bench.measure_arm("C", None, 3)["status"] == "unavailable"


def test_c_counts_all_measured_helpers_and_checks_provenance(monkeypatch):
    monkeypatch.setattr(bench, "git", lambda *_: b"same committed source")
    plan = json.loads(bench.PLAN.read_text(encoding="utf-8"))
    tasks = {t["id"]: {"status": "ok", "route": "proxy",
                        "report": {"summary": "fixture", "evidence": ["sample.py:1"]},
                        "metrics": {"calls": 1, "model": "fixture", "input_tokens": 20,
                                    "cache_hit": False, "errors": 0, "retries": 0,
                                    "output_tokens": 2, "cached_input_tokens": 5}}
             for t in plan["tasks"]}
    row = {"commit": "fixture", "plan_sha256": digest(plan), "tasks": tasks,
           "elapsed_ms": 300, "peak_concurrency": 2}
    _, usage = bench.helper_metrics(row, plan, "fixture")
    assert usage == {"input_tokens": 40, "output_tokens": 4, "cached_input_tokens": 10, "calls": 2}
    with pytest.raises(ValueError):
        bench.helper_metrics(dict(row, plan_sha256="wrong"), plan, "fixture")
    tasks["renderer-guards"]["metrics"]["calls"] = 0
    with pytest.raises(ValueError):
        bench.helper_metrics(row, plan, "fixture")
