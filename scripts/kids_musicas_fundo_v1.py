"""Duas trilhas Kids no Remotion, sem alterar os arquivos originais.

Fonte: MP3 adicionados pelo criador na RAIZ do repositorio.
O uso e local para revisao; direitos/licencas continuam pendentes antes
de qualquer publicacao. Nao usar nos canais Games ou Otaku.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

TRACKS = (
    ("Wondertrail _Main Theme_.mp3", "wondertrail-kids-01.mp3"),
    ("Wondertrail _Main Theme_2.mp3", "wondertrail-kids-02.mp3"),
)
MUSIC_POLICY = "kids/background-music/v1"
MUSIC_VOLUME = 0.075  # lower volume than voice. Verify by listening.
FADE_SECONDS = 1.5


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def choose_track(episode_id: str) -> tuple[int, str, str]:
    """Fixed alternation: 1,3 use first track; 2,4 use second."""
    parts = ("-p01-", "-p02-", "-p03-", "-p04-")
    for i, part in enumerate(parts):
        if part in episode_id and episode_id.startswith("kids-emanuelly-"):
            index = i % 2
            return index, *TRACKS[index]
    pilots = {
        "kids-001-estrela-azul": 0,
        "kids-002-cinco-passarinhos": 1,
        "kids-003-formas-casinha": 0,
    }
    if episode_id not in pilots:
        raise ValueError("Musica Kids nao autorizada para este episodio: " + episode_id)
    index = pilots[episode_id]
    return index, *TRACKS[index]


def _source(root: Path, episode_id: str) -> tuple[Path, str]:
    _index, filename, published_name = choose_track(episode_id)
    source = root / filename
    if not source.is_file() or source.is_symlink():
        raise FileNotFoundError("Faixa Kids ausente na raiz do projeto: " + str(source))
    if source.stat().st_size < 100_000:
        raise ValueError("Faixa Kids muito pequena ou incompleta: " + filename)
    with source.open("rb") as stream:
        prefix = stream.read(3)
    if not (prefix == b"ID3" or (prefix[:1] == b"\xff" and prefix[1] & 0xE0 == 0xE0)):
        raise ValueError("Faixa Kids nao parece MP3 valido: " + filename)
    return source, published_name


def music_signature(root: Path, episode_id: str) -> str:
    source, _name = _source(root, episode_id)
    return sha256(source)


def prepare_kids_music(root: Path, episode_id: str) -> dict:
    """Copy source into Remotion public once and verify bytes before rendering.

    Unlike the original MP3, the public copy is a build artifact, never a
    new tracked file, and remains only on the user's machine or CI sandbox.
    """
    source, file_name = _source(root, episode_id)
    digest = sha256(source)
    destination = root / "motion-remotion" / "public" / "generated" / "kids-musicas" / file_name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.is_file() or sha256(destination) != digest:
        partial = destination.with_suffix(".partial")
        shutil.copy2(source, partial)
        if sha256(partial) != digest:
            partial.unlink(missing_ok=True)
            raise ValueError("Copia da trilha Kids nao corresponde ao MP3 original")
        partial.replace(destination)
    return {
        "schema": MUSIC_POLICY,
        "audio": "generated/kids-musicas/" + file_name,
        "source_name": source.name,
        "sha256": digest,
        "volume": MUSIC_VOLUME,
        "fade_seconds": FADE_SECONDS,
        "rights_review": "pending_before_publication",
    }
