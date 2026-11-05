"""No Google network, no OAuth, no YouTube write during PR/CI QA."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import cloud_youtube_private_5011 as publish
import youtube_env_policy_guard as gate


def base_env():
    return {'GITHUB_REPOSITORY':'HelioConde/AutoEditorVideo',
            'GITHUB_REF':'refs/heads/main',
            'GITHUB_EVENT_NAME':'workflow_dispatch',
            'GITHUB_RUN_ATTEMPT':'1',
            'PRIVATE_UPLOAD_CONFIRMED':'true',
            'EXPECTED_CHANNEL_ID':publish.EXPECTED['br'][0],
            'YOUTUBE_CLIENT_JSON':'{"installed":{"client_id":"fake","client_secret":"fake"}}',
            'YOUTUBE_BR_TOKEN_JSON':'{"client_id":"fake","refresh_token":"fake"}'}


def test_br_owner_preflight():
    publish.preflight(base_env(),'br')


@pytest.mark.parametrize('changes,code',[
    ({'GITHUB_REF':'refs/heads/feature'},'UNAUTHORIZED_EVENT'),
    ({'GITHUB_EVENT_NAME':'pull_request'},'UNAUTHORIZED_EVENT'),
    ({'GITHUB_RUN_ATTEMPT':'2'},'RERUN_BLOCKED'),
    ({'PRIVATE_UPLOAD_CONFIRMED':'false'},'EXPLICIT_PRIVATE_APPROVAL_REQUIRED'),
    ({'EXPECTED_CHANNEL_ID':'UCBoNbQjaMYdpJqPLRZAFkvQ'},'EXPECTED_CHANNEL_ID_MISMATCH'),
    ({'YOUTUBE_CLIENT_JSON':''},'YOUTUBE_CHANNEL_OAUTH_NOT_CONFIGURED'),
    ({'YOUTUBE_BR_TOKEN_JSON':''},'YOUTUBE_CHANNEL_OAUTH_NOT_CONFIGURED'),
])
def test_denied_before_any_network(changes,code):
    with pytest.raises(publish.UploadBlocked,match=code):
        publish.preflight(base_env()|changes,'br')


def test_separate_english_token_and_exact_channel():
    env=base_env()|{
      'EXPECTED_CHANNEL_ID':publish.EXPECTED['en'][0],
      'YOUTUBE_EN_TOKEN_JSON':'{"client_id":"fake","refresh_token":"fake"}'}
    publish.preflight(env,'en')
    del env['YOUTUBE_EN_TOKEN_JSON']
    with pytest.raises(publish.UploadBlocked,match='YOUTUBE_CHANNEL_OAUTH_NOT_CONFIGURED'):
        publish.preflight(env,'en')


def test_review_rejects_wrong_sha_before_publication(tmp_path):
    fake=tmp_path/f'br-{publish.ID}-autoeditorvideo.mp4'
    fake.write_bytes(b'fake MP4 bytes' * 20000)
    cover=tmp_path/f'br-{publish.ID}-cover.jpg'
    Image.new('RGB',(540,960)).save(cover,format='JPEG')
    (tmp_path/'review-summary.json').write_text(json.dumps({
      'schema':'autoeditorvideo/dual-cloud-review/v1',
      'episode':publish.ID,'publication':'not_performed',
      'render_origin':'original AutoEditorVideo Remotion in GitHub Actions',
      'videos':[
        {'channel':'br','expected_youtube_channel_id':publish.EXPECTED['br'][0],
         'mp4':fake.name,'cover':cover.name,'sha256':'0'*64},
        {'channel':'en'}]}))
    with pytest.raises(publish.UploadBlocked,match='MP4_HASH_MISMATCH'):
        publish.validate_review('br',tmp_path)


def test_review_fails_when_incomplete(tmp_path):
    with pytest.raises((ValueError, OSError)):
        publish.validate_review('br',tmp_path)


def test_main_only_environment_and_private_upload_policy():
    from image_env_policy_guard import strict_environment_policy as _original
    assert gate.ENV_NAME == 'youtube-private-upload'
    assert gate.REPO == 'HelioConde/AutoEditorVideo'
    env={'name':'youtube-private-upload',
         'deployment_branch_policy':{'custom_branch_policies':True,
                                     'protected_branches':False}}
    policies={'total_count':1,'branch_policies':[{'name':'main','type':'branch'}]}
    gate.strict_environment_policy(env,policies)


def test_publisher_source_is_private_and_no_schedule():
    source=(ROOT/'scripts'/'cloud_youtube_private_5011.py').read_text()
    assert "'privacyStatus':'private'" in source
    assert "publishAt" not in source
    assert "image_generation" not in source
    assert "PROXY_ACCOUNTS_JSON" not in source
