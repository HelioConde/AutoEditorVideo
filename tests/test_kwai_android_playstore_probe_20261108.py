"""Offline tests: Kwai Brazil Android Play Store only; never install/login/post."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kwai_android_playstore_probe_20261108 as kwai

class KwaiPlayProbeTests(unittest.TestCase):
    def test_official_package_and_policy(self):
        kwai.policy()
        self.assertEqual(kwai.PACKAGE,"com.kwai.video")
        self.assertEqual(kwai.STORE,"com.android.vending")
        self.assertEqual(kwai.MARKET,"market://details?id=com.kwai.video")
        self.assertTrue(kwai.policy()["live_publication_requires_separate_creator_approval"])

    def test_main_branch_exact_authorization_required(self):
        e={"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
           "GITHUB_REF":"refs/heads/develop",
           "GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"1",
           "GITHUB_WORKFLOW":kwai.WORKFLOW,
           "KWAI_READ_ONLY_EMULATOR_TEST":"yes"}
        with patch.dict(os.environ,e,clear=True):
            with self.assertRaises(kwai.KwaiProbeBlocked):
                kwai.guard()

    def test_social_credentials_are_forbidden(self):
        env={"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
             "GITHUB_REF":"refs/heads/main",
             "GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"1",
             "GITHUB_WORKFLOW":kwai.WORKFLOW,
             "KWAI_READ_ONLY_EMULATOR_TEST":"yes",
             "KWAI_ACCESS_TOKEN":"SHOULD_NOT_PASS"}
        with patch.dict(os.environ,env,clear=True):
            with self.assertRaises(kwai.KwaiProbeBlocked):
                kwai.guard()

    def test_clean_authorized_test_allowed(self):
        env={"GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
             "GITHUB_REF":"refs/heads/main",
             "GITHUB_EVENT_NAME":"push","GITHUB_RUN_ATTEMPT":"1",
             "GITHUB_WORKFLOW":kwai.WORKFLOW,
             "KWAI_READ_ONLY_EMULATOR_TEST":"yes"}
        with patch.dict(os.environ,env,clear=True):
            kwai.guard()

    def test_no_install_post_or_other_social_networks_in_code(self):
        src=(ROOT/"scripts"/"kwai_android_playstore_probe_20261108.py").read_text()
        for bad in ('"install","-r"', '"adb","install"', "requests.post(",
                    "videos().insert(", "input tap", "uiautomator", "login(",
                    "open.kuaishou.com/openapi/photo/publish"):
            self.assertNotIn(bad,src)
        self.assertIn("com.kwai.video",src)
        self.assertIn("screencap",src)
        self.assertIn("sha256sum",src)
        self.assertIn('"NOT_PROVEN"',src)

    def test_forbidden_package_lookup_not_used(self):
        with self.assertRaises(kwai.KwaiProbeBlocked):
            kwai.installed("com.zhiliaoapp.musically")

if __name__=="__main__":
    unittest.main()
