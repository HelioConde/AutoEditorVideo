"""Teste offline do fluxo multicenas: sem API, sem upload."""
import base64
import io
import json
from pathlib import Path
import sys
import pytest
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import roteiro_para_storyboard as s
import master_scenes as m
import renderizar_master_remotion as r
import narracao_shorts as t

def png(fg=False):
    im=Image.new('RGBA' if fg else 'RGB',m.SIZE,(0,0,0,0) if fg else '#152347')
    if fg:ImageDraw.Draw(im).rectangle((260,360,750,1100),fill=(190,30,52,255))
    data=io.BytesIO();im.save(data,'PNG');return data.getvalue()

def test_dynamic_storyboard_varies_with_story_and_hold_time():
    ep=s.select_episode('003-death-note-xadrez')
    normal=s.build_storyboard(ep,max_hold=6)
    slow=s.build_storyboard(ep,max_hold=12)
    faster=s.build_storyboard(ep,max_hold=3)
    assert normal['narrative_beats']==3
    assert slow['shot_count']<normal['shot_count']<faster['shot_count']
    assert normal['shot_count']!=7
    assert ' '.join(x['trecho_roteiro'] for x in normal['scenes'])==ep['script']
    assert len({x['prompt'] for x in normal['scenes']})==normal['shot_count']

def test_single_event_can_be_single_image():
    ep={'id':'teste-curto','script':'Light observa o tabuleiro por alguns instantes.',
        'character':'Light','object':'peça','background':'sala'}
    assert s.build_storyboard(ep,max_hold=12)['shot_count']==1

def test_masked_edit_uses_same_input(tmp_path):
    master=tmp_path/'master.png';master.write_bytes(png())
    mask=tmp_path/'mask.png';mask.write_bytes(png(True))
    payloads=[]
    def post(_,**args):
        payloads.append(args['json'])
        return type('R',(),{'ok':True,'json':lambda self:{
            'data':[{'b64_json':base64.b64encode(png(True)).decode()}]}})()
    m.request_edit(master,'test','gpt-image-1.5','test',transparent=True,post=post)
    m.request_edit(master,'erase','gpt-image-1.5','test',transparent=False,mask=mask,post=post)
    assert payloads[0]['images']==payloads[1]['images']
    assert payloads[0]['background']=='transparent'
    assert payloads[1]['background']=='opaque'
    assert payloads[1]['mask']['image_url'].startswith('data:image/png;')

def test_alpha_validation_rejects_opaque():
    with pytest.raises(ValueError,match='alpha'):
        m.validate_image(png(),alpha=True)
    assert m.validate_image(png(True),alpha=True)['opaque_fraction']>.03

def test_caches_master_and_edited_layers_without_network(tmp_path):
    ep=s.build_storyboard(s.select_episode('003-death-note-xadrez'),max_hold=12)
    scene=ep['scenes'][0]
    track=[]
    def gen(prompt,model):track.append('master');return png()
    def edit(path,prompt,model,*,transparent,mask=None):
        track.append('foreground' if transparent else 'background')
        return png(True) if transparent else png()
    one=m.execute_scene(ep,scene,'gpt-image-1.5',directory=tmp_path,generate=gen,edit=edit)
    assert one['status']=='aguardando_revisao_visual'
    assert track==['master','foreground','background']
    assert (tmp_path/'comparacao.jpg').exists()
    m.execute_scene(ep,scene,'gpt-image-1.5',directory=tmp_path,offline=True)
    assert track==['master','foreground','background']

def test_cache_paths_depend_on_model_and_prompt(tmp_path):
    ep=s.build_storyboard(s.select_episode('003-death-note-xadrez'),max_hold=12)
    shot=ep['scenes'][0]
    paths={m.scene_dir(ep,shot,'gpt-image-1.5',tmp_path),
           m.scene_dir(ep,shot,'gpt-image-2',tmp_path),
           m.scene_dir(ep,{**shot,'prompt':shot['prompt']+' revisto'},'gpt-image-1.5',tmp_path)}
    assert len(paths)==3

def test_frame_timeline_is_contiguous():
    ep=s.build_storyboard(s.select_episode('003-death-note-xadrez'),max_hold=6)
    bounds=r.assign_frames(ep['scenes'],30.4)
    assert bounds[0][0]==0
    assert bounds[-1][1]>=912
    assert all(a[1]==b[0] for a,b in zip(bounds,bounds[1:]))
    assert all(end>start for start,end in bounds)

def test_ass_generation_uses_real_boundaries():
    data=t.ass_dialogues([{'start':0,'end':.34,'text':'Light'},
                          {'start':.35,'end':.69,'text':'Yagami'}])
    assert data.count('Dialogue:')==2
    assert t.ass_stamp(1.5)=='0:00:01.50'
    with pytest.raises(ValueError):
        t.ass_dialogues([])

def test_no_upload_or_background_requests_during_planning():
    for name in ('roteiro_para_storyboard.py','master_scenes.py','renderizar_master_remotion.py'):
        content=(ROOT/'scripts'/name).read_text(encoding='utf-8')
        assert 'youtube.videos().insert' not in content
        assert 'publishAt' not in content
