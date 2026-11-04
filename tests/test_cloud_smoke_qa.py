"""Offline unit tests for synthetic Remotion cloud render QA."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cloud_smoke_qa import validate


def fixture_info():
    return {"streams":[{"codec_type":"video","width":480,"height":854,
                        "codec_name":"h264","r_frame_rate":"24/1"}],
            "format":{"duration":"1.5"}}


def test_valid_smoke_metadata():
    validate(fixture_info())


@pytest.mark.parametrize("key,value",[
    ("width",1080),("codec_name","vp8"),("r_frame_rate","30/1"),
])
def test_mismatch_fails(key,value):
    info=fixture_info()
    info["streams"][0][key]=value
    with pytest.raises(ValueError):
        validate(info)


def test_long_duration_fails():
    info=fixture_info()
    info["format"]["duration"]="61.0"
    with pytest.raises(ValueError,match="duration"):
        validate(info)
