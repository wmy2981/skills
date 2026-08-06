"""Format and print vision API results."""

import json


def format_output(result: dict, json_mode: bool = False) -> None:
    """Print the result to stdout in plain text or JSON."""
    if json_mode:
        output = {
            "status": result.get("status", "ok"),
            "id": result.get("id"),
            "created": result.get("created"),
            "finish_reason": result.get("finish_reason"),
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
        # Plain text: [result] block only (model/usage info is not shown;
        # metadata block is printed separately by the CLI)
        print("[result]")
        print(result.get("content", ""))
