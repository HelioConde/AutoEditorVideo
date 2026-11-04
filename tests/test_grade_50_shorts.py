"""Offline QA: batch of 50 distinct anime Shorts, no uploads or image calls."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

import grade_50_shorts as grade
from roteiro_para_storyboard import build_storyboard
from metadata_shorts import load_episodes, publisher_episode


def test_grade_has_exactly_50_original_scripts_and_no_duplicates():
    episodes=grade.load_queue()
    assert len(episodes)==50
    assert len({e['id'] for e in episodes})==50
    assert len({e['series'].casefold() for e in episodes})==50
    assert episodes[0]['series']=='Black Clover'
    assert episodes[-1]['series']=='Fullmetal Alchemist: Brotherhood'
    assert episodes[24]['series']=='Frieren: Beyond Journey\'s End'
    assert episodes[41]['series']=='Naruto'
    assert all(65<=len(e['script'].split())<=140 for e in episodes)
    assert all(e['script'].startswith(e['hook']) and e['script'].endswith(e['cta'])
               for e in episodes)
    assert all('Otaku Multicena' not in e['script'] for e in episodes)


def test_all_titles_and_descriptions_are_publishable_and_brand_consistent():
    episodes=grade.load_queue()
    catalog=load_episodes(include_recaps=True)
    for ep in episodes:
        assert ep['id'] in catalog
        meta=publisher_episode(catalog[ep['id']])
        assert 1<=len(meta['titulo_youtube'])<=100
        assert '#OtakuMulticena' in meta['descricao_youtube']
        assert len(meta['descricao_youtube'])<=5000
        assert not meta['descricao_youtube'].endswith('#ArquivoOtaku')


def test_storyboard_works_for_first_middle_and_nostalgic_episodes():
    episodes=grade.load_queue()
    for idx in (0,12,24,41,49):
        plan=build_storyboard(episodes[idx],max_hold=6)
        assert plan['id']==episodes[idx]['id']
        assert 1<=len(plan['scenes'])<=60
        assert all(s['duracao_estimada_s']>0 for s in plan['scenes'])
        assert 'visual_diversity_qa' in plan


def test_index_ranges_and_schedule_are_safe():
    queue=grade.load_queue()
    assert grade.selection(queue,1,1)[0]['id']==queue[0]['id']
    assert grade.selection(queue,45,6)[-1]['id']==queue[-1]['id']
    with pytest.raises(ValueError):
        grade.selection(queue,49,5)
    with pytest.raises(ValueError):
        grade.scheduled_at('2026-11-20T09:00:00',0,24)
    start=(datetime.now(timezone.utc)+timedelta(days=5)).isoformat()
    first=datetime.fromisoformat(grade.scheduled_at(start,0,24))
    second=datetime.fromisoformat(grade.scheduled_at(start,1,24))
    assert (second-first)==timedelta(hours=24)


def test_publication_without_confirmation_never_invokes_external_commands(monkeypatch):
    args=grade.parser().parse_args(['--acao','agendar','--inicio-na-lista','1',
                                  '--quantidade','2'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    calls=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:calls.append('called'))
    with pytest.raises(ValueError,match='ConfirmarPublicacao'):
        grade.run(args)
    assert calls==[]


def test_production_with_nonzero_image_budget_needs_confirmation(monkeypatch):
    args=grade.parser().parse_args(['--acao','produzir','--inicio-na-lista','1',
                                  '--quantidade','1','--max-chamadas-por-video','27'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    calls=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:calls.append('called'))
    with pytest.raises(ValueError,match='ConfirmarCotaImagem'):
        grade.run(args)
    assert calls==[]


def test_schedule_upload_is_private_and_uses_zero_new_image_calls():
    args=grade.parser().parse_args(['--acao','agendar','--inicio-na-lista','1',
                                  '--quantidade','1','--confirmar-publicacao',
                                  '--inicio-agendamento','2027-03-10T09:00:00-03:00'])
    cmd=grade.local_command(grade.load_queue()[0],args,publish=True,
                            schedule='2027-03-10T09:00:00-03:00')
    assert '-Publicar' in cmd
    assert '-Privacidade' in cmd and cmd[cmd.index('-Privacidade')+1]=='private'
    assert '-MaxChamadas' in cmd and cmd[cmd.index('-MaxChamadas')+1]=='0'
    assert '-AgendarEm' in cmd
    assert '-Refazer' not in cmd
