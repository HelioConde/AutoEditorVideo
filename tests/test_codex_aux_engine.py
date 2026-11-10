import asyncio
import subprocess
from copy import deepcopy
from graphlib import CycleError

import pytest

from tools.codex_aux import engine
from tools.codex_aux.context import validate
from tools.codex_aux.engine import Ledger, route, run
from tools.codex_aux.proxy import ProxyError


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "sample.py").write_text("def inspect_scene():\n    return 3\n", encoding="utf-8")
    git("add", "sample.py")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
    return tmp_path


@pytest.fixture
def ledger(tmp_path):
    db = Ledger(tmp_path / "test.db")
    yield db
    db.close()


def task(name, kind="review", **options):
    return {"id": name, "kind": kind, "question": "Inspect " + name, "public": True,
            "files": [{"path": "sample.py", "start": 1, "end": 2}], **options}


class Fake:
    def __init__(self):
        self.calls = []
        self.checks = 0
        self.active = self.peak = 0
        self.cancelled = False

    async def preflight(self, model):
        self.checks += 1
        if model != "test-text":
            raise ProxyError("model_unavailable")

    async def analyze(self, model, question, context):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.calls.append(question)
        try:
            await asyncio.sleep(.01)
            if question == "quota":
                err = ProxyError("rate_limit")
                err.attempted = True
                raise err
            if question == "slow":
                await asyncio.sleep(20)
            if question == "echo":
                return {"summary": 'api_key = "demo-value"', "evidence": []}, {"input_tokens": 23}
            return {"summary": question, "evidence": ["sample.py:1"]}, {"input_tokens": 23}
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        finally:
            self.active -= 1


def batch(repo, ledger, tasks, client=None, **options):
    client = client or Fake()
    args = dict(model="test-text", client=client, pilot=True)
    return asyncio.run(run({"tasks": tasks}, repo, ledger, **(args | options)))


def test_independent_jobs_and_ordered_dependencies(repo, ledger):
    fake = Fake()
    tasks = [task("first"), task("second"), task("third", after=["first"]), task("last", "animation")]
    out = batch(repo, ledger, tasks, fake)
    assert fake.peak == out["peak_concurrency"] == 2
    assert fake.calls.index("Inspect third") > fake.calls.index("Inspect first")
    assert fake.checks == out["files_read"] == 1
    assert out["tasks"]["last"]["route"] == "astra"
    assert out["tasks"]["third"]["metrics"]["output_tokens"] is None
    assert ledger.report(out["run"])["first"]["report"]["summary"] == "Inspect first"
    ledger.assess(out["run"], "first", quality="pass", tests=2, rework=0)
    assert ledger.report(out["run"])["first"]["metrics"]["tests_passed"] == 2


def test_logical_duplicates_one_post_and_pinned_reuse(repo, ledger):
    fake = Fake()
    tasks = [task("a"), task("b", question="Inspect a")]
    first = batch(repo, ledger, tasks, fake, revision="fixture-v1")
    assert sum(row["metrics"]["calls"] for row in first["tasks"].values()) == 1
    assert batch(repo, ledger, tasks, fake, revision="fixture-v1")["tasks"]["a"]["metrics"]["cache_hit"]
    batch(repo, ledger, tasks, fake, revision="fixture-v2")
    assert len(fake.calls) == 2


def test_unpinned_rechecks_on_another_run(repo, ledger):
    fake = Fake()
    for _ in range(2):
        batch(repo, ledger, [task("a")], fake)
    assert len(fake.calls) == 2


def test_cache_hit_skips_inventory_and_edits_invalidate(repo, ledger, monkeypatch):
    tasks = [task("index", "inventory")]
    assert batch(repo, ledger, tasks)["tasks"]["index"]["report"]["evidence"] == ["sample.py:1 inspect_scene"]
    with monkeypatch.context() as patch:
        patch.setattr(engine, "inventory", lambda *_: pytest.fail("unexpected re-analysis"))
        assert batch(repo, ledger, tasks)["tasks"]["index"]["metrics"]["cache_hit"]
    (repo / "sample.py").write_text("def altered():\n    return 9\n")
    assert batch(repo, ledger, tasks)["tasks"]["index"]["report"]["evidence"] == ["sample.py:1 altered"]


