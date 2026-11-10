"""Schedule finite read-only plans. The primary agent handles every handoff."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import time
import uuid
from pathlib import Path

from .context import MAX_INPUT, Sources, digest, inventory, public_text, validate

COUNTERS = ("input_tokens", "output_tokens", "cached_input_tokens")


def route(task, model, pilot):
    if task["kind"] == "inventory":
        return "local", "source_inventory"
    if task["kind"] != "review":
        return "astra", "advanced_reasoning"
    if not (model and task.get("public")):
        return "astra", "no_public_model_route"
    budget = task.get("budget")
    if budget and (not budget["quality_ok"] or budget["delegated"] >= budget["direct"]):
        return "astra", "no_validated_benefit"
    if not budget and not pilot:
        return "astra", "unmeasured"
    return "proxy", "controlled_pilot" if not budget else "measured_benefit"


class Ledger:
    """An atomic claim survives crashes. Store public reports only with a pinned revision."""
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=5)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS receipts "
            "(key TEXT PRIMARY KEY, state TEXT NOT NULL, report TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS metrics (run TEXT, task TEXT, data TEXT, "
            "PRIMARY KEY(run, task))"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS reports (run TEXT, task TEXT, data TEXT, "
            "PRIMARY KEY(run, task))"
        )

    def lookup(self, key):
        return self.db.execute("SELECT state,report FROM receipts WHERE key=?", (key,)).fetchone()

    def claim(self, key):
        with self.db:
            cur = self.db.execute("INSERT OR IGNORE INTO receipts VALUES (?, 'pending', NULL)", (key,))
        return cur.rowcount == 1

    def release(self, key, *, uncertain):
        with self.db:
            if uncertain:
                self.db.execute("UPDATE receipts SET state='uncertain' WHERE key=?", (key,))
            else:
                self.db.execute("DELETE FROM receipts WHERE key=?", (key,))

    def record(self, run_id, task_id, metrics, report=None, completed_key=None, keep=False):
        with self.db:
            if completed_key and keep:
                self.db.execute("UPDATE receipts SET state='done',report=? WHERE key=?",
                                (json.dumps(report), completed_key))
            elif completed_key:
                self.db.execute("DELETE FROM receipts WHERE key=?", (completed_key,))
            self.db.execute("INSERT INTO metrics VALUES (?,?,?)", (run_id, task_id, json.dumps(metrics)))
            if report is not None:
                self.db.execute("INSERT INTO reports VALUES (?,?,?)", (run_id, task_id, json.dumps(report)))

    def report(self, run_id):
        return {tid: {"metrics": json.loads(stats), "report": json.loads(report) if report else None}
                for tid, stats, report in self.db.execute(
                    "SELECT task, metrics.data, reports.data FROM metrics "
                    "LEFT JOIN reports USING(run,task) WHERE run=? ORDER BY task", (run_id,))}

    def assess(self, run_id, task_id, *, quality, tests, rework):
        if quality not in ("pass", "fail") or min(tests, rework) < 0:
            raise ValueError("invalid_assessment")
        with self.db:
            row = self.db.execute("SELECT data FROM metrics WHERE run=? AND task=?", (run_id, task_id)).fetchone()
            if not row:
                raise ValueError("task_not_found")
            stats = json.loads(row[0])
            stats.update(quality=quality, tests_passed=tests, rework=rework)
            self.db.execute("UPDATE metrics SET data=? WHERE run=? AND task=?",
                            (json.dumps(stats), run_id, task_id))

    def close(self):
        self.db.close()


async def run(plan, root, ledger, *, model=None, client=None, revision=None,
              pilot=False, concurrency=2, timeout=90, run_id=None):
    batch_start = time.monotonic()
    if type(concurrency) is not int or not 1 <= concurrency <= 2 or not 0 < timeout <= 600:
        raise ValueError("concurrency_1_or_2_timeout_up_to_600s")
    if model:
        public_text(model)
    if revision:
        public_text(revision)
    tasks, order = validate(plan)
    sources = Sources(root)
    # Capture every declared input before any paid call. One working snapshot per run.
    inputs = {tid: sources.select(task.get("files")) for tid, task in tasks.items()}
    public = {}
    for tid in order:
        public[tid] = (tasks[tid].get("public") and inputs[tid]["committed"] and not inputs[tid]["sensitive"]
                       and all(public[d] for d in tasks[tid].get("after", [])))
    implementation = digest([
        path.read_text(encoding="utf-8") for path in sorted(Path(__file__).parent.glob("*.py"))
        if path.name in {"context.py", "engine.py", "proxy.py"}
    ])
    run_id = run_id or uuid.uuid4().hex
    slots = asyncio.Semaphore(concurrency)
    active = peak = 0
    stopped = None
    check = None
    shared = {}
    jobs = {}

    async def execute(tid):
        nonlocal active, peak, stopped, check
        task = tasks[tid]
        source = inputs[tid]
        started = time.monotonic()
        deps = {dep: await jobs[dep] for dep in task.get("after", [])}
        mode, reason = route(task, model, pilot)
        stats = dict(model=None, task_type=task["kind"], calls=0, retries=0, errors=0,
                     cache_hit=False, input_tokens=0, output_tokens=0, cached_input_tokens=0,
                     quality=None, rework=None, tests_passed=None)

        def result(status, route_name, reason_code, report=None, receipt=None, *, completed_key=None, keep=False):
            stats["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            stats["status"] = status
            stats["route"] = route_name
            ledger.record(run_id, tid, stats, report, completed_key, keep)
            out = dict(status=status, route=route_name, reason=reason_code, metrics=stats)
            if report is not None:
                out["report"] = report
            if receipt:
                out["receipt"] = receipt
            if status == "direct":
                out["handoff"] = dict(question=task.get("question", ""), files=task["files"],
                                      dependencies=list(deps))
            return out

        if any(row["status"] != "ok" for row in deps.values()):
            return result("direct", "astra", "requires_dependency_review")
        if mode == "astra":
            return result("direct", mode, reason)
        context = source["context"]
        if deps and mode == "proxy":
            context += "\nUpstream public reports:\n" + json.dumps(
                {key: row["report"] for key, row in deps.items()}, ensure_ascii=False)
        if mode == "proxy":
            if source["sensitive"]:
                return result("direct", "astra", "sensitive_context")
            if not public[tid]:
                return result("direct", "astra", "requires_reviewed_public_source")
            try:
                public_text(context)
            except ValueError:
                return result("direct", "astra", "sensitive_context")
            if len(context.encode()) > MAX_INPUT:
                return result("direct", "astra", "context_too_large")
            if client is None:
                return result("direct", "astra", "proxy_unavailable")
        key = digest([implementation, sources.head, mode, source["signature"],
                      task.get("question"), digest(context), model if mode == "proxy" else None,
                      revision if mode == "proxy" else None])
        if key in shared:
            prior = await shared[key]
            stats["cache_hit"] = prior["status"] == "ok"
            return result(prior["status"], prior["route"], "same_run_" + prior["reason"],
                          prior.get("report"), prior.get("receipt"))
        shared[key] = asyncio.current_task()
        saved = ledger.lookup(key)
        if saved:
            if saved[0] == "done":
                stats["cache_hit"] = True
                return result("ok", mode, "verified_input_cache", json.loads(saved[1]))
            return result("direct", "astra", "verify_previous_request", receipt=key)

        if mode == "local":
            claimed = ledger.claim(key)
            return result("ok", mode, reason, inventory(source["chunks"]),
                          completed_key=key if claimed else None, keep=True)

        async with slots:
            if stopped:
                return result("direct", "astra", stopped)
            from .proxy import ProxyError
            stats["model"] = model
            if check is None:
                check = asyncio.create_task(asyncio.wait_for(client.preflight(model), timeout))
            try:
                await asyncio.shield(check)
            except (ProxyError, TimeoutError) as exc:
                stopped = getattr(exc, "code", "preflight_timeout")
                stats["errors"] = 1
                return result("direct", "astra", stopped)
            if stopped:
                return result("direct", "astra", stopped)
            if not ledger.claim(key):
                return result("direct", "astra", "verify_previous_request", receipt=key)
            active += 1
            peak = max(peak, active)
            try:
                stats.update({name: None for name in COUNTERS})
                report, usage = await asyncio.wait_for(
                    client.analyze(model, task["question"], context), timeout)
                stats["calls"] = 1
                stats.update({name: (usage or {}).get(name) for name in COUNTERS})
                # Defensive check before writing model text to disk or stdout.
                for line in (report["summary"], *report["evidence"]):
                    public_text(line)
                return result("ok", mode, reason, report, completed_key=key, keep=bool(revision))
            except asyncio.CancelledError:
                ledger.release(key, uncertain=True)
                stats.update(calls=None, errors=1, status="cancelled", route=mode,
                             elapsed_ms=round((time.monotonic() - started) * 1000))
                ledger.record(run_id, tid, stats)
                raise
            except (ProxyError, TimeoutError, ValueError) as exc:
                code = getattr(exc, "code", "timeout" if isinstance(exc, TimeoutError) else "invalid_report")
                uncertain = getattr(exc, "uncertain", True)
                attempted = getattr(exc, "attempted", None)
                if attempted is not None:
                    stats["calls"] = int(attempted)
                elif stats["calls"] != 1:
                    stats["calls"] = None
                if attempted is False:
                    stats.update({name: 0 for name in COUNTERS})
                elif getattr(exc, "usage", None):
                    stats.update({name: exc.usage.get(name) for name in COUNTERS})
                stats["errors"] = 1
                ledger.release(key, uncertain=uncertain)
                # Pause the remaining batch after a backend failure, including 429.
                stopped = code
                return result("direct", "astra", code, receipt=key if uncertain else None)
            finally:
                active -= 1

    try:
        async with asyncio.TaskGroup() as group:
            for tid in order:
                jobs[tid] = group.create_task(execute(tid))
    finally:
        if check and not check.done():
            check.cancel()
            await asyncio.gather(check, return_exceptions=True)
    return {"run": run_id, "commit": sources.head, "peak_concurrency": peak, "plan_sha256": digest(plan),
            "elapsed_ms": round((time.monotonic() - batch_start) * 1000),
            "files_read": len(sources.files), "tasks": {tid: jobs[tid].result() for tid in tasks}}
