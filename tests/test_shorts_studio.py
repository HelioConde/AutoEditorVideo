"""No-network tests for Shorts Studio connection, UI commands and pinned cache."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.error import HTTPError

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'scripts'))
from shorts_studio import Job, build_command
import estado_codex_proxy as codex
import master_scenes as master


class Reply:
    def __init__(self,payload=None,status=200):
        self.status=status
        self.body=io.BytesIO(json.dumps(payload or {}).encode())
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return self.body.read(*args)


def test_connection_does_not_require_images_and_reports_server(tmp_path):
    (tmp_path/'chatgpt-codex-proxy').mkdir()
    (tmp_path/'chatgpt-codex-proxy'/'.env').write_text(
        'PROXY_API_KEY=abcdefghijklmnopqrstuvwxyz\n')
    urls=[]
    def opener(req,timeout):
        urls.append(req.full_url)
        if req.full_url.endswith('/health/live'): return Reply()
        assert req.get_header('Authorization')=='Bearer abcdefghijklmnopqrstuvwxyz'
        return Reply({'accounts':[{'eligible_now':True},{'eligible_now':False}]})
    status=codex.connection_status(tmp_path,opener=opener)
    assert status['state']=='conectado'
    assert status['eligible']==1
    assert len(urls)==2
    assert not any('images' in url for url in urls)


def test_proxy_online_without_credentials_is_distinct_from_offline(tmp_path,monkeypatch):
    monkeypatch.delenv('ARQUIVO_OTAKU_PROXY_ENV',raising=False)
    assert codex.connection_status(tmp_path,opener=lambda req,timeout: Reply())['state']=='sem_chave'
    def offline(req,timeout):
        raise OSError('refused')
    assert codex.connection_status(tmp_path,opener=offline)['state']=='offline'


def test_connected_but_no_eligible_account_is_not_called_offline(tmp_path,monkeypatch):
    monkeypatch.delenv('ARQUIVO_OTAKU_PROXY_ENV',raising=False)
    (tmp_path/'chatgpt-codex-proxy').mkdir()
    (tmp_path/'chatgpt-codex-proxy'/'.env').write_text(
        'PROXY_API_KEY=abcdefghijklmnopqrstuvwxyz\n')
    def opener(req,timeout):
        if req.full_url.endswith('/health/live'):return Reply()
        return Reply({'accounts':[{'eligible_now':False}]})
    status=codex.connection_status(tmp_path,opener=opener)
    assert status['server'] and status['authenticated']
    assert status['state']=='sem_conta_elegivel'


def test_commands_are_allowlisted_and_zero_budget_means_no_images(tmp_path):
    base={'id':'003-death-note-xadrez','scene':6,'model':'gpt-image-1.5',
          'budget':0,'all':False}
    cmd=build_command({**base,'action':'offline'},root=tmp_path)
    assert '-Offline' in cmd and cmd[-1]=='0'
    assert '-MaxChamadas' in cmd
    repaired=build_command({**base,'action':'reparar'},root=tmp_path)
    assert '-RepararFundo' in repaired and repaired[-1]=='1'
    assert '-Id' in repaired and '-Cena' in repaired
    assert '-Renderizar' in build_command({**base,'action':'render'},root=tmp_path)


@pytest.mark.parametrize('override',[
    {'action':'x'}, {'id':'bad;Remove-Item'}, {'scene':0},
    {'model':'unknown'}, {'budget':181}, {'all':'true'},
])
def test_ui_rejects_invalid_parameters(override,tmp_path):
    base={'action':'cache','id':'003-death-note-xadrez','scene':6,
          'model':'gpt-image-1.5','budget':0,'all':False}
    with pytest.raises(ValueError):
        build_command({**base,**override},root=tmp_path)


def test_ui_requires_explicit_single_scene_repair(tmp_path):
    with pytest.raises(ValueError,match='uma cena'):
        build_command({'action':'reparar','all':True,'id':'test-episode',
                       'scene':6,'model':'gpt-image-1.5','budget':1},root=tmp_path)


def test_pinned_storyboard_is_stable_without_replan(tmp_path,monkeypatch):
    monkeypatch.setattr(master,'ROOT',tmp_path)
    monkeypatch.setattr(master,'OUT',tmp_path/'assets'/'gerados'/'shorts-animados')
    plans=tmp_path/'assets'/'gerados'/'planos-visuais'
    plans.mkdir(parents=True)
    plan=plans/'003-death-note-xadrez-master-dinamico.json'
    def body(prompt):
        return {'schema':'arquivo-otaku/master-storyboards/v2','id':'003-death-note-xadrez',
                'scenes':[{'id':'01','subject':'personagens','prompt':prompt}]}
    old=body('old prompt '+('A'*50))
    plan.write_text(json.dumps(old))
    selected=master.production_storyboard('003-death-note-xadrez',6)
    assert selected.read_text()==json.dumps(old)
    plan.write_text(json.dumps(body('new prompt '+('B'*50))))
    assert master.production_storyboard('003-death-note-xadrez',6).read_text()==json.dumps(old)


def test_job_tracks_single_active_process():
    job=Job()
    assert job.status()['busy'] is False
    with job.lock: job.busy=True
    with pytest.raises(ValueError,match='Uma tarefa'):
        job.start(['not-a-real-command'],'cache')
