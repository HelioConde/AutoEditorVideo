"""Normalizacao opcional da trilha final do Short, sem nova geracao IA."""
from __future__ import annotations
import shutil
from pathlib import Path
import subprocess


def ffmpeg_executable():
    candidate=shutil.which('ffmpeg')
    if candidate: return candidate
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError,OSError):
        return None


def normalize_video_audio(path:Path, target_lufs:int=-16) -> dict:
    """Aumenta consistencia sonora sem alterar a trilha de video.

    Se o ffmpeg falhar ou estiver ausente, preserva integralmente o MP4 de entrada.
    """
    path=Path(path)
    exe=ffmpeg_executable()
    if not exe:return {'status':'skipped','reason':'ffmpeg nao encontrado; video preservado'}
    tmp=path.with_name(path.stem+'.normalize-tmp.mp4')
    try:
        cmd=[exe,'-hide_banner','-nostdin','-loglevel','error','-y',
            '-i',str(path),'-map','0:v:0','-map','0:a:0','-c:v','copy',
            '-af',f'loudnorm=I={target_lufs}:TP=-1.5:LRA=11',
            '-c:a','aac','-b:a','192k','-movflags','+faststart',str(tmp)]
        proc=subprocess.run(cmd,capture_output=True,text=True,timeout=240)
        if proc.returncode != 0 or not tmp.is_file() or tmp.stat().st_size < 1000:
            return {'status':'skipped','reason':'FFmpeg recusou normalizacao; original preservado','details':proc.stderr[-350:]}
        tmp.replace(path)
        return {'status':'normalized','target_lufs':target_lufs,'true_peak_db':-1.5}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'status':'skipped','reason':f'{type(exc).__name__}; original preservado'}
    finally:
        if tmp.exists():tmp.unlink()
