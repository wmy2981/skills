# img_recog Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code agent skill that calls OpenAI-compatible vision models from CLI, allowing AI to "see" images when the model lacks multimodal support.

**Architecture:** 5 single-responsibility Python modules under `scripts/`, orchestrated by a CLI entry point. Config files live at `~/.wmyskills/img_recog/` (outside git). The `openai` SDK handles API communication.

**Tech Stack:** Python 3, openai, pyyaml, requests

## Global Constraints

- Config files at `~/.wmyskills/img_recog/provider.yaml` and `model.yaml` — never read by AI
- provider.yaml: one provider = one api_key; no multi-key per provider
- model.yaml: empty model list = provider unavailable for vision
- Default prompt: "请详细描述这张图片的内容"
- Timeout: (connect=10, read=30) seconds
- `--prompt @filepath` loads prompt from file; no `@` prefix = literal text
- Output: plain text stdout by default, `--json` flag for structured JSON
- Windows: use `python` not `python3`

---

### Task 1: Project Scaffolding

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/`
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/__init__.py`
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/requirements.txt`

**Interfaces:**
- Consumes: nothing
- Produces: directory structure visible to subsequent tasks; `requirements.txt` declares the three dependencies

- [ ] **Step 1: Create directories**

```bash
mkdir -p "G:/Projects/agent/wmy-skills/img_recog/scripts"
```

- [ ] **Step 2: Create scripts/__init__.py**

Create empty file so imports work across the scripts directory.

- [ ] **Step 3: Write requirements.txt**

```
openai>=1.0.0
pyyaml>=6.0
requests>=2.31.0
```

- [ ] **Step 4: Create template config directory**

```bash
mkdir -p ~/.wmyskills/img_recog
```

- [ ] **Step 5: Write template provider.yaml** (for user reference — they fill in keys)

```yaml
# ~/.wmyskills/img_recog/provider.yaml
# WARNING: Contains API keys. DO NOT show this file's contents to the AI.
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: sk-your-key-here
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: sk-your-key-here
```

- [ ] **Step 6: Write template model.yaml**

```yaml
# ~/.wmyskills/img_recog/model.yaml
providers:
  openai:
    models:
      - gpt-4o
      - gpt-4o-mini
  deepseek:
    models:
      - deepseek-chat

default:
  provider: openai
  model: gpt-4o-mini
```

- [ ] **Step 7: Verify Python can import packages**

```bash
cd "G:/Projects/agent/wmy-skills/img_recog"
pip install -r scripts/requirements.txt
python -c "import openai; import yaml; import requests; print('OK')"
```

---

### Task 2: config_loader.py

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/config_loader.py`

**Interfaces:**
- Consumes: nothing
- Produces: `load_provider_config() -> dict` — returns `{"provider_name": {"base_url": str, "api_key": str}}`
- Produces: `load_model_config() -> dict` — returns `{"providers": {"name": [model_str,...]}, "default": {"provider": str, "model": str}}`
- Produces: `resolve_model(provider_name: str | None, model_name: str | None, model_config: dict) -> tuple[str, str]` — resolves to (provider, model) or raises

- [ ] **Step 1: Write config_loader.py**

