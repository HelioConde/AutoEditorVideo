"""Unit tests for official TikTok integration; never calls TikTok APIs."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publicar_tiktok as tk


def test_tiktok_caption_utf8_and_no_youtube_short_tags():
    manifest = tk.read_json(tk.MANIFEST)
    assert len(manifest["episodes"]) == 5
    for episode in manifest["episodes"]:
        caption = tk.caption(episode)
        assert "#Shorts" not in caption
        assert "#ArquivoOtaku" in caption
        assert "\ufffd" not in caption
        assert len(caption.encode("utf-16-le")) // 2 < 2200
    assert "MAÇÃS" in tk.caption(manifest["episodes"][-1])


@pytest.mark.parametrize("size,expected_count,expected_chunk", [
    (4_000_000, 1, 4_000_000),
    (50_000_123, 1, 50_000_123),
    (70_000_123, 7, 10_000_000),
    (100_000_123, 10, 10_000_000),
])
def test_tiktok_upload_chunks_cover_video_exactly(size, expected_count, expected_chunk):
    chunk_size, chunks = tk.chunk_plan(size)
    assert chunk_size == expected_chunk
    assert len(chunks) == expected_count
    assert chunks[0][0] == 0
    assert sum(chunk_len for _, chunk_len in chunks) == size
    for first, second in zip(chunks, chunks[1:]):
        assert first[0] + first[1] == second[0]
    assert chunks[-1][0] + chunks[-1][1] == size
    assert chunks[-1][1] <= 128_000_000


def test_tiktok_rejects_untrusted_upload_host():
    for url in ("http://open-upload.tiktokapis.com/video/",
                "https://tiktokapis.com.evil.example/video/",
                "https://evil.example/"):
        with pytest.raises(tk.TikTokError, match="dominio confiavel"):
            tk.validate_upload_url(url)
    tk.validate_upload_url("https://upload.us.tiktokapis.com/video/?upload_id=example")


def test_tiktok_pkce_uses_tiktok_hex_sha256():
    config = {"client_key": "demo", "redirect_uri": "http://127.0.0.1:8731/callback/"}
    verifier = "verifier-only"
    challenge = hashlib.sha256(verifier.encode()).hexdigest()
    url = tk.auth_url(config, "video.upload", "some-state", challenge)
    assert "code_challenge=" + challenge in url
    assert "scope=user.info.basic%2Cvideo.upload" in url
    assert "state=some-state" in url


def test_existing_upload_is_not_initialized_again(monkeypatch, tmp_path):
    monkeypatch.setattr(tk, "STATE", tmp_path / "estado.json")
    item = {"id": "003", "digest": "abcdef", "size": 1000, "video": tmp_path / "unused.mp4",
            "caption": "abc", "duration": 33.0}
    token = {"open_id": "owner123", "access_token": "hidden"}
    key = tk.key_for(item, token["open_id"], "rascunho")
    previous = {"id": "003", "status": "transferido_aguardando_processamento",
                "publish_id": "v_inbox_example"}
    saved = {"items": {key: previous}}
    monkeypatch.setattr(tk, "api_post", lambda *_args: pytest.fail("duplicate API request"))
    assert tk.send_one(item, "rascunho", "SELF_ONLY", token, None, saved) == previous


def test_initialize_inbox_and_keep_publish_id_even_if_transfer_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(tk, "STATE", tmp_path / "estado.json")
    video = tmp_path / "video.mp4"
    video.write_bytes(b"x" * 1000)
    item = {"id": "003", "digest": hashlib.sha256(video.read_bytes()).hexdigest(),
            "video": video, "size": 1000, "caption": "Teste", "duration": 10.0}
    saved = {"schema": "arquivo-otaku/tiktok/v1", "items": {}}
    token = {"open_id": "alice", "access_token": "secret"}
    calls = []

    def fake_api(route, *_args):
        calls.append(route)
        return {"publish_id": "pub123",
                "upload_url": "https://open-upload.tiktokapis.com/video/?example"}

    def fake_transfer(*_args):
        assert tk.STATE.is_file()
        raise RuntimeError("Network interrupted")

    monkeypatch.setattr(tk, "api_post", fake_api)
    monkeypatch.setattr(tk, "transfer", fake_transfer)
    with pytest.raises(tk.TikTokError, match="nao rode"):
        tk.send_one(item, "rascunho", "SELF_ONLY", token, None, saved)
    assert calls == ["inbox/video/init/"]
    stored = tk.read_json(tk.STATE)["items"]
    record = next(iter(stored.values()))
    assert record["publish_id"] == "pub123"
    assert record["status"] == "transferencia_interrompida_verifique_status"


def test_direct_mode_requires_creator_privacy_and_duration(monkeypatch):
    token = {"open_id": "account123", "access_token": "secret"}
    item = {"id": "003", "digest": "d123", "size": 100, "duration": 40, "caption": "Texto"}
    with pytest.raises(tk.TikTokError, match="indisponivel"):
        tk.send_one(item, "direto", "PUBLIC_TO_EVERYONE", token,
                    {"privacy_level_options": ["SELF_ONLY"], "max_video_post_duration_sec": 300},
                    {"items": {}})
    with pytest.raises(tk.TikTokError, match="duracao"):
        tk.send_one(item, "direto", "SELF_ONLY", token,
                    {"privacy_level_options": ["SELF_ONLY"], "max_video_post_duration_sec": 30},
                    {"items": {}})


def test_preparation_never_network_and_does_not_send(monkeypatch, capsys):
    data = {"id": "003", "duration": 33.2, "width": 1080, "height": 1920, "size": 1_500_000,
            "caption": "Legenda"}
    monkeypatch.setattr(tk, "episode_items", lambda *_args: [data])
    monkeypatch.setattr(tk, "get_token", lambda *_args: pytest.fail("must not read tokens"))
    assert tk.main(["--acao", "preparar"]) == 0
    assert "Nenhum arquivo enviado" in capsys.readouterr().out
