"""Offline failure diagnostics for image edits and safe retry behavior.

No Docker, image generation, credentials or YouTube is used here.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

import master_scenes as scenes
import fluxo_unico_short as flow


def test_edit_http_400_is_recorded_as_nonretryable_without_proxy_body(
    tmp_path,monkeypatch
):
    monkeypatch.setattr(scenes,'scene_dir',lambda *_a,**_k:tmp_path)
    (tmp_path/'master.png').write_bytes(b'already-paid-master')
    ep={'id':'5005-bleach-thousand-year-blood-war'}
    shot={'id':'01','prompt':'Anime battle illustration, no logos or text.'}
    error=RuntimeError('Proxy recusou images/edits (HTTP 400): '
                       'INTERNAL PROVIDER ERROR and token-secret. '
                       'Sem gerar nova cena de forma independente.')
    report=scenes.scene_failure_report(ep,shot,'gpt-image-2',error)
    assert report['stage']=='foreground'
    assert report['category']=='payload_ou_modelo_incompativel'
    assert report['http_status']==400
    assert report['retryable'] is False
    saved=(tmp_path/'scene-failure.json').read_text(encoding='utf-8')
    assert 'token-secret' not in saved
    assert (tmp_path/'master.png').read_bytes()==b'already-paid-master'


def test_edit_http_503_is_retryable_and_identifies_background(
    tmp_path,monkeypatch
):
    monkeypatch.setattr(scenes,'scene_dir',lambda *_a,**_k:tmp_path)
    (tmp_path/'master.png').write_bytes(b'master')
    (tmp_path/'foreground-raw.png').write_bytes(b'foreground')
    report=scenes.scene_failure_report(
        {'id':'5005-bleach-thousand-year-blood-war'},
        {'id':'07','prompt':'Example prompt with static art'},
        'gpt-image-2',
        RuntimeError('Proxy recusou images/edits (HTTP 503): bad gateway')
    )
    assert report['stage']=='background'
    assert report['retryable'] is True
    assert report['http_status']==503


def test_quota_429_never_retries_immediately(tmp_path,monkeypatch):
    monkeypatch.setattr(scenes,'scene_dir',lambda *_a,**_k:tmp_path)
    ep={'id':'5005-bleach-thousand-year-blood-war'}
    shot={'id':'06','prompt':'Cinematic scene of Ichigo in Seireitei'}
    report=scenes.scene_failure_report(
        ep,shot,'gpt-image-2',
        RuntimeError('Proxy recusou images/edits (HTTP 429): too many requests')
    )
    assert report['retryable'] is False
    calls=[]
    monkeypatch.setattr(flow,'pending_calls',lambda *_a:2)
    def runner(_args,*,label):
        calls.append(label)
        return False
    budget=[8]
    assert flow.generate_scene_with_retry(
        ep,shot,model='gpt-image-2',budget=budget,attempts=3,runner=runner
    ) is False
    assert len(calls)==1
    assert budget==[7]


def test_retries_transient_5xx_using_existing_cached_files(tmp_path,monkeypatch):
    monkeypatch.setattr(scenes,'scene_dir',lambda *_a,**_k:tmp_path)
    ep={'id':'5005-bleach-thousand-year-blood-war'}
    shot={'id':'07','prompt':'Bleach scene in Seireitei at dusk'}
    scenes.scene_failure_report(
        ep,shot,'gpt-image-2',
        RuntimeError('Proxy recusou images/edits (HTTP 502): gateway')
    )
    calls=[]
    monkeypatch.setattr(flow,'pending_calls',lambda *_a:2 if len(calls)<2 else 0)
    def runner(_args,*,label):
        calls.append(label)
        if len(calls)==2:
            (tmp_path/'scene-failure.json').unlink()
            return True
        return False
    assert flow.generate_scene_with_retry(
        ep,shot,model='gpt-image-2',budget=[5],attempts=2,runner=runner
    ) is True
    assert len(calls)==2