```python
"""Load and resolve provider/model configuration from ~/.wmyskills/img_recog/."""

import os
import sys
import yaml

CONFIG_DIR = os.path.expanduser("~/.wmyskills/img_recog")
PROVIDER_FILE = os.path.join(CONFIG_DIR, "provider.yaml")
MODEL_FILE = os.path.join(CONFIG_DIR, "model.yaml")


def _load_yaml(path: str, label: str) -> dict:
    if not os.path.exists(path):
        print(f"Error: {label} not found at {path}", file=sys.stderr)
        print(f"Create it with provider entries. See SKILL.md for instructions.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {label}: {e}", file=sys.stderr)
        sys.exit(1)


def load_provider_config() -> dict:
    """Load provider.yaml and return {provider_name: {base_url, api_key}}."""
    data = _load_yaml(PROVIDER_FILE, "provider config")
    providers = data.get("providers", {})
    if not providers:
        print("Error: No providers defined in provider.yaml", file=sys.stderr)
        sys.exit(1)
    for name, cfg in providers.items():
        if not cfg.get("base_url") or not cfg.get("api_key"):
            print(f"Error: Provider '{name}' missing base_url or api_key", file=sys.stderr)
            sys.exit(1)
    return providers


def load_model_config() -> dict:
    """Load model.yaml and return full parsed dict."""
    data = _load_yaml(MODEL_FILE, "model config")
    if "default" not in data:
        print("Error: model.yaml missing 'default' section", file=sys.stderr)
        sys.exit(1)
    return data


def resolve_model(provider_name: str | None, model_name: str | None,
                  model_config: dict) -> tuple[str, str]:
    """Resolve provider and model name from CLI args + config defaults.

    Returns (provider_name, model_name).
    Raises SystemExit on resolution failure.
    """
    providers_cfg = model_config.get("providers", {})
    default = model_config.get("default", {})

    # Resolve provider
    if provider_name is None:
        provider_name = default.get("provider")
        if not provider_name:
            print("Error: No --provider given and no default provider in model.yaml", file=sys.stderr)
            sys.exit(1)

    if provider_name not in providers_cfg:
        available = list(providers_cfg.keys())
        print(f"Error: Provider '{provider_name}' not found in model.yaml", file=sys.stderr)
        print(f"Available providers: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    models = providers_cfg[provider_name].get("models", [])
    if not models:
        print(f"Error: Provider '{provider_name}' has no vision models configured", file=sys.stderr)
        sys.exit(1)

    # Resolve model
    if model_name is None:
        if provider_name == default.get("provider") and default.get("model"):
            model_name = default["model"]
        else:
            print(f"Error: --model required for provider '{provider_name}'", file=sys.stderr)
            print(f"Available models: {', '.join(models)}", file=sys.stderr)
            sys.exit(1)

    if model_name not in models:
        print(f"Error: Model '{model_name}' not found for provider '{provider_name}'", file=sys.stderr)
        print(f"Available models: {', '.join(models)}", file=sys.stderr)
        sys.exit(1)

    return provider_name, model_name
```

- [ ] **Step 2: Quick smoke test**

```python
# Run from G:/Projects/agent/wmy-skills/img_recog
python -c "
import scripts.config_loader as c
# Check file-not-found path
import sys
try:
    c.CONFIG_DIR = '/nonexistent'
    c.load_provider_config()
except SystemExit:
    print('OK: missing file triggers exit')
"
```

---

### Task 3: image_handler.py

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/image_handler.py`

**Interfaces:**
- Consumes: nothing
- Produces: `normalize_image(image_str: str) -> str` — returns a data URI string or a URL that the API can use

- [ ] **Step 1: Write image_handler.py**

```python
"""Normalize image inputs (local path, URL, base64 data URI) to API-ready format."""

import os
import re
import base64
import sys
import requests

