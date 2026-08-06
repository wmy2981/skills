"""Compress images to a target file size using ffmpeg (WebP output).

Used by --compact: turns an image data URI into a compressed WebP data URI
whose size is at or below the requested target. No persistent files are
written — temporary files live in a TemporaryDirectory and are auto-cleaned.
"""

import base64
import binascii
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from image_handler import DATA_URI_PATTERN

MAX_EDGE = 2048            # longest-edge cap (px) applied before quality iteration
QUALITY_START = 90         # webp quality start, stepped down by 10
QUALITY_END = 30           # webp quality floor
SIZE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(B|KB|K|MB|M)?\s*$", re.IGNORECASE)
SIZE_UNITS = {"B": 1, "K": 1024, "KB": 1024, "M": 1024 ** 2, "MB": 1024 ** 2}


def parse_size(value: str) -> int:
    """Parse a size argument into bytes.

    Accepts '500KB', '0.5MB', '512000B', bare '500' (interpreted as KB).
    Case-insensitive. Exits with an error message on invalid input.
    """
    m = SIZE_RE.match(value)
    if not m or float(m.group(1)) <= 0:
        print(f"Error: Invalid --compact size: '{value}'. "
              "Expected e.g. 500KB, 0.5MB, or 512000B (unit B/KB/MB, "
              "case-insensitive; bare numbers are KB).", file=sys.stderr)
        sys.exit(1)
    unit = SIZE_UNITS[(m.group(2) or "KB").upper()]
    return round(float(m.group(1)) * unit)


def _probe(path: str) -> dict:
    """Read width/height/frame count via ffprobe; {} on any failure."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    try:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
             "-show_entries", "stream=width,height,nb_read_frames", "-of", "json", path],
            capture_output=True,
        )
    except OSError:
        return {}
    if proc.returncode != 0:
        return {}
    try:
        info = json.loads(proc.stdout.decode("utf-8", errors="replace"))
        stream = (info.get("streams") or [{}])[0]
        return {
            "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0),
            "frames": int(stream.get("nb_read_frames") or 1),
        }
    except (ValueError, json.JSONDecodeError):
        return {}


def _run_ffmpeg(cmd: list[str]) -> None:
    """Run ffmpeg; exit with an error message on failure."""
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        print(f"Error: ffmpeg failed: {stderr[-500:]}", file=sys.stderr)
        sys.exit(1)


def compress_image(data: bytes, target_bytes: int) -> dict:
    """Compress raw image bytes to WebP ≤ target_bytes (best effort).

    Strategy: cap the longest edge at MAX_EDGE, then step webp quality down
    from QUALITY_START to QUALITY_END until the target is met. Animated images
    are skipped (only the first frame would be usable).

    Returns:
        {"skipped": True, "reason": "already-small"|"animated", "original_bytes": int}
        {"skipped": False, "data": bytes, "original_bytes": int,
         "compressed_bytes": int, "width": int, "height": int}
    """
    if len(data) <= target_bytes:
        return {"skipped": True, "reason": "already-small", "original_bytes": len(data)}

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("Error: ffmpeg not found. --compact requires ffmpeg (with libwebp). "
              "Install it, e.g.: winget install ffmpeg (Windows) / "
              "brew install ffmpeg (macOS) / apt install ffmpeg (Debian/Ubuntu).",
              file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "input")
        out_path = os.path.join(tmp, "output.webp")
        with open(in_path, "wb") as f:
            f.write(data)

        probe = _probe(in_path)
        if probe.get("frames", 1) > 1:
            return {"skipped": True, "reason": "animated", "original_bytes": len(data)}

        # Scale to max edge first (keeps aspect ratio), then step quality down.
        scale = f"scale='min({MAX_EDGE},iw)':-2"
        for quality in range(QUALITY_START, QUALITY_END - 1, -10):
            _run_ffmpeg([ffmpeg, "-y", "-i", in_path, "-vf", scale,
                         "-c:v", "libwebp", "-quality", str(quality), out_path])
            with open(out_path, "rb") as f:
                result_bytes = f.read()
            if len(result_bytes) <= target_bytes:
                break
        if len(result_bytes) > target_bytes:
            print(f"Warning: could not compress to {target_bytes} bytes "
                  f"(best effort: {len(result_bytes)} bytes at quality {quality}). "
                  "Sending best effort result.", file=sys.stderr)

        probe_out = _probe(out_path)
        return {
            "skipped": False,
            "data": result_bytes,
            "original_bytes": len(data),
            "compressed_bytes": len(result_bytes),
            "width": probe_out.get("width", 0),
            "height": probe_out.get("height", 0),
        }


def compress_data_uri(uri: str, size_arg: str) -> tuple[str, dict]:
    """Compress an image data URI to ≤ target size; returns (new_uri, stats).

    Stats: {"skipped": True, "reason": "already-small"|"animated", "original_bytes": int}
           or {"skipped": False, "original_bytes": int, "compressed_bytes": int,
               "width": int, "height": int}
    """
    target_bytes = parse_size(size_arg)
    m = DATA_URI_PATTERN.match(uri)
    if not m:
        print("Error: Cannot compress image: not a valid data URI", file=sys.stderr)
        sys.exit(1)
    try:
        data = base64.b64decode(m.group(1))
    except (ValueError, binascii.Error):
        print("Error: Cannot compress image: invalid base64 data", file=sys.stderr)
        sys.exit(1)

    result = compress_image(data, target_bytes)
    if result.get("skipped"):
        return uri, result
    new_uri = "data:image/webp;base64," + base64.b64encode(result["data"]).decode("ascii")
    # stats are for the agent output — the internal bytes payload stays internal
    stats = {k: v for k, v in result.items() if k != "data"}
    return new_uri, stats
