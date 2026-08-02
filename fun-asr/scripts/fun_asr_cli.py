#!/usr/bin/env python3
"""
Fun-ASR CLI — Audio transcription via Alibaba Cloud DashScope Fun-ASR API.

Transcribes audio files (mp3, wav, m4a, flac, ogg, aac, etc.) using the
Fun-ASR non-real-time speech recognition model. Supports speaker diarization,
multi-language recognition, and multiple output formats (text, JSON, SRT).

Workflow:
  Local audio -> S3 (presigned URL) -> Fun-ASR async transcription
    -> Poll -> Download -> Format -> Save

Exit codes (for agent consumption):
  0  Success
  2  Configuration / environment variable error
  3  File not found or invalid
  4  API / network error
  5  Audio format / processing error
  6  ASR task failure
  7  Timeout
  8  Invalid arguments
"""

import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import boto3
import requests
from botocore.config import Config as BotoConfig
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VERSION = "0.3.0"
TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

DASHSCOPE_URL = "https://dashscope.aliyuncs.com/api/v1"
SUBMIT_URL = f"{DASHSCOPE_URL}/services/audio/asr/transcription"
QUERY_URL = f"{DASHSCOPE_URL}/tasks"

POLL_INTERVAL = 2        # polling interval (seconds)
MAX_WAIT = 1800          # max wait time (30 minutes)
PRESIGNED_EXPIRE = 7200  # presigned URL validity (2 hours)
PRICE_PER_SECOND = 0.00022  # Fun-ASR price: CNY/second
OUTPUT_DIR = Path.home() / ".wmyskills" / "fun-asr" / "outputs"

# Exit codes
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 2
EXIT_FILE_ERROR = 3
EXIT_API_ERROR = 4
EXIT_AUDIO_ERROR = 5
EXIT_TASK_FAILED = 6
EXIT_TIMEOUT = 7
EXIT_ARG_ERROR = 8

# ---------------------------------------------------------------------------
# Output helpers — plain text to stderr.
# ---------------------------------------------------------------------------

def info(message: str):
    """Print an info message to stderr."""
    print(f"[info] {message}", file=sys.stderr)


