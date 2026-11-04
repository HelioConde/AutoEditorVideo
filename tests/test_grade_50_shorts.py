"""Offline QA: batch of 50 distinct anime Shorts, no uploads or image calls."""
from __future__ import annotations

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


def test_index_ranges_and_no_scheduling_controls():
    queue=grade.load_queue()
    assert grade.selection(queue,1,1)[0]['id']==queue[0]['id']
    assert grade.selection(queue,45,6)[-1]['id']==queue[-1]['id']
    with pytest.raises(ValueError):
        grade.selection(queue,49,5)
    assert 'agendar' not in grade.parser()._option_string_actions['--acao'].choices
    assert '--inicio-agendamento' not in grade.parser()._option_string_actions


def test_publication_without_confirmation_never_invokes_external_commands(monkeypatch):
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','2'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    calls=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:calls.append('called'))
    with pytest.raises(ValueError,match='ConfirmarPublicacao'):
        grade.run(args)
    assert calls==[]


def test_production_with_nonzero_image_budget_needs_confirmation(monkeypatch):
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','1',
                                   '--max-chamadas-por-video','27',
                                   '--confirmar-publicacao'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    calls=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:calls.append('called'))
    with pytest.raises(ValueError,match='ConfirmarCotaImagem'):
        grade.run(args)
    assert calls==[]


def test_immediate_upload_is_public_and_uses_zero_new_image_calls():
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','1',
                                   '--confirmar-publicacao'])
    cmd=grade.local_command(grade.load_queue()[0],args,publish=True)
    assert '-Publicar' in cmd
    assert '-Privacidade' in cmd and cmd[cmd.index('-Privacidade')+1]=='public'
    assert '-MaxChamadas' in cmd and cmd[cmd.index('-MaxChamadas')+1]=='0'
    assert '-AgendarEm' not in cmd
    assert '-Refazer' not in cmd


def test_produces_validates_then_uploads_one_public_video(monkeypatch,tmp_path):
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','1',
                                   '--confirmar-publicacao'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    ep=grade.load_queue()[0]
    video=tmp_path/'ready.mp4'
    video.write_bytes(b'mocked-video-no-real-upload')
    monkeypatch.setattr(grade,'video_paths',lambda *_: (video,tmp_path/'cover.jpg'))
    events=[]
    journal={}
    monkeypatch.setattr(grade,'load_journal',lambda:journal)
    monkeypatch.setattr(grade,'save_journal',lambda value:events.append(('journal',value[ep['id']]['status'])))
    monkeypatch.setattr(grade,'ensure_ready',
                        lambda *_a,**_k:events.append(('qa',ep['id'])) or video)
    def fake_invoke(cmd,*,label):
        events.append(('invoke','-Publicar' in cmd))
    monkeypatch.setattr(grade,'invoke',fake_invoke)
    lookup={'count':0}
    def fake_existing(_):
        lookup['count']+=1
        if lookup['count']>=3:
            return {'video_id':'test1234567','privacidade_solicitada':'public',
                    'publicacao_publica_confirmada':True,
                    'thumbnail_status':'pending_processing'}
        return None
    monkeypatch.setattr(grade,'confirmed_existing_upload',fake_existing)
    assert grade.run(args)==0
    assert events[:4]==[
        ('invoke',False),('qa',ep['id']),
        ('journal','upload_iniciado'),('invoke',True)]
    assert journal[ep['id']]['status']=='publicado-publico'
    assert journal[ep['id']]['thumbnail_status']=='pending_processing'


def test_resume_after_ambiguous_upload_never_reuploads(monkeypatch):
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','1',
                                   '--confirmar-publicacao'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    ep=grade.load_queue()[0]
    monkeypatch.setattr(grade,'load_journal',
                        lambda:{ep['id']:{'status':'upload_indeterminado'}})
    events=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:events.append('run'))
    with pytest.raises(RuntimeError,match='Confira o YouTube Studio'):
        grade.run(args)
    assert events==[]


