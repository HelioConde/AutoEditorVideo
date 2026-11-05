#!/usr/bin/env python3
"""Read-only GitHub API gate for three independent YouTube environments.

Runs in a normal unprotected job before ANY OAuth Secret becomes available.
A workflow-created Environment with permissive defaults is NOT acceptable.
"""
from __future__ import annotations
import json
import os
from urllib import request, error

from youtube_channel_registry import NEW_CHANNELS, get_channel

REPO="HelioConde/AutoEditorVideo"

class UnsafeYouTubeEnvironment(ValueError):
    pass

def policy_is_main_only(channel:str, environment:dict, policies:dict)->None:
    if channel not in NEW_CHANNELS:
        raise UnsafeYouTubeEnvironment("CHANNEL_NOT_ALLOWED")
    expected=get_channel(channel)["youtube_environment"]
    if not isinstance(environment,dict) or environment.get("name")!=expected:
        raise UnsafeYouTubeEnvironment("ENVIRONMENT_NOT_FOUND_OR_WRONG_CHANNEL")
    branch=environment.get("deployment_branch_policy") or {}
    if branch.get("protected_branches") is not False or branch.get("custom_branch_policies") is not True:
        raise UnsafeYouTubeEnvironment("ENVIRONMENT_CUSTOM_MAIN_BRANCH_RULE_REQUIRED")
    if not isinstance(policies,dict) or not isinstance(policies.get("branch_policies"),list):
        raise UnsafeYouTubeEnvironment("BRANCH_POLICY_UNVERIFIED")
    rules=policies["branch_policies"]
    if policies.get("total_count")!=1 or len(rules)!=1:
        raise UnsafeYouTubeEnvironment("BRANCH_POLICY_NOT_EXACTLY_ONE")
    if rules[0].get("name")!="main" or rules[0].get("type","branch")!="branch":
        raise UnsafeYouTubeEnvironment("ENVIRONMENT_ONLY_MAIN_ALLOWED")

def fetch_protected_policy(channel:str, token:str, *, opener=None)->tuple[dict,dict]:
    if channel not in NEW_CHANNELS:
        raise UnsafeYouTubeEnvironment("CHANNEL_NOT_ALLOWED")
    if not token:
        raise UnsafeYouTubeEnvironment("GITHUB_READ_TOKEN_MISSING")
    name=get_channel(channel)["youtube_environment"]
    base=f"https://api.github.com/repos/{REPO}/environments/{name}"
    headers={
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"AutoEditorVideo-YouTube-Environment-Policy-Gate",
        "Authorization":"Bearer "+token,
    }
    def one(url:str)->dict:
        if url not in (base,base+"/deployment-branch-policies?per_page=100"):
            raise UnsafeYouTubeEnvironment("UNEXPECTED_GITHUB_API_URL")
        try:
            req=request.Request(url,headers=headers)
            with (opener or request.urlopen)(req,timeout=15) as response:
                return json.loads(response.read(65536))
        except (OSError,ValueError,TypeError,error.URLError):
            raise UnsafeYouTubeEnvironment("GITHUB_ENVIRONMENT_POLICY_API_UNAVAILABLE") from None
    return one(base),one(base+"/deployment-branch-policies?per_page=100")

def main()->int:
    env=os.environ
    if env.get("GITHUB_REPOSITORY")!=REPO:
        print("[YOUTUBE ENV] WRONG_REPOSITORY")
        return 1
    if env.get("GITHUB_REF")!="refs/heads/main":
        print("[YOUTUBE ENV] MAIN_ONLY")
        return 1
    if env.get("GITHUB_EVENT_NAME")!="workflow_dispatch" or env.get("GITHUB_RUN_ATTEMPT")!="1":
        print("[YOUTUBE ENV] ONE_SHOT_MANUAL_ONLY")
        return 1
    channel=env.get("CHANNEL_SLUG","")
    try:
        environment,policies=fetch_protected_policy(channel,env.get("GH_TOKEN",""))
        policy_is_main_only(channel,environment,policies)
    except UnsafeYouTubeEnvironment as exc:
        print("[YOUTUBE ENV] "+str(exc))
        return 1
    except Exception:
        print("[YOUTUBE ENV] UNCLASSIFIED_CHECK_FAILED")
        return 1
    print("[YOUTUBE ENV] MAIN_ONLY_PROTECTION_VERIFIED_"+channel.upper())
    print("[SAFETY] NO_YOUTUBE_SECRETS_ACCESSED_IN_GATE")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
