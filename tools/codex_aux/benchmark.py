"""Compare one Fofinhos EP01 QA task using the native Codex CLI and ChatGPT login.

A starts with the original AGENTS.md and two whole tracked sources. B uses the
new root, explicitly supplied applicable policies and audited source slices.
C replaces the slices with successful read-only proxy evidence. Run each arm
once in a fresh process. Only numeric metrics and hashes leave the harness.
"""
import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "48533df"
PYTHON_SOURCE = "scripts/fofinhos_ep01_render.py"
RENDERER = "motion-remotion/src/fofinhos-ambient-effects.tsx"
MODEL = "gpt-6-astra"
PLAN = Path(__file__).with_name("ambient_plan.json")
POLICIES = (
    "docs/politicas/seguranca-e-reservas.md", "docs/politicas/producao.md",
    "docs/politicas/fofinhos-referencias.md", "docs/politicas/fofinhos-animacao.md",
    "docs/politicas/movimento-e-voz.md", "motion-remotion/AGENTS.md",
    "scripts/AGENTS.md", "docs/memoria/animacao.md",
)
FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")
TRUTH = {
    "scene1": [2, 2, 3, 8, 0, 0],
    "scene14": [0, 0, 0, 0, 4, 1],
    "hidden_at_night": [0, 0, 0, 0, 0, 6],
    "opacity": [0, 0.5, 1],
    "anchor": [0, 1920],
    "valid_density_max": 8,
}
QUESTION = """Read-only review of the shipped Fofinhos EP01 ambient overlay.
Use the supplied evidence. Return JSON only. Do not use tools.
For counts use [clouds,butterflies,petals,pollen,eggSparkles,motes].
scene1: rendered counts for canonical scene 1 in daylight with invisible egg.
scene14: rendered counts for canonical scene 14 at night with egg visible.
hidden_at_night: rendered counts at night with egg hidden and every plan count 99
(use renderer safeguards independently of Python's plan validation).
opacity: top-level SVG opacity 0, 12 and 24 frames after scene start.
anchor: pixel anchor [x,y] if normalized eggX=-0.25 and eggY=1.1.
valid_density_max: inclusive maximum accepted by Python's density check."""
# Do not send unreviewed local files, private media, or raw intermediate logs.
SENSITIVE = re.compile(
    r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY|sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{30,}|"
    r"eyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{8,}"
)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL)


def source(path):
    return git("show", f"{BASE}:{path}").decode("utf-8")


def excerpts():
    code = source(PYTHON_SOURCE)
    nodes = [
        n for n in ast.parse(code).body
        if (isinstance(n, ast.FunctionDef) and n.name == "ambient_profiles")
        or (isinstance(n, ast.Assign)
            and any(getattr(t, "id", "") == "AMBIENT_SCENES" for t in n.targets))
    ]
    if len(nodes) != 2:
        raise ValueError("source_contract_changed")
    overlay = source(RENDERER)
    return "\n".join(ast.get_source_segment(code, n) for n in nodes) + "\n" + (
        overlay[overlay.index("const capped"):overlay.index("{/* Clouds:")]
    )


def read_policy(name):
    if name not in ("AGENTS.md", *POLICIES):
        raise ValueError("policy_path")
    return git("show", f"HEAD:{name}").decode("utf-8-sig").replace("\r\n", "\n")


