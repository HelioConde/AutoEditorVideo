"""Validacao offline do segundo episodio."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from diretor_visual import load_plan,scene_prompt
from planejador_editorial import audit_plan
from publicar_arquivo_otaku import text_metadata,cover_hook
from gerar_video_codex import output_filename

def test_new_episode_schema():
    ep=load_plan(ROOT/'conteudos'/'002-death-note-memoria-direcao.json')
    assert ep['id']=='002-death-note-memoria'
    assert len(ep['cenas'])==7
    assert len({x['id'] for x in ep['cenas']})==7
    assert ep['roteiro_melhorado'].startswith(ep['gancho_primeiros_segundos'])
    assert audit_plan(ep)['alertas']==[]

def test_new_episode_has_distinct_shots():
    ep=load_plan(ROOT/'conteudos'/'002-death-note-memoria-direcao.json')
    assert len({scene_prompt(x,ep) for x in ep['cenas']})==7

def test_distinct_video_name():
    ep=load_plan(ROOT/'conteudos'/'002-death-note-memoria-direcao.json')
    assert output_filename(ep,False)=='arquivo-otaku-002-death-note-memoria-codex.mp4'
    assert output_filename(ep,True)=='arquivo-otaku-002-death-note-memoria-reuso.mp4'
    assert output_filename({'id':'001-death-note'},False)=='arquivo-otaku-piloto-codex-v07.mp4'

def test_specific_title_and_cover():
    ep=load_plan(ROOT/'conteudos'/'002-death-note-memoria-direcao.json')
    meta=text_metadata(ep)
    assert meta['titulo']==ep['titulo_youtube']
    assert meta['descricao']==ep['descricao_youtube']
    assert cover_hook(ep)==ep['capa_texto']

def test_no_accidental_public_upload():
    text=(ROOT/'autoeditor.ps1').read_text(encoding='utf-8')
    assert "-and -not $ConfirmarPublico" in text
    assert "'private'" in text
    assert "ConfirmarEnvio" in text
    assert "Refazer" in text
