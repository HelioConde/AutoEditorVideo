"""Offline thumbnail contract tests. No YouTube API, generation, OAuth or upload."""
from pathlib import Path
import io
import json
import sys

import pytest
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import youtube_short_thumbnail as thumb
import repair_5011_short_thumbnails as repair
import cloud_youtube_private_5011 as publisher

BR="F8kIJBor9wY"
EN="0urpb0yCcWw"

def cover(tmp_path,w=540,h=960):
    file=tmp_path/'cover.jpg'
    Image.new("RGB",(w,h),"orange").save(file,format='JPEG')
    return file

class MockYT:
    def __init__(self,stage="succeeded",privacy="private"):
        self.stage=stage
        self.privacy=privacy
        self.calls=[]
    def videos(self):
        return self
    def list(self,*,part,id):
        assert part=="processingDetails,status"
        self.calls.append(("list",id))
        self.video_id=id
        return self
    def execute(self):
        if self.calls[-1][0]=="list":
            return {"items":[{"id":self.video_id,"status":{"privacyStatus":self.privacy},
                "processingDetails":{"processingStatus":self.stage}}]}
        return {"items":[{"default":{"url":"https://i.ytimg.com/test.jpg"}}]}
    def thumbnails(self):
        return self
    def set(self,*,videoId,media_body):
        self.calls.append(("set",videoId))
        assert media_body.mimetype()=="image/jpeg"
        return self

def test_valid_9_16_jpeg(tmp_path):
    img=cover(tmp_path)
    assert thumb.validate_cover(img)["height"]==960

def test_reject_landscape_before_google_call(tmp_path):
    yt=MockYT()
    with pytest.raises(thumb.ThumbnailBlocked,match="NOT_VERTICAL"):
        thumb.attach_thumbnail(yt,BR,cover(tmp_path,960,540))
    assert yt.calls==[]

def test_thumbnail_set_exactly_once_only_after_processing(tmp_path):
    yt=MockYT()
    result=thumb.attach_thumbnail(yt,BR,cover(tmp_path))
    assert result['status']=="api_acknowledged"
    assert yt.calls==[('list',BR),('set',BR)]

@pytest.mark.parametrize('stage',["failed","terminated","unexpected"])
def test_never_upload_covers_before_successful_processing(stage,tmp_path):
    yt=MockYT(stage=stage)
    with pytest.raises(thumb.ThumbnailBlocked):
        thumb.attach_thumbnail(yt,BR,cover(tmp_path))
    assert not any(kind=="set" for kind,_ in yt.calls)

def test_processing_pending_does_not_upload(tmp_path):
    yt=MockYT(stage="processing")
    with pytest.raises(thumb.ThumbnailBlocked,match="STILL_PENDING"):
        thumb.attach_thumbnail(yt,BR,cover(tmp_path),
            waiter=lambda video,id: thumb.wait_for_processing(video,id,attempts=2,delay=0,sleeper=lambda _:None))
    assert yt.calls==[('list',BR),('list',BR)]

def test_refuse_if_private_changed(tmp_path):
    yt=MockYT(privacy="public")
    with pytest.raises(thumb.ThumbnailBlocked,match="PRIVACY_CHANGED"):
        thumb.attach_thumbnail(yt,BR,cover(tmp_path))
    assert yt.calls==[('list',BR)]

def env(channel):
    return {"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_RUN_ATTEMPT":"1",
            "REPAIR_ONLY_5011":"true",
            "YOUTUBE_CLIENT_JSON":"fictional",
            f"YOUTUBE_{channel.upper()}_TOKEN_JSON":"fictional"}

@pytest.mark.parametrize('channel',["br","en"])
def test_fixed_channel_identity_and_guard(channel):
    repair.preflight(env(channel),channel)

@pytest.mark.parametrize('mods,reason',[
    ({"GITHUB_REF":"refs/heads/feature"},"MAIN_ONLY"),
    ({"GITHUB_EVENT_NAME":"workflow_dispatch"},"ONE_SHOT_MERGE_ONLY"),
    ({"GITHUB_RUN_ATTEMPT":"2"},"NO_RETRY_WITHOUT_APPROVAL"),
    ({"REPAIR_ONLY_5011":"false"},"EXPLICIT_REPAIR_GATE_REQUIRED"),
    ({"YOUTUBE_BR_TOKEN_JSON":""},"SEPARATE_YOUTUBE_OAUTH_SECRET_MISSING"),
])
def test_unauthorized_cloud_repairs_never_touch_youtube(mods,reason):
    with pytest.raises(repair.RepairBlocked,match=reason):
        repair.preflight(env("br")|mods,"br")

def test_current_video_ids_are_unique_and_existing():
    assert BR==repair.CHANNEL_VIDEO_ID["br"]
    assert EN==repair.CHANNEL_VIDEO_ID["en"]
    assert BR!=EN
    assert repair.ID=="5011-gachiakuta"

def test_original_cloud_upload_preserves_receipt_before_thumbnail():
    text=(Path(__file__).resolve().parents[1]/'scripts'/'cloud_youtube_private_5011.py').read_text()
    first=text.index("record=publish_one(os.environ,args.channel)")
    written=text.index("file.write_text(json.dumps(record",first)
    thumb_step=text.index("attach_thumbnail(youtube",first)
    assert first<written<thumb_step
    assert "MP4_ALREADY_UPLOADED_DO_NOT_REUPLOAD" in text

def test_repair_only_has_no_video_upload_code():
    code=(Path(__file__).resolve().parents[1]/'scripts'/'repair_5011_short_thumbnails.py').read_text()
    assert "videos().insert(" not in code
    assert "videos().update(" not in code
    assert "youtube.upload" not in code
    assert "thumbnails" in code
