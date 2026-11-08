"""Offline regression tests for future Instagram Reels on AutoEditorVideo."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import instagram_api_readiness as ig

class InstagramReadinessTests(unittest.TestCase):
    def test_channel_profiles_are_known_and_all_unconnected(self):
        config=ig.get_config()
        self.assertEqual(tuple(config["account_routes"]),ig.PROFILE_KEYS)
        self.assertTrue(all(v is None for v in config["account_routes"].values()))
        self.assertEqual(ig.inspect()["connected_channels"],[])

    def test_meta_instagram_login_permissions_are_not_facebook_permissions(self):
        conf=ig.get_config()
        self.assertEqual(conf["authentication"],"instagram_login")
        self.assertEqual(conf["required_permissions"],[
            "instagram_business_basic","instagram_business_content_publish"])
        self.assertTrue(conf["no_facebook_page_required_for_instagram_login"])

    def test_all_real_actions_disabled_until_meta_authorization(self):
        c=ig.get_config()
        for key in ("oauth_connected","meta_app_created",
                    "hosting_public_https_configured","reels_publication_enabled",
                    "real_upload_enabled","auto_publish_enabled",
                    "secret_transfer_enabled","github_environment_created"):
            self.assertFalse(c[key],key)

    def test_public_https_media_url_without_credentials(self):
        self.assertEqual(ig.media_https_url("https://cdn.example.org/reels/demo.mp4"),
                         "https://cdn.example.org/reels/demo.mp4")

    def test_reject_unsafe_media_urls(self):
        invalid=(
            "http://cdn.example.org/reel.mp4",
            "https://localhost/foo.mp4",
            "https://127.0.0.1/foo.mp4",
            "https://192.168.1.10/foo.mp4",
            "https://cdn.example.org/foo.txt",
            "file:///tmp/foo.mp4",
            "https://u:p@cdn.example.org/foo.mp4",
            "https://cdn.example.org:8080/foo.mp4",
            "https://cdn.example.org/foo.mp4#auth",
            "https://media.example.test/foo.mp4",
            "https://cdn.example.org/foo.mp4\nTOKEN"
        )
        for url in invalid:
            with self.subTest(url=url):
                with self.assertRaises(ig.InstagramBlocked):
                    ig.media_https_url(url)

    def test_no_channel_can_be_published_until_id_is_verified(self):
        with self.assertRaisesRegex(ig.InstagramBlocked,"NOT_VERIFIED"):
            ig.plan_reel("br","17841409999999999",
                         "https://cdn.example.org/reel.mp4","Teste")
        with self.assertRaisesRegex(ig.InstagramBlocked,"CHANNEL_UNKNOWN"):
            ig.plan_reel("not-a-channel","17841409999999999",
                         "https://cdn.example.org/reel.mp4","Teste")
        with self.assertRaisesRegex(ig.InstagramBlocked,"USER_ID"):
            ig.plan_reel("br","@fake_profile",
                         "https://cdn.example.org/reel.mp4","Teste")

    def test_offline_request_sequence_is_correct_when_mapping_is_mocked(self):
        mock_config=ig.get_config()
        mock_config["account_routes"]["br"]="17841409999999999"
        with patch.object(ig,"get_config",return_value=mock_config):
            data=ig.plan_reel("br","17841409999999999",
                              "https://cdn.example.org/reel.mp4","Legenda aprovada")
        self.assertFalse(data["publish_enabled"])
        self.assertEqual(
            [x["method"] for x in data["api_sequence"]],["POST","GET","POST"])
        self.assertIn("/media_publish",data["api_sequence"][2]["path"])
        self.assertEqual(data["api_sequence"][0]["body"]["media_type"],"REELS")
        self.assertEqual(data["note"],"PLAN_ONLY_NO_HTTP_NO_POSTING_NOT_EXECUTABLE")

    def test_publication_explicitly_blocked_even_when_profile_mapping_is_mocked(self):
        mock_config=ig.get_config()
        mock_config["account_routes"]["br"]="17841409999999999"
        with patch.object(ig,"get_config",return_value=mock_config):
            with self.assertRaisesRegex(ig.InstagramBlocked,"SEPARATE_AUTHORIZATION"):
                ig.plan_reel("br","17841409999999999",
                             "https://cdn.example.org/reel.mp4","Teste",publish=True)

    def test_no_live_auth_token_or_http_requests_in_source(self):
        text=(ROOT/"scripts"/"instagram_api_readiness.py").read_text(encoding="utf-8")
        for forbidden in ("requests.post(", "urlopen(", "videos().insert(",
                          "gh secret set", "subprocess.run(", "access_token=",
                          "graph.facebook.com", "open_browser=True"):
            self.assertNotIn(forbidden,text)
        self.assertIn("INSTAGRAM_REAL_PUBLICATION_REQUIRES_SEPARATE_AUTHORIZATION",text)

    def test_github_environment_requires_main_only(self):
        env={"name":"instagram-private-publish","deployment_branch_policy":{
            "custom_branch_policies":True,"protected_branches":False}}
        policy={"total_count":1,"branch_policies":[{"name":"main","type":"branch"}]}
        ig.github_environment_main_only(env,policy)
        with self.assertRaises(ig.InstagramBlocked):
            ig.github_environment_main_only(env,{
                "total_count":2,
                "branch_policies":[
                    {"name":"main","type":"branch"},{"name":"staging","type":"branch"}]})
        with self.assertRaises(ig.InstagramBlocked):
            ig.github_environment_main_only(
                {"name":"instagram-private-publish",
                 "deployment_branch_policy":{
                     "custom_branch_policies":False,"protected_branches":True}},
                policy)

    def test_tampered_policy_is_fail_closed(self):
        data=ig.get_config()
        data["auto_publish_enabled"]=True
        with patch.object(ig.CONFIG.__class__,"read_text",return_value=json.dumps(data)):
            with self.assertRaises(ig.InstagramBlocked):
                ig.get_config()

if __name__=="__main__":
    unittest.main()
