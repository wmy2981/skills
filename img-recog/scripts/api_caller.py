"""Call OpenAI-compatible vision model API."""

import sys
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError, AuthenticationError, RateLimitError


def call_vision_model(provider_cfg: dict, model: str, image_uri: str,
                      prompt: str = "请详细描述这张图片的内容",
                      timeout: tuple = (10, 30),
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

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_uri}},
                    ],
                }
            ],
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
