# img-recog Skill — Design Document

## Overview

A Claude Code agent skill for image recognition using OpenAI-compatible vision models. Serves as a `read`-tool replacement when the model does not support multimodal input. Uses Python + `openai` SDK to call vision-capable models.

## Project Path

`G:/Projects/agent/wmy-skills/img-recog/`

## Directory Structure

```
img-recog/
├── SKILL.md                    # Skill definition, usage, trigger keywords
└── scripts/
    ├── config_loader.py        # Read provider.yaml / model.yaml
    ├── image_handler.py        # Handle local/URL/base64 image → API payload
    ├── api_caller.py           # Call vision model via openai SDK
    ├── output_formatter.py     # Format output (plain text / JSON)
    ├── img-recog_cli.py        # CLI entry point, argparse
    └── requirements.txt        # openai, pyyaml, requests
```

## Configuration

### Location

`~/.wmyskills/img-recog/provider.yaml` — API provider credentials
`~/.wmyskills/img-recog/model.yaml` — Model mapping and defaults

These files are outside the git repo and must NOT be read by AI (enforced via SKILL.md instruction only).

### provider.yaml

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: sk-xxxxx
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: sk-yyyyy
```

- One provider = one `api_key`. No multi-key per provider.
- Loaded only at runtime by the Python script, never by AI tooling.

### model.yaml

```yaml
providers:
  openai:
    models:
      - gpt-4o
      - gpt-4o-mini
  deepseek:
    models:
      - deepseek-chat
  siliconflow: {}   # Empty = no vision models for this provider

default:
  provider: openai
  model: gpt-4o-mini
```

- Empty model list → provider is not available for image recognition.
- Provider not listed in `providers` → same as empty (unavailable).
- `default` section specifies fallback provider and model when CLI args omit them.

## CLI Interface

```
usage: img-recog_cli.py [-h] [--provider PROVIDER] [--model MODEL]
                        --img IMG [--prompt PROMPT] [--json]
```

| Argument   | Required | Description |
|------------|----------|-------------|
| `--provider` | No | Override provider. Defaults to `default.provider` in model.yaml |
| `--model` | No | Override model. Defaults to `default.model` if default provider matches; else must be specified if provider has multiple models |
| `--img` | Yes | Image source: local path, HTTP(S) URL, or data URI (`data:image/...;base64,...`) |
| `--prompt` | No | Prompt text, or `@filepath` to read from file. Default: "请详细描述这张图片的内容" |
| `--json` | No | Output JSON with `status`, `response`, `usage` fields instead of plain text |

### Provider/Model Resolution

1. Read model.yaml → build provider→models map and defaults
2. No `--provider` → use `default.provider`
3. `--provider` given → validate it exists and has non-empty model list
4. No `--model` + default provider matches → use `default.model`
5. No `--model` + provider has multiple models → error with available list
6. `--model` given → validate it's in the provider's model list

### Examples

```bash
python scripts/img-recog_cli.py --img screenshot.png
python scripts/img-recog_cli.py --provider deepseek --img photo.jpg --prompt "提取文字"
python scripts/img-recog_cli.py --img https://example.com/pic.jpg --prompt @prompt.txt
python scripts/img-recog_cli.py --img data:image/png;base64,iVBOR... --json
```

## Data Flow

```
CLI (argparse)
  ↓
config_loader.py → parse model.yaml → resolve provider & model
config_loader.py → parse provider.yaml → get api_key & base_url
  ↓
image_handler.py → normalize image:
  ├─ local file → read → base64 → data URI
  ├─ HTTP(S) URL → pass URL directly (API-supported)
  └─ data URI → extract and validate base64
  ↓
api_caller.py → openai.ChatCompletion.create(
    model=model,
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_uri}}
        ]
    }],
    max_tokens=2048,
    timeout=(10, 30)  # connect=10s, read=30s
)
  ↓
output_formatter.py → plain text or JSON → stdout
```

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Local image not found | Exit with error, show path |
| URL unreachable | Try base64 fallback; if still fails, show URL error |
| Invalid base64 data URI | Exit with format hint |
| API 401 (auth failure) | Hint to check provider.yaml api_key |
| Model doesn't support vision | Error: model not suitable |
| Request timeout (30s read) | Hint: network or image too large |
| provider.yaml missing | Hint to create at ~/.wmyskills/img-recog/ |
| model.yaml missing | Same as above |
| Unknown --provider | List available providers |
| Unknown --model | List available models for that provider |

## Dependencies

- `openai` — OpenAI SDK for API calls
- `pyyaml` — YAML config parsing
- `requests` — HTTP(S) image download fallback

## Security

- API keys stored in `provider.yaml` outside git repo
- SKILL.md instructs AI not to read provider.yaml
- No key exposure through error messages or debug output
- Base64 image data handled in-memory, not written to disk
