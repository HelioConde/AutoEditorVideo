"""Regressao: evita erro de quoting do PowerShell 5.1 no argumento -c."""
from pathlib import Path

ROOT = Path(__file__).parents[1]

def test_gpt4free_import_sem_print_com_aspas():
    script = (ROOT / "scripts/instalar-gpt4free.ps1").read_text(encoding="utf-8")
    assert "& $python -c 'import g4f, fastapi, PIL'" in script
    assert 'print("GPT4Free importado' not in script

def test_mpt_import_sem_print_com_aspas():
    script = (ROOT / "scripts/instalar-windows.ps1").read_text(encoding="utf-8")
    assert "& $python -c 'import sys, PIL; assert sys.version_info[:2] == (3, 11), sys.version'" in script
    assert 'print("Python:"' not in script
