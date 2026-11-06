#!/usr/bin/env python3
"""Use reusable, versioned FFmpeg/FFprobe GitHub Actions cache, no sudo/apt.

Installs an FFmpeg 8.0 pair from the pinned static-ffmpeg==3.0 package
ONLY when there is no complete GitHub Actions cache entry. Only the two
public executables are copied into the cache, never credentials, auth or media.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

class ToolchainBlocked(RuntimeError):
    pass

def validate(path: Path, name: str) -> str:
    if not path.is_file() or not os.access(path, os.X_OK) or path.stat().st_size < 100_000:
        raise ToolchainBlocked(f"MISSING_OR_INVALID_{name.upper()}")
    try:
        output=subprocess.run([str(path),"-version"],check=True,capture_output=True,
                              text=True,timeout=25).stdout
    except (OSError,subprocess.SubprocessError) as exc:
        raise ToolchainBlocked(f"{name.upper()}_VERSION_UNAVAILABLE") from exc
    if not output.lower().startswith(name.lower()+" version"):
        raise ToolchainBlocked(f"{name.upper()}_IDENTITY_INVALID")
    return output.splitlines()[0]

def check(folder:Path) -> dict:
    return {"ffmpeg":validate(folder/"ffmpeg","ffmpeg"),
            "ffprobe":validate(folder/"ffprobe","ffprobe")}

def setup(folder:Path) -> dict:
    folder=folder.resolve()
    if folder.is_dir():
        try: return check(folder)
        except ToolchainBlocked: pass
    from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
    sources=get_or_fetch_platform_executables_else_raise()
    if len(sources)!=2:
        raise ToolchainBlocked("UPSTREAM_DID_NOT_PROVIDE_FFMPEG_AND_FFPROBE")
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="otaku-ffmpeg-") as staging:
        stage=Path(staging)
        for source,name in zip(sources,("ffmpeg","ffprobe")):
            target=stage/name
            shutil.copy2(source,target)
            target.chmod(0o755)
            validate(target,name)
        # Atomic replacement avoids treating a failed download as a valid cache.
        for name in ("ffmpeg","ffprobe"):
            os.replace(stage/name,folder/name)
    return check(folder)

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--dir",required=True,type=Path)
    parser.add_argument("--check-only",action="store_true")
    args=parser.parse_args()
    state=check(args.dir) if args.check_only else setup(args.dir)
    for name,value in state.items():
        print("[MEDIA CACHE] "+name+": "+value,flush=True)
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (ToolchainBlocked,RuntimeError,OSError) as exc:
        raise SystemExit("[MEDIA CACHE BLOCKED] "+str(exc)) from None
