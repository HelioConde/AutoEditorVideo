#!/usr/bin/env python3
"""Kwai Brasil GitHub OAuth connection readiness. Offline and read-only.

No GitHub secret writes, OAuth exchange, login, browser automation, publishing
or private file reading. This preflight intentionally fails closed for any
attempt to mark Kwai Brazil as officially API-verified without a later code
review. Kuaishou China OAuth docs alone do not establish Kwai Brazil support.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"config"/"kwai-br-github-oauth-readiness.json"
REPO="HelioConde/AutoEditorVideo"
ENVIRONMENT="kwai-private-publish"
SECRET_NAMES=("KWAI_APP_ID","KWAI_APP_SECRET","KWAI_OAUTH_TOKEN_JSON")
SCOPE="user_video_publish"

class KwaiReadinessBlocked(ValueError):
    pass

def validate_plan()->dict:
    d=json.loads(PATH.read_text(encoding="utf-8"))
    if (
        d.get("schema")!="autoeditorvideo/kwai-br-github-oauth-readiness/v1"
        or d.get("platform")!="kwai_brazil"
        or d.get("goal")!="store_official_oauth_in_github_environment_like_youtube"
        or d.get("oauth_supported_by_kuaishou_domestic_docs") is not True
        or any(d.get(k) is not False for k in (
            "kwai_brazil_content_publishing_api_verified",
            "kwai_brazil_app_approval_received",
            "oauth_authorization_completed",
            "github_access_configured",
            "publication_enabled",
            "token_refresh_automatic_enabled"))
        or d.get("github_repository")!=REPO
        or d.get("github_environment")!=ENVIRONMENT
        or d.get("branch_allowlist")!=["main"]
        or d.get("planned_secret_names")!=list(SECRET_NAMES)
        or d.get("scopes_required")!=[SCOPE]
        or d.get("credential_source")!="official_oauth_only_not_mobile_application_password"
        or d.get("validation_status")!="blocked_until_official_kwai_brazil_developer_approval"
        or any(d.get(k) is not True for k in (
            "owner_consent_required","forbid_passwords",
            "forbid_sms_and_two_factor_codes",
            "forbid_android_cookies_or_sessions",
            "forbid_android_emulator_account_import",
            "forbid_live_publishing",
            "never_touch_youtube_secrets",
            "require_refresh_rotation_atomic_protection",
            "no_upload_without_real_account_id_and_receipt"))
    ):
        raise KwaiReadinessBlocked("OFFICIAL_BRAZIL_API_CREDENTIAL_APPROVAL_REQUIRED")
    return d

def protected_main_only(environment:dict,policies:dict)->None:
    """Read-only proof of exact branch protection before FUTURE OAuth storage."""
    if not isinstance(environment,dict) or environment.get("name")!=ENVIRONMENT:
        raise KwaiReadinessBlocked("KWAI_ENVIRONMENT_NOT_FOUND")
    setup=environment.get("deployment_branch_policy") or {}
    if setup.get("custom_branch_policies") is not True or setup.get("protected_branches") is not False:
        raise KwaiReadinessBlocked("KWAI_ENVIRONMENT_NOT_RESTRICTED_TO_CUSTOM_BRANCHES")
    rows=policies.get("branch_policies") if isinstance(policies,dict) else None
    if (not isinstance(rows,list) or policies.get("total_count")!=1
            or len(rows)!=1 or rows[0].get("name")!="main"
            or rows[0].get("type","branch")!="branch"):
        raise KwaiReadinessBlocked("KWAI_ENVIRONMENT_MUST_ALLOW_MAIN_ONLY")

def main(argv=None)->int:
    p=argparse.ArgumentParser()
    p.add_argument("--action",choices=("inspect","validate-policy"),default="inspect")
    args=p.parse_args(argv)
    try:
        d=validate_plan()
        if args.action=="inspect":
            print("[KWAI] OAuth para Kwai Brasil: AINDA NAO CONFIRMADO PELA PLATAFORMA.")
            print("[KWAI] Nenhuma conta conectada; nao ha token para transferir ao GitHub.")
            print("[GITHUB] Ambiente planejado: "+d["github_environment"]+" (somente main).")
            print("[GITHUB] Secrets previstos: "+", ".join(SECRET_NAMES)+".")
            print("[SEGURANCA] Somente OAuth oficial, nunca senha, cookie, SMS ou sessao Android.")
            print("[PROXIMO] Confirmar acesso de desenvolvedor Kwai Brasil e app_id/app_secret.")
        else:
            print("KWAI_GITHUB_OAUTH_OFFLINE_POLICY_VALID_NO_LOGIN_OR_UPLOAD")
        return 0
    except (ValueError,OSError,TypeError) as ex:
        print("[KWAI BLOQUEADO] "+(
            str(ex) if isinstance(ex,KwaiReadinessBlocked) else type(ex).__name__
        ),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
