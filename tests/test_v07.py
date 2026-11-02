import json
import sys
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import editor_shorts as e
import gerar_video_codex as g
import diretor_visual as d
import planejador_editorial as p


def test_shots_counts_and_real_crops(tmp_path):
    sources=[]
    for i in range(7):
        im=Image.new('RGB',(1024,1536),(30+i*12,55+i*8,80+i*7))
        for x in range(100,600):
            for y in range(100,500,25):im.putpixel((x,y),(240,200,110))
        f=tmp_path/f'{i}.jpg';im.save(f);sources.append(f)
    shots=e.create_shot_sequence(sources,tmp_path/'out')
    assert len(shots)==14
    assert all(f.is_file() for f in shots)
    assert len(set(str(x) for x in shots))==14
    assert shots[0].read_bytes()!=shots[1].read_bytes()
    data=json.loads((tmp_path/'out'/'plano-cortes-v07.json').read_text())
    assert len(data['shots'])==14
    assert data['duration_per_cut_s']==3


def test_new_cli_defaults_for_short():
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    args=g.mpt_args(Path('/tmp/mpt'),plan,[g.MATERIAL_DIR/'x.jpg'])
    assert args[args.index('--video-clip-duration')+1]=='3'
    assert args[args.index('--font-size')+1]=='83'
    assert args[args.index('--subtitle-display-mode')+1]=='word_by_word'


def test_editorial_check_and_no_fake_new_claims():
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    result=p.audit_plan(plan)
    assert result['palavras']>70
    assert result['cenas']==7
    assert len(result['ganchos_para_testar'])==3
    assert 'Gancho do plano diferente' not in result['alertas']
    assert all('vazou' not in x.lower() for x in result['ganchos_para_testar'])


def test_explicit_publish_separation():
    body=(ROOT/'gerar-video-codex.ps1').read_text()
    assert 'publicar-youtube.ps1' not in body
    assert 'arquivo-otaku-piloto-v07-reuso.mp4' in body


def test_audio_no_ffmpeg_preserves_video(monkeypatch,tmp_path):
    import finalizador_audio as a
    video=tmp_path/'video.mp4';video.write_bytes(b'FAKE-VIDEO')
    monkeypatch.setattr(a,'ffmpeg_executable',lambda:None)
    result=a.normalize_video_audio(video)
    assert result['status']=='skipped'
    assert video.read_bytes()==b'FAKE-VIDEO'


def test_new_episode_metadata_title_is_dynamic():
    import publicar_arquivo_otaku as pub
    plan=d.load_plan(ROOT/'conteudos'/'001-death-note-direcao.json')
    meta=pub.text_metadata(plan)
    assert 'O segredo de Death Note' in meta['titulo']
    assert len(meta['titulo'])<=100


def test_locked_old_partial_filename_no_longer_blocks(tmp_path):
    source = tmp_path / 'source.jpg'
    Image.new('RGB', (800, 1200), (190, 40, 55)).save(source)
    destination = tmp_path / 'cuts'
    destination.mkdir()
    original = e.create_shot_sequence([source] * 3, destination)
    first = original[0]
    first.unlink()
    first.with_suffix('.partial.jpg').mkdir()
    recovered = e.create_shot_sequence([source] * 3, destination)
    assert recovered[0].is_file()
    with Image.open(recovered[0]) as im:
        assert im.size == (800, 1200)
    assert not list(destination.glob('*.tmp.jpg'))


def test_cuts_are_cached_and_manifest_restored(tmp_path):
    source = tmp_path / 'source.jpg'
    Image.new('RGB', (800, 1200), (100, 140, 80)).save(source)
    dest = tmp_path / 'cuts'
    first = e.create_shot_sequence([source] * 3, dest)
    before = [f.stat().st_mtime_ns for f in first]
    second = e.create_shot_sequence([source] * 3, dest)
    assert first == second
    assert [f.stat().st_mtime_ns for f in second] == before


def test_powershell_script_can_handle_different_episode_ids():
    body=(ROOT/'gerar-video-codex.ps1').read_text(encoding='utf-8')
    assert body.count('} finally { Pop-Location }') == 1
    assert body.count("$target=Join-Path") == 1
    assert 'if($Plano)' in body
