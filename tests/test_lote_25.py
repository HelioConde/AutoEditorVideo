"""Batch dry-run must never publish, waste quota or pass unreviewed scripts."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import lote_25 as batch


def test_25_diverse_ideas_not_approved():
    manifest=batch.read_manifest(batch.DEFAULT_MANIFEST)
    assert len(manifest["items"])==25
    assert all(x["aprovado"] is False and x["checagem_factual"] is False for x in manifest["items"])
    ready, rejected=batch.eligible_items(manifest)
    assert not ready
    assert len(rejected)==25


def test_no_generation_without_confirm(capsys):
    data=batch.read_manifest(batch.DEFAULT_MANIFEST)
    assert batch.run_batch(data,ROOT,25,False,False,False)==0
    assert "Nenhum video, imagem, upload" in capsys.readouterr().out


def test_fails_closed_without_approved_plans(tmp_path):
    data=batch.read_manifest(batch.DEFAULT_MANIFEST)
    assert batch.run_batch(data,tmp_path,25,False,True,False)==2


def test_path_traversal_blocked(tmp_path):
    (tmp_path/"conteudos").mkdir()
    for path in ["../.secrets/youtube-token.json","/etc/passwd","conteudos/../../.env"]:
        try:
            batch.safe_episode_path(path,tmp_path)
        except ValueError:
            pass
        else:
            raise AssertionError("fora do escopo aceito: "+path)


def test_duplicate_id_rejected(tmp_path):
    data=batch.read_manifest(batch.DEFAULT_MANIFEST)
    data["items"][1]["id"]=data["items"][0]["id"]
    path=tmp_path/"in.json"
    path.write_text(json.dumps(data),encoding="utf-8")
    try:
        batch.read_manifest(path)
    except ValueError:
        pass
    else:
        raise AssertionError("ID duplicado foi aceito")


def test_no_upload_implementation():
    source=(ROOT/"scripts"/"lote_25.py").read_text(encoding="utf-8")
    assert "videos.insert" not in source
    assert "upload(" not in source
    assert "publishAt" not in source
