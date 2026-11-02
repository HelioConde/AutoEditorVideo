"""Local HTTP smoke test: UI assets, status and same-origin request protection."""
from __future__ import annotations
from http.server import ThreadingHTTPServer
from pathlib import Path
import json
import re
import sys
import threading
from urllib import request, error

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from shorts_studio import Handler, Job


def test_local_studio_serves_ui_and_rejects_unsafe_requests():
    job=Job()
    handler=type('TestStudioHandler',(Handler,),{'job':job})
    server=ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    origin='http://127.0.0.1:'+str(server.server_port)
    try:
        with request.urlopen(origin+'/',timeout=3) as res:
            page=res.read().decode('utf-8')
            assert 'Shorts Studio' in page
            assert 'style-src' in res.headers['Content-Security-Policy']
        token=re.search(r'<meta name="studio-token" content="([^"]+)">',page).group(1)
        with request.urlopen(origin+'/studio.js',timeout=3) as res:
            script=res.read().decode('utf-8')
            assert 'data-action' in script
        with request.urlopen(request.Request(origin+'/api/state',
                          headers={'X-Studio-Token':token}),timeout=3) as res:
            assert json.load(res)['busy'] is False
        body=json.dumps({'action':'gerar','id':'003-death-note-xadrez',
                         'scene':6,'model':'gpt-image-1.5','budget':1,'all':False}).encode()
        req=request.Request(origin+'/api/run',data=body,method='POST',
                            headers={'Content-Type':'application/json',
                                     'X-Studio-Token':token,
                                     'Origin':'http://evil.example'})
        try:
            request.urlopen(req,timeout=3)
            assert False,'Cross-origin POST should have been rejected'
        except error.HTTPError as exc:
            assert exc.code==403
        assert job.status()['busy'] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
