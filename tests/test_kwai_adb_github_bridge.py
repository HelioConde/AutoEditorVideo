"""No-network guards for GitHub Actions -> Windows Samsung ADB bridge."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kwai_adb_local_bridge as bridge
import kwai_adb_artifact_gate as gate

class KwaiBridgeTests(unittest.TestCase):
    def test_android_tls_wifi_serial_parsed_without_exposing_it(self):
        output=("List of devices attached\n"
                "adb-RXCW102A49B-oGHvwM._adb-tls-connect._tcp   device\n")
        with patch.object(bridge,"exec_adb",return_value=output):
            serial=bridge.device_serial("adb")
        self.assertEqual(serial,"adb-RXCW102A49B-oGHvwM._adb-tls-connect._tcp")

    def test_ambiguity_and_emulator_devices_are_blocked(self):
        for result in (
            "List of devices attached\n",
            "List of devices attached\nemulator-5554 device\n",
            "List of devices attached\nabcde unauthorized\n",
            "List of devices attached\nSamsung01 device\nSamsung02 device\n",
        ):
            with self.subTest(output=result),patch.object(bridge,"exec_adb",return_value=result):
                with self.assertRaises(bridge.BridgeBlocked):
                    bridge.device_serial("adb")

    def test_only_correct_samsung_model_and_kwai_app_can_be_verified(self):
        def check(adb,*args,**kwargs):
            prop=args[-1]
            if prop=="ro.product.manufacturer":return "samsung"
            if prop=="ro.product.model":return "SM-M236B"
            if prop=="ro.build.version.sdk":return "34"
            if prop=="com.kwai.video":return "package:/data/app/base.apk"
            raise AssertionError(args)
        with patch.object(bridge,"exec_adb",side_effect=check):
            x=bridge.check_phone("adb","tls-device")
        self.assertTrue(x["kwai_official_app_installed"])
        self.assertFalse(x["kwai_posting_automated"])

    def test_unknown_phone_cannot_receive_video(self):
        with patch.object(bridge,"exec_adb",side_effect=["samsung","SM-N0000","34","package:/a"]):
            with self.assertRaises(bridge.BridgeBlocked):
                bridge.check_phone("adb","tls-device")

    def test_mp4_selection_refuses_ambiguous_files_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"one.mp4").write_bytes(b"\0\0\0\x18ftyp"+b"a"*20000)
            selected,h=bridge.safe_video(root)
            self.assertEqual(selected.name,"one.mp4")
            self.assertEqual(len(h),64)
            for name in ("../one.mp4","/one.mp4","C:/one.mp4","one.mp4/../file"):
                with self.subTest(relative=name):
                    with self.assertRaises(bridge.BridgeBlocked):
                        bridge.safe_video(root,name)
            (root/"two.mp4").write_bytes(b"\0\0\0\x18ftyp"+b"b"*20000)
            with self.assertRaises(bridge.BridgeBlocked):
                bridge.safe_video(root)
            chosen,_=bridge.safe_video(root,"two.mp4")
            self.assertEqual(chosen.name,"two.mp4")

    def test_staging_is_idempotent_and_never_touches_publish_button(self):
        sha="ab"*32
        remote=bridge.DEVICE_MEDIA_DIR+"/ae_"+sha[:32]+".mp4"
        with patch.object(bridge,"android_sha",return_value=sha),patch.object(bridge,"exec_adb") as called:
            report=bridge.stage("adb","serial",Path("video.mp4"),sha)
        self.assertEqual(report["stage_result"],"already_staged_same_hash")
        self.assertEqual(report["remote_media_path"],remote)
        self.assertFalse(report["kwai_publish_success"])
        all_args=[args for args,_ in called.call_args_list]
        self.assertFalse(any("push" in str(args) for args in all_args))
        self.assertFalse(any("input" in str(args) or "tap" in str(args) for args in all_args))

    def test_source_artifact_stage_requires_explicit_qa(self):
        gate.require_stage_inputs("diagnose","","","")
        with self.assertRaises(gate.ProvenanceBlocked):
            gate.require_stage_inputs("stage","12345","videos-br","false")
        with self.assertRaises(gate.ProvenanceBlocked):
            gate.require_stage_inputs("stage","12345","../safe","true")
        gate.require_stage_inputs("stage","12345","videos-br","true")

    def test_source_run_must_succeed_from_main_and_same_repo(self):
        row={"id":12345,"status":"completed","conclusion":"success",
             "head_branch":"main","event":"push",
             "repository":{"full_name":gate.REPO},
             "head_repository":{"full_name":gate.REPO}}
        gate.require_source_run(row,"12345")
        for key,value in (
            ("conclusion","failure"),("head_branch","danger"),("event","pull_request"),
            ("head_repository",{"full_name":"someone/AutoEditorVideo"})):
            bad={**row,key:value}
            with self.subTest(field=key),self.assertRaises(gate.ProvenanceBlocked):
                gate.require_source_run(bad,"12345")

    def test_missing_expired_or_massive_artifact_is_blocked(self):
        good={"name":"video-staged","expired":False,"size_in_bytes":500000}
        gate.require_artifact([good],"video-staged")
        for item in (
            {**good,"expired":True},
            {**good,"size_in_bytes":0},
            {**good,"size_in_bytes":2*1024**3},
        ):
            with self.assertRaises(gate.ProvenanceBlocked):
                gate.require_artifact([item],"video-staged")

    def test_no_kwai_auto_post_commands_or_auth_access(self):
        src=(ROOT/"scripts"/"kwai_adb_local_bridge.py").read_text(encoding="utf-8")
        for command in ("adb shell input tap","media_publish","videos().insert(",
                        "requests.post(", "access_token","refresh_token",
                        "input keyevent 66","uiautomator click"):
            self.assertNotIn(command,src)
        self.assertIn("KWAI_PACKAGE=",src)
        self.assertIn("NO_KWAI_LOGIN_NO_AUTOMATED_POST",src)

if __name__=="__main__":
    unittest.main()
