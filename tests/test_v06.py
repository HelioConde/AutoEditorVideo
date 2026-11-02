from pathlib import Path
import sys
import json
import io
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import diretor_visual as d
import gerar_video_codex as g
import publicar_arquivo_otaku as p


def test_plan_and_unique_visual_types():
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    assert len(plan['cenas']) == 7
    assert len({x['tipo'] for x in plan['cenas']})>=5
    assert 'Light' in plan['cenas'][0]['descricao'] and 'L Lawliet' in plan['cenas'][0]['descricao']
    assert 'key light' in d.scene_prompt(plan['cenas'][0],plan)


def test_luminance_correction_preserves_noir():
    image=Image.new('RGB',(1024,1536),(21,24,30))
    improved,qa=d.quality_adjust_image(image)
    assert qa['gamma']<1
    assert qa['depois']['mediana']>qa['antes']['mediana']
    assert qa['depois']['mediana']<130
    assert improved.size==(1024,1536)


def test_duplicate_detection():
    rows=[{'id':'1','assinatura':'0'*16},{'id':'2','assinatura':'0'*16},{'id':'3','assinatura':'f'*16}]
    result=d.duplicate_warnings(rows)
    assert len(result)==1 and '1 e 2' in result[0]


def test_generate_cached_images_one_api_per_scene(tmp_path):
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    count=[]
    test=Image.new('RGB',(1024,1536),(28,36,46))
    stream=io.BytesIO();test.save(stream,'PNG')
    def fetch(prompt,model,key):
        count.append(prompt)
        return stream.getvalue()
    mat=tmp_path/'materials';qa=tmp_path/'qa.json'
    a=g.stage_images(plan,'gpt-image-1.5','test-key',fetcher=fetch,material_dir=mat,report=qa)
    b=g.stage_images(plan,'gpt-image-1.5','test-key',fetcher=fetch,material_dir=mat,report=qa)
    assert len(a)==len(b)==7 and len(count)==7
    assert json.loads(qa.read_text())['status']=='concluido'
    assert Image.open(a[0]).size==(1024,1536)


def test_cli_args_respect_source_and_sequence(monkeypatch,tmp_path):
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    monkeypatch.setattr(g,'MATERIAL_DIR',tmp_path)
    files=[tmp_path/f'{i}.jpg' for i in range(7)]
    args=g.mpt_args(tmp_path/'mpt.exe',plan,files)
    assert args[args.index('--video-source')+1]=='local'
    assert args[args.index('--video-concat-mode')+1]=='sequential'
    assert args[args.index('--video-materials')+1].count(',')==6
    assert '--video-script' in args and plan['roteiro_melhorado'] in args


def test_covers_safe_and_readable(tmp_path):
    src=tmp_path/'sample.png'
    Image.new('RGB',(1024,1536),(55,72,92)).save(src)
    for portrait,w,h in ((True,1080,1920),(False,1280,720)):
        dst=tmp_path/('shorts.jpg' if portrait else 'youtube.jpg')
        p.cover_image(src,dst,w,h,'SEM LUTAS?','DEATH NOTE',portrait)
        with Image.open(dst) as im:
            assert im.size==(w,h)
        assert dst.stat().st_size>9000


def test_cover_hook_for_other_anime():
    assert p.cover_hook({'serie':'Death Note'})=='SEM LUTAS?'
    assert 'HUNTER' in p.cover_hook({'serie':'Hunter x Hunter','titulo':'O mistério de Hunter x Hunter'})
    assert 'Light Yagami' not in p.text_metadata({'serie':'Hunter x Hunter','titulo':'Analisando Hunter x Hunter'})['descricao']


def test_upload_not_automated_in_video_script():
    code=(ROOT/'scripts'/'gerar_video_codex.py').read_text(encoding='utf-8')
    assert 'youtube.videos()' not in code
    assert 'arquivo-otaku-piloto-codex-v07.mp4' in code
    assert 'arquivo-otaku-piloto-codex.mp4' not in code


def test_publish_public_default_in_explicit_upload_only():
    src=(ROOT/'publicar-youtube.ps1').read_text(encoding='utf-8')
    assert "$Privacidade='public'" in src
    assert "$Etapa='preparar'" in src
    assert '--video' in src


def test_state_per_video_and_oauth_preflight():
    src=(ROOT/'scripts'/'publicar_arquivo_otaku.py').read_text(encoding='utf-8')
    assert 'estado-upload-' in src
    assert 'verify_oauth_config()  # Before calling AI services' in src


def test_reuse_images_without_request_to_proxy(monkeypatch,tmp_path):
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    image_folder=tmp_path/'imagens'
    image_folder.mkdir()
    for i,filename in enumerate(['openai-image-3ac809aae11b.png',
        'openai-image-a64df63fa0f8.png','openai-image-6ca00534820a.png',
        'openai-image-4e3cf553947c.png','openai-image-88ec8c8a025d.png']):
        Image.new('RGB',(1024,1536),(38+i*12,48+i*8,70+i*4)).save(image_folder/filename)
    def no_proxy(*args,**kwargs):
        raise AssertionError('Nunca acessar o Codex Proxy no modo de reutilizacao')
    monkeypatch.setattr(g,'check_proxy_accounts',no_proxy)
    monkeypatch.setattr(g,'request_image',no_proxy)
    material_dir=tmp_path/'mpt'/'storage'/'local_videos'
    report=tmp_path/'qa.json'
    first=g.stage_existing_images(plan,'gpt-image-1.5',image_folder,material_dir,report)
    again=g.stage_existing_images(plan,'gpt-image-1.5',image_folder,material_dir,report)
    assert len(first)==7 and first==again
    assert report.is_file()
    body=json.loads(report.read_text())
    assert body['modo']=='reutilizacao sem IA'
    assert all(f.is_file() for f in first)
    assert [f.name for f in first]==[f.name for f in again]
    assert len(body['alertas'])>=1 # first/last intentionally reuse chess shot


def test_reuse_fails_when_not_enough_images(tmp_path):
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    folder=tmp_path/'empty'
    folder.mkdir()
    import pytest
    with pytest.raises(RuntimeError,match='menos de 3'):
        g.stage_existing_images(plan,'gpt-image-1.5',folder,tmp_path/'output',tmp_path/'qa.json')


def test_powershell_exposes_offline_mode():
    s=(ROOT/'gerar-video-codex.ps1').read_text(encoding='utf-8')
    assert '[switch]$ReutilizarImagens' in s
    assert "'--reutilizar-imagens'" in s
