"""Fail-closed contract checks for the one-at-a-time PUBLIC BR experiment.

Offline tests: no credential access, no image provider, no YouTube calls.
"""
from __future__ import annotations
import ast
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
FILES=[
  "scripts/otaku_br_50_generate_images.py",
  "scripts/otaku_br_50_render.py",
  "scripts/otaku_br_50_upload_public.py",
  "scripts/otaku_br_50_setup_media.py",
]

def test_new_generation_and_publication_scripts_compile_without_execution():
    for path in FILES:
        content=(ROOT/path).read_text(encoding="utf-8")
        ast.parse(content,filename=path)
        assert "Otaku" in content or "otaku" in content

def test_image_generation_is_separated_from_youtube_oauth():
    content=(ROOT/FILES[0]).read_text(encoding="utf-8")
    assert 'MAX_IMAGE_CALLS' in content
    assert 'MODEL="gpt-image-2"' in content
    assert "check_proxy_accounts(key)" in content
    assert '("push","workflow_dispatch")' in content
    assert "youtube.videos()" not in content
    assert "YOUTUBE_BR_TOKEN_JSON" not in content
    assert "PROXY_API_KEY" not in (ROOT/FILES[2]).read_text(encoding="utf-8")

def test_publication_requires_successful_thumbnail_and_prior_receipt():
    content=(ROOT/FILES[2]).read_text(encoding="utf-8")
    assert 'privacy="public"' in content
    assert 'if number<50:' in content
    assert 'previous.get("stage")!="public_processed_cover_acknowledged"' in content
    assert content.index("verify_processing(youtube,video_id)") < content.index("youtube.thumbnails().set(")
    assert content.index("youtube.thumbnails().set(") < content.index('stage="public_processed_cover_acknowledged"')
    assert 'exists_in_playlist(' in content
    assert 'store_receipt(number,preliminary)' in content
    assert 'human_visual_review' in content

def test_workflow_separates_secrets_starts_one_video_and_next_only_after_upload():
    src=(ROOT/".github/workflows/otaku-br-50-serial-public.yml").read_text(encoding="utf-8")
    data=yaml.load(src,Loader=yaml.BaseLoader)
    jobs=data["jobs"]
    assert "generate-render-one" in jobs
    assert "upload-public-cover-one" in jobs
    assert "launch-next-only-after-covered-publication" in jobs
    assert jobs["generate-render-one"]["environment"]=="image-generation"
    assert jobs["upload-public-cover-one"]["environment"]=="youtube-private-upload"
    assert jobs["generate-render-one"]["env"]["EPISODE_NUMBER"]
    assert "upload-public-cover-one" in jobs["launch-next-only-after-covered-publication"]["needs"]
    assert "gh workflow run otaku-br-50-serial-public.yml" in src
    assert '-R "$GITHUB_REPOSITORY" --ref main' in src
    assert 'then .number_start else error("INVALID_SERIAL_RESUME_AUTHORIZATION")' in src
    assert "sleep 180" in src
    assert "YOUTUBE_BR_TOKEN_JSON" not in str(jobs["generate-render-one"])
    assert "PROXY_ACCOUNTS_JSON" not in str(jobs["upload-public-cover-one"])
    assert data["concurrency"]["cancel-in-progress"]=="${{ github.event_name == 'push' }}"

def test_media_toolchain_is_reused_and_apt_is_never_invoked():
    """Regression: #45 and #48 failed with timeout 124 during apt-get.
    Cached binaries/npm/node_modules/proxy avoid repeated setup and compilation.
    """
    src=(ROOT/".github/workflows/otaku-br-50-serial-public.yml").read_text(encoding="utf-8")
    data=yaml.load(src,Loader=yaml.BaseLoader)
    steps=data["jobs"]["generate-render-one"]["steps"]
    assert data["jobs"]["generate-render-one"]["runs-on"] == "ubuntu-24.04"
    assert "sudo apt-get" not in src
    assert "static-ffmpeg==3.0" in src
    assert "otaku_br_50_setup_media.py --dir .cache/otaku-br-50/ffmpeg" in src
    assert 'echo "$GITHUB_WORKSPACE/.cache/otaku-br-50/ffmpeg" >> "$GITHUB_PATH"' in src
    assert "from capa_cinematografica import load_font" in src
    cache_names={x.get("id") for x in steps if x.get("uses","").startswith("actions/cache")}
    assert {"ffmpeg-cache","remotion-cache","proxy-cache"} <= cache_names
    assert "steps.remotion-cache.outputs.cache-hit != 'true'" in src
    assert "steps.proxy-cache.outputs.cache-hit != 'true'" in src
    assert "npm ci --no-audit --no-fund" in src
    assert "otaku-native-proxy" in src


def test_ffmpeg_cache_script_checks_version_and_copy_atomicity():
    source=(ROOT/"scripts/otaku_br_50_setup_media.py").read_text(encoding="utf-8")
    assert "get_or_fetch_platform_executables_else_raise" in source
    assert '("ffmpeg","ffprobe")' in source
    assert "os.replace(stage/name,folder/name)" in source
    assert 'folder/"ffprobe"' in source
    assert "setup(args.dir)" in source
