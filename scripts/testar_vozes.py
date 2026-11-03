#!/usr/bin/env python3
"""Local side-by-side voice-only test. Never creates video or uploads to YouTube."""
from __future__ import annotations

import argparse
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from roteiro_para_storyboard import select_episode
from narracao_shorts import ensure_voice


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara voz VoiceStudio e Edge TTS, sem publicar")
    parser.add_argument("--id", default="401-jujutsu-kaisen-ep01")
    parser.add_argument("--comparar-edge", action="store_true")
    parser.add_argument("--amostra-curta", action="store_true",
                        help="Testa primeiro uma frase curta em pasta separada, sem MP4/upload.")
    args = parser.parse_args()
    episode = select_episode(args.id)
    folder = ROOT / "assets" / "gerados" / "shorts-animados" / args.id
    if args.amostra_curta:
        episode = dict(episode)
        episode["script"] = (
            "Yuji encontrou um dedo amaldiçoado. Sukuna despertou, "
            "mas Yuji recuperou o controle."
        )
        folder = folder / "teste-voz-curta"
    print("[TESTE] Motor VoiceStudio: " +
          os.environ.get("OTAKU_VOICESTUDIO_MODEL", "tts-1") +
          " | roteiro: " + str(len(episode["script"].split())) +
          " palavras | sem renderizacao/upload", flush=True)
    try:
        voice, sub = ensure_voice(episode, folder, create=True, engine="voicestudio")
        print(f"[VOICESTUDIO OK] {voice}\n[LEGENDAS REALMENTE ALINHADAS] {sub}")
        if args.comparar_edge:
            edge_voice, edge_sub = ensure_voice(episode, folder, create=True, engine="edge")
            print(f"[EDGE TTS OK] {edge_voice}\n[EDGE LEGENDAS] {edge_sub}")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        print(f"[TESTE BLOQUEADO; NENHUM UPLOAD] {exc}", file=sys.stderr)
        return 1
    print("[TESTE FINALIZADO] Escute os MP3. Nenhum video foi renderizado nem enviado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
