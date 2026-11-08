"""Offline no-network tests for safe Android emulator smoke experiment."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import android_emulator_safe_smoke as android

class SafeAndroidSmokeTests(unittest.TestCase):
    def test_policy_is_nondestructive(self):
        android.validate_policy()
        data=android.policy()
        self.assertEqual(data["android_api"],34)
        self.assertEqual(data["architecture"],"x86_64")
        for field in (
            "install_third_party_apks","login_to_tiktok_or_kwai",
            "upload_real_video","post_any_content","save_social_credentials"
        ):
            self.assertFalse(data[field],field)

    def test_sha256_parse_accepts_standard_android_output(self):
        token="ab"*32
        self.assertEqual(android.parse_android_sha256(
            token+"  /sdcard/Movies/autoeditorvideo-ci-test-only.mp4"),token)

    def test_sha256_parse_rejects_malformed_data(self):
        for value in ("", "aaaaaaaa: error", "sha256: 123", "wrong hash output"):
            with self.subTest(value=value):
                with self.assertRaises(android.SmokeBlocked):
                    android.parse_android_sha256(value)

    def test_emulator_requires_exact_one_shot_main_branch(self):
        with patch.dict("os.environ",{
            "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
            "GITHUB_REF":"refs/heads/testing",
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_RUN_ATTEMPT":"1",
            "GITHUB_WORKFLOW":android.WORKFLOW,
            "ANDROID_SMOKE_NO_PUBLICATION":"yes",
            "ANDROID_EMULATOR_TEST_ONLY":"true",
        },clear=True):
            with self.assertRaises(android.SmokeBlocked):
                android.guard()

    def test_emulator_refuses_provider_secret(self):
        with patch.dict("os.environ",{
            "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_RUN_ATTEMPT":"1",
            "GITHUB_WORKFLOW":android.WORKFLOW,
            "ANDROID_SMOKE_NO_PUBLICATION":"yes",
            "ANDROID_EMULATOR_TEST_ONLY":"true",
            "TIKTOK_ACCESS_TOKEN":"TEST_DONT_USE"
        },clear=True):
            with self.assertRaises(android.SmokeBlocked):
                android.guard()

    def test_emulator_accepts_authorized_clean_ci_environment(self):
        with patch.dict("os.environ",{
            "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
            "GITHUB_REF":"refs/heads/main",
            "GITHUB_EVENT_NAME":"push",
            "GITHUB_RUN_ATTEMPT":"1",
            "GITHUB_WORKFLOW":android.WORKFLOW,
            "ANDROID_SMOKE_NO_PUBLICATION":"yes",
            "ANDROID_EMULATOR_TEST_ONLY":"true",
        },clear=True):
            android.guard()

    def test_no_real_platform_automation_in_test_source(self):
        text=(ROOT/"scripts"/"android_emulator_safe_smoke.py").read_text()
        self.assertNotIn("requests.post(",text)
        self.assertNotIn("selenium",text)
        self.assertNotIn("playwright",text)
        self.assertNotIn("adb install",text)
        self.assertNotIn("videos().insert(",text)
        self.assertIn("supports_tiktok_or_kwai_publishing",text)
        self.assertIn('"NOT_TESTED"',text)
        self.assertIn("screencap",text)
        self.assertIn("sha256sum",text)

if __name__=="__main__":
    unittest.main()
