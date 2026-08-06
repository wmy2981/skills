"""Call OpenAI-compatible vision model API."""

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


class VisionAPIError(Exception):
    """Raised on any API failure; message is safe to print to the user."""


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
                      max_tokens: int | None = 4096) -> dict:
    """Call the vision API and return structured response.

    Returns:
        {"content": str, "model": str, "usage": dict, "status": "ok"}
    """
    max_tokens = max_tokens or 4096
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
        raise VisionAPIError("Authentication failed. Check api_key in provider.yaml")
    except RateLimitError:
        raise VisionAPIError("Rate limited (429). Check your API quota and retry later.")
    except APITimeoutError:
        raise VisionAPIError("Request timed out. Image may be too large or network slow.")
    except APIConnectionError:
        raise VisionAPIError("Cannot connect to API. Check base_url in provider.yaml and network.")
    except APIError as e:
        status = getattr(e, "status_code", 0)
        if status == 400:
            raise VisionAPIError("Bad request. Model may not support image input.")
        if status == 404:
            raise VisionAPIError(f"Model '{model}' not found at provider endpoint.")
        raise VisionAPIError(f"API returned status {status}: {e}")

    if not resp.choices:
        raise VisionAPIError("API returned empty response (no choices)")
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
        "id": resp.id,
        "created": resp.created,
        "finish_reason": choice.finish_reason,
    }