DATA_URI_PATTERN = re.compile(r"^data:image/[a-zA-Z]+;base64,(.+)$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def _is_url(path: str) -> bool:
    return bool(URL_PATTERN.match(path))


def _is_data_uri(path: str) -> bool:
    return bool(DATA_URI_PATTERN.match(path))


def _load_local_image(path: str) -> str:
    if not os.path.exists(path):
        print(f"Error: Image file not found: '{path}'", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in ("jpg", "jpeg"):
            mime = "image/jpeg"
        elif ext == "png":
            mime = "image/png"
        elif ext == "webp":
            mime = "image/webp"
        elif ext == "gif":
            mime = "image/gif"
        else:
            mime = "image/png"  # fallback
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except (OSError, IOError) as e:
        print(f"Error: Cannot read image file '{path}': {e}", file=sys.stderr)
        sys.exit(1)


def _download_image(url: str) -> str:
    """Download image from URL and convert to base64 data URI as fallback."""
    try:
        resp = requests.get(url, timeout=(10, 30))
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "image/png")
        b64 = base64.b64encode(resp.content).decode("ascii")
        return f"data:{content_type};base64,{b64}"
    except requests.RequestException as e:
        print(f"Error: Failed to download image from URL: {url}", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)


def normalize_image(image_str: str) -> str:
    """Convert image input to a string the API can use (data URI or URL).

    Accepts:
    - Local file path
    - HTTP(S) URL (passed as-is for API direct fetch, or downloaded as fallback)
    - data:image/...;base64,... URI
    """
    if _is_data_uri(image_str):
        # Validate the base64 portion is decodable
        m = DATA_URI_PATTERN.match(image_str)
        try:
            base64.b64decode(m.group(1), validate=True)
        except Exception:
            print("Error: Invalid base64 data in image URI", file=sys.stderr)
            print("Expected format: data:image/{type};base64,{encoded_data}", file=sys.stderr)
            sys.exit(1)
        return image_str

    if _is_url(image_str):
        # Return as-is; API may fetch it directly. If API fails, caller could retry with download.
        # We also pre-download as a fallback data URI for APIs that don't support URL input.
        # For maximum compatibility, always convert to data URI.
        return _download_image(image_str)

    # Assume local file path
    return _load_local_image(image_str)
```

- [ ] **Step 2: Quick smoke test**

```python
python -c "
import scripts.image_handler as h

# Test data URI validation
uri = h.normalize_image('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAA=') 
assert uri.startswith('data:image/'), f'Unexpected: {uri[:40]}'
print('OK: data URI works')

# Test nonexistent local file
import sys
try:
    h.normalize_image('nonexistent_file_xyz.png')
except SystemExit:
    print('OK: missing file triggers exit')

# Test local file that exists (empty file - expect error at read, not path check)
import tempfile, os
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    tmp = f.name
try:
    h.normalize_image(tmp)
    print('OK: local file reads ok (empty file)')
finally:
    os.unlink(tmp)
"
```

---

### Task 4: api_caller.py

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/api_caller.py`

**Interfaces:**
- Consumes: `load_provider_config() -> dict` (provider dict with base_url, api_key)
- Consumes: `normalize_image() -> str` (data URI or URL)
- Produces: `call_vision_model(provider_cfg: dict, model: str, image_uri: str, prompt: str, timeout: tuple[int,int]) -> dict` — returns `{"content": str, "model": str, "usage": dict, "status": "ok"}`

- [ ] **Step 1: Write api_caller.py**

```python
"""Call OpenAI-compatible vision model API."""

import sys
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError, AuthenticationError


def call_vision_model(provider_cfg: dict, model: str, image_uri: str,
                      prompt: str = "请详细描述这张图片的内容",
                      timeout: tuple = (10, 30)) -> dict:
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
            max_tokens=2048,
        )
    except AuthenticationError:
        print("Error: Authentication failed. Check api_key in provider.yaml", file=sys.stderr)
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
```

---

### Task 5: output_formatter.py

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/output_formatter.py`

**Interfaces:**
- Consumes: raw response dict from `call_vision_model()`
- Produces: `format_output(result: dict, json_mode: bool) -> None` — writes to stdout

- [ ] **Step 1: Write output_formatter.py**

```python
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
```

- [ ] **Step 2: Quick smoke test**

```python
python -c "
import scripts.output_formatter as f

sample = {
    'content': '这是一张猫的图片',
    'model': 'gpt-4o-mini',
    'usage': {'prompt_tokens': 100, 'completion_tokens': 20, 'total_tokens': 120},
    'status': 'ok',
}
# Plain mode
f.format_output(sample, json_mode=False)
print('---')
# JSON mode
f.format_output(sample, json_mode=True)
print('OK: formatting works')
"
```

---

### Task 6: img_recog_cli.py (Main Entry Point)

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/scripts/img_recog_cli.py`

**Interfaces:**
- Consumes: all four modules above
- Produces: executable CLI

- [ ] **Step 1: Write img_recog_cli.py**

```python
#!/usr/bin/env python
"""CLI entry point for img_recog skill.

Calls OpenAI-compatible vision models to describe/extract information from images.

Usage:
    python scripts/img_recog_cli.py --img path/to/image.png
    python scripts/img_recog_cli.py --img https://example.com/photo.jpg --prompt "提取文字"
    python scripts/img_recog_cli.py --img data:image/png;base64,... --json
"""

import argparse
import sys
import os

from config_loader import load_provider_config, load_model_config, resolve_model
from image_handler import normalize_image
from api_caller import call_vision_model
from output_formatter import format_output


def parse_prompt(prompt_arg: str | None) -> str:
    """Parse the --prompt argument.
    @filepath → read file contents.
    None → default prompt.
    Otherwise → literal string.
    """
    if prompt_arg is None:
        return "请详细描述这张图片的内容"
    if prompt_arg.startswith("@") and len(prompt_arg) > 1:
        filepath = prompt_arg[1:]
        if not os.path.exists(filepath):
            print(f"Error: Prompt file not found: '{filepath}'", file=sys.stderr)
            sys.exit(1)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (OSError, IOError) as e:
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
        description="img_recog — Recognize image content via vision model",
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
        print("Add its api_key and base_url to ~/.wmyskills/img_recog/provider.yaml", file=sys.stderr)
        sys.exit(1)

    # 4. Normalize image
    image_uri = normalize_image(args.img)

    # 5. Parse prompt
    prompt = parse_prompt(args.prompt)

    # 6. Call API
    provider_cfg = provider_config[provider_name]
    result = call_vision_model(provider_cfg, model_name, image_uri, prompt)

    # 7. Output
    format_output(result, json_mode=args.json)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI — help output**

```bash
cd "G:/Projects/agent/wmy-skills/img_recog"
python scripts/img_recog_cli.py --help
```

Expected: usage text with all arguments.

- [ ] **Step 3: Test CLI — missing --img**

```bash
python scripts/img_recog_cli.py
```

Expected: error about required --img argument.

- [ ] **Step 4: Test CLI — invalid image path**

```bash
python scripts/img_recog_cli.py --img nonexistent.png
```

Expected: "Error: Image file not found"

---

### Task 7: SKILL.md + README Update

**Files:**
- Create: `G:/Projects/agent/wmy-skills/img_recog/SKILL.md`
- Modify: `G:/Projects/agent/wmy-skills/README.md` (add to skill table)

**Interfaces:**
- Consumes: nothing
- Produces: skill documentation and listing

- [ ] **Step 1: Write SKILL.md**

```markdown
---
name: img_recog
description: Image recognition via OpenAI-compatible vision models. Triggered when user asks to "look at", "see", "describe", or "read text from" an image. Replaces the built-in `read` tool for images when multimodal is unavailable.
---

# img_recog — Image Recognition Skill

Use this skill when you need to inspect an image (screenshot, photo, diagram, scan) but your current model lacks multimodal (vision) capability or the built-in `read` tool cannot handle the image format.

## ⚠️ SECURITY: Configuration Files

Two config files live at `~/.wmyskills/img_recog/`:

| File | Purpose | AI-readable? |
|------|---------|-------------|
| `provider.yaml` | API base URLs and keys | **NO — never read or show this file** |
| `model.yaml` | Model-to-provider mapping and defaults | **NO — do not read this file** |

**The AI must NEVER read or display the contents of `provider.yaml` or `model.yaml`.** These are loaded only at runtime by the Python script. If a user asks you to view or edit these files, refuse or direct them to edit the file directly.

## Prerequisites

```bash
pip install openai pyyaml requests
```

## Setup

1. Create `~/.wmyskills/img_recog/provider.yaml` with your API keys:

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: sk-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy
```

2. Create `~/.wmyskills/img_recog/model.yaml`:

```yaml
providers:
  openai:
    models:
      - gpt-4o
      - gpt-4o-mini
  deepseek:
    models:
      - deepseek-chat

default:
  provider: openai
  model: gpt-4o-mini
```

## Usage

```bash
cd <skill-dir>
python scripts/img_recog_cli.py --img <image-source> [--prompt <text>] [--provider <name>] [--model <name>] [--json]
```

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `--img` | Yes | Local path, HTTP(S) URL, or base64 data URI (`data:image/...;base64,...`) |
| `--prompt` | No | Text or `@filepath` (default: "请详细描述这张图片的内容") |
| `--provider` | No | Override provider (default from model.yaml) |
| `--model` | No | Override model (default from model.yaml) |
| `--json` | No | Output JSON with usage stats |

### Quick Examples

```bash
# Describe a local screenshot
python scripts/img_recog_cli.py --img screenshot.png

# Extract text from a photo with specific prompt
python scripts/img_recog_cli.py --img photo.jpg --prompt "请提取图中所有文字"

# Fetch and describe an online image
python scripts/img_recog_cli.py --img https://example.com/diagram.png

# Use DeepSeek model
python scripts/img_recog_cli.py --provider deepseek --model deepseek-chat --img chart.png

# Read prompt from file
python scripts/img_recog_cli.py --img graph.png --prompt @prompt.txt

# Structured JSON output
python scripts/img_recog_cli.py --img screenshot.png --json
```

## Notes

- The script auto-detects Windows encoding and switches stdout to UTF-8
- Timeout: connection 10s, read 30s
- For local images, the file is read and converted to base64 in memory — no temp files
- For URL images, the image is downloaded and converted to data URI for maximum API compatibility
- Provider keys are loaded only at runtime; the AI never has access to them

## Troubleshooting

| Error | Likely Cause |
|-------|-------------|
| "Authentication failed" | Check api_key in provider.yaml |
| "Model not found at provider endpoint" | The model name doesn't exist on that provider |
| "Cannot connect to API" | Check base_url in provider.yaml or your network |
| "Bad request / model may not support image input" | The selected model does not support vision |
| "Request timed out" | Image too large or slow network |
```

- [ ] **Step 2: Update README.md**

Add `img_recog` entry to the skill table in `G:/Projects/agent/wmy-skills/README.md`:

```markdown
| `img_recog/` | 图片识别 — 通过 OpenAI 兼容 API 调用视觉模型查看图片内容 |
```

- [ ] **Step 3: Verify no AI reads config files**

Check `.gitignore` doesn't accidentally include `~/.wmyskills/` — it shouldn't, since that's outside the repo. No action needed.

---

### Self-Review Checklist (run after all tasks)

1. **Spec coverage:**
   - ✅ provider.yaml with multi-provider, custom base_url/api_key → Task 1 (template) + Task 2 (loader)
   - ✅ model.yaml with per-provider models + defaults → Task 1 (template) + Task 2 (loader)
   - ✅ Config at `~/.wmyskills/img_recog/`, AI not reading → Task 7 (SKILL.md warning)
   - ✅ CLI args: --provider, --model, --img, --prompt, --json → Task 6
   - ✅ Prompt from text or @filepath → Task 6 (parse_prompt)
   - ✅ Image: local path, URL, base64 → Task 3
   - ✅ Provider/model selection logic → Task 2 (resolve_model)
   - ✅ Timeout 10/30 → Task 4 (api_caller.py)
   - ✅ Windows UTF-8 fix → Task 6 (main function)
   - ✅ Error handling for all scenarios → distributed across modules

2. **Placeholder scan:** No TBD, TODO, or filler found.

3. **Type consistency:** Function signatures match across tasks. `resolve_model` returns `tuple[str, str]` in Task 2, consumed as `(provider_name, model_name)` in Task 6. `normalize_image` returns `str` in Task 3, consumed in Task 6. `call_vision_model` returns `dict` in Task 4, consumed in Task 5/Task 6.