def test_limit_halts_queue_but_keeps_siblings(repo, ledger):
    fake = Fake()
    out = batch(repo, ledger, [task("a"), task("b", question="quota"), task("c", after=["b"])], fake)
    assert ledger.report(out["run"])["a"]["metrics"]["status"] == "ok"
    assert out["tasks"]["b"]["reason"] == "rate_limit"
    assert out["tasks"]["c"]["reason"] == "requires_dependency_review"
    assert "Inspect c" not in fake.calls
    fake = Fake()
    out = batch(repo, ledger, [task("q", question="quota"), task("queued")], fake, concurrency=1)
    assert fake.calls == ["quota"] and out["tasks"]["queued"]["metrics"]["calls"] == 0


def test_timeout_retains_claim_across_runs(repo, ledger):
    fake = Fake()
    task_list = [task("stalled", question="slow")]
    first = batch(repo, ledger, task_list, fake, timeout=.07)
    assert fake.cancelled and first["tasks"]["stalled"]["receipt"]
    second = batch(repo, ledger, task_list, fake)
    assert second["tasks"]["stalled"]["reason"] == "verify_previous_request"
    assert len(fake.calls) == 1


def test_cancelled_batch_closes_request_and_keeps_completed_sibling(repo, ledger):
    async def cancel():
        client = Fake()
        job = asyncio.create_task(run({"tasks": [task("done"), task("waiting", question="slow")]},
                                      repo, ledger, client=client, model="test-text", pilot=True, run_id="test"))
        async with asyncio.timeout(3):
            while "done" not in ledger.report("test"):
                await asyncio.sleep(.005)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job
        assert client.cancelled
    asyncio.run(cancel())
    assert ledger.report("test")["done"]["report"] and ledger.report("test")["waiting"]["metrics"]["status"] == "cancelled"


def test_explicit_model_and_economics(repo, ledger):
    assert route(task("r"), "test-text", False)[0] == "astra"
    budget = dict(direct=100, delegated=90, quality_ok=True)
    assert route(task("r", budget=budget), "test-text", False)[0] == "proxy"
    assert route(task("r", budget=dict(budget, delegated=110)), "test-text", True)[0] == "astra"
    assert route(task("r", budget=dict(budget, quality_ok=False)), "test-text", True)[0] == "astra"
    assert route(task("x", "integration"), "test-text", True)[0] == "astra"
    assert route(task("x", "inventory"), None, False)[0] == "local"
    assert route(task("x", public=False), "test-text", True)[0] == "astra"
    fake = Fake()
    out = batch(repo, ledger, [task("x")], fake, model="absent")
    assert not fake.calls and out["tasks"]["x"]["reason"] == "model_unavailable"


@pytest.mark.parametrize("value", ['api_key = "fixture-secret"', 'password: fixture-secret',
                                   'Bearer syntheticBearercredential12345'])
def test_secrets_are_rejected_before_inference(repo, ledger, value):
    (repo / "sample.py").write_text(value + "\npass\n")
    fake = Fake()
    row = batch(repo, ledger, [task("x")], fake)["tasks"]["x"]
    assert row["reason"] == "sensitive_context" and fake.checks == 0 and value not in str(row)
    with pytest.raises(ValueError):
        batch(repo, ledger, [task("x", question=value)], fake)


def test_sensitive_report_preserves_real_usage_without_recording_body(repo, ledger):
    out = batch(repo, ledger, [task("x", question="echo")])
    row = out["tasks"]["x"]
    assert row["metrics"]["calls"] == 1 and row["metrics"]["input_tokens"] == 23
    assert "demo-value" not in str(ledger.report(out["run"])) and "report" not in row


def test_invalid_plan_cannot_send_earlier_valid_task(repo, ledger):
    fake = Fake()
    bad = task("invalid")
    bad["files"][0]["path"] = "../private.py"
    with pytest.raises(ValueError):
        batch(repo, ledger, [task("a"), bad], fake)
    assert not fake.calls
    with pytest.raises(CycleError):
        validate({"tasks": [task("a", after=["b"]), task("b", after=["a"])]})
    with pytest.raises(ValueError):
        validate({"tasks": [task("a", after=["unknown"])]})


def test_dirty_or_nonpublic_dependency_stays_local(repo, ledger):
    (repo / "other.py").write_text("def local_only():\n    pass\n")
    index = deepcopy(task("index", "inventory"))
    index["files"][0]["path"] = "other.py"
    fake = Fake()
    row = batch(repo, ledger, [index, task("x", after=["index"])], fake)["tasks"]["x"]
    assert row["reason"] == "requires_reviewed_public_source"
    assert fake.checks == 0
