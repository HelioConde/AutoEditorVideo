#!/usr/bin/env python3
"""Preparador de um piloto editorial para MoneyPrinterTurbo.

Gera apenas cartelas originais. A renderização final é delegada à CLI OFICIAL
mpt (com vozes pt-BR e materiais locais). Não baixa episódios/animes.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'conteudos'
ASSETS = ROOT / 'assets' / 'gerados'


def load_ep(code):
    if not re.fullmatch(r'[a-z0-9-]+', code):
        raise ValueError('Identificador inválido do episódio')
    path = CONTENT / f'{code}.json'
    if not path.is_file():
        raise FileNotFoundError(f'Episódio não encontrado: {path}')
    data = json.loads(path.read_text(encoding='utf-8'))
    assert isinstance(data['roteiro'], str) and len(data['roteiro']) > 50
    assert len(data['cenas']) > 0
    return data


def get_font(size, bold=True):
    from PIL import ImageFont
    fonts = [
        # Windows
        r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\seguisb.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf',
        # Linux
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/lato/Lato-Heavy.ttf' if bold else '/usr/share/fonts/truetype/lato/Lato-Regular.ttf'
    ]
    for font in fonts:
        try:
            return ImageFont.truetype(font, size)
        except (OSError, ValueError):
            pass
    return ImageFont.load_default()


def render_card(ep, index, scene, output):
    from PIL import Image, ImageDraw
    W, H = 1080, 1920
    im = Image.new('RGB', (W,H), '#10111c')
    draw = ImageDraw.Draw(im)
    # Simple original graphic language: frame, editorial grid, timeline.
    draw.rectangle((0,0,W,28), fill='#7857ff')
    draw.rectangle((0,H-27,W,H), fill='#4be0ea')
    for j in range(12):
        x = 120 + 82*j
        draw.line((x,240,x+220,1580), fill='#1c1d30', width=3)
    for k in range(6):
        cx,cy=540+(k%2)*150,780+(k//2)*90
        radius=175+95*k
        draw.arc((cx-radius,cy-radius,cx+radius,cy+radius), 190,310, fill='#262540', width=6)
    draw.rectangle((60,90,1020,1830), outline='#363350', width=3)
    draw.rounded_rectangle((92,136,435,210),radius=14,fill='#26243b')
    draw.text((116,158), 'ARQUIVO OTAKU  /  SHORTS',font=get_font(26),fill='#4be0ea')
    draw.text((104,280),f'ARQUIVO  {index+1:02d} / {len(ep["cenas"]):02d}',font=get_font(38),fill='#8d8bad')
    words=scene['cartela'].split('\n')
    lines=[]
    for item in words:
        if len(item)>19:
            # max-size friendly wrapping with complete words
            cur=''
            for w in item.split():
                probe=(cur+' '+w).strip()
                if len(probe)>17 and cur:
                    lines.append(cur)
                    cur=w
                else:
                    cur=probe
            if cur:lines.append(cur)
        else:
            lines.append(item)
    largest=max(len(x) for x in lines)
    f=get_font(96 if largest<=15 else 80 if largest<=19 else 68)
    line_h=f.size+38 if hasattr(f,'size') else 100
    y=int(H/2-len(lines)*line_h/2)
    for idx,line in enumerate(lines):
        box=draw.textbbox((0,0),line,font=f)
        text_w=box[2]-box[0]
        while text_w>900 and getattr(f,'size',36)>42:
            f=get_font(f.size-4)
            box=draw.textbbox((0,0),line,font=f)
            text_w=box[2]-box[0]
        draw.text(((W-text_w)//2,y+idx*line_h),line,font=f,fill='#f8f9ff',stroke_width=1,stroke_fill='#f8f9ff')
    draw.rounded_rectangle((104,1500,974,1510),radius=4,fill='#3e3d54')
    draw.rounded_rectangle((104,1500,104+int(870*(index+1)/len(ep['cenas'])),1510),radius=4,fill='#7857ff')
    draw.text((104,1560),ep['serie'].upper(),font=get_font(36),fill='#4be0ea')
    draw.text((104,1660),'ANÁLISE ORIGINAL • PT-BR',font=get_font(30,bold=False),fill='#aaa9c0')
    im.save(output,quality=92)


def main():
    parser=argparse.ArgumentParser(description='Prepara piloto autoral para MoneyPrinterTurbo')
    parser.add_argument('--episodio',default='001-death-note')
    parser.add_argument('--renderizar',action='store_true',help='Executa o pacote oficial mpt cli após preparar cartelas')
    parser.add_argument('--imagens', choices=['cartelas','ia-gratis','gpt4free'], default='cartelas', help='Fonte de imagem do piloto')
    a=parser.parse_args()
    try:
        ep=load_ep(a.episodio)
        out_dir=ASSETS/a.episodio
        out_dir.mkdir(parents=True,exist_ok=True)
        materials=[]
        for i,cena in enumerate(ep['cenas']):
            p=out_dir/f'cena-{i+1:02d}.png'
            render_card(ep,i,cena,p)
            materials.append(p)
        manifest={
            'episodio':a.episodio,
            'material':[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'titular':'Arquivo Otaku (arte editorial original)',
                'permissao':'criado localmente para este projeto','fonte':'scripts/piloto.py'} for p in materials],
            'revisao_humana':'PENDENTE',
            'observacao':'Cartelas originais. Nenhuma cena ou arte oficial de anime é incluída.'
        }
        (out_dir/'licencas.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        (out_dir/'roteiro.txt').write_text(ep['roteiro']+'\n',encoding='utf-8')
        print('PILOTO PREPARADO:',ep['titulo'])
        print('ROTEIRO:',out_dir/'roteiro.txt')
        print('MATERIAIS ORIGINAIS:',len(materials))
        print('REVISAR:',out_dir/'licencas.json')
        if not a.renderizar:
            print('Para renderizar com o MoneyPrinterTurbo: scripts/rodar-piloto.ps1 -Modo renderizar')
            return 0
        # Chamada fiel à CLI mpt atual. Sem downloads de anime e sem trilha.
        scripts_bin=Path(sys.executable).parent
        mpt=scripts_bin/('mpt.exe' if os.name=='nt' else 'mpt')
        if not mpt.is_file():
            raise RuntimeError('mpt não foi instalado nesse ambiente; instale o pacote oficial: python -m pip install mpt')
        if a.imagens in ('ia-gratis','gpt4free'):
            import requests
            if a.imagens == 'ia-gratis':
                try:
                    health = requests.get('http://127.0.0.1:7861/health', timeout=3).json()
                    if health.get('app') != 'arquivo-otaku-ai-horde':
                        raise RuntimeError('A porta 7861 nao e a ponte do Arquivo Otaku')
                except (requests.RequestException, ValueError) as exc:
                    raise RuntimeError('Ponte AI Horde indisponivel; abra scripts\\iniciar-api-gratis.ps1 em outro PowerShell') from exc
            else:
                try:
                    response = requests.get('http://127.0.0.1:1337/openapi.json',timeout=7)
                    response.raise_for_status()
                    paths = response.json().get('paths',{})
                    if '/v1/images/generations' not in paths:
                        raise RuntimeError('A porta 1337 nao corresponde a API GPT4Free compatível')
                except (requests.RequestException, ValueError) as exc:
                    raise RuntimeError('GPT4Free indisponivel. Mantenha .\\scripts\\iniciar-gpt4free.ps1 aberto.') from exc
            os.environ['MPT_HOME'] = str(ROOT / '.mpt-runtime')
            if not (ROOT / '.mpt-runtime' / 'config.toml').is_file():
                raise RuntimeError('Configure a fonte primeiro: scripts\\configurar-gpt4free.ps1 ou scripts\\configurar-gratis.ps1')
        cmd=[str(mpt),'cli',
            '--video-script',ep['roteiro'],
            '--video-subject',ep['titulo'],
            '--video-source',('openai_image' if a.imagens in ('ia-gratis','gpt4free') else 'local'),
            '--video-aspect','9:16',
            '--video-clip-duration','6',
            '--voice-name','pt-BR-AntonioNeural',
            '--voice-rate','1.05',
            '--bgm-type','none',
            '--subtitle-enabled',
            '--subtitle-position','bottom',
            '--subtitle-display-mode','word_by_word',
            '--text-fore-color','#FFFFFF',
            '--stroke-color','#000000',
            '--stroke-width','2',
            '--font-size','56',
            '--video-count','1',
            '--stop-at','video']
        if a.imagens in ('ia-gratis','gpt4free'):
            prompts=[c['prompt_imagem'] for c in ep['cenas'] if c.get('prompt_imagem')]
            if not prompts:
                raise RuntimeError('Episodio sem prompt_imagem nas cenas')
            if any(',' in p for p in prompts):
                raise ValueError('Nao use virgula dentro dos prompts: CLI separa termos por virgula')
            cmd.extend(['--video-terms', ','.join(prompts), '--match-materials-to-script'])
            print('Modo IA:', 'GPT4Free' if a.imagens == 'gpt4free' else 'AI Horde', '| via openai_image; sujeito a disponibilidade.',flush=True)
        else:
            cmd.extend(['--video-materials',','.join(map(str,materials))])
        print('Executando MoneyPrinterTurbo com narração PT-BR e sem música...',flush=True)
        return subprocess.run(cmd,cwd=str(ROOT),check=False).returncode
    except (ValueError,KeyError,FileNotFoundError,ImportError,RuntimeError) as exc:
        print('ERRO:',exc,file=sys.stderr)
        return 1


if __name__=='__main__':
    sys.exit(main())
