"""Offline read-only BR YouTube OAuth classification without network or uploads."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import pytest
from google.auth.exceptions import RefreshError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cloud_youtube_private_5011 as uploader
import youtube_br_oauth_readonly_probe as probe

def fake_env():
    return {
        'GITHUB_REPOSITORY':'HelioConde/AutoEditorVideo',
        'GITHUB_REF':'refs/heads/main',
        'GITHUB_EVENT_NAME':'push',
        'GITHUB_RUN_ATTEMPT':'1',
        'YOUTUBE_CLIENT_JSON':json.dumps({'installed':{
            'client_id':'fake-client','client_secret':'fake-secret'}}),
        'YOUTUBE_BR_TOKEN_JSON':json.dumps({
            'client_id':'fake-client','client_secret':'fake-secret',
            'refresh_token':'fake-refresh','token':'fake-access',
            'scopes':list(uploader.SCOPES)}),
    }

@pytest.mark.parametrize("changes,reason", [
    ({'GITHUB_EVENT_NAME':'workflow_dispatch'},'READONLY_PUSH_DIAGNOSTIC_ONLY'),
    ({'GITHUB_REF':'refs/heads/other'},'MAIN_ONLY'),
    ({'GITHUB_RUN_ATTEMPT':'2'},'RERUN_NOT_ALLOWED'),
    ({'GITHUB_REPOSITORY':'other/repo'},'WRONG_REPOSITORY'),
    ({'YOUTUBE_BR_TOKEN_JSON':''},'YOUTUBE_ENVIRONMENT_SECRET_MISSING'),
])
def test_readonly_gate_refuses_non_main_and_missing_auth(changes,reason,capsys):
    def forbidden(*args):
        raise AssertionError("OAuth must never be requested")
    assert probe.main(fake_env()|changes,verify=forbidden)==1
    assert reason in capsys.readouterr().out

def test_readonly_probe_success_only_checks_channel(capsys):
    calls=[]
    def reader(env,channel):
        calls.append(channel)
        return object(),"fake-uploads-playlist"
    assert probe.main(fake_env(),verify=reader)==0
    assert calls==['br']
    out=capsys.readouterr().out
    assert "VERIFIED_BR_CHANNEL" in out
    assert "ZERO_YOUTUBE_UPLOADS" in out
    assert 'fake-secret' not in out

def test_original_br_token_readonly_scope_missing_is_specific_and_safe(capsys):
    env=fake_env()
    token=json.loads(env['YOUTUBE_BR_TOKEN_JSON'])
    token['scopes']=['https://www.googleapis.com/auth/youtube.upload']
    env['YOUTUBE_BR_TOKEN_JSON']=json.dumps(token)
    with pytest.raises(uploader.UploadBlocked,match='YOUTUBE_READONLY_SCOPE_MISSING_IN_STORED_TOKEN'):
        uploader.authorized_youtube(env,'br')
    out=capsys.readouterr().out
    assert 'fake-secret' not in out and 'fake-refresh' not in out

def test_original_br_token_upload_scope_missing_is_specific():
    env=fake_env()
    token=json.loads(env['YOUTUBE_BR_TOKEN_JSON'])
    token['scopes']=['https://www.googleapis.com/auth/youtube.readonly']
    env['YOUTUBE_BR_TOKEN_JSON']=json.dumps(token)
    with pytest.raises(uploader.UploadBlocked,match='YOUTUBE_UPLOAD_SCOPE_MISSING_IN_STORED_TOKEN'):
        uploader.authorized_youtube(env,'br')

@pytest.mark.parametrize('text,code',[
    ('invalid_grant: token expired','OAUTH_REFRESH_INVALID_GRANT'),
    ('invalid_scope: missing YouTube','OAUTH_REFRESH_INVALID_SCOPE'),
    ('invalid_client','OAUTH_REFRESH_INVALID_CLIENT'),
    ('private-provider-body','OAUTH_REFRESH_REJECTED'),
])
def test_google_refresh_error_categorized_without_leaking_message(text,code):
    assert uploader._safe_refresh_reason(RefreshError(text)) == code

def test_unchanged_upload_safety():
    uploader_code=(ROOT/'scripts'/'cloud_youtube_private_5011.py').read_text()
    probe_code=(ROOT/'scripts'/'youtube_br_oauth_readonly_probe.py').read_text()
    assert 'privacyStatus' in uploader_code and "'private'" in uploader_code
    assert "videos().insert" not in probe_code
    assert "publish_one" not in probe_code
    assert "PROXY_ACCOUNTS_JSON" not in probe_code
