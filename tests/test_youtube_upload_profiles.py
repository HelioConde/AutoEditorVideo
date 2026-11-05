"""Offline-only tests for BR/EN YouTube upload defaults and TRUE generated covers."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from youtube_upload_profiles import build_insert_body,load_profiles,UploadProfileError
from youtube_short_thumbnail import verified_generated_cover,ThumbnailBlocked
import cloud_youtube_private_5011 as cloud

def test_profiles_are_separate_and_never_auto_publish():
    cfg=load_profiles()
    assert cfg["br"]["youtube_channel_id"]==cloud.EXPECTED["br"][0]
    assert cfg["en"]["youtube_channel_id"]==cloud.EXPECTED["en"][0]
    assert cfg["br"]["privacy_default"]=="private"
    assert cfg["en"]["privacy_default"]=="private"
    assert cfg["br"]["commentary_moderation_studio"]=="none"
    assert cfg["en"]["commentary_moderation_studio"]=="basic"
    for ch in ("br","en"):
        assert cfg[ch]["category_id"]=="1"
        assert cfg[ch]["license"]=="youtube"
        assert cfg[ch]["embeddable"] is True
        assert cfg[ch]["self_declared_made_for_kids"] is False

def test_br_title_hashtags_and_episode_specific_metadata():
    m={"title":"Light caçou Kira SEM SABER que era ele mesmo! 🤯 #Shorts",
       "description":"No arco Yotsuba, Light perdeu as memórias.\n\nNo arco Yotsuba, Light perdeu as memórias.",
       "tags":["Death Note","Kira","free movie","Anime Brasil","Otaku Multicena"],
       "channel_id":cloud.EXPECTED["br"][0],
       "spoilers":True}
    p=build_insert_body("br",m)
    assert p["snippet"]["title"]==m["title"]
    assert p["snippet"]["defaultLanguage"]=="pt-BR"
    assert p["snippet"]["categoryId"]=="1"
    assert "Light" in p["snippet"]["description"]
    assert p["snippet"]["description"].count("No arco Yotsuba")==1
    assert "#OtakuMulticena" in p["snippet"]["description"]
    assert "⚠️ Contém spoilers" in p["snippet"]["description"]
    assert "free movie" not in p["snippet"]["tags"]
    assert p["status"]=={"privacyStatus":"private","selfDeclaredMadeForKids":False,
                          "license":"youtube","embeddable":True,"publicStatsViewable":True}

def test_en_language_and_identity_never_copy_br():
    p=build_insert_body("en",{
        "titulo":"Who played the better game? L or Light? #Shorts",
        "descricao":"An in-depth analysis of the mind games between Light and L.",
        "tags":["Death Note","Anime Analysis","movies english","L Lawliet"],
        "channel_id":cloud.EXPECTED["en"][0]
    })
    assert p["snippet"]["defaultLanguage"]=="en-US"
    assert "Subscribe" in p["snippet"]["description"]
    assert "#OtakuReframe" in p["snippet"]["description"]
    assert "Otaku Multicena" not in p["snippet"]["description"]
    assert "movies english" not in p["snippet"]["tags"]
    assert p["status"]["privacyStatus"]=="private"

def test_requires_explicit_boolean_for_realistic_synthetic_media():
    base={"title":"Short Title","description":"An independently narrated anime analysis.","tags":[]}
    assert "containsSyntheticMedia" not in build_insert_body("en",base)["status"]
    base["containsSyntheticMedia"]=True
    assert build_insert_body("en",base)["status"]["containsSyntheticMedia"] is True
    base["containsSyntheticMedia"]="yes"
    with pytest.raises(UploadProfileError,match="EXPLICIT_BOOLEAN"):
        build_insert_body("en",base)

@pytest.mark.parametrize("channel",["br","en"])
def test_forbid_cross_channel_metadata(channel):
    other="en" if channel=="br" else "br"
    with pytest.raises(UploadProfileError,match="CHANNEL_ID_DIFFERENT"):
        build_insert_body(channel,{"title":"X","description":"Y"*40,"tags":[],
            "channel_id":cloud.EXPECTED[other][0]})

def test_tags_with_long_spam_are_dropped():
    m={"title":"Title","description":"A short video about Gachiakuta.",
       "tags":["Gachiakuta"]*9+["x"*130]+["a"*80]*10+["free movies"]}
    p=build_insert_body("br",m)
    tags=p["snippet"]["tags"]
    assert len(tags)==len(set(tags))
    assert len(",".join(tags))<=500
    assert "free movies" not in tags

def make_cover(tmp_path,channel="br"):
    name=f"{channel}-5011-gachiakuta-cover.jpg"
    path=tmp_path/name
    Image.new("RGB",(540,960),(22,66,111)).save(path,format="JPEG")
    return path

def signed_summary(tmp_path, channel="br",schema="v2",original=True):
    image=make_cover(tmp_path,channel)
    digest=hashlib.sha256(image.read_bytes()).hexdigest()
    item={"channel":channel,"cover":image.name}
    if schema=="v2":
        item["cover_sha256"]=digest
    summary={"schema":f"autoeditorvideo/dual-cloud-review/{schema}",
             "episode":"5011-gachiakuta",
             "render_origin":"original AutoEditorVideo Remotion in GitHub Actions" if original else "external-video",
             "videos":[item,{"channel":"en" if channel=="br" else "br"}]}
    return image,digest,summary

def test_uses_exact_original_generated_cover_and_signed_sha(tmp_path):
    image,digest,summary=signed_summary(tmp_path,"en")
    result,actual=verified_generated_cover(tmp_path,summary,"en","5011-gachiakuta")
    assert result==image and actual==digest

def test_reject_missing_or_wrong_channel_cover(tmp_path):
    image,digest,summary=signed_summary(tmp_path,"br")
    with pytest.raises(ThumbnailBlocked,match="WRONG_CHANNEL"):
        verified_generated_cover(tmp_path,summary,"en","5011-gachiakuta")
    image.unlink()
    with pytest.raises(ThumbnailBlocked,match="THUMBNAIL_FILE_MISSING"):
        verified_generated_cover(tmp_path,summary,"br","5011-gachiakuta")

def test_reject_changed_cover_not_generated(tmp_path):
    image,digest,summary=signed_summary(tmp_path)
    Image.new("RGB",(540,960),(240,5,10)).save(image,format="JPEG")
    with pytest.raises(ThumbnailBlocked,match="SHA256_MISMATCH"):
        verified_generated_cover(tmp_path,summary,"br","5011-gachiakuta")

def test_reject_external_render_thumbnail(tmp_path):
    image,digest,summary=signed_summary(tmp_path,original=False)
    with pytest.raises(ThumbnailBlocked,match="NOT_AN_AUTOEDITORVIDEO"):
        verified_generated_cover(tmp_path,summary,"br","5011-gachiakuta")

def test_fail_if_future_v2_manifest_missing_cover_digest(tmp_path):
    image,digest,summary=signed_summary(tmp_path,"br")
    summary["videos"][0].pop("cover_sha256")
    with pytest.raises(ThumbnailBlocked,match="COVER_DIGEST_NOT_RECORDED"):
        verified_generated_cover(tmp_path,summary,"br","5011-gachiakuta")

def test_previous_immutable_5011_v1_artifact_compatibility_only(tmp_path):
    image,digest,summary=signed_summary(tmp_path,"br",schema="v1")
    assert verified_generated_cover(tmp_path,summary,"br","5011-gachiakuta")== (image,digest)
    summary["episode"]="5012-solo-leveling"
    summary["videos"][0]["cover"]="br-5012-solo-leveling-cover.jpg"
    image.rename(tmp_path/"br-5012-solo-leveling-cover.jpg")
    with pytest.raises(ThumbnailBlocked,match="COVER_DIGEST_NOT_RECORDED"):
        verified_generated_cover(tmp_path,summary,"br","5012-solo-leveling")

def test_cloud_uploader_has_no_random_screenshot_or_thumbnail_fallback():
    uploader=(ROOT/"scripts"/"cloud_youtube_private_5011.py").read_text()
    assert "verified_generated_cover" in uploader
    assert "build_insert_body" in uploader
    assert "attach_thumbnail" in uploader
    assert "screenshot(" not in uploader
    assert "youtube.thumbnails().set" not in uploader
