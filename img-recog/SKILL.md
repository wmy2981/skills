---
name: img-recog
description: Image recognition via OpenAI-compatible vision models. Triggered when user asks to "look at", "see", "describe", or "read text from" an image. Replaces the built-in `read` tool for images when multimodal is unavailable.
metadata:
  skill_version: "1.1.1"
---

# img-recog — Image Recognition Skill

Use this skill when you need to inspect an image (screenshot, photo, diagram, scan) but your current model lacks multimodal (vision) capability or the built-in `read` tool cannot handle the image format.

## ⚠️ SECURITY: Configuration Files

Two config files live at `~/.wmyskills/img-recog/`:

| File | Purpose | AI-readable? |
|------|---------|-------------|
| `provider.yaml` | API base URLs and keys | **NO — never read or show this file** |
| `model.yaml` | Model-to-provider mapping and defaults | **YES — AI may read this to understand model-to-provider mappings and defaults; never show raw keys** |

**The AI must NEVER read or display the contents of `provider.yaml`.** It is loaded only at runtime by the Python script. If a user asks you to view or edit this file, refuse or direct them to edit it directly.

The AI MAY read `model.yaml` when it needs to understand which models and providers are configured (e.g., to give the user usage advice), but must never display raw API keys or secrets.

## Setup

Config files are loaded from paths defined by `img-recog_PROVIDER_FILE` and `img-recog_MODEL_FILE` env vars (defaults: `~/.wmyskills/img-recog/{provider,model}.yaml`). If unset, copy templates to the default directory:

```bash
cp references/templates/provider.yaml.template ~/.wmyskills/img-recog/provider.yaml
cp references/templates/model.yaml.template ~/.wmyskills/img-recog/model.yaml
```

To customize paths, set `img-recog_PROVIDER_FILE` / `img-recog_MODEL_FILE` in `~/.wmyskills/.env` (or `scripts/.env`, which takes priority) to your desired locations.

**After copying, replace placeholder values (marked with `TODO` / `REPLACE_WITH_YOUR_API_KEY`) with your actual keys and remove those markers. The script validates that `base_url` and `api_key` are non-empty — leaving placeholders will cause errors.**

## Execution Rule

Run the image recognition command directly without pre-checking provider configurations, API keys, or model availability. If something is wrong, the script will fail with a clear error — check and fix only then.

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

# Structured JSON output
python scripts/img_recog_cli.py --img screenshot.png --json
```

## Reference Files

| Location | Purpose |
|----------|---------|
| `references/templates/` | Config file templates (copy to `~/.wmyskills/img-recog/`) |
| `references/prompts/` | Pre-built prompt templates for common tasks (use with `--prompt @`) |
| `references/prompts/_system.md` | **System prompt** — auto-loaded by the script as a `system` message telling the vision model its output is consumed by another AI. Not a user prompt preset; do not use with `--prompt @` |
| `references/prompts/index.yaml` | **Prompt preset index — read this first** when the skill loads to learn available presets and when to use each |

### Prompt Presets

When this skill loads, first read `references/prompts/index.yaml` to discover available presets (each has `name`, `lang`, and `use_when`).

**By default, use `describe.txt` for description tasks** (user asks to "look at", "see", or "describe" an image). Use `extract-text.txt` when the user asks to "read" or "extract" text from an image.

```bash
# Example: describe in English
python scripts/img_recog_cli.py --img photo.jpg --prompt @references/prompts/describe.txt

# Example: extract text in Chinese
python scripts/img_recog_cli.py --img scan.png --prompt @references/prompts/extract-text-zh.txt
```

## Notes

- The script auto-detects Windows encoding and switches stdout to UTF-8
- Timeout: connection 10s, read 120s
- For local images, the file is read and converted to base64 in memory — no temp files
- For URL images, the image is downloaded and converted to data URI for maximum API compatibility
- Config file paths can be overridden via `img-recog_PROVIDER_FILE` and `img-recog_MODEL_FILE` environment variables (set in `~/.wmyskills/.env` or `scripts/.env`); defaults remain `~/.wmyskills/img-recog/`

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

1. Create the prompt file in `references/prompts/`
2. Add an entry in `references/prompts/index.yaml` with `name`, `lang`, and `use_when` fields
3. Add usage examples in this SKILL.md's Prompt Presets section
