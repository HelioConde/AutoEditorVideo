#!/usr/bin/env python3
"""Ponte local OpenAI Images -> AI Horde (servico comunitario gratuito).

Somente 127.0.0.1; sem armazenamento ou exposicao de chaves.
Requer requests (instalado com mpt). Usa parametros modestos para anônimos.
"""
import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

APP_NAME = 'arquivo-otaku-ai-horde'
HORDE_API = 'https://aihorde.net/api/v2'
MAX_WAIT = 240  # MPT sincronico tem read timeout de 300s
MAX_PROMPT = 2500


def fetch_image(prompt, *, api_key=None, model=None, session=None, max_wait=MAX_WAIT):
    session = session or requests.Session()
    api_key = api_key or os.environ.get('AI_HORDE_API_KEY', '0000000000')
    model = model if model is not None else os.environ.get('AI_HORDE_MODEL', '').strip()
    headers = {
        'apikey': api_key,
        'Client-Agent': 'ArquivoOtaku:0.3:github.com/HelioConde',
        'Content-Type': 'application/json',
    }
    payload = {
        'prompt': prompt,
        'params': {'n': 1, 'width': 512, 'height': 768, 'steps': 18},
        'nsfw': False,
        'censor_nsfw': True,
        'allow_downgrade': True,
        'r2': True,
    }
    if model:
        payload['models'] = [model]
    response = session.post(f'{HORDE_API}/generate/async', json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    job_id = response.json().get('id')
    if not job_id or not isinstance(job_id, str):
        raise RuntimeError('AI Horde nao retornou identificador de tarefa')
    deadline = time.monotonic() + max_wait
    completed = False
    try:
        while time.monotonic() < deadline:
            status = session.get(f'{HORDE_API}/generate/check/{job_id}', headers=headers, timeout=20)
            status.raise_for_status()
            result = status.json()
            if result.get('faulted'):
                raise RuntimeError('AI Horde informou falha na geracao')
            if result.get('done'):
                completed = True
                break
            time.sleep(5)
        if not completed:
            raise TimeoutError('Fila gratuita excedeu 4 minutos; tente depois ou escolha outro modelo')
        result = session.get(f'{HORDE_API}/generate/status/{job_id}', headers=headers, timeout=30)
        result.raise_for_status()
        generations = result.json().get('generations') or []
        if not generations or not generations[0].get('img'):
            raise RuntimeError('AI Horde concluiu, mas nao retornou URL de imagem')
        url = generations[0]['img']
        if not url.startswith('https://'):
            raise RuntimeError('Link de imagem inesperado no retorno da AI Horde')
        # Devolvemos a URL no formato OpenAI; MPT faz download e valida imagem.
        return url
    finally:
        if not completed:
            try:
                session.delete(f'{HORDE_API}/generate/status/{job_id}', headers=headers, timeout=8)
            except requests.RequestException:
                pass


class Handler(BaseHTTPRequestHandler):
    server_version = 'ArquivoOtakuHorde/0.3'

    def send_json(self, code, body):
        raw = json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/health':
            return self.send_json(200, {'app': APP_NAME, 'status': 'ok', 'provider': 'AI Horde'})
        return self.send_json(404, {'error': {'message': 'Nao encontrado'}})

    def do_POST(self):
        if self.path != '/v1/images/generations':
            return self.send_json(404, {'error': {'message': 'Nao encontrado'}})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 20000:
                return self.send_json(413, {'error': {'message': 'Requisicao muito grande ou vazia'}})
            data = json.loads(self.rfile.read(length))
            prompt = data.get('prompt', '')
            if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > MAX_PROMPT:
                return self.send_json(400, {'error': {'message': 'Prompt ausente ou muito longo'}})
            if data.get('n', 1) != 1:
                return self.send_json(400, {'error': {'message': 'Esta ponte permite uma imagem por vez'}})
            url = fetch_image(prompt)
            return self.send_json(200, {'created': int(time.time()), 'data': [{'url': url}]})
        except (requests.RequestException, RuntimeError, TimeoutError, ValueError) as exc:
            # 422 nao aciona repeticao automatica no MPT e evita fila duplicada.
            return self.send_json(422, {'error': {'message': str(exc)[:400]}})
        except Exception:
            return self.send_json(500, {'error': {'message': 'Falha inesperada na ponte'}})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=7861)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'{APP_NAME} aberto em http://127.0.0.1:{args.port}/health', flush=True)
    print('Gratuito comunitario; fila, modelos e limites variaveis.', flush=True)
    httpd.serve_forever()


if __name__ == '__main__':
    main()
