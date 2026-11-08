"""Offline guard tests for read-only GitHub watcher -> phone (no runner on public)."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import kwai_github_pc_agent as agent

def item():
    return {
        "queue_id":"br-5001-qa-verified",
        "channel":"br",
        "run_id":42467580687,
        "artifact_name":"ready-short-mp4",
        "relative_video":"export/final.mp4",
        "sha256":"ab"*32,
        "approved_for_local_stage":True,
        "status":"approved",
    }

class KwaiPCWatcherTests(unittest.TestCase):
    def test_empty_github_queue_does_not_trigger_phone(self):
        payload={
            "schema":"autoeditorvideo/kwai-local-adb-stage-queue/v1",
            "platform":"kwai_brazil",
            "source_repository":"HelioConde/AutoEditorVideo",
            "stage_only_no_publish":True,
            "requires_approved_video":True,
            "requires_successful_main_run":True,
            "allow_unapproved_artifacts":False,
            "automatic_stage_queue_enabled":True,
            "items":[],
        }
        with patch.object(agent,"gh",return_value=json.dumps(payload)):
            self.assertEqual(agent.queue(),[])
        with patch.object(agent,"queue",return_value=[]),patch.object(agent,"adb_exe") as adb:
            self.assertEqual(agent.process_once()["newly_staged"],0)
            adb.assert_not_called()

    def test_valid_queue_item_needs_sha_and_explicit_approval(self):
        agent.validate_item(item())
        for invalid in (
            {**item(),"sha256":"0"*12},
            {**item(),"status":"held"},
            {**item(),"approved_for_local_stage":False},
            {**item(),"channel":"random"},
            {**item(),"run_id":-1},
            {**item(),"relative_video":None},
            {**item(),"queue_id":"../evil"},
        ):
            with self.subTest(row=invalid),self.assertRaises(agent.AgentBlocked):
                agent.validate_item(invalid)

    def test_unapproved_held_entries_are_not_staged(self):
        held={**item(),"status":"held","approved_for_local_stage":False}
        agent.validate_item(held)
        with patch.object(agent,"queue",return_value=[held]),patch.object(agent,"adb_exe") as adb:
            self.assertEqual(agent.process_once()["newly_staged"],0)
            adb.assert_not_called()

    def test_dry_run_cannot_contact_phone(self):
        with patch.object(agent,"queue",return_value=[item()]),patch.object(agent,"adb_exe") as adb:
            self.assertEqual(agent.process_once(dry_run=True)["approved_count"],1)
            adb.assert_not_called()

    def test_already_processed_entry_is_skipped(self):
        with patch.object(agent,"queue",return_value=[item()]):
            with patch.object(agent,"receipts",return_value={
                item()["queue_id"]:{"sha256":item()["sha256"]}}):
                with patch.object(agent,"app_data_path",return_value=Path("fake")):
                    with patch.object(agent,"adb_exe") as adb:
                        self.assertEqual(agent.process_once()["newly_staged"],0)
                        adb.assert_not_called()

    def test_receipts_only_on_local_disk(self):
        with tempfile.TemporaryDirectory() as t:
            file=Path(t)/"state.json"
            agent.save_receipts(file,{"test":{"sha256":"00"*32,"published":False}})
            self.assertFalse(agent.receipts(file)["test"]["published"])

    def test_github_api_is_restricted_to_own_repo(self):
        with self.assertRaises(agent.AgentBlocked):
            agent.gh_json("repos/other/project/actions/runs/1234")

    def test_agent_contains_no_platform_publication_or_login(self):
        s=(ROOT/"scripts"/"kwai_github_pc_agent.py").read_text(encoding="utf-8")
        for t in ("adb shell input tap","gh secret set","requests.post(",
                  "media_publish","adb install","appium"):
            self.assertNotIn(t,s)
        self.assertIn("AUTO",s.upper())

if __name__=="__main__":
    unittest.main()
