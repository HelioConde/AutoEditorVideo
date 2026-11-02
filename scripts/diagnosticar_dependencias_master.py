#!/usr/bin/env python3
"""Diagnostico sem traceback para o bootstrap PowerShell do Arquivo Otaku.

Imprime nomes de distribuicoes ausentes no stdout (uma linha) e sempre
retorna 0 no fluxo normal, para o PowerShell nao transformar import falho
em erro terminante antes que o uv consiga instalar os pacotes.
"""
from __future__ import annotations

import argparse
import importlib

CORE = (("Pillow", "PIL.Image"), ("numpy", "numpy"), ("requests", "requests"))
VOICE = (("edge-tts", "edge_tts"),)


def missing_packages(*, voice: bool = False, importer=None) -> list[str]:
    importer = importer or importlib.import_module
    packages = VOICE if voice else CORE
    missing = []
    for distribution, module in packages:
        try:
            importer(module)
        except (ImportError, OSError, RuntimeError):
            # Incompatible/broken installs also need a repair attempt.
            missing.append(distribution)
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostica dependencias sem stderr ou traceback")
    parser.add_argument("--voz", action="store_true", help="Verifica somente edge-tts")
    args = parser.parse_args(argv)
    print(" ".join(missing_packages(voice=args.voz)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
