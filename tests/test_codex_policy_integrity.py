"""Protect the user's original policies, including in shallow checkouts without git history."""
import hashlib
import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "docs/politicas"
ORIGINAL_SECTION_DIGEST = "6a2a322b3ce2cfca92cf350a482739073ae99dfb0dd824a7cd655bf1ca4ec135"


def test_every_original_policy_survived_modularization():
    # Derived from git blob 95c4771e70ced2fb0d503a732a0625a1ef99f398.
    # Reordering entire sections and correcting a relocated link are intentional.
    sections = []
    boundary = r"(?m)(?=^#{1,2} |^Projeto local de produção|^- Nunca enviar `\.env`)"
    for policy in sorted(POLICIES.glob("*.md")):
        text = policy.read_text(encoding="utf-8").replace(
            "](../OTAKU-MULTICENA-3-0.md)", "](docs/OTAKU-MULTICENA-3-0.md)"
        )
        sections.extend(section.strip("\n") for section in re.split(boundary, text) if section.strip())
    assert len(sections) == 32
    digest = hashlib.sha256("\0".join(sorted(sections)).encode("utf-8")).hexdigest()
    assert digest == ORIGINAL_SECTION_DIGEST, "Review the owner's policy change before updating this baseline"


def test_root_routes_every_canonical_policy_for_sessions_started_at_root():
    index = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    paths = set(re.findall(r"\]\((docs/politicas/[^)]+)\)", index))
    assert paths == {p.relative_to(ROOT).as_posix() for p in POLICIES.glob("*.md")}
    assert len(index.encode("utf-8")) < 56_489


@pytest.mark.parametrize(("trigger", "targets"), [
    ("reserva", ("docs/politicas/seguranca-e-reservas.md",)),
    ("automação do motor", ("docs/politicas/producao.md",)),
    ("OAuth", ("docs/politicas/seguranca-e-reservas.md",)),
    ("agendamento", ("docs/politicas/publicacao.md",)),
    ("Otaku Multicena BR", ("docs/politicas/otaku.md",)),
    ("Emanuelly", ("docs/politicas/fofinhos-referencias.md", "docs/politicas/fofinhos-animacao.md")),
    ("Alchemy Lab", ("docs/politicas/gamer-ia.md",)),
    ("pilotos 3×2", ("docs/politicas/lancadores-e-pilotos.md",)),
    ("Remotion", ("docs/politicas/movimento-e-voz.md", "motion-remotion/AGENTS.md")),
    ("PowerShell", ("scripts/AGENTS.md",)),
    ("GitHub Actions", (".github/workflows/AGENTS.md",)),
])
def test_task_triggers_reach_required_policies(trigger, targets):
    index = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    row = next(line for line in index.splitlines()
               if line.startswith("|") and trigger in line.split("|")[1])
    for target in targets:
        assert f"]({target})" in row
        assert (ROOT / target).is_file()


def test_scoped_instructions_refer_back_to_global_routes():
    for filename in ("scripts/AGENTS.md", "motion-remotion/AGENTS.md", ".github/workflows/AGENTS.md"):
        scoped = ROOT / filename
        links = re.findall(r"\]\(([^)]+)\)", scoped.read_text(encoding="utf-8"))
        resolved = {(scoped.parent / link).resolve() for link in links}
        assert ROOT / "AGENTS.md" in resolved
        assert all(path.is_file() for path in resolved)
