#!/usr/bin/env python
"""CLI entry point for img-recog skill.

Calls OpenAI-compatible vision models to describe/extract information from images.

Usage:
    python scripts/img_recog_cli.py --img path/to/image.png
    python scripts/img_recog_cli.py --img https://example.com/photo.jpg --prompt "提取文字"
    python scripts/img_recog_cli.py --img data:image/png;base64,... --json
"""

import argparse
import os
import sys

from api_caller import call_vision_model
from config_loader import load_model_config, load_provider_config, resolve_model
from image_compressor import compress_data_uri
from image_handler import normalize_image
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
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

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

    # 5. Optional compression (skipped entirely unless --compact is passed)
    compact_stats = None
    if args.compact:
        image_uri, compact_stats = compress_data_uri(image_uri, args.compact)
        if not args.json:
            print(compact_summary(compact_stats), file=sys.stderr)

    # 6. Parse prompt
    prompt = parse_prompt(args.prompt)

    # 7. Call API
    provider_cfg = provider_config[provider_name]
    result = call_vision_model(provider_cfg, model_name, image_uri, prompt)

    # 8. Output
    if compact_stats is not None:
        result["compression"] = compact_stats
    format_output(result, json_mode=args.json)


if __name__ == "__main__":
    main()
