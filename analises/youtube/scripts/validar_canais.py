#!/usr/bin/env python3
"""Valida a central de análise YouTube sem acessar APIs ou modificar uploads."""
from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
EXPECTED_KEYS = {"br", "en", "games", "kids", "alchemy"}


def main() -> int:
    config = json.loads((BASE / "config" / "canais.json").read_text(encoding="utf-8"))
    channels = config["channels"]
    keys = [item["key"] for item in channels]
    ids = [item["youtube_channel_id"] for item in channels]
    assert len(channels) == 5, "Esperados cinco canais"
    assert set(keys) == EXPECTED_KEYS, "Canais ausentes ou inesperados"
    assert len(set(ids)) == len(ids), "IDs duplicados"
    assert all(value.startswith("UC") for value in ids), "ID de canal inválido"
    assert config["policies"]["read_only"] is True
    assert config["policies"]["no_upload_actions"] is True
    print("Central YouTube: 5 canais válidos; análise somente leitura.")
    for item in channels:
        print(f'- {item["key"]}: {item["name"]} ({item["youtube_channel_id"]})')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
