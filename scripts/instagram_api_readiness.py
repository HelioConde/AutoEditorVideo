#!/usr/bin/env python3
"""Instagram Reels API planning and security gate for AutoEditorVideo.

This module deliberately performs ZERO HTTP or social-network actions.
It validates official Instagram Login requirements, account routing,
public HTTPS media URL eligibility, and the container/status/publish
sequence. A future, separately authorized uploader may consume the plan,
but this script never authenticates, uploads, creates a container or posts.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config"/"instagram-api-readiness.json"
PROFILE_KEYS=("br","en","games","kids","alchemy")
PERMISSIONS=("instagram_business_basic","instagram_business_content_publish")
SECRET_NAMES=("INSTAGRAM_APP_ID","INSTAGRAM_APP_SECRET","INSTAGRAM_OAUTH_TOKEN_JSON")
VERSION="v25.0"
BASE="https://graph.instagram.com/"
ACCOUNT_ID=re.compile(r"[0-9]{6,25}\Z")
CONTAINER_ID=re.compile(r"[0-9]{6,25}\Z")

class InstagramBlocked(ValueError):
    pass

def get_config()->dict:
    value=json.loads(CONFIG.read_text(encoding="utf-8"))
    expected={
        "schema":"autoeditorvideo/instagram-api-readiness/v1",
        "target_platform":"instagram_reels",
        "authentication":"instagram_login",
        "graph_api_version":VERSION,
        "required_account_type":["BUSINESS","CREATOR"],
        "required_permissions":list(PERMISSIONS),
        "github_repository":"HelioConde/AutoEditorVideo",
        "github_environment_planned":"instagram-private-publish",
        "github_environment_created":False,
        "environment_branch_allowlist":["main"],
        "secret_names_planned":list(SECRET_NAMES),
        "oauth_connected":False,
        "meta_app_created":False,
        "hosting_public_https_configured":False,
        "reels_publication_enabled":False,
        "real_upload_enabled":False,
        "auto_publish_enabled":False,
        "secret_transfer_enabled":False,
        "no_instagram_token_committed":True,
        "no_facebook_page_required_for_instagram_login":True,
        "ensure_owner_identity_before_publish":True,
        "require_independent_qa_before_publish":True,
        "require_explicit_go_live_approval":True,
        "account_routes":{x:None for x in PROFILE_KEYS},
        "media_url_requirement":"public_https_mp4_reachable_by_meta",
        "deferred_implementation":[
            "oauth_app_registration_and_local_authorization",
            "public_video_hosting","account_id_verification",
            "private_token_storage_with_protected_branch_policy",
            "container_creation","processing_polling",
            "explicit_publish_and_idempotency_receipts"],
        "references":[
            "https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/",
            "https://developers.facebook.com/docs/instagram-platform/content-publishing/"
        ]
    }
    if value!=expected:
        raise InstagramBlocked("INSTAGRAM_CONFIG_CHANGED_OR_NOT_SAFE_OFFLINE")
    return value

def github_environment_main_only(environment:dict,policies:dict)->None:
    if not isinstance(environment,dict) or environment.get("name")!="instagram-private-publish":
        raise InstagramBlocked("INSTAGRAM_PROTECTED_ENVIRONMENT_NOT_FOUND")
    rules=environment.get("deployment_branch_policy") or {}
    if rules.get("custom_branch_policies") is not True or rules.get("protected_branches") is not False:
        raise InstagramBlocked("INSTAGRAM_ONLY_MAIN_CUSTOM_BRANCH_POLICY_REQUIRED")
    entries=policies.get("branch_policies") if isinstance(policies,dict) else None
    if (not isinstance(entries,list) or len(entries)!=1
        or policies.get("total_count")!=1 or entries[0].get("name")!="main"
        or entries[0].get("type","branch")!="branch"):
        raise InstagramBlocked("INSTAGRAM_ENVIRONMENT_MUST_ALLOW_ONLY_MAIN")

def media_https_url(url:str)->str:
    if not isinstance(url,str) or len(url)>1800 or any(ord(c)<32 for c in url):
        raise InstagramBlocked("INSTAGRAM_VIDEO_URL_INVALID")
    try:
        parts=urlsplit(url)
        port=parts.port
        host=parts.hostname or ""
    except ValueError:
        raise InstagramBlocked("INSTAGRAM_VIDEO_URL_INVALID") from None
    if (parts.scheme!="https" or not host or "." not in host
        or parts.username is not None or parts.password is not None
        or parts.fragment or port not in (None,443)
        or host in ("localhost","127.0.0.1")
        or host.endswith((".local",".internal",".localhost",".test",".example"))
        or re.search(r"[^a-z0-9.-]",host.lower())
        or not parts.path.lower().endswith((".mp4",".mov"))):
        raise InstagramBlocked("INSTAGRAM_PUBLIC_HTTPS_MP4_URL_REQUIRED")
    try:
        ip=ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not ip.is_global:
            raise InstagramBlocked("INSTAGRAM_LOCAL_MEDIA_IP_FORBIDDEN")
    # A URL that passes structure validation still must be actually public.
    # This offline planner CANNOT guarantee that Meta can fetch it.
    return url

def validate_target(channel:str,instagram_user_id:str)->None:
    if channel not in PROFILE_KEYS:
        raise InstagramBlocked("INSTAGRAM_CHANNEL_UNKNOWN")
    if not isinstance(instagram_user_id,str) or not ACCOUNT_ID.fullmatch(instagram_user_id):
        raise InstagramBlocked("INSTAGRAM_USER_ID_MUST_BE_EXACT_NUMERIC_ID")
    mapping=get_config()["account_routes"]
    if mapping[channel]!=instagram_user_id:
        raise InstagramBlocked("INSTAGRAM_CHANNEL_NOT_VERIFIED_OR_NOT_CONNECTED")

def inspect()->dict:
    d=get_config()
    return {
        "platform":d["target_platform"],
        "authentication":d["authentication"],
        "target_channels":list(d["account_routes"]),
        "connected_channels":[],
        "meta_app_created":False,
        "oauth_connected":False,
        "video_host_configured":False,
        "live_upload_enabled":False,
        "public_reels_enabled":False,
        "github_environment_planned":d["github_environment_planned"],
        "github_environment_created":False,
        "status":"requires_creator_meta_app_and_oauth"
    }

def plan_reel(channel:str,instagram_user_id:str,video_url:str,caption:str,
              *,publish:bool=False)->dict:
    get_config()
    if publish:
        raise InstagramBlocked("INSTAGRAM_REAL_PUBLICATION_REQUIRES_SEPARATE_AUTHORIZATION")
    media_https_url(video_url)
    if not isinstance(caption,str) or not caption.strip() or len(caption)>2200:
        raise InstagramBlocked("INSTAGRAM_CAPTION_INVALID")
    # No routing is configured yet, thus cannot bind ANY real IG account.
    validate_target(channel,instagram_user_id)
    return {
        "channel":channel,
        "instagram_user_id":instagram_user_id,
        "media_type":"REELS",
        "media_url":video_url,
        "caption":caption,
        "publish_enabled":False,
        "api_sequence":[
            {"method":"POST","path":VERSION+"/"+instagram_user_id+"/media",
             "body":{"media_type":"REELS","video_url":video_url,"caption":caption}},
            {"method":"GET","path":VERSION+"/{creation_id}?fields=status_code"},
            {"method":"POST","path":VERSION+"/"+instagram_user_id+"/media_publish",
             "body":{"creation_id":"{creation_id}"}}
        ],
        "note":"PLAN_ONLY_NO_HTTP_NO_POSTING_NOT_EXECUTABLE"
    }

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description="Safe Instagram Reels onboarding")
    parser.add_argument("--action",choices=("inspect","preflight"),default="inspect")
    args=parser.parse_args(argv)
    try:
        result=inspect() if args.action=="inspect" else get_config()
    except (ValueError,OSError,TypeError):
        print("[INSTAGRAM] SECURITY_PREFLIGHT_FAILED",file=sys.stderr)
        return 2
    if args.action=="inspect":
        print(json.dumps(result,ensure_ascii=False,indent=2))
    else:
        print("INSTAGRAM_OFFLINE_PREFLIGHT_OK_NO_SECRETS_NO_UPLOAD_NO_PUBLICATION")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
