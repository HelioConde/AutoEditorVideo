"""Pure fake YouTube tests: never initiate upload or use real OAuth."""
from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

from publicar_arquivo_otaku import wait_for_thumbnail_processing


@pytest.fixture
def fake_google_errors(monkeypatch):
    pkg=types.ModuleType('googleapiclient')
    errors=types.ModuleType('googleapiclient.errors')
    class FakeHttpError(Exception):
        pass
    errors.HttpError=FakeHttpError
    monkeypatch.setitem(sys.modules,'googleapiclient',pkg)
    monkeypatch.setitem(sys.modules,'googleapiclient.errors',errors)
    return FakeHttpError


class FakeYouTube:
    def __init__(self,states):
        self.states=list(states)
        self.calls=0
    def videos(self):
        return self
    def list(self,*,part,id):
        assert part=='processingDetails'
        assert id=='abc123def45'
        return self
    def execute(self):
        index=min(self.calls,len(self.states)-1)
        status=self.states[index]
        self.calls+=1
        if isinstance(status,Exception):
            raise status
        return {'items':[{'processingDetails':{'processingStatus':status}}]}


def test_thumbnail_waits_for_processing_success(fake_google_errors):
    api=FakeYouTube(['processing','processing','succeeded'])
    delays=[]
    status=wait_for_thumbnail_processing(api,'abc123def45',
                                         attempts=5,delay=.01,
                                         sleeper=lambda n:delays.append(n))
    assert status=='succeeded'
    assert api.calls==3
    assert delays==[.01,.01]


def test_thumb_does_not_claim_success_when_video_is_still_processing(fake_google_errors):
    api=FakeYouTube(['processing'])
    assert wait_for_thumbnail_processing(api,'abc123def45',attempts=3,
                                         delay=0,sleeper=lambda _:None)=='pending'
    assert api.calls==3


def test_thumb_never_uploads_on_failure_or_forbidden(fake_google_errors):
    api=FakeYouTube(['failed'])
    assert wait_for_thumbnail_processing(api,'abc123def45',attempts=2,
                                         sleeper=lambda _:None)=='failed'
    api=FakeYouTube([fake_google_errors('forbidden')])
    assert wait_for_thumbnail_processing(api,'abc123def45',attempts=2,
                                         sleeper=lambda _:None)=='unknown'
