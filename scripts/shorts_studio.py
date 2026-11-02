#!/usr/bin/env python3
"""Browser-based local Shorts control panel, stdlib only; no public network bind."""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import webbrowser

from estado_codex_proxy import connection_status

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
EP_ID=re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
MODELS={'gpt-image-1.5','gpt-image-2'}
ACTIONS={'planejar','cache','validar','offline','reparar','gerar','render',
         'iniciar_proxy','login_proxy'}


def build_command(payload:dict,root:Path=ROOT,python:str|None=None,windows:bool=True)->list[str]:
    """Only allow known actions and validated flags. Never execute arbitrary text."""
    if not isinstance(payload,dict):
        raise ValueError('Requisicao invalida')
    action=payload.get('action')
    if action not in ACTIONS:
        raise ValueError('Acao desconhecida')
    python=python or sys.executable
    episode=payload.get('id','003-death-note-xadrez')
    model=payload.get('model','gpt-image-1.5')
    scene=payload.get('scene',6)
    budget=payload.get('budget',0)
    all_scenes=payload.get('all',False)
    if not isinstance(episode,str) or not EP_ID.fullmatch(episode):
        raise ValueError('ID do episodio invalido')
    if model not in MODELS:
        raise ValueError('Modelo invalido')
    if type(scene) is not int or not 1<=scene<=60:
        raise ValueError('Cena invalida')
    if type(budget) is not int or not 0<=budget<=180:
        raise ValueError('Orcamento invalido')
    if type(all_scenes) is not bool:
        raise ValueError('Selecao de cenas invalida')
    ps=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File']
    if action in ('iniciar_proxy','login_proxy'):
        return ps+[str(root/'testar-codex-proxy.ps1'),
                   '-Acao','instalar' if action=='iniciar_proxy' else 'login']
    base=ps+[str(root/'gerar-shorts-master.ps1'),
             '-Id',episode,'-Modelo',model,'-Cena',str(scene)]
    if all_scenes or action=='render':
        base+=['-TodasCenas']
    if action=='planejar':
        return base+['-SomentePlanejar']
    if action=='cache':
        return base+['-DiagnosticarCache','-MaxChamadas','0']
    if action=='validar':
        return base+['-SomenteValidar','-MaxChamadas','0']
    if action=='offline':
        return base+['-Offline','-MaxChamadas','0']
    if action=='reparar':
        if all_scenes:
            raise ValueError('Reparo de fundo deve ser de uma cena por vez')
        return base+['-RepararFundo','-MaxChamadas','1']
    if action=='render':
        return base+['-Offline','-MaxChamadas','0','-Renderizar']
    return base+['-MaxChamadas',str(budget)]


class Job:
    def __init__(self):
        self.lock=threading.Lock()
        self.lines=deque(maxlen=500)
        self.process=None
        self.busy=False
        self.code=None
        self.action=''
        self.token=secrets.token_urlsafe(28)

    def status(self):
        with self.lock:
            return {'busy':self.busy,'code':self.code,'action':self.action,
                    'logs':list(self.lines)}

    def start(self,command:list[str],action:str):
        with self.lock:
            if self.busy:
                raise ValueError('Uma tarefa ja esta em execucao')
            self.busy=True
            self.code=None
            self.action=action
            self.lines.clear()
            self.lines.append('[STUDIO] '+action+' iniciado')
        threading.Thread(target=self._run,args=(command,),daemon=True).start()

    def _run(self,command):
        status=1
        try:
            kwargs={}
            if os.name=='nt':
                kwargs['creationflags']=getattr(subprocess,'CREATE_NO_WINDOW',0)
            proc=subprocess.Popen(command,cwd=str(ROOT),stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,text=True,bufsize=1,
                                  encoding='utf-8',errors='replace',**kwargs)
            with self.lock:
                self.process=proc
            assert proc.stdout
            for line in proc.stdout:
                with self.lock:
                    self.lines.append(line.rstrip())
            status=proc.wait()
        except (OSError,ValueError) as exc:
            with self.lock:
                self.lines.append('[ERRO] Nao foi possivel executar: '+str(exc))
        finally:
            with self.lock:
                self.code=status
                self.busy=False
                self.process=None
                self.lines.append('[STUDIO] '+('Concluido' if status==0
                                             else 'Falhou (codigo '+str(status)+')'))


class Handler(BaseHTTPRequestHandler):
    job:Job=None

    def log_message(self,*args):
        pass  # No tokens or generated media in server console logs.

    def respond(self,code:int,data:bytes,content_type:str):
        self.send_response(code)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',
                         "default-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def json(self,code:int,obj:dict):
        self.respond(code,json.dumps(obj,ensure_ascii=False).encode('utf-8'),
                     'application/json; charset=utf-8')

    def authorized(self):
        return (self.headers.get('X-Studio-Token')==self.job.token and
                self.headers.get('Host') in ('127.0.0.1:'+str(self.server.server_port),
                                            'localhost:'+str(self.server.server_port)))

    def do_GET(self):
        if self.path=='/':
            page=(HERE/'shorts-studio.html').read_text(encoding='utf-8')
            page=page.replace('__STUDIO_TOKEN__',self.job.token)
            self.respond(200,page.encode('utf-8'),'text/html; charset=utf-8')
        elif self.path=='/studio.js':
            self.respond(200,(HERE/'shorts-studio.js').read_bytes(),
                         'application/javascript; charset=utf-8')
        elif self.path=='/api/state' and self.authorized():
            self.json(200,self.job.status())
        elif self.path=='/api/connection' and self.authorized():
            self.json(200,connection_status())
        else:
            self.json(404,{'error':'Nao encontrado'})

    def do_POST(self):
        if self.path!='/api/run' or not self.authorized():
            self.json(403,{'error':'Acesso negado'})
            return
        if not self.headers.get('Content-Type','').startswith('application/json'):
            self.json(415,{'error':'Use application/json'})
            return
        origin=self.headers.get('Origin')
        expected='http://'+self.headers.get('Host','')
        if origin!=expected:
            self.json(403,{'error':'Origem nao autorizada'})
            return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4096:
                raise ValueError('Requisicao muito grande ou vazia')
            payload=json.loads(self.rfile.read(length))
            command=build_command(payload)
            self.job.start(command,payload['action'])
            self.json(200,{'ok':True})
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc:
            self.json(400,{'error':str(exc)})


def main():
    job=Job()
    handler=type('StudioHandler',(Handler,),{'job':job})
    with ThreadingHTTPServer(('127.0.0.1',0),handler) as server:
        url='http://127.0.0.1:'+str(server.server_port)+'/'
        print('[STUDIO] Interface local: '+url,flush=True)
        print('[STUDIO] Credenciais nunca sao enviadas ao GitHub.',flush=True)
        webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__=='__main__':
    main()
