"""Normalize image inputs (local path, URL, base64 data URI) to API-ready format."""

import os
import re
import base64
import sys
import requests

DATA_URI_PATTERN = re.compile(r"^data:image/[a-zA-Z]+;base64,(.+)$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def _is_url(path: str) -> bool:
    return bool(URL_PATTERN.match(path))


def _is_data_uri(path: str) -> bool:
    return bool(DATA_URI_PATTERN.match(path))


def _load_local_image(path: str) -> str:
    if not os.path.exists(path):
        print(f"Error: Image file not found: '{path}'", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ("jpg", "jpeg"):
            mime = "image/jpeg"
        elif ext == "png":
            mime = "image/png"
        elif ext == "webp":
            mime = "image/webp"
        elif ext == "gif":
            mime = "image/gif"
        else:
            mime = "image/png"  # fallback
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except (OSError, IOError) as e:
        print(f"Error: Cannot read image file '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def _download_image(url: str) -> str:
    """Download image from URL and convert to base64 data URI as fallback."""
    try:
        resp = requests.get(url, timeout=(10, 30))
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode("ascii")
        return f"data:{content_type};base64,{b64}"
    except requests.RequestException as e:
        print(f"Error: Failed to download image from URL: {url}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)


def normalize_image(image_str: str) -> str:
    """Convert image input to a string the API can use (data URI or URL).

    Accepts:
    - Local file path
    - HTTP(S) URL (passed as-is for API direct fetch, or downloaded as fallback)
    - data:image/...;base64,... URI
    """
    if _is_data_uri(image_str):
        # Validate the base64 portion is decodable
        m = DATA_URI_PATTERN.match(image_str)
        try:
            base64.b64decode(m.group(1), validate=True)
        except Exception:
            print("Error: Invalid base64 data in image URI", file=sys.stderr)
            print("Expected format: data:image/{type};base64,{encoded_data}", file=sys.stderr)
            sys.exit(1)
        return image_str

    if _is_url(image_str):
        # Return as-is; API may fetch it directly. If API fails, caller could retry with download.
        # We also pre-download as a fallback data URI for APIs that don't support URL input.
        # For maximum compatibility, always convert to data URI.
        return _download_image(image_str)

    # Assume local file path
    return _load_local_image(image_str)
