"""Run from a Git repository root: python -m tools.codex_aux --help."""
import argparse
import asyncio
import json
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path

from .context import git
from .engine import Ledger, run
from .proxy import ProxyClient, ProxyError


def main():
    parser = argparse.ArgumentParser(description="Bounded, read-only source analysis for Astra.")
    commands = parser.add_subparsers(dest="action", required=True)
    execute = commands.add_parser("run", help="run a JSON task plan")
    execute.add_argument("plan", type=Path)
    execute.add_argument("--model", help="exact model advertised by the local proxy")
    execute.add_argument("--revision", help="verified backend + model revision for cross-run report reuse")
    execute.add_argument("--pilot", action="store_true", help="allow a controlled unmeasured public review")
    execute.add_argument("--concurrency", type=int, choices=(1, 2), default=2)
    execute.add_argument("--timeout", type=float, default=90)
    recover = commands.add_parser("report", help="recover completed tasks by run identifier")
    recover.add_argument("run_id")
    assess = commands.add_parser("assess", help="record the primary agent's verified quality, tests and rework")
    assess.add_argument("run_id")
    assess.add_argument("task_id")
    assess.add_argument("--quality", required=True, choices=("pass", "fail"))
    assess.add_argument("--tests", required=True, type=int)
    assess.add_argument("--rework", required=True, type=int, help="number of corrective iterations")
    probe = commands.add_parser("probe", help="check the local service, account and model catalog using GET")
    probe.add_argument("--model", help="check an exact catalog entry")
    args = parser.parse_args()
    if args.action == "probe":
        catalog = asyncio.run(ProxyClient(timeout=5).preflight(args.model))
        print(json.dumps({"advertised": catalog}))
        return 0

    root = Path.cwd()
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir").decode().strip())
    ledger = Ledger(git_dir / "codex-aux.sqlite3")
    try:
        if args.action == "assess":
            ledger.assess(args.run_id, args.task_id, quality=args.quality, tests=args.tests, rework=args.rework)
            return 0
        if args.action == "report":
            recovered = ledger.report(args.run_id)
            print(json.dumps(recovered, ensure_ascii=True))
            return 0 if recovered else 1
        if args.plan.stat().st_size > 128_000:
            raise ValueError("plan_too_large")
        plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
        run_id = uuid.uuid4().hex
        print("run " + run_id, file=sys.stderr, flush=True)
        output = asyncio.run(run(
            plan, root, ledger, model=args.model,
            client=ProxyClient(timeout=args.timeout) if args.model else None,
            pilot=args.pilot, concurrency=args.concurrency, timeout=args.timeout,
            revision=args.revision, run_id=run_id,
        ))
        print(json.dumps(output, ensure_ascii=True, indent=2))
        return 0 if all(row["status"] == "ok" for row in output["tasks"].values()) else 2
    finally:
        ledger.close()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except (OSError, ValueError, TypeError, ExceptionGroup, sqlite3.Error, subprocess.SubprocessError, ProxyError) as exc:
        # Do not render exceptions containing source text, paths, API keys or HTTP bodies.
        code = getattr(exc, "code", None) or type(exc).__name__
        if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], str):
            candidate = exc.args[0]
            if candidate.isascii() and candidate.replace("_", "").isalnum():
                code = candidate
        print(json.dumps({"error": code}), file=sys.stderr)
        sys.exit(1)
