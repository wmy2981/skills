"""Extract image metadata: size, width, height, color, device, app, time, location.

Uses ffprobe for technical fields (size/dimensions/pixel format) and Pillow for
EXIF (device/app/time/location). Never exits on failure — missing fields become
None, and a totally unprobeable image yields None so recognition is unaffected.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

FIELDS = ("size", "width", "height", "color", "device", "app", "time", "location")

# EXIF tag IDs
TAG_MAKE = 0x010F
TAG_MODEL = 0x0110
TAG_SOFTWARE = 0x0131
TAG_DATETIME_ORIGINAL = 0x9003
GPS_IFD = 0x8825
# GPS IFD sub-tags
GPS_LAT_REF = 1
GPS_LAT = 2
GPS_LON_REF = 3
GPS_LON = 4


def empty_metadata() -> dict:
    """Metadata dict with every field set to None."""
    return {field: None for field in FIELDS}


def _probe_basics(data: bytes) -> dict:
    """width/height/pix_fmt via ffprobe; {} on any failure."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "input")
        with open(path, "wb") as f:
            f.write(data)
        try:
            proc = subprocess.run(
                [ffprobe, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height,pix_fmt", "-of", "json", path],
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
                "width": stream.get("width"),
                "height": stream.get("height"),
                "color": stream.get("pix_fmt"),
            }
        except (ValueError, json.JSONDecodeError):
            return {}


def _exif_tags(data: bytes) -> dict | None:
    """EXIF tags via Pillow; {} when no EXIF, None when the image cannot be opened.

    The GPS IFD must be expanded via get_ifd() while the file handle is still
    open — the top-level Exif dict only holds the GPS IFD offset otherwise.
    """
    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow is required for --metadata (pip install -r scripts/requirements.txt)",
              file=sys.stderr)
        return None
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "input")
        with open(path, "wb") as f:
            f.write(data)
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                tags = dict(exif)
                gps = exif.get_ifd(GPS_IFD)
                if gps:
                    tags[GPS_IFD] = gps
                return tags
        except Exception:
            return None


def _dms_to_decimal(dms, ref) -> float | None:
    """Convert EXIF DMS (degrees, minutes, seconds) to decimal degrees."""
    try:
        deg, minutes, sec = (float(x) for x in dms)
    except (TypeError, ValueError):
        return None
    value = deg + minutes / 60 + sec / 3600
    if str(ref).upper() in ("S", "W"):
        value = -value
    return value


def _gps_location(exif: dict) -> dict | None:
    """GPS from EXIF IFD as {"lat": float, "lon": float}; None if absent/invalid."""
    gps = exif.get(GPS_IFD)
    if not isinstance(gps, dict):
        return None
    lat = _dms_to_decimal(gps.get(GPS_LAT), gps.get(GPS_LAT_REF))
    lon = _dms_to_decimal(gps.get(GPS_LON), gps.get(GPS_LON_REF))
    if lat is None or lon is None:
        return None
    return {"lat": round(lat, 6), "lon": round(lon, 6)}


def _iso_time(value: str) -> str:
    """Convert EXIF 'YYYY:MM:DD HH:MM:SS' to ISO 8601; keep original on parse failure."""
    try:
        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S").isoformat()
    except ValueError:
        return value


def get_metadata(data: bytes) -> dict | None:
    """Extract the 8 metadata fields from raw image bytes.

    Returns a dict with all FIELDS (missing ones are None), or None when the
    image cannot be probed at all (unrecognized/corrupt data).
    """
    md = empty_metadata()
    md["size"] = len(data)

    basics = _probe_basics(data)
    if not basics:
        return None
    md["width"] = basics.get("width")
    md["height"] = basics.get("height")
    md["color"] = basics.get("color")

    exif = _exif_tags(data)
    if exif:
        md["device"] = exif.get(TAG_MODEL) or exif.get(TAG_MAKE)
        md["app"] = exif.get(TAG_SOFTWARE)
        raw_time = exif.get(TAG_DATETIME_ORIGINAL)
        if isinstance(raw_time, str):
            md["time"] = _iso_time(raw_time)
        md["location"] = _gps_location(exif)
    return md