def helper_metrics(data, plan, expected_commit):
    fingerprint = hashlib.sha256(json.dumps(plan, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if data.get("commit") != expected_commit or data.get("plan_sha256") != fingerprint:
        raise ValueError("wrong_proxy_experiment")
    for filename in (PYTHON_SOURCE, RENDERER):
        if git("show", f"{expected_commit}:{filename}") != git("show", f"{BASE}:{filename}"):
            raise ValueError("wrong_animation_revision")
    evidence = []
    totals = {key: 0 for key in (*FIELDS, "calls")}
    rows = data["tasks"]
    if (set(rows) != {"scripted-density", "renderer-guards"} or
            type(data.get("elapsed_ms")) is not int or data["elapsed_ms"] <= 0 or
            type(data.get("peak_concurrency")) is not int or not 1 <= data["peak_concurrency"] <= 2):
        raise ValueError("incomplete_proxy_experiment")
    for task in plan["tasks"]:
        row = rows[task["id"]]
        if row["status"] != "ok" or row["route"] != "proxy":
            raise ValueError("incomplete_proxy_task")
        metrics = row["metrics"]
        if (metrics.get("calls") != 1 or metrics.get("cache_hit") is not False or
                metrics.get("errors") != 0 or metrics.get("retries") != 0 or
                not isinstance(metrics.get("model"), str) or not metrics["model"]):
            raise ValueError("unmeasured_proxy_run")
        report = row["report"]
        if (not isinstance(report, dict) or set(report) != {"summary", "evidence"}
                or not isinstance(report["summary"], str) or not report["summary"].strip()
                or not isinstance(report["evidence"], list) or not report["evidence"]
                or not all(isinstance(item, str) and item.strip() for item in report["evidence"])):
            raise ValueError("incomplete_proxy_evidence")
        for key in totals:
            value = metrics.get(key)
            if type(value) is not int or value < 0:
                raise ValueError("unmeasured_proxy_run")
            totals[key] += value
        if metrics["cached_input_tokens"] > metrics["input_tokens"]:
            raise ValueError("inconsistent_proxy_usage")
        evidence.append(json.dumps(report, ensure_ascii=False))
    return "\n".join(evidence), totals


def run_helpers(model, timeout):
    # Generate provenance inside this invocation. No arbitrary imported report is accepted.
    head = git("rev-parse", "HEAD").decode().strip()
    for name in (PYTHON_SOURCE, RENDERER):
        local = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        if local != git("show", f"{BASE}:{name}").replace(b"\r\n", b"\n"):
            raise ValueError("wrong_animation_revision")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    # The committed plan is public, exactly scoped to the pinned source revision.
    if git("show", f"{head}:tools/codex_aux/ambient_plan.json").decode() != PLAN.read_text(encoding="utf-8"):
        raise ValueError("proxy_plan_not_committed")
    run = subprocess.run([sys.executable, "-m", "tools.codex_aux", "run", str(PLAN),
                          "--pilot", "--concurrency", "2", "--model", model,
                          "--timeout", str(min(600, timeout))], cwd=ROOT,
                         capture_output=True, timeout=timeout+30)
    if run.returncode != 0:
        raise ValueError("incomplete_proxy_run")
    result = json.loads(run.stdout)
    evidence, usage = helper_metrics(result, plan, head)
    return evidence, usage, {k: result[k] for k in ("plan_sha256", "elapsed_ms", "peak_concurrency")}


def sanitized_failure(stderr):
    text = stderr.lower()
    for tag, markers in (
        ("authentication", ["unauthorized", "authentication", " 401", " 403"]),
        ("rate_limit", ["429", "rate limit", "usage limit", "quota"]),
        ("configuration", ["config", "unexpected argument"]),
        ("model_unavailable", ["model is not supported", "model not found"]),
    ):
        if any(marker in text for marker in markers):
            return tag
    return "cli_error"


def chatgpt_login():
    probe = subprocess.run(["codex", "login", "status"], capture_output=True, timeout=15)
    return probe.returncode == 0 and b"chatgpt" in (probe.stdout + probe.stderr).lower()


def measure_arm(arm, model, timeout):
    wall_start = time.monotonic()
    helper, helper_usage, helper_run = "", None, None
    result = {"arm": arm, "model": MODEL, "effort": "ultra",
              "source_commit": git("rev-parse", BASE).decode().strip()}
    if arm == "C" and not model:
        return {**result, "status": "unavailable", "reason": "no_measured_proxy_evidence"}
    if not chatgpt_login():
        return {**result, "status": "unavailable", "reason": "chatgpt_login_required"}
    if arm == "C":
        helper, helper_usage, helper_run = run_helpers(model, timeout)
    if arm == "A":
        root = source("AGENTS.md")
        sources = source(PYTHON_SOURCE) + "\n" + source(RENDERER)
    else:
        root = read_policy("AGENTS.md")
        docs = "\n\n".join(read_policy(p) for p in POLICIES)
        sources = docs + "\n" + (excerpts() if arm == "B" else helper)
    prompt = "<evidence>\n" + sources + "\n</evidence>\n\n" + QUESTION
    if SENSITIVE.search(root + prompt):
        raise ValueError("sensitive_input_rejected")
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"):
        env.pop(key, None)
    with tempfile.TemporaryDirectory(prefix="fofinhos-bench-") as temp:
        directory = Path(temp)
        subprocess.run(["git", "init", "-q", temp], check=True, capture_output=True)
        policy = directory / "AGENTS.md"
        policy.write_text(root, encoding="utf-8")
        schema = {
            "type": "object", "required": list(TRUTH), "additionalProperties": False,
            "properties": {
                k: ({"type": "array", "items": {"type": "number"}} if isinstance(v, list)
                    else {"type": "integer"}) for k, v in TRUTH.items()
            },
        }
        schema_path = directory / "answer.schema.json"
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        cli = ["codex", "--no-daemon", "-a", "never", "exec", "--strict-config",
               "--ignore-user-config", "--ephemeral", "--json", "-s", "read-only",
               "-m", MODEL, "-c", 'model_reasoning_effort="ultra"',
               "-c", 'model_provider="openai"', "-c", 'forced_login_method="chatgpt"',
               "-c", 'web_search="disabled"', "-c", "apps._default.enabled=false",
               "-c", "plugins._default.enabled=false", "--output-schema", str(schema_path)]
        for feature in ("shell_tool", "apps", "plugins", "multi_agent", "hooks", "view_image"):
            cli.extend(["--disable", feature])
        start = time.monotonic()
        result.update(prompt_bytes=len(prompt.encode()),
                      prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
                      root_bytes=policy.stat().st_size,
                      root_sha256=hashlib.sha256(policy.read_bytes()).hexdigest())
        try:
            run = subprocess.run(cli + ["-"], cwd=directory, env=env, input=prompt.encode(),
                                 timeout=timeout, capture_output=True)
        except subprocess.TimeoutExpired:
            return {**result, "status": "timeout", "elapsed_ms": round((time.monotonic()-start)*1000)}
    result["elapsed_ms"] = round((time.monotonic()-start) * 1000)
    result["end_to_end_ms"] = round((time.monotonic()-wall_start) * 1000)
    if helper_run is not None:
        result.update(auxiliary=helper_run, auxiliary_model=model)
    raw = run.stdout.decode("utf-8", "replace")
    if run.returncode:
        return {**result, "status": "failed",
                "reason": sanitized_failure(raw + run.stderr.decode("utf-8", "replace"))}
    events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    turns = [x for x in events if x.get("type") == "turn.completed"]
    tools = [x for x in events if x.get("item", {}).get("type") not in
             (None, "reasoning", "agent_message")]
    messages = [x["item"].get("text", "") for x in events if x.get("type")=="item.completed"
                and x.get("item", {}).get("type")=="agent_message"]
    if len(turns) != 1 or tools or not messages or any(x.get("type") == "error" for x in events):
        return {**result, "status": "invalid", "reason": "not_one_tool_free_turn"}
    usage = turns[0].get("usage", {})
    if not all(type(usage.get(k)) is int and usage[k] >= 0 for k in FIELDS):
        return {**result, "status": "invalid", "reason": "missing_usage"}
    answer = json.loads(messages[-1])
    totals = {k: usage[k] + (helper_usage[k] if helper_usage else 0) for k in FIELDS}
    return {**result, "status": "completed", "astra_turns": 1,
            "proxy_calls": helper_usage["calls"] if helper_usage else 0,
            "astra_usage": {k: usage[k] for k in FIELDS}, "proxy_usage": helper_usage,
            "usage": totals, "total_tokens": totals["input_tokens"]+totals["output_tokens"],
            "checks": {k: answer.get(k)==expected for k, expected in TRUTH.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arm", choices="ABC")
    parser.add_argument("--aux-model", help="Exact advertised proxy model for an explicit C pilot.")
    parser.add_argument("--timeout", type=int, default=180)
    options = parser.parse_args()
    if options.timeout <= 0 or options.timeout > 600 or (options.aux_model and options.arm != "C"):
        parser.error("Use a 1..600s timeout and supply --aux-model only with C.")
    try:
        result = measure_arm(options.arm, options.aux_model, options.timeout)
    except (ValueError, TypeError, KeyError, OSError, subprocess.SubprocessError) as exc:
        code = str(exc)
        result = {"arm": options.arm, "status": "failed",
                  "reason": code if re.fullmatch("[a-z_]{1,60}", code) else "invalid_experiment"}
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["status"]=="completed" and all(result["checks"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
