#!/usr/bin/env python
"""CLI entry point for img-recog skill.

Calls OpenAI-compatible vision models to describe/extract information from images.

Usage:
    python scripts/img_recog_cli.py --img path/to/image.png
    python scripts/img_recog_cli.py --img https://example.com/photo.jpg --prompt "提取文字"
    python scripts/img_recog_cli.py --img data:image/png;base64,... --json
"""

import argparse
import base64
import json
import os
import sys
import threading

from api_caller import VisionAPIError, call_vision_model
from config_loader import load_model_config, load_provider_config, resolve_model
from image_compressor import compress_data_uri
from image_handler import DATA_URI_PATTERN, normalize_image
from image_metadata import FIELDS, empty_metadata, get_metadata
from output_formatter import format_output


def _fmt_bytes(n: int) -> str:
    """Human-readable byte size."""
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f}MB"
    return f"{n / 1024:.1f}KB"


def compact_summary(stats: dict) -> str:
    """One-line human summary of compression stats."""
    if stats.get("skipped"):
        reason = "animated image" if stats.get("reason") == "animated" else "already within target"
        return f"[Compressed: skipped — {reason}]"
    return (f"[Compressed: {_fmt_bytes(stats['original_bytes'])} -> "
            f"{_fmt_bytes(stats['compressed_bytes'])} (WebP {stats['width']}x{stats['height']})]")


def _print_metadata_block(md: dict) -> None:
    """Print the [metadata] block to stderr (non-JSON mode)."""
    print("[metadata]", file=sys.stderr)
    for key in FIELDS:
        value = md[key]
        if key == "location" and isinstance(value, dict):
            value = f"{value['lat']}, {value['lon']}"
        print(f"{key}: {value if value is not None else 'null'}", file=sys.stderr)


def _metadata_worker(image_uri: str, json_mode: bool, holder: dict) -> None:
    """Background thread: extract metadata, print block (non-JSON), store result.

    Never raises and never aborts the flow — a failed acquisition yields an
    all-null metadata dict plus a warning line; recognition proceeds regardless.
    """
    md = None
    reason = ""
    try:
        m = DATA_URI_PATTERN.match(image_uri)
        if not m:
            raise ValueError("image is not a data URI")
        md = get_metadata(base64.b64decode(m.group(1)))
        if md is None:
            reason = "cannot probe image (unrecognized or corrupt data)"
    except Exception as e:
        reason = str(e)
    if md is None:
        print(f"Error: metadata acquisition failed: {reason or 'unknown error'}", file=sys.stderr)
        md = empty_metadata()
    holder["metadata"] = md
    if not json_mode:
        _print_metadata_block(md)


def _emit_error_json(error: str, holder: dict) -> None:
    """JSON-mode error output: status=error, with metadata when requested."""
    output = {"status": "error", "error": str(error)}
    if "metadata" in holder:
        output["metadata"] = holder["metadata"]
    print(json.dumps(output, ensure_ascii=False, indent=2))


def parse_prompt(prompt_arg: str | None) -> str:
    """Parse the --prompt argument.
    @filepath -> read file contents.
    None -> default prompt.
    Otherwise -> literal string.
    """
    if prompt_arg is None:
        return "Please describe this image in detail"
    if prompt_arg.startswith("@") and len(prompt_arg) > 1:
        filepath = prompt_arg[1:]
        if not os.path.exists(filepath):
            print(f"Error: Prompt file not found: '{filepath}'", file=sys.stderr)
            sys.exit(1)
        try:
            with open(filepath, encoding="utf-8") as f:
                return f.read().strip()
        except OSError as e:
            print(f"Error: Cannot read prompt file '{filepath}': {e}", file=sys.stderr)
            sys.exit(1)
    return prompt_arg


def main():
    # Handle Windows encoding
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="img-recog — Recognize image content via vision model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --img screenshot.png\n"
            "  %(prog)s --provider deepseek --img photo.jpg --prompt \"提取文字\"\n"
            "  %(prog)s --img https://example.com/pic.jpg --prompt @prompt.txt\n"
            "  %(prog)s --img data:image/png;base64,iVBOR... --json\n"
        ),
    )
    parser.add_argument("--provider", help="API provider name (default: from model.yaml)")
    parser.add_argument("--model", help="Model name (default: from model.yaml)")
    parser.add_argument("--img", required=True, help="Image: local path, URL, or data URI")
    parser.add_argument("--prompt", help="Prompt text, or @filepath to read from file")
    parser.add_argument("--compact", help="Compress image to target size as WebP before sending, "
                                          "e.g. 500KB / 0.5MB / 512000B (bare numbers are KB)")
    parser.add_argument("--metadata", action="store_true",
                        help="Also extract image metadata (size/width/height/color/device/app/"
                             "time/location) in parallel and output it to the agent; not sent to the model")
    parser.add_argument("--max-tokens", type=int,
                        help="Maximum output tokens (default: 4096)")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    if args.max_tokens is not None and args.max_tokens <= 0:
        parser.error("--max-tokens must be a positive integer")

    # 1. Load configs
    model_config = load_model_config()
    provider_config = load_provider_config()

    # 2. Resolve provider and model
    provider_name, model_name = resolve_model(args.provider, args.model, model_config)

    # 3. Verify provider has credentials
    if provider_name not in provider_config:
        print(f"Error: Provider '{provider_name}' has no credentials in provider.yaml", file=sys.stderr)
        print("Add its api_key and base_url to ~/.wmyskills/img-recog/provider.yaml", file=sys.stderr)
        sys.exit(1)

    # 4. Normalize image
    image_uri = normalize_image(args.img)

    # 5. Metadata in parallel — runs while recognition proceeds below;
    #    never blocks or aborts the flow, and is never sent to the model.
    metadata_holder: dict = {}
    metadata_thread = None
    if args.metadata:
        metadata_thread = threading.Thread(
            target=_metadata_worker, args=(image_uri, args.json, metadata_holder), daemon=True
        )
        metadata_thread.start()

    # 6. Optional compression (skipped entirely unless --compact is passed;
    #    metadata always reflects the original image)
    compact_stats = None
    if args.compact:
        image_uri, compact_stats = compress_data_uri(image_uri, args.compact)
        if not args.json:
            print(compact_summary(compact_stats), file=sys.stderr)

    # 7. Parse prompt
    prompt = parse_prompt(args.prompt)

    # 8. Call API
    provider_cfg = provider_config[provider_name]
    try:
        result = call_vision_model(provider_cfg, model_name, image_uri, prompt,
                                   max_tokens=args.max_tokens)
    except VisionAPIError as e:
        if metadata_thread is not None:
            metadata_thread.join()
        if args.json:
            _emit_error_json(e, metadata_holder)
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # 9. Output (metadata merged only when --metadata was used)
    if metadata_thread is not None:
        metadata_thread.join()
        result["metadata"] = metadata_holder["metadata"]
    if compact_stats is not None:
        result["compression"] = compact_stats
    format_output(result, json_mode=args.json)


if __name__ == "__main__":
    main()
