"""All Gamer + Alchemy upload entrypoints must sanitize user-facing keywords."""
from pathlib import Path
import ast,re,sys

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/"scripts"))
from youtube_public_tags import public_tags

ALL_UPLOAD_ENTRYPOINTS=[
 "games_alchemy_ai_upload.py",
 "games_alchemy_recut_v2_upload.py",
 "games_alchemy_native_v3_upload.py",
 "games_alchemy_reference_v4_upload.py",
 "gamer_v4_three_reupload.py",
 "gamer_reference_style_5s_upload.py",
 "alchemy_v4_single_request_retry.py",
 "alchemy_v4_single_request_retry2.py",
]

def test_every_upload_filters_technical_keywords_before_youtube():
    for filename in ALL_UPLOAD_ENTRYPOINTS:
        source=(R/"scripts"/filename).read_text(encoding="utf-8")
        ast.parse(source,filename)
        assert "from youtube_public_tags import public_tags" in source,filename
        assert re.search(r'["\']tags["\']\s*:\s*public_tags\(',source),filename

def test_public_tags_do_not_remove_valuable_seo_words():
    tags=[
      "Hélio Conde","Minecraft","Minecraft Brasil","Minecraft nostalgia",
      "Minecraft sobrevivência","autoeditorvideo-id-game-002-first-night",
      "autoeditorvideo-gamer-v4-reupload-once-20261105",
      "creeper","primeira noite Minecraft",
      "IA generativa","você lembra?"
    ]
    cleaned=public_tags(tags)
    assert len(cleaned)==len(tags)-2
    assert cleaned[0:5]==tags[0:5]
    assert "creeper" in cleaned
    assert "IA generativa" in cleaned
    assert "autoeditorvideo" not in ",".join(cleaned).lower()

def test_no_autoeditorvideo_control_labels_in_end_user_tags():
    for filename in ALL_UPLOAD_ENTRYPOINTS:
        source=(R/"scripts"/filename).read_text(encoding="utf-8")
        # Existing control-token literals can still support read-only legacy
        # reconciliation, but must not be included in videos.insert snippet.
        assert not re.search(r'["\']tags["\']\s*:\s*(?:list\(dict\.fromkeys\()?meta\["tags"\]\s*\+\s*\[TAG',source),filename
