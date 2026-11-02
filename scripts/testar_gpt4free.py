#!/usr/bin/env python3
"""Faz UMA chamada OpenAI-compatible e salva um PNG testado por Pillow.

Nao ha geracao de video nem pagamentos automaticos. Sem fallbacks ou repeticoes
que possam consumir creditos inesperadamente. Nao envia credenciais.
"""
import argparse
import base64
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_PROMPT = (
    'Original anime-inspired noir illustration of a mysterious black notebook on a desk, '
    'blue moonlight through a window, cinematic lighting, hand-drawn look, '
    'vertical composition, no characters from existing franchises, no text, no watermark'
)
MAX_IMAGE_BYTES = 25 * 1024 * 1024


def parse_response(body):
    if not isinstance(body, dict):
        raise ValueError('A API nao retornou um objeto JSON')
    entries = body.get('data')
    if not isinstance(entries, list) or not entries:
        error = body.get('error')
        if isinstance(error, dict):
            raise ValueError(str(error.get('message', error))[:400])
        raise ValueError('A resposta nao trouxe imagens em data[0]')
    item = entries[0]
    if not isinstance(item, dict):
        raise ValueError('data[0] nao e um objeto')
    if isinstance(item.get('b64_json'), str) and item['b64_json']:
        return ('base64', item['b64_json'])
    url = item.get('url')
    if isinstance(url, str) and urlparse(url).scheme in ('http', 'https'):
        return ('url', url)
    raise ValueError('A imagem nao veio como url HTTP(S) nem b64_json')


def request_image(base_url, model, prompt, timeout):
    url = base_url.rstrip('/') + '/images/generations'
    body = json.dumps({'model': model, 'prompt': prompt, 'n': 1, 'size': '512x768'}).encode('utf-8')
    req = Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(1_000_000)
    except HTTPError as exc:
        message = exc.read(1500).decode('utf-8', errors='replace')
        raise RuntimeError(f'HTTP {exc.code} na geracao: {message[:500]}') from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f'Falha de conexao/timeout. O servidor esta aberto? {exc}') from exc
    try:
        payload=json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError('Resposta invalida (nao e JSON).') from exc
    kind, result = parse_response(payload)
    if kind == 'base64':
        image_bytes=base64.b64decode(result,validate=True)
    else:
        # Esta URL veio da resposta do provedor. Um teste local nunca deve enviar dados sigilosos.
        with urlopen(Request(result,headers={'User-Agent':'ArquivoOtaku-G4F-Tester/1.0'}),timeout=90) as image_response:
            image_bytes=image_response.read(MAX_IMAGE_BYTES+1)
    if not image_bytes or len(image_bytes)>MAX_IMAGE_BYTES:
        raise RuntimeError('Imagem ausente ou com mais de 25 MB')
    return image_bytes, kind


def save_png(data, target):
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        size=image.size
        if image.width < 128 or image.height < 128:
            raise RuntimeError('Imagem retornada tem resolucao pequena demais')
        if image.width * image.height > 30_000_000:
            raise RuntimeError('Imagem ultrapassa limite seguro de pixels')
        target.parent.mkdir(parents=True, exist_ok=True)
        image.convert('RGB').save(target, 'PNG')
        return size


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base-url',default='http://127.0.0.1:1337/v1')
    p.add_argument('--model',default='flux')
    p.add_argument('--prompt',default=DEFAULT_PROMPT)
    p.add_argument('--out',default='assets/gerados/teste-gpt4free.png')
    p.add_argument('--timeout',type=int,default=285)
    opts=p.parse_args()
    if urlparse(opts.base_url).hostname not in ('127.0.0.1','localhost','::1'):
        p.error('Neste teste, use somente a API local (127.0.0.1).')
    print('Gerando UMA imagem. Modelo:',opts.model, flush=True)
    try:
        image_bytes,kind=request_image(opts.base_url, opts.model, opts.prompt, opts.timeout)
        target=Path(opts.out).expanduser().resolve()
        size=save_png(image_bytes,target)
        print('SUCESSO! Imagem salva:',target)
        print('Dimensoes:',f'{size[0]}x{size[1]}','| Retorno:',kind)
        return 0
    except Exception as exc:
        print('TESTE FALHOU:',str(exc)[:650])
        print('Pode ser um provedor temporariamente indisponivel ou exigindo autenticacao.')
        return 1

if __name__=='__main__':
    raise SystemExit(main())
