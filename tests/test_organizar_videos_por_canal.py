"""Organizador de MP4 sem mover, apagar ou misturar canais."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import organizar_videos_por_canal as library


def file_at(root: Path, rel: str, payload: bytes = b"MP4-DADOS-EXEMPLO") -> Path:
    path = root / "assets" / "gerados" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def fixture(root: Path) -> tuple[list[Path], list[Path]]:
    relevant = [
        file_at(root, "piloto-canais-v3/kids/kids-001-estrela-azul/final.mp4", b"KIDS"),
        file_at(root, "piloto-canais-v3/games/game-001-minecraft-um-coracao/final.mp4", b"GAME"),
        file_at(root, "shorts-animados/003-death-note-xadrez/003-death-note-xadrez-master-multicenas-personagens-v3-equilibrado.mp4", b"PT"),
        file_at(root, "shorts-animados/003-death-note-xadrez/en-US/003-death-note-xadrez-en-US-master-multicenas-personagens-v3-equilibrado.mp4", b"EN"),
        file_at(root, "arquivo-otaku-piloto-v07-reuso.mp4", b"LEGADO PT"),
    ]
    ignored = [
        file_at(root, "piloto-canais-v3/capturas/game-001-minecraft-um-coracao/cena-01.mp4", b"ORIGINAL GAMEPLAY"),
        file_at(root, "shorts-animados/003-death-note-xadrez/cena-03.mp4", b"CENA INTERMEDIA"),
        file_at(root, "shorts-animados/003-death-note-xadrez/en-US/preview.mp4", b"PREVIA"),
        file_at(root, "resultado-inesperado.mp4", b"DESCONHECIDO"),
        file_at(root, "shorts-animados/003-death-note-xadrez/render-temp.mp4", b"TEMPORARIO"),
    ]
    return relevant, ignored


def test_preview_finds_four_channels_and_does_not_write(tmp_path):
    relevant, ignored = fixture(tmp_path)
    before = {x: x.read_bytes() for x in relevant + ignored}
    result = library.organize(root=tmp_path)
    assert result["preview"] is True
    assert result["channels"] == {
        "Kids": 1, "Gamer": 1, "Otaku Multicena": 2, "Otaku Reframe": 1
    }
    assert result["source_files_moved"] == 0
    assert result["source_files_deleted"] == 0
    assert result["youtube_uploads"] == 0
    assert not (tmp_path / "assets/gerados/biblioteca-videos").exists()
    assert all(f.read_bytes() == original for f, original in before.items())
    assert any("resultado-inesperado.mp4" in item for item in result["unclassified"])
    assert not any("capturas/" in item.replace("\\", "/") for item in result["unclassified"])


def test_organize_copies_preserving_originals_and_is_idempotent(tmp_path):
    relevant, ignored = fixture(tmp_path)
    original = {x: x.read_bytes() for x in relevant + ignored}
    first = library.organize(root=tmp_path, preview=False)
    dest = tmp_path / "assets" / "gerados" / "biblioteca-videos"
    assert {p.name for p in dest.iterdir() if p.is_dir()} == set(library.CHANNELS)
    assert all(item["status"] == "copiado" for item in first["files"])
    assert len(first["files"]) == 5
    assert (dest / "Otaku Reframe" / "003-death-note-xadrez" /
            relevant[3].name).read_bytes() == b"EN"
    assert (dest / "Otaku Multicena" / "arquivos-antigos" /
            relevant[4].name).read_bytes() == b"LEGADO PT"
    assert all(f.read_bytes() == original_data for f, original_data in original.items())
    assert json.loads((dest / "catalogo.json").read_text(encoding="utf-8"))["schema"] == \
           "autoeditorvideo/biblioteca-videos/v1"
    second = library.organize(root=tmp_path, preview=False)
    assert all(item["status"] == "existente" for item in second["files"])
    assert sum(1 for _ in dest.rglob("*.mp4")) == 5


def test_rerender_creates_a_version_instead_of_overwriting(tmp_path):
    file = file_at(tmp_path, "piloto-canais-v3/kids/kids-001-estrela-azul/final.mp4", b"PRIMEIRO")
    library.organize(root=tmp_path, preview=False)
    file.write_bytes(b"SEGUNDO")
    again = library.organize(root=tmp_path, preview=False)
    copied = again["files"][0]
    assert copied["status"] == "copiado"
    lib = tmp_path / "assets/gerados/biblioteca-videos/Kids/kids-001-estrela-azul"
    assert (lib / "final.mp4").read_bytes() == b"PRIMEIRO"
    assert (lib / ("final--" + hashlib.sha256(b"SEGUNDO").hexdigest()[:12] + ".mp4")).read_bytes() == b"SEGUNDO"
    assert file.read_bytes() == b"SEGUNDO"
    third = library.organize(root=tmp_path, preview=False)
    assert third["files"][0]["status"] == "existente"


def test_ambiguous_sources_are_never_guessed(tmp_path):
    unknown = file_at(tmp_path, "shorts-animados/003-death-note-xadrez/strange.mp4")
    row = library.classify(unknown, root=tmp_path)
    assert row is None
    assert library.classify(file_at(tmp_path, "resultado-v06.mp4"), root=tmp_path) is None
    assert library.classify(file_at(tmp_path, "piloto-canais-v3/games/game-001-a/final.mp4"),
                            root=tmp_path).channel == "Gamer"
    wrong = file_at(tmp_path, "piloto-canais-v3/games/kids-001-x/final.mp4")
    assert library.classify(wrong, root=tmp_path) is None


def test_cannot_archive_outside_generation_folder(tmp_path):
    relevant, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="DENTRO"):
        library.organize(root=tmp_path, output=tmp_path / "fora", preview=False)
    assert all(x.is_file() for x in relevant)


def test_cli_preview_and_organize_without_network(tmp_path, capsys):
    file_at(tmp_path, "piloto-canais-v3/kids/kids-002-cinco-passarinhos/final.mp4")
    assert library.main(["--acao", "prever", "--raiz", str(tmp_path)]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["channels"]["Kids"] == 1
    assert library.main(["--acao", "organizar", "--raiz", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["files"][0]["status"] == "copiado"
    assert (tmp_path / "assets/gerados/biblioteca-videos/Kids").is_dir()
