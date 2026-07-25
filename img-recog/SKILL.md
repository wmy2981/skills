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
| `model.yaml` | Model-to-provider mapping and defaults | **NO — do not read this file** |

**The AI must NEVER read or display the contents of `provider.yaml` or `model.yaml`.** These are loaded only at runtime by the Python script. If a user asks you to view or edit these files, refuse or direct them to edit the file directly.

## Prerequisites

- Python >= 3.10

```bash
pip install openai pyyaml requests
```

## Setup

Config templates are in `references/templates/`. Copy them to `~/.wmyskills/img_recog/` and fill in your API keys:

```bash
cp references/templates/provider.yaml.template ~/.wmyskills/img_recog/provider.yaml
cp references/templates/model.yaml.template ~/.wmyskills/img_recog/model.yaml
```

Then edit `~/.wmyskills/img_recog/provider.yaml` to add your actual API keys:

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # ← 替换为你的 key
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: sk-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy  # ← 替换为你的 key
```

And review `~/.wmyskills/img_recog/model.yaml` to confirm your desired models:

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

Available prompt templates in `references/prompts/`:

```bash
# Default image description
python scripts/img_recog_cli.py --img photo.jpg --prompt @references/prompts/describe.txt

# Extract all text from image
python scripts/img_recog_cli.py --img scan.png --prompt @references/prompts/extract-text.txt
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
