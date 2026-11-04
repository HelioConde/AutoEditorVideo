#!/usr/bin/env python3
"""Biblioteca navegavel por canal. NUNCA move, apaga ou altera o MP4 original.

Origem: assets/gerados, com caminhos antigos intactos para render, cache,
YouTube, Instagram, TikTok e Kwai. Destino: assets/gerados/biblioteca-videos.
Padrao copia: arquivos independentes; modo hardlink opcional e economico.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("Kids", "Gamer", "Otaku Multicena", "Otaku Reframe")
LIBRARY = ("assets", "gerados", "biblioteca-videos")
SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")
VIDEO_EXTENSIONS = {".mp4"}
NOT_FINAL = ("preview", "render-temp", "temp-", "sample", "teste-", "test-",
             "cena-", "clip-", "frame-", "draft-")


@dataclass(frozen=True)
class Video:
    source: Path
    channel: str
    episode: str


def _safe_component(value: str) -> str:
    name = SAFE_NAME.sub("-", value).strip(".-")[:110]
    return name or "avulso"


def _final_video(filename: str) -> bool:
    lower = filename.casefold()
    return Path(filename).suffix.lower() in VIDEO_EXTENSIONS and not (
        lower.startswith(NOT_FINAL) or lower.endswith(".partial.mp4")
    )


def classify(source: Path, *, root: Path = ROOT) -> Video | None:
    """Conservative rules. Ambiguous videos are reported, never misfiled."""
    source = Path(source)
    generation = root / "assets" / "gerados"
    try:
        rel = source.relative_to(generation)
    except ValueError:
        return None
    parts = rel.parts
    if not parts or not _final_video(parts[-1]):
        return None
    if parts[0].casefold() == "biblioteca-videos":
        return None
    if parts[0] == "kids-emanuelly":
        if (len(parts) == 3 and parts[2] == "final.mp4"
                and re.fullmatch(r"kids-emanuelly-ep01-p0[1-4]-[a-z0-9-]+", parts[1])):
            return Video(source, "Kids", _safe_component(parts[1]))
        return None
    if parts[0] == "piloto-canais-v3":
        # Nunca copiar trechos de captura como se fossem videos finais.
        if len(parts) != 4 or parts[1] not in ("games", "kids") or parts[3] != "final.mp4":
            return None
        if not re.fullmatch(r"(game|kids)-\d{3}-[a-z0-9-]+", parts[2]):
            return None
        channel = "Gamer" if parts[1] == "games" else "Kids"
        if (parts[1] == "games") != parts[2].startswith("game-"):
            return None
        return Video(source, channel, _safe_component(parts[2]))
    if parts[0] == "shorts-animados":
        # Nao varrer cenas, testes, assets, fontes ou cortes intermediarios.
        if len(parts) == 4 and parts[2].casefold() == "en-us":
            if "-en-us-" not in parts[3].casefold():
                return None
            return Video(source, "Otaku Reframe", _safe_component(parts[1]))
        if len(parts) == 3 and parts[2].casefold().startswith("arquivo-otaku-"):
            return Video(source, "Otaku Multicena", _safe_component(parts[1]))
        if len(parts) == 3 and parts[2].startswith(parts[1]) and "-en-US-" not in parts[2]:
            return Video(source, "Otaku Multicena", _safe_component(parts[1]))
        return None
    # Alguns videos da versao antiga estao soltos em assets/gerados.
    if len(parts) == 1 and parts[0].casefold().startswith("arquivo-otaku-"):
        return Video(source, "Otaku Multicena", "arquivos-antigos")
    return None


def scan(root: Path = ROOT) -> tuple[list[Video], list[Path]]:
    gen = root / "assets" / "gerados"
    if not gen.exists():
        return [], []
    if not gen.is_dir():
        raise ValueError("assets/gerados existe, mas nao e uma pasta")
    videos, unknown = [], []
    # Restrict scanning to known output locations to avoid copying game captures.
    roots = [gen / "shorts-animados", gen / "piloto-canais-v3", gen / "kids-emanuelly"]
    files = [p for p in gen.glob("*.mp4") if p.is_file()]
    for candidate in roots:
        if candidate.is_dir():
            files.extend(p for p in candidate.rglob("*.mp4") if p.is_file())
    for file in sorted(set(files)):
        if not file.is_file() or file.is_symlink():
            unknown.append(file)
            continue
        row = classify(file, root=root)
        if row is not None:
            videos.append(row)
        elif not str(file).startswith(str(gen / "piloto-canais-v3" / "capturas")):
            unknown.append(file)
    return videos, unknown


def digest(file: Path) -> str:
    h = hashlib.sha256()
    with file.open("rb") as f:
        while True:
            data = f.read(4 * 1024 * 1024)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _destination(video: Video, output: Path) -> Path:
    assert video.channel in CHANNELS
    return output / video.channel / video.episode / video.source.name


def archive_one(video: Video, *, output: Path, method: str = "copiar") -> dict:
    """Idempotente. Nao modifica ou apaga versoes antigas, mesmo em colisao."""
    if method not in ("copiar", "link"):
        raise ValueError("Metodo invalido")
    src = video.source
    if not src.is_file() or src.is_symlink():
        raise ValueError("Origem ausente ou simbolica, nao organizar: " + str(src))
    src_hash = digest(src)
    destination = _destination(video, output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and digest(destination) == src_hash:
        return {"status": "existente", "channel": video.channel,
                "episode": video.episode, "source": str(src),
                "destination": str(destination), "sha256": src_hash,
                "size_bytes": src.stat().st_size}
    if destination.exists():
        destination = destination.with_name(
            destination.stem + "--" + src_hash[:12] + destination.suffix
        )
    if destination.is_file() and digest(destination) == src_hash:
        status = "existente"
    else:
        if destination.exists():
            raise ValueError("Colisao nao resolvida: " + str(destination))
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".partial",
                                         delete=False) as temp:
            tmp = Path(temp.name)
        tmp.unlink()
        try:
            if method == "link":
                os.link(src, tmp)
            else:
                shutil.copy2(src, tmp)
            if digest(tmp) != src_hash:
                raise IOError("Copia nao confere com arquivo original")
            # Recuse replacing an existing destination even if it appeared
            # between planning and the actual copy. No destructive moves.
            if destination.exists():
                raise FileExistsError("Destino apareceu durante a operacao: " + str(destination))
            tmp.rename(destination)
        finally:
            tmp.unlink(missing_ok=True)
        status = "vinculado" if method == "link" else "copiado"
    return {"status": status, "channel": video.channel,
            "episode": video.episode, "source": str(src),
            "destination": str(destination), "sha256": src_hash,
            "size_bytes": src.stat().st_size}


def organize(*, root: Path = ROOT, output: Path | None = None, method: str = "copiar",
             preview: bool = True) -> dict:
    root = Path(root).resolve()
    generation = (root / "assets" / "gerados").resolve()
    target = (Path(output) if output else generation / "biblioteca-videos").resolve()
    if target == generation or target == root or generation not in target.parents:
        raise ValueError("Destino da biblioteca deve ficar DENTRO de assets/gerados")
    videos, unknown = scan(root)
    rows = []
    for item in videos:
        destination = _destination(item, target)
        rows.append(
            {"channel": item.channel, "episode": item.episode,
             "source": str(item.source), "destination": str(destination),
             "size_bytes": item.source.stat().st_size, "status": "previsto"}
            if preview else archive_one(item, output=target, method=method)
        )
    if not preview:
        for channel in CHANNELS:
            (target / channel).mkdir(parents=True, exist_ok=True)
        catalog = {
            "schema": "autoeditorvideo/biblioteca-videos/v1",
            "method": method,
            "note": "Originais preservados no local antigo; biblioteca nao substitui backup",
            "videos": rows,
            "nao_identificados": [str(x) for x in unknown],
        }
        manifest = target / "catalogo.json"
        temp = target / "catalogo.partial.json"
        temp.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        temp.replace(manifest)
    return {
        "preview": preview,
        "root": str(root),
        "library": str(target),
        "channels": {name: sum(v.channel == name for v in videos) for name in CHANNELS},
        "files": rows,
        "unclassified": [str(x) for x in unknown],
        "source_files_moved": 0,
        "source_files_deleted": 0,
        "youtube_uploads": 0,
    }



def refresh_library_after_render(root: Path = ROOT) -> dict:
    """Sync only after the user has initialized the library via Organizar.

    This is post-render best-effort indexing, not a rendering QA, publishing
    action or reason to regenerate video. The original file remains untouched.
    """
    root = Path(root).resolve()
    target = root / "assets" / "gerados" / "biblioteca-videos"
    if not target.is_dir():
        return {"status": "not_initialized", "copied": 0}
    result = organize(root=root, preview=False)
    return {
        "status": "updated",
        "videos": len(result["files"]),
        "copied": sum(row["status"] == "copiado" for row in result["files"]),
        "unknown": len(result["unclassified"]),
    }

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Organizar MP4 por Kids, Gamer, Otaku Multicena e Reframe")
    p.add_argument("--acao", choices=("prever", "organizar"), default="prever")
    p.add_argument("--raiz", type=Path, default=ROOT)
    p.add_argument("--saida", type=Path)
    p.add_argument("--metodo", choices=("copiar", "link"), default="copiar")
    args = p.parse_args(argv)
    report = organize(root=args.raiz, output=args.saida, method=args.metodo,
                      preview=(args.acao == "prever"))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print("[ORGANIZADOR BLOQUEADO] " + str(exc), file=sys.stderr)
        raise SystemExit(1)
