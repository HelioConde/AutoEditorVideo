"""Regressao: PowerShell nao deve abortar ao testar imports ausentes."""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "diagnosticar_dependencias_master.py"
spec = importlib.util.spec_from_file_location("diagnosticar_dependencias_master", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_core_all_present():
    assert mod.missing_packages(importer=lambda module: None) == []


def test_core_two_missing():
    def load(module):
        if module in {"PIL.Image", "requests"}:
            raise ModuleNotFoundError(module)
    assert mod.missing_packages(importer=load) == ["Pillow", "requests"]


def test_broken_numpy_import_can_be_repaired():
    def load(module):
        if module == "numpy":
            raise RuntimeError("DLL failed")
    assert mod.missing_packages(importer=load) == ["numpy"]


def test_voice_is_independent_of_core():
    def load(module):
        if module == "edge_tts":
            raise ModuleNotFoundError(module)
    assert mod.missing_packages(voice=True, importer=load) == ["edge-tts"]


def test_cli_never_tracebacks_for_missing_optional_package():
    cp = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--voz"],
        capture_output=True, text=True, check=False
    )
    assert cp.returncode == 0
    assert cp.stderr == ""
    assert cp.stdout.strip() in ("", "edge-tts")


def test_ps1_checks_missing_dependencies_without_triggering_native_stderr():
    ps1 = (ROOT / "gerar-shorts-master.ps1").read_text(encoding="utf-8")
    assert "diagnosticar_dependencias_master.py" in ps1
    assert not any("2>$null" in line and not line.lstrip().startswith("#") for line in ps1.splitlines())
    assert "uv pip install --python $py -r" in ps1
    assert "$missingVoice" in ps1
