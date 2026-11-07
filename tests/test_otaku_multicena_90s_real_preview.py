"""Guard one real GitHub 90s media preview from touching the public 50-Short queue.

All tests are OFFLINE. No Edge TTS, image-provider requests or MP4 produced.
"""
from pathlib import Path
import importlib
import json
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
preview=importlib.import_module("otaku_multicena_90s_real_preview")

def test_preview_environment_requires_specific_workflow_and_keeps_pause():
    env={
      "OTAKU_SINGLE_REVIEW_AUTHORIZED":"1",
      "GITHUB_RUN_ATTEMPT":"1",
      "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
      "GITHUB_REF":"refs/heads/main",
      "GITHUB_EVENT_NAME":"push",
      "GITHUB_WORKFLOW":"Otaku V5 - REAL 90s MP4 review from AutoEditorVideo (no upload)",
      "IMAGE_MODEL":"gpt-image-2","MAX_IMAGE_CALLS":"10",
    }
    row=preview.validate_environment(env)
    assert row["rank"]==1 and row["anime"]=="Death Note"
    assert row["ending_policy"]=="answer_only_no_cta"
    for k,v in [("OTAKU_SINGLE_REVIEW_AUTHORIZED","0"),
                ("GITHUB_RUN_ATTEMPT","2"),("GITHUB_REF","refs/heads/dev"),
                ("GITHUB_EVENT_NAME","workflow_dispatch"),("MAX_IMAGE_CALLS","11"),
                ("GITHUB_WORKFLOW","Otaku Multicena BR - 50 Shorts SERIAIS publicos (um por vez)")]:
        changed={**env,k:v}
        with pytest.raises(preview.PreviewBlocked):
            preview.validate_environment(changed)
    with pytest.raises(preview.PreviewBlocked,match="YOUTUBE_CREDENTIALS_NOT_PERMITTED"):
        preview.validate_environment({**env,"YOUTUBE_BR_TOKEN_JSON":"secret-placeholder"})

def test_real_tts_words_define_ten_nonoverlapping_scenes(tmp_path):
    row=preview.load(preview.PLAN)["items"][0]
    total=sum(len(preview._spoken_words(p["text"]).split()) for p in row["story_segments"])
    folder=tmp_path/"take1";folder.mkdir()
    words=[{"start":i*90/total,"end":(i+1)*90/total,"text":"word"}
           for i in range(total)]
    (folder/"marcacoes-voz.json").write_text(json.dumps({"words":words}),encoding="utf-8")
    audio=folder/"voz-master.mp3";audio.write_bytes(b"test not actual media")
    cuts=preview.build_cuts(row,audio,90*30)
    assert len(cuts)==11
    assert cuts[0]==0 and cuts[-1]==2700
    assert len(set(cuts))==11
    assert all(40<=b-a<=420 for a,b in zip(cuts,cuts[1:]))

def test_provider_budget_and_no_fake_artwork_fallback():
    src=(ROOT/"scripts/otaku_multicena_90s_real_preview.py").read_text(encoding="utf-8")
    assert preview.MODEL=="gpt-image-2"
    assert preview.SCENE_COUNT==preview.IMAGE_CALL_LIMIT==10
    assert "request_image(make_prompt(row,i),MODEL,key" in src
    assert "ensure_voice(" in src
    assert "captions_from_markers(" in src
    assert '"render:master"' in src
    assert 'inspect_mp4(mp4,duration_profile="short_90s_test")' in src
    assert "youtube.videos().insert" not in src
    assert "--publicar" not in src
    assert '"otaku-real-90s-review"' not in src  # artifact path is named clearly
    assert "no_fake_art_or_voice_fallback" in src

def test_control_flags_are_unchanged():
    control=preview.load(preview.PAUSE)
    assert control["pause_requested"] is True
    assert control["authorized_public"] is False
    assert control["maintenance_complete"] is False
    assert control["resume_authorized_after_maintenance"] is False
