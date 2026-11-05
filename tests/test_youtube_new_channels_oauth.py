"""Offline safety verification: no Google requests, OAuth or YouTube uploads."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import youtube_new_channels_oauth as oauth
import youtube_new_channels_env_guard as guard
from youtube_channel_registry import NEW_CHANNELS, get_channel


def fake_client():
    return {"installed":{"client_id":"fake-client-id","client_secret":"not-real"}}

def fake_token():
    return {"client_id":"fake-client-id","refresh_token":"fake-refresh-token",
            "scopes":list(oauth.SCOPES)}


@pytest.mark.parametrize("channel",NEW_CHANNELS)
def test_unchanged_three_channels_have_unique_target_and_token_paths(channel):
    row=get_channel(channel)
    assert row["cloud_upload_state"].startswith("blocked_")
    assert row["visibility_default"]=="private"
    assert row["oauth_token_secret_name"].startswith("YOUTUBE_")
    assert oauth.local_token_path(channel).name==f"youtube-{channel}-cloud-token.json"
    assert ".secrets" in str(oauth.local_token_path(channel))

def test_oauth_requires_both_upload_and_readonly_scopes():
    oauth.validate_token_fields(fake_client(),fake_token())
    bad=fake_token()
    bad["scopes"]=[oauth.SCOPES[0]]
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="SCOPES_REQUIRED"):
        oauth.validate_token_fields(fake_client(),bad)
    bad=fake_token()
    bad["refresh_token"]=""
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="REFRESH_TOKEN_MISSING"):
        oauth.validate_token_fields(fake_client(),bad)
    bad=fake_token()
    bad["client_id"]="another-client"
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="ANOTHER_OAUTH_CLIENT"):
        oauth.validate_token_fields(fake_client(),bad)

class ReadOnlyYouTube:
    def __init__(self,channel):
        self.channel=channel
    def channels(self):
        return self
    def list(self,*,part,mine):
        assert part=="id" and mine is True
        return self
    def execute(self):
        return {"items":[{"id":get_channel(self.channel)["youtube_channel_id"]}]}

@pytest.mark.parametrize("channel",NEW_CHANNELS)
def test_channel_read_only_identity_match(channel):
    yt=ReadOnlyYouTube(channel)
    assert oauth.verify_channel_identity(yt,channel)==get_channel(channel)["youtube_channel_id"]

@pytest.mark.parametrize("channel",NEW_CHANNELS)
def test_channel_does_not_accept_otaku_or_other_channel_oauth(channel):
    yt=ReadOnlyYouTube("br")
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="CHANNEL_ID_MISMATCH"):
        oauth.verify_channel_identity(yt,channel)
    alternate=next(s for s in NEW_CHANNELS if s!=channel)
    yt=ReadOnlyYouTube(alternate)
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="CHANNEL_ID_MISMATCH"):
        oauth.verify_channel_identity(yt,channel)

def cloud_env(channel):
    return {
        "GITHUB_REPOSITORY":"HelioConde/AutoEditorVideo",
        "GITHUB_REF":"refs/heads/main",
        "GITHUB_EVENT_NAME":"workflow_dispatch",
        "GITHUB_RUN_ATTEMPT":"1",
        "GITHUB_ACTIONS":"true",
        "EXPECTED_CHANNEL_SLUG":channel,
        "YOUTUBE_CLIENT_JSON":json.dumps(fake_client()),
        "YOUTUBE_CHANNEL_TOKEN_JSON":json.dumps(fake_token()),
    }

@pytest.mark.parametrize("mod,code",[
    ({"GITHUB_REPOSITORY":"someone/repo"},"WRONG_REPOSITORY"),
    ({"GITHUB_REF":"refs/heads/test"},"MAIN_ONLY"),
    ({"GITHUB_EVENT_NAME":"pull_request"},"ONE_SHOT_MANUAL_DIAGNOSTIC_ONLY"),
    ({"GITHUB_RUN_ATTEMPT":"2"},"ONE_SHOT_MANUAL_DIAGNOSTIC_ONLY"),
    ({"EXPECTED_CHANNEL_SLUG":"kids"},"CROSS_CHANNEL_WORKFLOW_INPUT"),
    ({"GITHUB_ACTIONS":"false"},"GITHUB_RUNNER_REQUIRED"),
    ({"YOUTUBE_CLIENT_JSON":""},"CHANNEL_SPECIFIC_OAUTH_SECRETS_MISSING"),
    ({"YOUTUBE_CHANNEL_TOKEN_JSON":""},"CHANNEL_SPECIFIC_OAUTH_SECRETS_MISSING"),
])
def test_cloud_blocks_broken_workflow_before_network(mod,code):
    with pytest.raises(oauth.NewChannelOAuthBlocked,match=code):
        oauth.verify_on_github("games",cloud_env("games")|mod)

def test_rejects_invalid_json_or_mismatched_client_in_cloud():
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="INVALID_OAUTH_SECRET_JSON"):
        oauth.verify_on_github("games",cloud_env("games")|{"YOUTUBE_CLIENT_JSON":"{"})
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="ANOTHER_OAUTH_CLIENT"):
        oauth.verify_on_github("games",cloud_env("games")|{
            "YOUTUBE_CHANNEL_TOKEN_JSON":json.dumps({**fake_token(),"client_id":"other"})
        })

def gh_policy(channel,*,name=None,branch="main"):
    return {"name":name or get_channel(channel)["youtube_environment"],
            "deployment_branch_policy":{"custom_branch_policies":True,"protected_branches":False}},{
            "total_count":1,
            "branch_policies":[{"name":branch,"type":"branch"}]
        }

@pytest.mark.parametrize("channel",NEW_CHANNELS)
def test_only_main_protected_environment_is_accepted(channel):
    env,policies=gh_policy(channel)
    guard.policy_is_main_only(channel,env,policies)
    with pytest.raises(guard.UnsafeYouTubeEnvironment,match="ONLY_MAIN_ALLOWED"):
        env,p=gh_policy(channel,branch="*")
        guard.policy_is_main_only(channel,env,p)
    with pytest.raises(guard.UnsafeYouTubeEnvironment,match="WRONG_CHANNEL"):
        env,p=gh_policy(channel,name="youtube-not-protected")
        guard.policy_is_main_only(channel,env,p)

def test_missing_environment_and_multiple_branches_do_not_unlock_oauth():
    env,policies=gh_policy("kids")
    env["deployment_branch_policy"]["custom_branch_policies"]=False
    with pytest.raises(guard.UnsafeYouTubeEnvironment,match="CUSTOM_MAIN_BRANCH_RULE_REQUIRED"):
        guard.policy_is_main_only("kids",env,policies)
    env,policies=gh_policy("kids")
    policies["total_count"]=2
    policies["branch_policies"].append({"name":"test","type":"branch"})
    with pytest.raises(guard.UnsafeYouTubeEnvironment,match="BRANCH_POLICY_NOT_EXACTLY_ONE"):
        guard.policy_is_main_only("kids",env,policies)

@pytest.mark.parametrize("channel",NEW_CHANNELS)
def test_local_login_refused_inside_github_without_oauth_calls(monkeypatch,channel):
    monkeypatch.setenv("GITHUB_ACTIONS","true")
    with pytest.raises(oauth.NewChannelOAuthBlocked,match="INTERACTIVE_LOGIN_FORBIDDEN_IN_GITHUB"):
        oauth.authorize_locally(channel)

def test_no_video_write_or_image_access_code_in_read_only_workflow():
    script=(ROOT/"scripts"/"youtube_new_channels_oauth.py").read_text(encoding="utf-8")
    workflow=(ROOT/".github"/"workflows"/"youtube-new-channels-oauth.yml").read_text(encoding="utf-8")
    assert "videos().insert(" not in script
    assert "thumbnails().set(" not in script
    assert "mcp__" not in script
    assert "PROXY_ACCOUNTS_JSON" not in workflow
    assert "images/generations" not in script
    for slug in NEW_CHANNELS:
        assert "environment: "+get_channel(slug)["youtube_environment"] in workflow
        assert "secrets."+get_channel(slug)["oauth_token_secret_name"] in workflow
    assert "github.run_attempt == 1" in workflow
    assert workflow.count("environment: youtube-private-upload")==3
    for legacy in ("youtube-games-private-upload","youtube-kids-private-upload",
                   "youtube-alchemy-private-upload"):
        assert legacy not in workflow


def test_powershell_only_writes_selected_token_and_preserves_otaku():
    ps=(ROOT/"conectar-novos-canais.ps1").read_text(encoding="utf-8")
    assert "& gh secret set $tokenSecretName -e $environment" in ps
    assert "gh secret set YOUTUBE_CLIENT_JSON" not in ps
    assert "youtube-private-upload" in ps
    assert "YOUTUBE_CLIENT_JSON' }).Count" in ps
    for token in ("YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON"):
        assert "gh secret set "+token not in ps
    assert "ConfirmarArmazenamentoGitHub" in ps


def test_legacy_otaku_workflow_keeps_same_shared_env_and_secret_names():
    old=(ROOT/".github"/"workflows"/"otaku-cloud-private-5011.yml").read_text(encoding="utf-8")
    assert old.count("environment: youtube-private-upload")==2
    for token in ("YOUTUBE_BR_TOKEN_JSON","YOUTUBE_EN_TOKEN_JSON","YOUTUBE_CLIENT_JSON"):
        assert "secrets."+token in old

