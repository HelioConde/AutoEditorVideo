#!/usr/bin/env python3
"""Protected read-only BR YouTube OAuth check.

No MP4 is downloaded, no YouTube upload is attempted, no artifacts are
published, and no OAuth client/token payloads are logged.
"""
from __future__ import annotations
import os
import sys

from cloud_youtube_private_5011 import authorized_youtube, UploadBlocked
from youtube_env_policy_guard import check as check_environment, InvalidEnvironment


def main(env:dict[str,str]|None=None, *, verify=None)->int:
    env = env if env is not None else os.environ
    if env.get('GITHUB_REPOSITORY')!='HelioConde/AutoEditorVideo':
        print('[BR OAUTH] WRONG_REPOSITORY')
        return 1
    if env.get('GITHUB_REF')!='refs/heads/main':
        print('[BR OAUTH] MAIN_ONLY')
        return 1
    if env.get('GITHUB_EVENT_NAME')!='push':
        print('[BR OAUTH] READONLY_PUSH_DIAGNOSTIC_ONLY')
        return 1
    if env.get('GITHUB_RUN_ATTEMPT')!='1':
        print('[BR OAUTH] RERUN_NOT_ALLOWED')
        return 1
    if not env.get('YOUTUBE_CLIENT_JSON') or not env.get('YOUTUBE_BR_TOKEN_JSON'):
        print('[BR OAUTH] YOUTUBE_ENVIRONMENT_SECRET_MISSING')
        return 1
    try:
        checker = verify if verify is not None else authorized_youtube
        checker(env,'br')
    except UploadBlocked as exc:
        print('[BR OAUTH] '+str(exc))
        print('[SAFETY] READONLY_NO_MP4_NO_UPLOAD_NO_PROVIDER_BODY')
        return 1
    except Exception:
        print('[BR OAUTH] READONLY_UNCLASSIFIED_ERROR')
        return 1
    print('[BR OAUTH] VERIFIED_BR_CHANNEL_WITH_UPLOAD_AND_READONLY_SCOPES')
    print('[SAFETY] ZERO_YOUTUBE_UPLOADS_NO_TOKENS_PRINTED')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
