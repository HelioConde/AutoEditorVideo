"""Prove character-pose frames and 8-12-shot pacing without generating video."""
import copy
from hashlib import sha256
import importlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
quality=importlib.import_module("otaku_multicena_quality_v3")

RIGHTS={"type":"creator_original","evidence":"Original fixture authored entirely in this unit test."}

def make_fixture(tmp_path: Path, count: int = 10, animated: bool = True):
    work=tmp_path/"assets"
    work.mkdir()
    caption_words=[]
    shot_words=[]
    for i in range(count):
        shot_words.append([f"cena{i}","historia","revela","misterio","agora","hoje"])
    script=" ".join(" ".join(x) for x in shot_words)
    for i,w in enumerate(script.split()):
        frame=i*19
        caption_words.append({"startFrame":frame,"endFrame":frame+15,"text":w})
    captions=[{"startFrame":w["startFrame"],"endFrame":w["endFrame"],
               "text":w["text"],"words":[w]} for w in caption_words]
    (work/"markers.json").write_text(json.dumps(captions),encoding="utf-8")
    (work/"voz-master.mp3").write_bytes(b"fake voice technical fixture "*20)
    doc={"schema":"autoeditorvideo/quality-preview/v3",
         "episode_id":"episode-original-quality-v3", "manual_visual_review":False,
         "duration_frames":1200,"voice":"voz-master.mp3",
         "voice_rights":RIGHTS,
         "narration_script":script,"hook_text":"cena0 historia",
         "payoff_text":f"cena{count-1} historia",
         "shots":[],"sha256":{}}
    for i in range(count):
        fname=f"clean-{i+1:02d}.png"
        Image.new("RGB",(1024,1536),(24+i*15,40,90)).save(work/fname)
        shot={"start_phrase":f"cena{i} historia","background":fname,
              "beat_role":"hook" if i==0 else "answer" if i==count-1 else "detail",
              "shot_type":"medium","rights":RIGHTS}
        if animated and i==2:
            frames=[]
            for j in range(2):
                name=f"pose-{j+1}.png"
                pose=Image.new("RGBA",(1024,1536),(0,0,0,0))
                ImageDraw.Draw(pose).rectangle((200+j*38,260,400+j*38,490),
                                               fill=(210,50,90,255))
                pose.save(work/name)
                frames.append(name)
            shot.update({"pose_frames":frames,"pose_fps":6,
                         "clean_plate_confirmed":True})
        if i==3:
            name="fx-audio.wav"
            (work/name).write_bytes(b"test sfx bytes "*60)
            shot["sound_effects"]=[{"file":name,"offset_seconds":.3,
                   "duration_seconds":.7,"volume":.22,"rights":RIGHTS}]
        doc["shots"].append(shot)
    for path in work.iterdir():
        if path.suffix in (".png",".mp3",".wav"):
            doc["sha256"][path.name]=sha256(path.read_bytes()).hexdigest()
    manifest=work/"quality.json"
    manifest.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
    return manifest, work/"markers.json",doc

def test_quality_mode_builds_ten_shots_and_actually_distinct_pose_frames(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path)
    output=tmp_path/"props.json"
    result=quality.build_preview(manifest,captions,tmp_path/"public",
                                 output_path=output)
    props=result["props"]
    qa=result["qa"]
    assert len(props["scenes"])==10
    assert qa["pose_animated_shots"]==1
    assert qa["static_shots"]==9
    assert qa["sound_effect_count"]==1
    assert props["animationMode"]=="esqueleto2d"
    assert props["scenes"][2]["renderMode"]=="multilayer"
    assert len(props["scenes"][2]["layers"][0]["rigFrames"]["frames"])==2
    assert props["scenes"][0]["startFrame"]==0
    assert props["scenes"][-1]["endFrame"]==1200
    assert all(
        b["startFrame"]>=a["endFrame"] or b["startFrame"]==a["endFrame"]
        for a,b in zip(props["scenes"],props["scenes"][1:])
    )
    assert output.exists()
    assert output.with_name("props-qa.json").exists()
    assert (tmp_path/"public/generated/otaku-quality-v3/episode-original-quality-v3/pose-1.png").exists()
    assert qa["rendered_video"] is False and qa["youtube_upload"] is False
    assert qa["human_visual_review"] is False

def test_no_pose_assets_means_no_faked_character_rig(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path,animated=False)
    result=quality.build_preview(manifest,captions,tmp_path/"public")
    assert result["qa"]["pose_animated_shots"]==0
    assert result["props"]["animationMode"]=="cinematica"
    assert all(s["renderMode"]=="master_static" for s in result["props"]["scenes"])

def test_changed_asset_hash_or_unlicensed_sound_blocks_preview(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path)
    # Source data cannot be silently swapped after the storyboard was reviewed.
    path=manifest.parent/"clean-01.png"
    path.write_bytes(path.read_bytes()+b"tampering")
    with pytest.raises(quality.QualityBlocked,match="ASSET_HASH_CHANGED"):
        quality.build_preview(manifest,captions,tmp_path/"public")
    manifest,captions,doc=make_fixture(tmp_path/"again")
    doc["shots"][3]["sound_effects"][0]["rights"]["type"]="unknown"
    manifest.write_text(json.dumps(doc),encoding="utf-8")
    with pytest.raises(quality.QualityBlocked,match="ASSET_RIGHTS_EVIDENCE_REQUIRED"):
        quality.build_preview(manifest,captions,tmp_path/"public")

def test_no_unrelated_episode_scenes_or_path_traversal(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path)
    doc["shots"][1]["background"]="../other.png"
    manifest.write_text(json.dumps(doc),encoding="utf-8")
    with pytest.raises(quality.QualityBlocked,match="INVALID_ASSET_FILENAME"):
        quality.build_preview(manifest,captions,tmp_path/"public")

def test_requires_eight_to_twelve_distinct_shots(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path)
    doc["shots"]=doc["shots"][:5]
    manifest.write_text(json.dumps(doc),encoding="utf-8")
    with pytest.raises(quality.QualityBlocked,match="REQUIRE_8_TO_12"):
        quality.build_preview(manifest,captions,tmp_path/"public")

def test_hook_and_payoff_must_match_actual_spoken_words(tmp_path):
    manifest,captions,doc=make_fixture(tmp_path)
    doc["payoff_text"]="cena0 historia"
    manifest.write_text(json.dumps(doc),encoding="utf-8")
    with pytest.raises(quality.QualityBlocked,match="PAYOFF_MUST_BE_IN_SECOND_HALF"):
        quality.build_preview(manifest,captions,tmp_path/"public")

def test_quality_module_has_no_youtube_or_image_generation_calls():
    txt=(ROOT/"scripts/otaku_multicena_quality_v3.py").read_text(encoding="utf-8")
    for marker in ("youtube.videos().insert", "request_image(", "gh workflow run",
                   "render:master","ensure_voice("):
        assert marker not in txt
