"""Call OpenAI-compatible vision model API."""

import sys
from pathlib import Path

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

# Shared system prompt: tells the vision model its output is consumed by
# another AI, not a human (loaded at runtime, missing file is not an error).
SYSTEM_PROMPT_FILE = (
    Path(__file__).resolve().parent.parent / "references" / "prompts" / "_system.md"
)


def load_system_prompt() -> str | None:
    """Return the system prompt text, or None if the file is unavailable."""
    try:
        content = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return content or None


def call_vision_model(provider_cfg: dict, model: str, image_uri: str,
                      prompt: str = "Please describe this image in detail",
                      timeout: tuple = (10, 120),
                      max_tokens: int = 4096) -> dict:
    """Call the vision API and return structured response.

    Returns:
        {"content": str, "model": str, "usage": dict, "status": "ok"}
    """
    client = OpenAI(
        base_url=provider_cfg["base_url"].rstrip("/") + "/",
        api_key=provider_cfg["api_key"],
        timeout=timeout,
    )

    messages = []
    system_prompt = load_system_prompt()
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_uri}},
            ],
        }
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    except AuthenticationError:
        print("Error: Authentication failed. Check api_key in provider.yaml", file=sys.stderr)
        sys.exit(1)
    except RateLimitError:
        print("Error: Rate limited (429). Check your API quota and retry later.", file=sys.stderr)
        sys.exit(1)
    except APITimeoutError:
        print("Error: Request timed out. Image may be too large or network slow.", file=sys.stderr)
        sys.exit(1)
    except APIConnectionError:
        print("Error: Cannot connect to API. Check base_url in provider.yaml and network.", file=sys.stderr)
        sys.exit(1)
    except APIError as e:
        status = getattr(e, "status_code", 0)
        if status == 400:
            print("Error: Bad request. Model may not support image input.", file=sys.stderr)
        elif status == 404:
            print(f"Error: Model '{model}' not found at provider endpoint.", file=sys.stderr)
        else:
            print(f"Error: API returned status {status}: {e}", file=sys.stderr)
        sys.exit(1)

    if not resp.choices:
        print("Error: API returned empty response (no choices)", file=sys.stderr)
        sys.exit(1)
    choice = resp.choices[0]
    content = choice.message.content or ""
    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
    }

    return {
        "content": content,
        "model": resp.model,
        "usage": usage,
        "status": "ok",
    }