def ensure_utf8_console():
    """Force stdout/stderr to UTF-8 encoding on Windows (terminal defaults to GBK)."""
    if sys.platform == "win32":
        # Reconfigure stdout/stderr to UTF-8 so Chinese/emoji output is not garbled
        for stream_name in ("stdout", "stderr"):
            stream = getattr(sys, stream_name)
            if stream and hasattr(stream, "buffer"):
                setattr(sys, stream_name,
                        io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"))
        # Also switch the terminal code page to UTF-8
        try:
            subprocess.run(["chcp", "65001"], capture_output=True, check=True)
        except Exception:
            pass


def warn(message: str):
    """Print a warning message to stderr."""
    print(f"[warn] {message}", file=sys.stderr)


def error(message: str):
    """Print an error message to stderr."""
    print(f"[error] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class FunAsrError(Exception):
    """Base exception for Fun-ASR errors."""
    exit_code = EXIT_API_ERROR

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


class ConfigError(FunAsrError):
    exit_code = EXIT_CONFIG_ERROR


class FileError(FunAsrError):
    exit_code = EXIT_FILE_ERROR


class TaskFailedError(FunAsrError):
    exit_code = EXIT_TASK_FAILED


class TimeoutError(FunAsrError):
    exit_code = EXIT_TIMEOUT


def fatal(exc: FunAsrError):
    """Print error to stderr and exit with the appropriate code."""
    error(str(exc))
    if exc.detail:
        print(f"[error] detail: {exc.detail}", file=sys.stderr)
    sys.exit(exc.exit_code)


# ---------------------------------------------------------------------------
# Environment / config
# ---------------------------------------------------------------------------

def load_env():
    """Load .env — priority: script dir > user global (~/.wmyskills/.env).
    load_dotenv never overrides, so script dir loads first, user global second."""
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env")
    load_dotenv(Path.home() / ".wmyskills" / ".env")


# ---------------------------------------------------------------------------
# Configuration extraction
# ---------------------------------------------------------------------------

def get_api_key() -> str:
    """Return the DashScope API key or raise ConfigError."""
    key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("BAILIAN_APIKEY")
    if not key:
        raise ConfigError(
            "DASHSCOPE_API_KEY is not set. "
            "Set it in your environment or .env file."
        )
    return key


def validate_config():
    """Validate required configuration. Raises ConfigError on failure."""
    missing = []
    if not os.getenv("DASHSCOPE_API_KEY") and not os.getenv("BAILIAN_APIKEY"):
        missing.append("DASHSCOPE_API_KEY")
    if not os.getenv("S3_ENDPOINT"):
        missing.append("S3_ENDPOINT")
    if not os.getenv("S3_BUCKET"):
        missing.append("S3_BUCKET")
    if missing:
        raise ConfigError("Missing required environment variables", "; ".join(missing))


def s3_config() -> dict:
    """Return S3 configuration from environment."""
    return {
        "endpoint": os.environ.get("S3_ENDPOINT", "").rstrip("/"),
        "bucket": os.environ.get("S3_BUCKET", ""),
        "prefix": os.environ.get("S3_PREFIX", "asr-uploads"),
        "region": os.environ.get("S3_REGION", "us-east-1"),
    }


# ---------------------------------------------------------------------------
# S3 operations (presigned URL approach)
# ---------------------------------------------------------------------------

def get_s3_client():
    """Create an S3 client (credentials from boto3 default chain)."""
    cfg = s3_config()
    if not cfg["endpoint"]:
        raise ConfigError("S3_ENDPOINT is not set")
    if not cfg["bucket"]:
        raise ConfigError("S3_BUCKET is not set")
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        config=BotoConfig(signature_version="s3v4", region_name=cfg["region"]),
    )


def upload_to_s3(local_path: str) -> tuple[str, str]:
    """
    Upload a file to S3 via presigned PUT URL.

    Returns (presigned_get_url, s3_key).
    """
    path = Path(local_path)
    if not path.exists():
        raise FileError(f"File not found: {local_path}")

    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 2048:
        raise FileError(
            f"File is too large ({size_mb:.1f} MB). Maximum allowed is 2 GB."
        )

    ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    safe_name = path.name.replace(" ", "_")
    cfg = s3_config()
    key = f"{cfg['prefix']}/{ts}_{safe_name}"

    info(f"Uploading to S3: {key} ({size_mb:.1f} MB)")

    s3 = get_s3_client()

    # Presigned PUT URL
    put_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": cfg["bucket"], "Key": key},
        ExpiresIn=3600,
    )

    # Upload
    try:
        with open(path, "rb") as fh:
            resp = requests.put(put_url, data=fh, timeout=600)
        if resp.status_code != 200:
            raise FileError(
                f"S3 upload failed (HTTP {resp.status_code})",
                resp.text[:300],
            )
    except requests.RequestException as exc:
        raise FileError("S3 upload failed", str(exc))

    info("S3 upload completed")

    # Presigned GET URL (for ASR service to download)
    get_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": cfg["bucket"], "Key": key},
        ExpiresIn=PRESIGNED_EXPIRE,
    )
    info(f"Download URL generated (valid for {PRESIGNED_EXPIRE // 3600}h)")

    return get_url, key


def delete_from_s3(key: str):
    """Delete a file from S3. Best-effort; failures are non-fatal."""
    try:
        s3 = get_s3_client()
        cfg = s3_config()
        s3.delete_object(Bucket=cfg["bucket"], Key=key)
        info(f"S3 temporary file cleaned up: {key}")
    except Exception as exc:
        warn(f"Failed to clean up S3 file: {key}: {exc}")


# ---------------------------------------------------------------------------
# Audio pre-processing
# ---------------------------------------------------------------------------

