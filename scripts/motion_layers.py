#!/usr/bin/env python3
"""Compositor 2.5D local: anima PNG com alpha sobre fundo. Nao publica."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess


def filters(has_object: bool) -> str:
    # FFmpeg computes each position per frame. Background, actor and prop
    # are genuinely separate layers, not a zoom of one flattened scene.
    pieces = [
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=rgba[bg]",
        "[1:v]scale=850:-2,format=rgba[personagem]",
        "[bg][personagem]overlay=x='(W-w)/2+16*sin(0.8*t)':y='H-h-230+8*sin(1.3*t)':format=auto:shortest=1[base]",
    ]
    if has_object:
        pieces += [
            "[2:v]scale=350:-2,format=rgba[objeto]",
            "[base][objeto]overlay=x='(W-w)/2+38*sin(1.1*t)':y='H-h-550+22*sin(0.7*t)':format=auto:shortest=1,format=yuv420p[v]",
        ]
    else:
        pieces += ["[base]format=yuv420p[v]"]
    return ";".join(pieces)


def validate_alpha(path: Path) -> None:
    from PIL import Image
    if not path.is_file():
        raise ValueError(f"Asset ausente: {path}")
    with Image.open(path) as im:
        if "A" not in im.getbands():
            raise ValueError(f"PNG sem canal alpha: {path.name}")
        alpha = im.getchannel("A")
        min_a, max_a = alpha.getextrema()
        if min_a >= 255 or max_a <= 0:
            raise ValueError(f"PNG nao possui area transparente + opaca: {path.name}")


def build_command(background: Path, character: Path, out: Path, seconds: float,
                  obj: Path | None = None, audio: Path | None = None) -> list[str]:
    if not 0.5 <= seconds <= 60:
        raise ValueError("Duracao de um clip 2.5D deve ser entre 0.5 e 60 segundos")
    cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y",
           "-loop","1","-framerate","30","-i",str(background),
           "-loop","1","-framerate","30","-i",str(character)]
    if obj:
        cmd += ["-loop","1","-framerate","30","-i",str(obj)]
    if audio:
        cmd += ["-i",str(audio)]
    cmd += ["-filter_complex", filters(bool(obj)), "-map","[v]"]
    if audio:
        cmd += ["-map",f"{3 if obj else 2}:a:0","-c:a","aac","-b:a","160k"]
    else:
        cmd += ["-an"]
    cmd += ["-r","30","-c:v","libx264","-preset","veryfast",
            "-crf","21","-pix_fmt","yuv420p","-t",str(seconds),"-movflags","+faststart",str(out)]
    return cmd


def main() -> int:
    ap = argparse.ArgumentParser(description="Anima personagem e objetos PNG sobre fundo estatico sem consumir IA.")
    ap.add_argument("--fundo",required=True,type=Path)
    ap.add_argument("--personagem",required=True,type=Path)
    ap.add_argument("--objeto",type=Path)
    ap.add_argument("--audio",type=Path,help="Opcional; clips sem audio sao validos como material MPT, mas nao como video final.")
    ap.add_argument("--segundos",type=float,default=5.0)
    ap.add_argument("--saida",type=Path,required=True)
    ap.add_argument("--previa",action="store_true")
    args = ap.parse_args()
    try:
        cmd=build_command(args.fundo,args.personagem,args.saida,args.segundos,args.objeto,args.audio)
        if args.previa:
            print("PREVIA sem gerar video:",subprocess.list2cmdline(cmd))
            return 0
        if not shutil.which("ffmpeg"):
            raise ValueError("FFmpeg nao encontrado no PATH")
        if not args.fundo.is_file():
            raise ValueError("Fundo ausente")
        validate_alpha(args.personagem)
        if args.objeto:
            validate_alpha(args.objeto)
        if args.audio and not args.audio.is_file():
            raise ValueError("Audio ausente")
        args.saida.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(cmd,check=True,timeout=240)
        print(f"[OK] Clip 2.5D animado criado: {args.saida}")
        return 0
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        print(f"[ERRO] Motion 2.5D: {exc}")
        return 1


if __name__=="__main__":
    raise SystemExit(main())
