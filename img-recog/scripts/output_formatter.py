"""Format and print vision API results."""

import json
import sys


def format_output(result: dict, json_mode: bool = False) -> None:
    """Print the result to stdout in plain text or JSON."""
    if json_mode:
        output = {
            "status": result.get("status", "ok"),
            "response": result.get("content", ""),
            "model": result.get("model", ""),
            "usage": result.get("usage", {}),
        }
        compression = result.get("compression")
        if compression is not None:
            output["compression"] = compression
        metadata = result.get("metadata")
        if metadata is not None:
            output["metadata"] = metadata
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        content = result.get("content", "")
        print(content)
        # Print usage info to stderr so it doesn't interfere with piping
        usage = result.get("usage", {})
        if usage:
            usage_line = (f"[Tokens: {usage.get('prompt_tokens', '?')} prompt / "
                          f"{usage.get('completion_tokens', '?')} completion | "
                          f"Model: {result.get('model', '?')}]")
            print(usage_line, file=sys.stderr)
