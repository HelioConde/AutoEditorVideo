#!/usr/bin/env python3
"""One authorized, strictly bounded image-generation smoke test on localhost.

Never uploads artwork, uses a child reference image, retries a generation,
prints provider bodies/tokens, or saves generated output as a CI artifact.
The image is validated in memory and then discarded.
"""
from __future__ import annotations

import base64
import binascii
from hashlib import sha256
import io
import json
import os
from urllib import error, request

from PIL import Image

from image_session_readonly_probe import check as account_readiness

URL = "http://127.0.0.1:8080/v1/images/generations"
MODEL = "gpt-image-2"
SIZE = "1024x1024"
MAX_BODY = 40_000_000
MAX_IMAGE = 25_000_000

# Fictional props only. NO photos/portraits, NO real child identity.
PROMPT = (
    "Make ONE original, cheerful 2D storybook illustration for a children's "
    "animation pipeline test: a soft sky-blue fabric toy star floating beside "
    "a single orange butterfly and a white daisy in a bright green meadow. "
    "Clean shapes, warm friendly lighting, gentle textures, vibrant colors. "
    "One coherent scene, no people, no faces of real children, no brand marks, "
    "no letters, no logos, no text, and no copyrighted characters."
)


class ImageProbeError(Exception):
    """A fixed safe code that never contains provider or OAuth response data."""


def decode_image_response(body: bytes) -> tuple[int, int]:
    if len(body) > MAX_BODY:
        raise ImageProbeError("RESPONSE_TOO_LARGE")
    try:
        obj = json.loads(body)
    except (TypeError, ValueError):
        raise ImageProbeError("INVALID_JSON") from None
    if not isinstance(obj, dict) or not isinstance(obj.get("data"), list) or len(obj["data"]) != 1:
        raise ImageProbeError("NO_SINGLE_IMAGE")
    item = obj["data"][0]
    if not isinstance(item, dict):
        raise ImageProbeError("INVALID_IMAGE_ENTRY")
    value = item.get("b64_json")
    if not isinstance(value, str) or not value:
        value = item.get("url")
        if not isinstance(value, str) or not value.startswith("data:image/png;base64,"):
            raise ImageProbeError("NO_INLINE_PNG")
        value = value.split(",", 1)[1]
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ImageProbeError("INVALID_BASE64") from None
    if len(raw) < 100 or len(raw) > MAX_IMAGE or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ImageProbeError("INVALID_PNG_BYTES")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG":
                raise ImageProbeError("NOT_PNG")
            width, height = image.size
            image.verify()
    except ImageProbeError:
        raise
    except (OSError, ValueError, SyntaxError):
        raise ImageProbeError("PNG_VERIFICATION_FAILED") from None
    if width < 512 or height < 512 or width > 2048 or height > 2048:
        raise ImageProbeError("UNEXPECTED_IMAGE_DIMENSIONS")
    return width, height


def request_single_image(key: str, opener=None) -> tuple[int, int]:
    if not isinstance(key, str) or len(key.strip()) < 15:
        raise ImageProbeError("PROXY_KEY_INVALID")
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "n": 1,
        "size": SIZE,
        "background": "opaque",
        "output_format": "png",
    }
    req = request.Request(
        URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
    )
    # ONE network request, no retry, and no fallback providers.
    try:
        handler = opener or request.urlopen
        with handler(req, timeout=360) as response:
            if response.status != 200:
                raise ImageProbeError("PROXY_HTTP_NOT_200")
            body = response.read(MAX_BODY + 1)
    except error.HTTPError as exc:
        # Do not print response body, which may include account details.
        code = exc.code if isinstance(exc.code, int) and 100 <= exc.code <= 599 else 0
        raise ImageProbeError(f"PROXY_HTTP_{code}") from None
    except (OSError, error.URLError, TimeoutError):
        raise ImageProbeError("PROXY_CONNECTION_FAILED") from None
    return decode_image_response(body)


def run(env: dict[str, str] | None = None,
        *, readiness=None, generate=None) -> int:
    env = os.environ if env is None else env
    if env.get("MAX_IMAGE_CALLS") != "1":
        print("[IMAGE_TEST] BUDGET_NOT_EXACTLY_ONE")
        return 1
    if env.get("IMAGE_MODEL") != MODEL:
        print("[IMAGE_TEST] MODEL_NOT_APPROVED")
        return 1
    key = env.get("PROXY_API_KEY", "")
    try:
        checker = readiness or account_readiness
        ready = checker(key)
        if ready != "ACCOUNT_RECORDS_LOADED_CACHED_ELIGIBLE":
            raise ImageProbeError("ACCOUNT_NOT_CACHED_ELIGIBLE")
        print("[IMAGE_TEST] READONLY_ACCOUNT_PREFLIGHT_OK")
        print("[IMAGE_TEST] REQUEST_BUDGET_ONE_NO_RETRIES")
        sender = generate or request_single_image
        width, height = sender(key)
        print(f"[IMAGE_TEST] REAL_IMAGE_VALIDATED_PNG_{width}x{height}")
        print("[SAFETY] NO_IMAGE_ARTIFACT_NO_CHILD_PHOTO_NO_YOUTUBE_UPLOAD")
        return 0
    except ImageProbeError as exc:
        print("[IMAGE_TEST] " + str(exc))
        return 1
    except Exception:
        # Never format foreign exception bodies, because they may include secrets.
        print("[IMAGE_TEST] UNKNOWN_FAILURE_NO_PROVIDER_BODY_LOGGED")
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
