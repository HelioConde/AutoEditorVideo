"""GitHub channel registration safety tests; no network, OAuth or upload."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import youtube_channel_registry as registry

def test_registry_all_five_ids_are_unique_and_exact():
    data=registry.load_registry()
    assert set(data["channels"])=={"br","en","games","kids","alchemy"}
    for slug,cid in registry.KNOWN_IDS.items():
        assert registry.get_channel(slug,registry=data)["youtube_channel_id"]==cid
    assert len(set(row["youtube_channel_id"] for row in data["channels"].values()))==5

def test_new_three_names_and_observed_youtube_titles_not_confused():
    data=registry.load_registry()["channels"]
    assert data["games"]["name"]=="Conde Games"
    assert data["games"]["observed_youtube_title"]=="Hélio Conde"
    assert data["games"]["brand_status"]=="proposed_not_renamed_on_youtube"
    assert data["kids"]["name"]=="Emanuelly Kids"
    assert data["kids"]["series"]=="Fofinhos"
    assert data["alchemy"]["name"]=="Alchemy Lab"
    assert data["alchemy"]["observed_youtube_title"]=="Alchemy Flames"
    assert data["alchemy"]["brand_status"]=="planned_rename_not_applied"

def test_kids_coppa_and_content_separation():
    cfg=registry.load_registry()["channels"]
    assert cfg["kids"]["made_for_kids_default"] is True
    assert cfg["kids"]["comments_policy"]=="disabled_by_YouTube_for_made_for_kids"
    assert cfg["kids"]["upload_safety"]["auto_publication"] is False
    for ch in ("games","alchemy","br","en"):
        assert cfg[ch]["made_for_kids_default"] is False
    assert cfg["games"]["youtube_category_id"]=="20"
    assert cfg["kids"]["youtube_category_id"]=="1"
    assert cfg["alchemy"]["youtube_category_id"]=="28"

@pytest.mark.parametrize("slug",list(registry.NEW_CHANNELS))
def test_registered_does_not_allow_upload(slug):
    with pytest.raises(registry.ChannelRegistryError,match="UPLOAD_NOT_AUTHORIZED"):
        registry.assert_upload_authorized(slug)

def test_single_shared_environment_and_five_distinct_token_secrets():
    config=registry.load_registry()
    data=config["channels"]
    assert config["policy"]["shared_youtube_environment"]=="youtube-private-upload"
    assert set(row["youtube_environment"] for row in data.values())=={"youtube-private-upload"}
    names={slug:row["oauth_token_secret_name"] for slug,row in data.items()}
    assert names=={
        "br":"YOUTUBE_BR_TOKEN_JSON",
        "en":"YOUTUBE_EN_TOKEN_JSON",
        "games":"YOUTUBE_GAMES_TOKEN_JSON",
        "kids":"YOUTUBE_KIDS_TOKEN_JSON",
        "alchemy":"YOUTUBE_ALCHEMY_TOKEN_JSON",
    }
    assert len(set(names.values()))==5
    for slug in registry.NEW_CHANNELS:
        assert data[slug]["cloud_upload_state"].startswith("blocked_until")
        assert data[slug]["visibility_default"]=="private"

def test_reject_channel_mapped_outside_existing_shared_environment(tmp_path):
    config=registry.load_registry()
    config["channels"]["games"]["youtube_environment"]="youtube-games-private-upload"
    file=tmp_path/"wrong-env.json"
    file.write_text(json.dumps(config),encoding="utf-8")
    with pytest.raises(registry.ChannelRegistryError,match="SHARED_YOUTUBE_ENVIRONMENT_REQUIRED"):
        registry.load_registry(file)

def test_otaku_existing_channels_unmodified_and_operational():
    data=registry.load_registry()["channels"]
    for slug in ("br","en"):
        assert registry.assert_upload_authorized(slug)["youtube_channel_id"]==data[slug]["youtube_channel_id"]
    old=json.loads((ROOT/"config"/"youtube-upload-profiles.json").read_text(encoding="utf-8"))
    for slug in ("br","en"):
        assert old[slug]["youtube_channel_id"]==data[slug]["youtube_channel_id"]
        assert old[slug]["privacy_default"]=="private"

def test_cross_channel_destination_rejected():
    with pytest.raises(registry.ChannelRegistryError,match="WRONG_DESTINATION"):
        registry.assert_correct_destination("kids",registry.KNOWN_IDS["games"])
    assert registry.assert_correct_destination("alchemy",registry.KNOWN_IDS["alchemy"])["name"]=="Alchemy Lab"

@pytest.mark.parametrize("slug",list(registry.NEW_CHANNELS))
def test_production_pilot_must_not_start_upload_automatically(slug):
    row=registry.get_channel(slug)
    assert row["upload_safety"]["auto_publication"] is False
    assert row["thumbnail_policy"]["never_reuse_other_channel_cover"] is True

def test_reject_swapped_ids_even_if_youtube_id_is_valid(tmp_path):
    data=registry.load_registry()
    changed=copy.deepcopy(data)
    changed["channels"]["games"]["youtube_channel_id"]=registry.KNOWN_IDS["kids"]
    path=tmp_path/"wrong.json"
    path.write_text(json.dumps(changed),encoding="utf-8")
    with pytest.raises(registry.ChannelRegistryError,match="CHANNEL_ID_MISMATCH"):
        registry.load_registry(path)

def test_reject_unsafe_kids_or_shared_token(tmp_path):
    data=registry.load_registry()
    data["channels"]["kids"]["made_for_kids_default"]=False
    p=tmp_path/"bad.json";p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(registry.ChannelRegistryError,match="KIDS_AUDIENCE_FLAG"):
        registry.load_registry(p)
    data["channels"]["kids"]["made_for_kids_default"]=True
    data["channels"]["kids"]["oauth_token_secret_name"]=data["channels"]["games"]["oauth_token_secret_name"]
    p.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(registry.ChannelRegistryError,match="OAUTH_SECRET_NAME_SHARED"):
        registry.load_registry(p)

def test_no_new_channel_auto_upload_routes_or_secrets_in_repository():
    text=(ROOT/"scripts"/"youtube_channel_registry.py").read_text(encoding="utf-8")
    assert "videos().insert(" not in text
    assert "secrets.YOUTUBE_" not in text
    assert "PROXY_ACCOUNTS_JSON" not in text

def test_pilot_remains_nonpublishing_until_brand_and_content_review():
    """Older 3x2 pilot has its OWN provisional editorial names and is sandbox only."""
    pilot=json.loads((ROOT/"conteudos"/"piloto-games-kids-3x2-v3.json").read_text(encoding="utf-8"))
    assert pilot["upload_enabled"] is False
    assert pilot["no_automatic_publication"] is True
    for item in pilot["channels"]:
        assert item["youtube_channel_id"] is None
    # Channel IDs are registered centrally but intentionally are not copied
    # into provisional pilot episode upload tickets.


def test_production_reservations_are_channel_scoped_and_new_channels_have_no_scripts():
    import production_reservations as queue
    data=queue.load()
    assert set(data["channels"])==set(registry.KNOWN_IDS)
    for slug in registry.NEW_CHANNELS:
        assert data["channels"][slug]["youtube_channel_id"]==registry.KNOWN_IDS[slug]
        assert data["channels"][slug]["upload_authorized"] is False
        assert not any(item["channel"]==slug for item in data["entries"])
    with pytest.raises(ValueError,match="NOT_RESERVED_IN_GITHUB"):
        queue.assert_reserved("games","game-001-minecraft-um-coracao","any_worker")
    with pytest.raises(ValueError,match="NOT_RESERVED_IN_GITHUB"):
        queue.assert_reserved("kids","kids-001-estrela-azul","any_worker")
    with pytest.raises(ValueError,match="NOT_RESERVED_IN_GITHUB"):
        queue.assert_reserved("alchemy","alchemy-001-introducao-ia","any_worker")
    # Existing Otaku entries remain intact, only their channel is allowed.
    assert queue.get_entry("br","5008-firefly-wedding",data)["status"]=="published"
    assert queue.get_entry("en","5008-firefly-wedding",data) is None

def test_new_channels_cannot_infer_next_episode_or_trigger_batch():
    import production_reservations as queue
    for slug in registry.NEW_CHANNELS:
        with pytest.raises(ValueError,match="EXPLICIT_EDITORIAL_SELECTION"):
            queue.next_available(slug)
