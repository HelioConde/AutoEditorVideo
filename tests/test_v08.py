import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import radar_editorial as r
import planejador_editorial as p

def test_ideas_valid_and_unique():
    items=r.read_json(r.DATA)['pautas']
    assert len(items)>=12
    assert len({i['id'] for i in items})==len(items)
    assert all(i['status']=='pauta_a_verificar' for i in items)
    assert all('prova_a_verificar' in i for i in items)

def test_scores_are_heurstic_not_real_views():
    item=r.read_json(r.DATA)['pautas'][0]
    result=r.score_idea(item)
    assert 0<=result['nota_editorial']<=100
    assert result['avisos']
    assert 'visualizacoes' not in result

def test_diversity():
    ranked=r.run(output=__import__('tempfile').TemporaryDirectory().name if False else ROOT/'tests'/'_out_tmp',quantity=6)
    assert len(ranked)==6
    assert len({x['obra'] for x in ranked})>=3

def test_unverified_news_flag():
    i=dict(r.read_json(r.DATA)['pautas'][0]);i['titulo_sugerido']='Vazou oficialmente o novo anime!'
    assert any('fonte' in x.lower() or 'noticias' in x.lower() for x in r.risk_flags(i))
    assert r.score_idea(i)['nota_editorial']<r.score_idea(r.read_json(r.DATA)['pautas'][0])['nota_editorial']

def test_studio_data_is_opt_in_and_validated():
    data=r.performance_by_format({'videos':[{'formato':'dilema','escolheram_assistir_pct':65.0,'percentual_medio_assistido':82.0},{'formato':'dilema','escolheram_assistir_pct':99.0,'percentual_medio_assistido':-1}]})
    assert data['dilema']['amostra']==1
    assert data['dilema']['assistiram_vs_deslizaram_pct']==65.0

def test_brief_does_not_claim_verified_facts():
    i=r.read_json(r.DATA)['pautas'][0]
    brief=r.brief_for(i)
    assert 'Ponto que falta conferir' in brief
    assert 'nao e roteiro verificado' in brief

def test_previous_episode_still_passes():
    plan=json.loads((ROOT/'conteudos'/'001-death-note-direcao.json').read_text())
    audit=p.audit_plan(plan)
    assert audit['cenas']==7
    assert not any('tese interpretativa' in a for a in audit['alertas'])
    assert len(audit['benchmark'])>=6

def test_radar_no_network_or_upload_code():
    text=(ROOT/'scripts'/'radar_editorial.py').read_text()
    assert 'requests.' not in text
    assert 'youtube.upload' not in text
    assert 'subprocess' not in text


def test_metadata_for_other_anime_no_death_note_tags():
    import publicar_arquivo_otaku as pub
    meta=pub.text_metadata({'serie':'Hunter x Hunter','titulo':'O medo de Killua','tese_original':'A coragem pode existir com medo.'})
    assert 'Hunter x Hunter' in meta['tags']
    assert 'Death Note' not in meta['tags']
    assert 'A coragem pode existir' in meta['descricao']
    assert 'Hunter x Hunter' in meta['titulo'] or 'Killua' in meta['titulo']

def test_generator_runs_preflight_offline():
    s=(ROOT/'scripts'/'gerar_video_codex.py').read_text()
    assert 'audit_plan(plan)' in s
    assert s.index('audit_plan(plan)') < s.index('check_proxy_accounts(key)', s.index('def main()'))