def test_existing_public_receipt_is_reconciled_without_reupload(monkeypatch,tmp_path):
    args=grade.parser().parse_args(['--acao','produzir-publicar',
                                   '--inicio-na-lista','1','--quantidade','1',
                                   '--confirmar-publicacao'])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    ep=grade.load_queue()[0]
    video=tmp_path/'previous.mp4'
    video.write_bytes(b'previous video data')
    monkeypatch.setattr(grade,'video_paths',lambda *_:(video,tmp_path/'cover.jpg'))
    state={ep['id']:{'status':'upload_indeterminado'}}
    monkeypatch.setattr(grade,'load_journal',lambda:state)
    monkeypatch.setattr(grade,'save_journal',lambda *_:None)
    monkeypatch.setattr(grade,'confirmed_existing_upload',lambda _:{
        'video_id':'abc123def45','privacidade_solicitada':'public',
        'publicacao_publica_confirmada':True,'thumbnail_status':'success'})
    uploads=[]
    monkeypatch.setattr(grade,'invoke',lambda *_a,**_k:uploads.append('called'))
    assert grade.run(args)==0
    assert not uploads
    assert state[ep['id']]['video_id']=='abc123def45'
    assert state[ep['id']]['status']=='publicado-publico'


def test_standard_2_5d_is_not_blocked_only_for_missing_character_masks(
    monkeypatch,tmp_path
):
    """Regression: Black Clover was rendered, yet every scene was 2.5D.

    It must publish with honest camera-only QA unless strict mode is enabled.
    """
    import json
    from PIL import Image
    ep=grade.load_queue()[0]
    folder=tmp_path/ep['id']
    folder.mkdir()
    video=folder/(ep['id']+'-master-multicenas-personagens-v3-equilibrado.mp4')
    video.write_bytes(b'pretend-valid-MP4')
    cover=folder/(ep['id']+'-master-capa.jpg')
    Image.effect_noise((720,1280),48).convert('RGB').save(cover,'JPEG',quality=90)
    assert cover.stat().st_size>10000
    qa={'id':ep['id'],'mp4':str(video),'animation_mode':'cinematica',
        'visual_shots':9,'camera_only_scenes':9}
    (folder/'qa-master-multicenas.json').write_text(
        json.dumps(qa),encoding='utf-8')
    monkeypatch.setattr(grade,'video_paths',lambda *_:(video,cover))
    monkeypatch.setattr(grade,'validate_video',lambda *_a,**_k:50.)
    assert grade.ensure_ready(ep,'equilibrado')==video
    with pytest.raises(RuntimeError,match='QA estrito'):
        grade.ensure_ready(ep,'equilibrado',require_character_motion=True)


def test_flat_scene_is_not_excuse_to_ignore_other_safety_checks(
    monkeypatch,tmp_path
):
    import json
    from PIL import Image
    ep=grade.load_queue()[0]
    folder=tmp_path/ep['id']
    folder.mkdir()
    video=folder/(ep['id']+'-master-multicenas-personagens-v3-equilibrado.mp4')
    video.write_bytes(b'fake-MP4')
    cover=folder/(ep['id']+'-master-capa.jpg')
    Image.effect_noise((720,1280),42).convert('RGB').save(cover,'JPEG',quality=90)
    qa={'id':ep['id'],'mp4':str(video),'animation_mode':'cinematica',
        'visual_shots':9,'camera_only_scenes':9}
    qa_path=folder/'qa-master-multicenas.json'
    qa_path.write_text(json.dumps(qa),encoding='utf-8')
    monkeypatch.setattr(grade,'video_paths',lambda *_:(video,cover))
    def invalid_duration(*_a,**_k):
        raise ValueError('duracao ultrapassou 60s')
    monkeypatch.setattr(grade,'validate_video',invalid_duration)
    with pytest.raises(ValueError,match='60s'):
        grade.ensure_ready(ep,'equilibrado')
    monkeypatch.setattr(grade,'validate_video',lambda *_a,**_k:49.)
    qa['id']='outro-episodio'
    qa_path.write_text(json.dumps(qa),encoding='utf-8')
    with pytest.raises(RuntimeError,match='QA nao pertence'):
        grade.ensure_ready(ep,'equilibrado')
    qa['id']=ep['id']
    qa['camera_only_scenes']=10
    qa_path.write_text(json.dumps(qa),encoding='utf-8')
    with pytest.raises(RuntimeError,match='Contagem de cenas'):
        grade.ensure_ready(ep,'equilibrado')


