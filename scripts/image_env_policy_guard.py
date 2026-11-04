#!/usr/bin/env python3
"""Fail-closed public GitHub environment policy gate. No OAuth secret access.

Called in a separate job before a protected environment job is scheduled.
"""
from __future__ import annotations

import json
import os
from urllib import request, error
from typing import Callable

REPO = "HelioConde/AutoEditorVideo"
ENV_NAME = "image-generation"
API_BASE = f"https://api.github.com/repos/{REPO}/environments/{ENV_NAME}"


class InvalidEnvironment(Exception):
    pass


def strict_environment_policy(environment: dict, policies: dict) -> None:
    if not isinstance(environment, dict) or environment.get("name") != ENV_NAME:
        raise InvalidEnvironment("ENVIRONMENT_MISSING")
    branch = environment.get("deployment_branch_policy") or {}
    if branch.get("custom_branch_policies") is not True or branch.get("protected_branches") is not False:
        raise InvalidEnvironment("CUSTOM_BRANCH_POLICY_REQUIRED")
    if not isinstance(policies, dict) or not isinstance(policies.get("branch_policies"), list):
        raise InvalidEnvironment("BRANCH_POLICY_UNVERIFIED")
    rules = policies["branch_policies"]
    if policies.get("total_count", len(rules)) != len(rules):
        raise InvalidEnvironment("BRANCH_POLICY_PAGINATION_UNVERIFIED")
    if len(rules) != 1 or rules[0].get("name") != "main" or rules[0].get("type", "branch") != "branch":
        raise InvalidEnvironment("ONLY_MAIN_ALLOWED")


def fetch_json(url: str, token: str = "", opener=None) -> dict:
    if url not in (API_BASE, API_BASE + "/deployment-branch-policies?per_page=100"):
        raise InvalidEnvironment("UNEXPECTED_API_URL")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AutoEditorVideo-ProtectedImagePreflight",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token.strip():
        headers["Authorization"] = "Bearer " + token.strip()
    open_fn = opener or request.urlopen
    try:
        with open_fn(request.Request(url, headers=headers), timeout=12) as res:
            return json.loads(res.read(65536))
    except (OSError, ValueError, error.URLError, TypeError):
        raise InvalidEnvironment("ENVIRONMENT_API_UNAVAILABLE") from None


def check(token: str = "", opener=None) -> None:
    env = fetch_json(API_BASE, token, opener)
    policies = fetch_json(API_BASE + "/deployment-branch-policies?per_page=100", token, opener)
    strict_environment_policy(env, policies)


def main() -> int:
    if os.environ.get("GITHUB_REF") != "refs/heads/main":
        print("[IMAGE_ENV] MAIN_ONLY")
        return 1
    if os.environ.get("GITHUB_REPOSITORY") != REPO:
        print("[IMAGE_ENV] WRONG_REPOSITORY")
        return 1
    try:
        check(os.environ.get("GH_TOKEN", ""))
    except InvalidEnvironment as exc:
        print("[IMAGE_ENV] " + str(exc))
        return 1
    print("[IMAGE_ENV] PROTECTED_MAIN_ONLY_OK")
    print("[SAFETY] NO_PRIVATE_SECRETS_ACCESSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