def probe_audio(file_path: str) -> tuple[float, int]:
    """Return (duration_seconds, num_channels) using ffprobe; (0.0, 0) on failure."""
    duration = 0.0
    channels = 0

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            duration = float(result.stdout.strip())
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=channels",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        if lines[0]:
            channels = int(lines[0])
    except Exception:
        pass

    return duration, channels


# Track temporary files for cleanup
_temp_files: list[str] = []


def _cleanup_temp(path: str):
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
    except OSError:
        pass


def cleanup_temp_files():
    while _temp_files:
        _cleanup_temp(_temp_files.pop())


def ensure_mono(file_path: str, channels: int = 0) -> str:
    """
    If the audio is not mono, convert it with ffmpeg.
    Accepts pre-probed channel count to avoid redundant ffprobe.
    Returns the (possibly new) mono file path.
    Tracks converted files for later cleanup.
    """
    path = Path(file_path)

    if channels == 0:
        warn("Channel count unknown; skipping mono conversion")
        return file_path

    if channels == 1:
        info("Audio is already mono, no conversion needed")
        return file_path

    info(f"Audio has {channels} channels. Converting to mono for diarization...")

    suffix = path.suffix if path.suffix else ".wav"
    tmp = tempfile.NamedTemporaryFile(suffix=f"_mono{suffix}", delete=False)
    output_path = tmp.name
    tmp.close()
    _temp_files.append(output_path)  # track for cleanup

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-ac", "1", output_path],
            capture_output=True, text=True, check=True, timeout=300,
        )
        info(f"Converted to mono: {output_path}")
        return output_path
    except subprocess.CalledProcessError as exc:
        warn(f"Mono conversion failed; using original file: {exc.stderr[:300]}")
        _cleanup_temp(output_path)
        return file_path
    except FileNotFoundError:
        warn("ffmpeg not found; skipping mono conversion")
        _cleanup_temp(output_path)
        return file_path


# ---------------------------------------------------------------------------
# Fun-ASR async transcription
# ---------------------------------------------------------------------------

def submit_task(file_url: str, model: str, diarization: bool,
                language: str, channel_id: int) -> str:
    """Submit a transcription task. Returns the task_id."""
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }

    payload: dict = {
        "model": model,
        "input": {"file_urls": [file_url]},
        "parameters": {"channel_id": [channel_id]},
    }
    if language:
        payload["parameters"]["language_hints"] = [language]
    if diarization:
        payload["parameters"]["diarization_enabled"] = True

    info(f"Submitting transcription task: model={model}, diarization={diarization}, lang={language}")

    try:
        resp = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)
    except requests.RequestException as exc:
        raise FunAsrError("Failed to submit transcription task", detail=str(exc))

    if resp.status_code != 200:
        raise FunAsrError(
            f"Task submission failed (HTTP {resp.status_code})",
            detail=resp.text[:500],
        )

    data = resp.json()
    task_id = data.get("output", {}).get("task_id")
    if not task_id:
        raise FunAsrError(
            "No task_id in response",
            detail=json.dumps(data, ensure_ascii=False)[:500],
        )

    info(f"Task submitted: {task_id}")
    return task_id


