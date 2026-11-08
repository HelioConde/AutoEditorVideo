"""Kwai Brazil OAuth preparedness: no secrets / no platform assumptions."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kwai_github_oauth_readiness as kwai

class KwaiReadinessTests(unittest.TestCase):
    def test_configuration_does_not_claim_kwai_brazil_api_support(self):
        d=kwai.validate_plan()
        self.assertEqual(d["platform"],"kwai_brazil")
        self.assertFalse(d["kwai_brazil_content_publishing_api_verified"])
        self.assertFalse(d["kwai_brazil_app_approval_received"])
        self.assertFalse(d["oauth_authorization_completed"])
        self.assertFalse(d["publication_enabled"])
        self.assertTrue(d["never_touch_youtube_secrets"])
        self.assertEqual(d["planned_secret_names"],list(kwai.SECRET_NAMES))

    def test_guard_blocks_fake_ready_for_publishing_state(self):
        with patch.object(kwai.PATH.__class__,"read_text",
                          return_value=json.dumps({
                              **kwai.validate_plan(),"publication_enabled":True
                          })):
            with self.assertRaises(kwai.KwaiReadinessBlocked):
                kwai.validate_plan()

    def test_environment_requires_only_main_branch(self):
        env={"name":"kwai-private-publish",
             "deployment_branch_policy":{
                "custom_branch_policies":True,"protected_branches":False}}
        good={"total_count":1,"branch_policies":[
            {"name":"main","type":"branch"}]}
        kwai.protected_main_only(env,good)
        with self.assertRaises(kwai.KwaiReadinessBlocked):
            kwai.protected_main_only(env,{
                "total_count":2,
                "branch_policies":[{"name":"main","type":"branch"},
                                   {"name":"staging","type":"branch"}]})

    def test_environment_not_allowed_without_explicit_branch_policies(self):
        with self.assertRaises(kwai.KwaiReadinessBlocked):
            kwai.protected_main_only({
                "name":"kwai-private-publish",
                "deployment_branch_policy":{
                    "custom_branch_policies":False,"protected_branches":True}
            },{"total_count":1,"branch_policies":[
                {"name":"main","type":"branch"}]})

    def test_no_token_upload_or_android_login_in_readiness_code(self):
        s=(ROOT/"scripts"/"kwai_github_oauth_readiness.py").read_text(encoding="utf-8")
        for token in ("videos().insert(", "requests.post(", "gh secret set",
                      "adb shell input","webbrowser.open(", "app_secret="):
            self.assertNotIn(token,s)
        self.assertIn("OFFICIAL_BRAZIL_API_CREDENTIAL_APPROVAL_REQUIRED",s)

if __name__=="__main__":
    unittest.main()
