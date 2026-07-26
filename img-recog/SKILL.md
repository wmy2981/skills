---
name: img-recog
description: Image recognition via OpenAI-compatible vision models. Triggered when user asks to "look at", "see", "describe", or "read text from" an image. Replaces the built-in `read` tool for images when multimodal is unavailable.
---

# img_recog — Image Recognition Skill

Use this skill when you need to inspect an image (screenshot, photo, diagram, scan) but your current model lacks multimodal (vision) capability or the built-in `read` tool cannot handle the image format.

## ⚠️ SECURITY: Configuration Files

Two config files live at `~/.wmyskills/img_recog/`:

| File | Purpose | AI-readable? |
|------|---------|-------------|
| `provider.yaml` | API base URLs and keys | **NO — never read or show this file** |
| `model.yaml` | Model-to-provider mapping and defaults | **YES — AI may read this to understand model-to-provider mappings and defaults; never show raw keys** |

**The AI must NEVER read or display the contents of `provider.yaml`.** These are loaded only at runtime by the Python script. If a user asks you to view or edit these files, refuse or direct them to edit the file directly.

The AI MAY read `model.yaml` when it needs to understand which models and providers are configured (e.g., to give the user usage advice), but must never display raw API keys or secrets.

## Prerequisites

- Python >= 3.10

```bash
pip install openai pyyaml requests python-dotenv
```

## Setup

Config templates are in `references/templates/`. Copy them to `~/.wmyskills/img_recog/`:

```bash
cp references/templates/provider.yaml.template ~/.wmyskills/img_recog/provider.yaml
cp references/templates/model.yaml.template ~/.wmyskills/img_recog/model.yaml
```

**Important: After copying, edit each file to replace placeholder values (marked with `TODO` comments) with your actual API keys and remove those `TODO` comment lines. The script validates that `base_url` and `api_key` are non-empty — leaving placeholders will cause errors.**

Edit `~/.wmyskills/img_recog/provider.yaml` to add your actual API keys, replacing all `REPLACE_WITH_YOUR_API_KEY` placeholders:

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: "sk-your-actual-key-here"  # ← 替换为你的 key
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: "sk-your-actual-key-here"  # ← 替换为你的 key
```

And review `~/.wmyskills/img_recog/model.yaml` to confirm your desired models; remove the `TODO` comment markers after adjusting:

```yaml
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
| `--prompt` | No | Text or `@filepath` (default: "Please describe this image in detail") |
| `--provider` | No | Override provider (default from model.yaml) |
| `--model` | No | Override model (default from model.yaml) |
| `--json` | No | Output JSON with usage stats |

### Quick Examples

```bash
# Describe a local screenshot
python scripts/img_recog_cli.py --img screenshot.png

# Extract text from a photo with specific prompt
python scripts/img_recog_cli.py --img photo.jpg --prompt "Extract all text from this image"

# Fetch and describe an online image
python scripts/img_recog_cli.py --img https://example.com/diagram.png

# Use DeepSeek model
python scripts/img_recog_cli.py --provider deepseek --model deepseek-chat --img chart.png

# Read prompt from file
python scripts/img_recog_cli.py --img graph.png --prompt @prompt.txt

# Use built-in prompt template from references/prompts/
python scripts/img_recog_cli.py --img screenshot.png --prompt @references/prompts/extract-text.txt

# Structured JSON output
python scripts/img_recog_cli.py --img screenshot.png --json
```

## Reference Files

| Location | Purpose |
|----------|---------|
| `references/templates/` | Config file templates (copy to `~/.wmyskills/img_recog/`) |
| `references/prompts/` | Pre-built prompt templates for common tasks (use with `--prompt @`) |
| `references/prompts/index.yaml` | **Prompt preset index — read this first** when the skill loads to learn available presets and when to use each |

### Prompt Presets

When this skill loads, first read `references/prompts/index.yaml` to discover available prompt presets. Each entry specifies:
- `name` — filename to use with `--prompt @references/prompts/<name>`
- `lang` — language code (`en` / `zh`)
- `use_when` — guidance on which scenarios to use this preset

Available presets:

| File | Lang | When to use |
|------|------|-------------|
| `describe.txt` | EN | Default image description |
| `describe-zh.txt` | ZH | 默认中文图片描述 |
| `extract-text.txt` | EN | Text extraction / OCR |
| `extract-text-zh.txt` | ZH | 中文文字提取 / OCR |

Examples:

```bash
# Describe an image (English)
python scripts/img_recog_cli.py --img photo.jpg --prompt @references/prompts/describe.txt

# Describe an image (Chinese)
python scripts/img_recog_cli.py --img photo.jpg --prompt @references/prompts/describe-zh.txt

# Extract text (English)
python scripts/img_recog_cli.py --img scan.png --prompt @references/prompts/extract-text.txt

# Extract text (Chinese)
python scripts/img_recog_cli.py --img scan.png --prompt @references/prompts/extract-text-zh.txt
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

## Adding a Prompt Preset

To add a new prompt preset:

1. Create `{name}.txt` (English) and `{name}-zh.txt` (Chinese) in `references/prompts/`
2. Add entries for both to `references/prompts/index.yaml` with `name`, `lang`, and `use_when` fields
3. Add usage examples in this SKILL.md's Prompt Presets section
