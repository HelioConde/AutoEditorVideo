#!/usr/bin/env python3
"""No-network regression tests for Google 308 upload and Kids upload idempotency."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from kids_static_90s_upload_20261107 import (
    CHANNEL_ID, KidsUploadBlocked, configure_resumable_transport,
    find_owned_uploads,
)

TITLE = "O Elefantinho e a Água Escondida 🐘💧 | História Infantil"
DESC = "história de teste, somente simulada"

class Request:
    def __init__(self, value):
        self.value = value
    def execute(self):
        return self.value

class Channels:
    def list(self, **kwargs):
        assert kwargs["mine"] is True
        return Request({"items": [{
            "id": CHANNEL_ID,
            "contentDetails": {"relatedPlaylists": {"uploads": "OWN_UPLOADED_VIDEOS"}}
        }]})

class Playlists:
    def __init__(self, videos):
        self.videos = videos
    def list(self, **kwargs):
        assert kwargs["playlistId"] == "OWN_UPLOADED_VIDEOS"
        return Request({"items": [
            {"contentDetails": {"videoId": v["id"]}} for v in self.videos
        ]})

class Videos:
    def __init__(self, videos):
        self.videos = videos
    def list(self, **kwargs):
        ids = kwargs["id"].split(",")
        return Request({"items": [v for v in self.videos if v["id"] in ids]})

class Service:
    def __init__(self, videos):
        self.data = videos
    def channels(self):
        return Channels()
    def playlistItems(self):
        return Playlists(self.data)
    def videos(self):
        return Videos(self.data)

def item():
    return {"metadata": {"title": TITLE, "description": DESC}}

def media(video_id="n3test_____"):
    return {"id": video_id,
            "snippet": {"title": TITLE, "description": DESC,
                        "channelId": CHANNEL_ID},
            "status": {"privacyStatus": "private",
                       "madeForKids": True}}

class KidsUploadRecoveryTests(unittest.TestCase):
    def test_disable_only_308_redirect_following(self):
        fake = SimpleNamespace(redirect_codes={301, 302, 303, 307, 308})
        configured = configure_resumable_transport(fake)
        self.assertEqual(configured.redirect_codes, {301, 302, 303, 307})

    def test_missing_transport_policy_fails_closed(self):
        with self.assertRaisesRegex(KidsUploadBlocked, "308_POLICY_UNAVAILABLE"):
            configure_resumable_transport(SimpleNamespace())

    def test_no_existing_private_upload(self):
        self.assertEqual(find_owned_uploads(Service([]), item()), [])

    def test_recovers_exact_one_original_private_kids_video(self):
        self.assertEqual(find_owned_uploads(Service([media()]), item()),
                         ["n3test_____"])

    def test_wrong_description_is_ambiguous(self):
        altered = media()
        altered["snippet"]["description"] = "other author unrelated content"
        with self.assertRaisesRegex(KidsUploadBlocked, "EXISTING_TITLE_AMBIGUOUS"):
            find_owned_uploads(Service([altered]), item())

    def test_wrong_privacy_is_ambiguous(self):
        altered = media()
        altered["status"]["privacyStatus"] = "public"
        with self.assertRaisesRegex(KidsUploadBlocked, "EXISTING_TITLE_AMBIGUOUS"):
            find_owned_uploads(Service([altered]), item())

    def test_wrong_kids_audience_flag_is_ambiguous(self):
        altered = media()
        altered["status"]["madeForKids"] = False
        with self.assertRaisesRegex(KidsUploadBlocked, "EXISTING_TITLE_AMBIGUOUS"):
            find_owned_uploads(Service([altered]), item())

    def test_two_matching_uploads_stop_instead_of_third_insert(self):
        with self.assertRaisesRegex(KidsUploadBlocked, "TWO_EXISTING_SAME_KIDS"):
            find_owned_uploads(Service([media("n3test_____"),
                                        media("x8test_____")]), item())

if __name__ == "__main__":
    unittest.main()
