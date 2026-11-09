"""Bounded, read-only source selection. No subprocess receives instructions from a model."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

SUFFIXES = {".py", ".ps1", ".ts", ".tsx", ".js", ".cjs", ".md", ".yml", ".yaml"}
EXCLUDED = {
    "node_modules", "dist", "build", "work", "storage", "assets", "public",
    "conteudos", "dados", "config", "configs", "outputs", "__pycache__",
}
NAME = re.compile(r"^[\w./-]+$", re.ASCII)
PRIVATE = re.compile(r"secret|credent|private|privad|password|passwd|oauth|auth[_.-]|token[_.-]", re.I)
SECRET = re.compile(
    r"-----BEGIN [^-]*(?:PRIVATE KEY|CERTIFICATE)-----|data:[^,\s]*;base64,"
    r"|(?:sk-(?:proj-)?|gh[pousr]_|github_pat_|AIza|AKIA|ya29\.|xox[baprs]-)[A-Za-z0-9_.-]{12,}"
    r"|Bearer\s+[A-Za-z0-9_./+=-]{12,}"
    r"|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{8,}"
    r"|(?:api[_-]?key|password|client[_-]?secret|refresh[_-]?token|access[_-]?token)"
    r"""["']?\s*[:=]\s*["'][^"'\s]{4,}["']"""
    r"|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|[A-Za-z]:[\\/](?:Users|Documents and Settings)[\\/]",
    re.I,
)
ASSIGNMENT = re.compile(
    r"""(?:api[_-]?key|password|client[_-]?secret|refresh[_-]?token|access[_-]?token)["']?\s*[:=]\s*[^\s,}\]]+""",
    re.I,
)
ID = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
SYMBOL = re.compile(r"^\s*(?:(?:export|async|public|private)\s+)*(?:class|def|function|const|interface|type)\s+([\w-]+)")
KINDS = {"inventory", "review", "architecture", "animation", "integration", "diagnosis"}
MAX_INPUT = 16000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def public_text(text):
    if not isinstance(text, str) or SECRET.search(text) or ASSIGNMENT.search(text) or "\x00" in text:
        raise ValueError("sensitive_or_invalid_text")
    return text


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


class Sources:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if Path(git(self.root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != self.root:
            raise ValueError("use_repository_root")
        self.head = git(self.root, "rev-parse", "HEAD").decode().strip()
        self.files = {}

    def read(self, name):
        if not isinstance(name, str) or not NAME.fullmatch(name):
            raise ValueError("invalid_source_path")
        public_text(name)
        rel = PurePosixPath(name)
        if (name != rel.as_posix() or rel.is_absolute() or rel.suffix.lower() not in SUFFIXES
                or PRIVATE.search(name) or any(
                    part.startswith(".") and part != ".github" or part.lower() in EXCLUDED
                    for part in rel.parts)):
            raise ValueError("source_path_disallowed")
        if name not in self.files:
            path = self.root / name
            if path.resolve() != path or not path.is_file() or path.stat().st_size > 1_000_000:
                raise ValueError("source_not_regular_or_too_large")
            data = path.read_bytes()
            try:
                blob = git(self.root, "show", self.head + ":" + name)
            except subprocess.CalledProcessError:
                blob = None
            clean = blob is not None and blob.replace(b"\r\n", b"\n") == data.replace(b"\r\n", b"\n")
            self.files[name] = (data.decode("utf-8-sig").splitlines(), hashlib.sha256(data).hexdigest(), clean)
        return self.files[name]

    def select(self, specs):
        if not isinstance(specs, list) or not 1 <= len(specs) <= 12:
            raise ValueError("select_1_to_12_source_ranges")
        chunks, signatures = [], []
        committed = True
        sensitive = False
        for spec in specs:
            if not isinstance(spec, dict) or set(spec) != {"path", "start", "end"}:
                raise ValueError("expected_path_start_end")
            name, start, end = spec["path"], spec["start"], spec["end"]
            lines, signature, clean = self.read(name)
            if (type(start) is not int or type(end) is not int
                    or not 1 <= start <= end <= len(lines) or end - start >= 160):
                raise ValueError("invalid_line_range")
            committed &= clean
            signatures.append((spec, signature))
            chunks.append({"path": name, "start": start, "lines": lines[start - 1:end]})
            for line in lines[start - 1:end]:
                try:
                    public_text(line)
                except ValueError:
                    sensitive = True
        packed = json.dumps(chunks, ensure_ascii=False)
        if len(packed.encode()) > MAX_INPUT:
            raise ValueError("source_context_exceeds_16000_bytes")
        return dict(context=packed, signature=digest(signatures), committed=committed, sensitive=sensitive,
                    chunks=chunks)


def inventory(chunks):
    evidence = []
    for chunk in chunks:
        for number, line in enumerate(chunk["lines"], chunk["start"]):
            match = SYMBOL.match(line)
            if match and not SECRET.search(match[1]) and len(evidence) < 40:
                evidence.append(f"{chunk['path']}:{number} {match[1]}")
    return {"summary": f"{len(chunks)} source range(s)", "evidence": evidence}


def validate(plan):
    if not isinstance(plan, dict) or set(plan) != {"tasks"} or not isinstance(plan["tasks"], list):
        raise ValueError("expected_tasks")
    tasks = {}
    for item in plan["tasks"]:
        if not isinstance(item, dict) or set(item) - {"id", "kind", "files", "question", "after", "budget", "public"}:
            raise ValueError("invalid_task_fields")
        tid = item.get("id")
        if not isinstance(tid, str) or not ID.fullmatch(tid) or tid in tasks or item.get("kind") not in KINDS:
            raise ValueError("invalid_task_id_or_kind")
        public_text(tid)
        question = public_text(item.get("question", ""))
        if len(question) > 2000 or (item["kind"] == "review" and not question.strip()):
            raise ValueError("invalid_question")
        after = item.get("after", [])
        if not isinstance(after, list) or not all(isinstance(v, str) and ID.fullmatch(v) for v in after):
            raise ValueError("invalid_dependencies")
        budget = item.get("budget")
        if budget is not None and (not isinstance(budget, dict) or set(budget) != {"direct", "delegated", "quality_ok"}
                or type(budget["quality_ok"]) is not bool
                or any(type(budget[k]) is not int or budget[k] <= 0 for k in ("direct", "delegated"))):
            raise ValueError("invalid_measured_budget")
        if type(item.get("public", False)) is not bool:
            raise ValueError("public_must_be_boolean")
        tasks[tid] = item
    if not 1 <= len(tasks) <= 64:
        raise ValueError("expected_1_to_64_tasks")
    from graphlib import TopologicalSorter
    graph = {tid: set(task.get("after", [])) for tid, task in tasks.items()}
    if any(dep not in tasks for deps in graph.values() for dep in deps):
        raise ValueError("unknown_dependency")
    return tasks, list(TopologicalSorter(graph).static_order())