def test_continue_after_failed_generation_publishes_only_next_valid_video(
    monkeypatch,tmp_path
):
    """One failed episode may be skipped, but NEVER uploaded half-finished."""
    args=grade.parser().parse_args([
        '--acao','produzir-publicar','--inicio-na-lista','5',
        '--quantidade','2','--confirmar-publicacao','--continuar-apos-falha'
    ])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    chosen=grade.load_queue()[4:6]
    video=tmp_path/'complete.mp4'
    video.write_bytes(b'test second episode')
    monkeypatch.setattr(grade,'video_paths',
                        lambda ep_id,_:(tmp_path/(ep_id+'.mp4'),tmp_path/'cover.jpg'))
    journal={}
    monkeypatch.setattr(grade,'load_journal',lambda:journal)
    monkeypatch.setattr(grade,'save_journal',lambda _:None)
    events=[]
    def runner(cmd,*,label):
        ep_id=cmd[cmd.index('-Id')+1]
        stage='upload' if '-Publicar' in cmd else 'render'
        events.append((ep_id,stage))
        if ep_id==chosen[0]['id']:
            raise RuntimeError('image editing rejected')
    monkeypatch.setattr(grade,'invoke',runner)
    monkeypatch.setattr(grade,'ensure_ready',lambda *_a,**_k:video)
    sent={'count':0}
    def receipt(_video):
        sent['count']+=1
        return {'video_id':'new12345678','privacidade_solicitada':'public',
                'publicacao_publica_confirmada':True,
                'thumbnail_status':'pending_processing'} if sent['count']>=4 else None
    monkeypatch.setattr(grade,'confirmed_existing_upload',receipt)
    assert grade.run(args)==2  # incomplete batch is disclosed
    assert journal[chosen[0]['id']]['status']=='falha_producao'
    assert journal[chosen[1]['id']]['status']=='publicado-publico'
    assert events==[(chosen[0]['id'],'render'),
                    (chosen[1]['id'],'render'),
                    (chosen[1]['id'],'upload')]


def test_stop_after_three_consecutive_production_failures(monkeypatch):
    args=grade.parser().parse_args([
        '--acao','produzir-publicar','--inicio-na-lista','5',
        '--quantidade','5','--confirmar-publicacao','--continuar-apos-falha'
    ])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    monkeypatch.setattr(grade,'load_journal',lambda:{})
    monkeypatch.setattr(grade,'save_journal',lambda *_a:None)
    monkeypatch.setattr(grade,'confirmed_existing_upload',lambda *_a:None)
    events=[]
    def fail(cmd,*,label):
        events.append(cmd[cmd.index('-Id')+1])
        assert '-Publicar' not in cmd
        raise RuntimeError('proxy offline')
    monkeypatch.setattr(grade,'invoke',fail)
    with pytest.raises(RuntimeError,match='Tres falhas consecutivas'):
        grade.run(args)
    assert len(events)==3


def test_continue_flag_never_skips_uncertain_upload(monkeypatch,tmp_path):
    args=grade.parser().parse_args([
        '--acao','produzir-publicar','--inicio-na-lista','1',
        '--quantidade','2','--confirmar-publicacao','--continuar-apos-falha'
    ])
    monkeypatch.setattr(grade.sys,'platform','win32')
    import publicar_arquivo_otaku as publisher
    monkeypatch.setattr(publisher,'verify_oauth_config',lambda:None)
    ep=grade.load_queue()[0]
    video=tmp_path/'video.mp4'
    video.write_bytes(b'pretend valid')
    monkeypatch.setattr(grade,'video_paths',lambda *_:(video,tmp_path/'cover.jpg'))
    monkeypatch.setattr(grade,'load_journal',lambda:{})
    monkeypatch.setattr(grade,'save_journal',lambda *_a:None)
    monkeypatch.setattr(grade,'confirmed_existing_upload',lambda _v:None)
    monkeypatch.setattr(grade,'ensure_ready',lambda *_a,**_kw:video)
    events=[]
    def upload_fails(cmd,*,label):
        events.append(cmd[cmd.index('-Id')+1])
        if '-Publicar' in cmd:
            raise RuntimeError('remote upload uncertain')
    monkeypatch.setattr(grade,'invoke',upload_fails)
    with pytest.raises(RuntimeError,match='remote upload uncertain'):
        grade.run(args)
    assert events==[ep['id'],ep['id']]
