"""Tests locais da interface OpenAI Images do kit (nao acessam g4f real)."""
import base64
import io
import json
import importlib.util
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from PIL import Image

FILE = Path(__file__).parents[1]/'scripts'/'testar_gpt4free.py'
spec = importlib.util.spec_from_file_location('smoke', FILE)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def make_png():
    b=io.BytesIO()
    Image.new('RGB',(512,768),'#202030').save(b,'PNG')
    return b.getvalue()


def test_response_b64():
    png=make_png()
    kind, data=smoke.parse_response({'data':[{'b64_json':base64.b64encode(png).decode('ascii')}]})
    assert kind == 'base64'
    assert base64.b64decode(data)==png


def test_parse_url_and_errors():
    assert smoke.parse_response({'data':[{'url':'http://127.0.0.1:1337/media/test.png'}]}) == ('url','http://127.0.0.1:1337/media/test.png')
    with pytest.raises(ValueError):
        smoke.parse_response({'error':{'message':'no free provider'}})
    with pytest.raises(ValueError):
        smoke.parse_response({'data':[{'url':'/media/test.png'}]})


def test_one_image_request_and_save(tmp_path):
    png=make_png()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == '/v1/images/generations'
            received=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert received['model']=='flux'
            assert received['n']==1
            payload=json.dumps({'data':[{'url':f'http://127.0.0.1:{self.server.server_port}/image.png'}]}).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.end_headers()
            self.wfile.write(payload)
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type','image/png')
            self.end_headers()
            self.wfile.write(png)
        def log_message(self,*args):
            pass
    server=ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thr=threading.Thread(target=server.serve_forever,daemon=True)
    thr.start()
    try:
        raw,mode=smoke.request_image(f'http://127.0.0.1:{server.server_port}/v1','flux','test prompt',5)
        assert mode=='url'
        dest=tmp_path/'sample.png'
        assert smoke.save_png(raw,dest)==(512,768)
        assert dest.exists()
    finally:
        server.shutdown()
        server.server_close()


def test_piloto_uses_openai_image_for_g4f():
    s=(Path(__file__).parents[1]/'scripts'/'piloto.py').read_text(encoding='utf-8')
    assert "('openai_image' if a.imagens in ('ia-gratis','gpt4free') else 'local')" in s