def poll_task(task_id: str) -> dict:
    """Poll for task completion. Returns the full response on SUCCEEDED."""
    headers = {
        "Authorization": f"Bearer {get_api_key()}",
        "X-DashScope-Async": "enable",
    }

    start = time.time()
    last_status = ""

    while True:
        elapsed = time.time() - start
        if elapsed > MAX_WAIT:
            raise TimeoutError(
                f"Transcription timed out after {MAX_WAIT}s",
                detail=f"task_id={task_id}",
            )

        try:
            resp = requests.get(f"{QUERY_URL}/{task_id}", headers=headers, timeout=30)
        except requests.RequestException as exc:
            warn(f"Poll request failed, retrying: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        if resp.status_code != 200:
            warn(f"Poll returned HTTP {resp.status_code}, retrying")
            time.sleep(POLL_INTERVAL)
            continue

        data = resp.json()
        output = data.get("output", {})
        status = output.get("task_status", "")

        if status != last_status:
            info(f"Task status: {status} (elapsed: {elapsed:.0f}s)")
            last_status = status

        if status == "SUCCEEDED":
            info(f"Transcription completed (elapsed: {elapsed:.0f}s)")
            return data
        elif status == "FAILED":
            msg = output.get("message", "Unknown error")
            if any(p in msg for p in
                   ["ASR_RESPONSE_HAVE_NO_WORDS", "SUCCESS_WITH_NO_VALID_FRAGMENT"]):
                raise TaskFailedError(
                    "No valid speech detected in the audio. The file may be silent, "
                    "too quiet, or contain only noise. Do NOT retry automatically "
                    "- ask the user to provide different audio."
                )
            raise TaskFailedError("Transcription failed", detail=msg)
        elif status == "UNKNOWN":
            raise TaskFailedError("Task entered UNKNOWN status")

        time.sleep(POLL_INTERVAL)


def download_result(task_response: dict) -> dict:
    """Download transcription results from the completed task response."""
    results = task_response.get("output", {}).get("results", [])
    if not results:
        raise FunAsrError("No results in task response")

    all_data = []
    for i, r in enumerate(results):
        if r.get("subtask_status") != "SUCCEEDED":
            warn(f"Subtask {i}: unexpected status {r.get('subtask_status')}")
            continue

        url = r.get("transcription_url")
        if not url:
            warn(f"Subtask {i}: no transcription_url")
            continue

        info(f"Downloading result {i + 1}/{len(results)}")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            data["_file_url"] = r.get("file_url", "")
            all_data.append(data)
        except Exception as exc:
            warn(f"Failed to download result {i}: {exc}")

    if not all_data:
        raise FunAsrError("No transcription results could be downloaded")

    return all_data[0] if len(all_data) == 1 else all_data


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _ms_to_ts(ms: int) -> str:
    """Milliseconds -> HH:MM:SS"""
    s, ms_ = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m_ = divmod(m, 60)
    return f"{h:02d}:{m_:02d}:{s:02d}"


def _ms_to_srt_ts(ms: int) -> str:
    """Milliseconds -> HH:MM:SS,mmm (SRT format)"""
    s, ms_ = divmod(ms, 1000)
    m, s = divmod(s, 60)
    h, m_ = divmod(m, 60)
    return f"{h:02d}:{m_:02d}:{s:02d},{ms_:03d}"


def format_text(result: dict) -> str:
    """Format transcription as plain text with speaker labels and timestamps."""
    lines = []
    for t in result.get("transcripts", []):
        for sent in t.get("sentences", []):
            speaker = sent.get("speaker_id", "")
            bt = _ms_to_ts(sent.get("begin_time", 0))
            et = _ms_to_ts(sent.get("end_time", 0))
            text = sent.get("text", "").strip()

            header = f"[Speaker {speaker}] {bt} - {et}" if speaker else f"[{bt} - {et}]"
            lines.extend([header, text, ""])

    return "\n".join(lines)


def format_srt(result: dict) -> str:
    """Format transcription as SRT subtitle format."""
    blocks = []
    idx = 0
    for t in result.get("transcripts", []):
        for sent in t.get("sentences", []):
            idx += 1
            bt = _ms_to_srt_ts(sent.get("begin_time", 0))
            et = _ms_to_srt_ts(sent.get("end_time", 0))
            text = sent.get("text", "").strip()
            speaker = sent.get("speaker_id", "")
            tag = f"[S{speaker}] " if speaker else ""

            blocks.extend([str(idx), f"{bt} --> {et}", f"{tag}{text}", ""])

    return "\n".join(blocks)


def format_as(result: dict, fmt: str) -> str:
    """Format transcription result in the requested output format."""
    if fmt == "json":
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "srt":
        return format_srt(result)
    else:
        return format_text(result)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Transcribe audio using Alibaba Cloud DashScope Fun-ASR "
            "(non-real-time speech recognition)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
Examples:
  python fun_asr_cli.py meeting.mp3
  python fun_asr_cli.py meeting.mp3 --format json
  python fun_asr_cli.py meeting.mp3 --format srt
  python fun_asr_cli.py lecture.wav --no-diarization
  python fun_asr_cli.py japanese.mp3 --language ja --model paraformer-v2
  python fun_asr_cli.py audio.wav --quiet

Output formats:
  text    Plain text with speaker labels and timestamps (default)
  json    Full JSON with all metadata (timestamps, speaker IDs, confidence)
  srt     Standard SRT subtitle format for video editors

Version: {VERSION}
""",
    )

    parser.add_argument("file", nargs="?", help="Path to the audio file")
    parser.add_argument(
        "--model", default="fun-asr",
        choices=[
            "fun-asr", "paraformer-v2", "paraformer-v1",
            "fun-asr-mtl", "paraformer-mtl-v1",
        ],
        help="ASR model (default: fun-asr)",
    )
    parser.add_argument(
        "--diarization", action="store_true", default=True,
        help="Enable speaker diarization (default)",
    )
    parser.add_argument(
        "--no-diarization", dest="diarization", action="store_false",
        help="Disable speaker diarization",
    )
    parser.add_argument(
        "--language", default="zh",
        help="Language hint (default: zh). Common: zh, en, ja, ko, yue",
    )
    parser.add_argument(
        "--channel-id", type=int, default=0,
        help="Audio channel to transcribe (default: 0, first channel)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output file path (default: ~/.wmyskills/fun-asr/outputs/&lt;file&gt;_&lt;timestamp&gt;.&lt;ext&gt;)",
    )
    parser.add_argument(
        "--format", default="text", choices=["text", "json", "srt"],
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--keep-s3", action="store_true",
        help="Keep the temporary file on S3 after transcription",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit",
    )

    return parser


def main():
    load_env()
    ensure_utf8_console()
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(f"fun-asr v{VERSION}")
        sys.exit(EXIT_SUCCESS)

    if not args.file:
        parser.error("the following arguments are required: file")

    try:
        validate_config()

        file_path = args.file
        if not os.path.isfile(file_path):
            raise FileError(f"File not found: {file_path}")

        # 1. Probe audio (duration + channel count)
        dur, channels = probe_audio(file_path)
        est_cost = dur * PRICE_PER_SECOND
        info(f"Audio duration: {dur:.1f}s ({dur / 60:.1f} min)")
        info(f"Estimated cost: CNY {est_cost:.4f} (CNY {PRICE_PER_SECOND}/s)")

        if args.diarization and dur > 7200:
            raise FileError(
                f"Audio duration ({dur / 3600:.1f}h) exceeds the 2-hour limit "
                "for speaker diarization. Use --no-diarization or split the file."
            )

        # 2. Mono conversion (required for diarization)
        if args.diarization:
            file_path = ensure_mono(file_path, channels)

        # 3. Upload to S3
        s3_url, s3_key = upload_to_s3(file_path)

        # 4. Submit task
        task_id = submit_task(
            file_url=s3_url,
            model=args.model,
            diarization=args.diarization,
            language=args.language,
            channel_id=args.channel_id,
        )

        # 5. Poll until done
        task_response = poll_task(task_id)

        # 6. Download results
        result = download_result(task_response)

        # 7. Format output
        output = format_as(result, args.format)

        # 8. Save to output directory
        if args.output:
            out_path = args.output
            Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            base = Path(args.file).stem
            ext_map = {"text": "txt", "json": "json", "srt": "srt"}
            ts = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
            out_path = str(OUTPUT_DIR / f"{base}_{ts}.{ext_map[args.format]}")

        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(output)

        # 9. Report completion — print output file path for agent consumption
        print(f"Output file: {Path(out_path).resolve()}")

        # 10. Cleanup S3 (unless --keep-s3)
        if not args.keep_s3:
            delete_from_s3(s3_key)

    except FunAsrError as exc:
        fatal(exc)
    except KeyboardInterrupt:
        warn("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup_temp_files()
