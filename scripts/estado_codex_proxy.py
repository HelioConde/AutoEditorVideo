#!/usr/bin/env python3
"""Read-only status of the local third-party Codex Proxy. Never print credentials."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = 'http://127.0.0.1:8080'


def credentials_file(root: Path = ROOT) -> Path | None:
    candidates = [
        Path(os.environ['ARQUIVO_OTAKU_PROXY_ENV'])
        if os.environ.get('ARQUIVO_OTAKU_PROXY_ENV') else None,
        root / 'chatgpt-codex-proxy' / '.env',
        root.parent / 'arquivo-otaku-kit' / 'chatgpt-codex-proxy' / '.env',
    ]
    return next((p for p in candidates if p and p.is_file()), None)


def read_local_key(path: Path | None) -> str | None:
    if path is None:
        return None
    match = re.search(r'(?m)^PROXY_API_KEY\s*=\s*(.*?)\s*$',
                      path.read_text(encoding='utf-8-sig'))
    if not match:
        return None
    key = match.group(1).strip().strip("\"'")
    return key if len(key) >= 15 and not key.startswith('change-me') else None


def connection_status(root: Path = ROOT, *, opener=None) -> dict:
    """Separate server reachability, authentication and eligible accounts.

    No image calls, no account switching, no token exposure, no automatic login.
    """
    opener = opener or request.urlopen
    result = {'state': 'offline', 'server': False, 'authenticated': False,
              'accounts': 0, 'eligible': 0,
              'message': 'Proxy local indisponivel. Inicie o Docker/Proxy.'}
    try:
        with opener(request.Request(BASE_URL + '/health/live'), timeout=3) as response:
            if response.status != 200:
                result['message'] = 'Proxy respondeu com HTTP '+str(response.status)
                return result
    except (OSError, error.URLError, TimeoutError) as exc:
        return result
    result['server'] = True
    key = read_local_key(credentials_file(root))
    if not key:
        result.update(state='sem_chave',
                      message='Proxy ligado, mas .env/PROXY_API_KEY local nao foi encontrado.')
        return result
    req = request.Request(BASE_URL + '/admin/accounts',
                          headers={'Authorization': 'Bearer '+key})
    try:
        with opener(req, timeout=6) as response:
            if response.status != 200:
                result.update(state='erro_autenticacao',
                              message='Nao foi possivel consultar contas no proxy.')
                return result
            data = json.load(response)
    except error.HTTPError as exc:
        result.update(state='erro_autenticacao',
                      message='A chave foi recusada pelo proxy (HTTP '+str(exc.code)+').')
        return result
    except (OSError, error.URLError, TimeoutError, ValueError, TypeError):
        result.update(state='erro_contas',
                      message='Proxy ligado, mas a consulta autenticada de contas falhou.')
        return result
    accounts = data.get('accounts', []) if isinstance(data, dict) else []
    accounts = accounts if isinstance(accounts, list) else []
    eligible = sum(1 for a in accounts
                   if isinstance(a, dict) and a.get('eligible_now') is True)
    result.update(authenticated=True, accounts=len(accounts), eligible=eligible)
    if eligible:
        result.update(state='conectado', message='Proxy conectado; ha conta elegivel.')
    else:
        result.update(state='sem_conta_elegivel',
                      message='Proxy conectado, mas nenhuma conta elegivel agora. '
                              'Nao contorne limites de uso.')
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Verifica somente a conexao local do Codex Proxy')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    status = connection_status()
    if args.json:
        print(json.dumps(status, ensure_ascii=False))
    else:
        print('[CODEX] '+status['state']+' | '+status['message'])
        print('[CODEX] Servidor: '+('online' if status['server'] else 'offline')+
              ' | autenticado: '+('sim' if status['authenticated'] else 'nao')+
              ' | contas elegiveis: '+str(status['eligible']))
    return 0  # diagnostic state is not a task execution failure


if __name__ == '__main__':
    raise SystemExit(main())
