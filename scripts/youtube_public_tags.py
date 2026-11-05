#!/usr/bin/env python3
"""Public YouTube keywords must never contain AutoEditorVideo control tokens.

The former uploaders stored de-duplication markers in snippet.tags, where
YouTube Studio and vidIQ display them as zero-score SEO tags. Keep technical
identifiers in private receipts / repository reservations instead.
"""
from __future__ import annotations

from typing import Iterable

INTERNAL_PREFIXES = ("autoeditorvideo-", "autoeditorvideo_", "autoeditorvideo:")


def is_internal_tag(tag: str) -> bool:
    if not isinstance(tag, str):
        raise TypeError("YouTube tag is not a string")
    return tag.strip().casefold().startswith(INTERNAL_PREFIXES)


def public_tags(tags: Iterable[str]) -> list[str]:
    """Preserve real tags exactly and in order, filtering ONLY internal IDs."""
    cleaned = []
    for tag in tags:
        if not isinstance(tag, str):
            raise TypeError("YouTube tag is not a string")
        if tag and not is_internal_tag(tag):
            cleaned.append(tag)
    return cleaned


def internal_tags(tags: Iterable[str]) -> list[str]:
    return [tag for tag in tags if is_internal_tag(tag)]
