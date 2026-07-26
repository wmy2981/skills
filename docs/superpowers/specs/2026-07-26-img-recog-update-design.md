# img-recog Skill Update — Design Spec

## Overview

Update the `img-recog` skill to support bilingual prompt presets (Chinese/English), model.yaml readability, env-var-based config paths, English default prompts, and a structured prompt preset index.

## Changes

### 1. Security: model.yaml readability

**File**: `img-recog/SKILL.md`

Change the security table:

| File | Purpose | AI-readable? |
|------|---------|-------------|
| `provider.yaml` | API base URLs and keys | **NO — never read or show this file** |
| `model.yaml` | Model-to-provider mapping and defaults | **YES — AI may read this to understand model mappings and defaults; never show raw keys** |

**Rationale**: The AI needs to know which models are configured to give accurate `--provider`/`--model` advice to the user, but must never access API keys.

### 2. Bilingual Prompt Presets

**Directory**: `img-recog/references/prompts/`

| File | Language | Content |
|------|----------|---------|
| `describe.txt` | English | "Please describe this image in detail" |
| `describe-zh.txt` | Chinese | Current Chinese description prompt |
| `extract-text.txt` | English | "Extract all text from this image, preserving the original layout and line breaks" |
| `extract-text-zh.txt` | Chinese | Current Chinese extraction prompt |

**Impact**: Default prompt in code changes to English (see §5). Users can use `--prompt @references/prompts/describe-zh.txt` for Chinese.

### 3. Config Init: Remove Placeholder Content

**File**: `img-recog/SKILL.md` — Setup section

After the `cp` commands, add explicit instruction to delete/replace placeholder lines in the copied config files before they can be used. The instruction must say:

> After copying, edit each file to replace placeholder values (marked with `# ← 替换为` comments) with your actual API keys and remove those comments. The script will reject placeholder values.

### 4. Env-Var Support for Config Paths

**Files**: `img-recog/scripts/config_loader.py`, `img-recog/scripts/requirements.txt`

- Add `python-dotenv` dependency
- `config_loader.py` loads `.env` from:
  1. `scripts/.env` (next to the code)
  2. `~/.wmyskills/img-recog/.env` (next to config files)
- New env vars:

| Var | Default | Description |
|-----|---------|-------------|
| `img-recog_PROVIDER_FILE` | `~/.wmyskills/img-recog/provider.yaml` | Path to provider config |
| `img-recog_MODEL_FILE` | `~/.wmyskills/img-recog/model.yaml` | Path to model config |

- Default behavior unchanged when env vars are unset
- Keep `scripts/.env` in `.gitignore` (already gitignored by name pattern)

### 5. Default Prompt → English

**Files**: `img-recog/scripts/img_recog_cli.py`, `img-recog/scripts/api_caller.py`

Change default prompt string:
- `"请详细描述这张图片的内容"` → `"Please describe this image in detail"`

### 6. Prompt Preset Index + Add-Preset Process

**New file**: `img-recog/references/prompts/index.yaml`

```yaml
prompts:
  - name: describe.txt
    lang: en
    use_when: "User asks to look at, see, describe, or analyze an image"
  - name: describe-zh.txt
    lang: zh
    use_when: "用户要求描述、查看、分析图片内容时"
  - name: extract-text.txt
    lang: en
    use_when: "User asks to read text, extract text, or OCR from an image"
  - name: extract-text-zh.txt
    lang: zh
    use_when: "用户要求提取文字、读取文字、OCR图片时"
```

**SKILL.md** adds:
- Instruction: "Every time this skill loads, first read `references/prompts/index.yaml` to learn available prompt presets"
- New section **Adding a Prompt Preset**:
  1. Create `{name}.txt` (English) and `{name}-zh.txt` (Chinese) in `references/prompts/`
  2. Add entry to `references/prompts/index.yaml`
  3. Update the usage examples in SKILL.md

## Files to Modify

| File | Action |
|------|--------|
| `img-recog/SKILL.md` | Edit: security table, setup section, prompt sections, add index.yaml instruction, add add-preset process |
| `img-recog/scripts/config_loader.py` | Edit: add .env loading and env-var overrides |
| `img-recog/scripts/img_recog_cli.py` | Edit: default prompt to English |
| `img-recog/scripts/api_caller.py` | Edit: default prompt param to English |
| `img-recog/scripts/requirements.txt` | Edit: add `python-dotenv` |
| `img-recog/scripts/.env` | Create: template (gitignored) |
| `img-recog/references/prompts/describe.txt` | Edit: English content |
| `img-recog/references/prompts/extract-text.txt` | Edit: English content |
| `img-recog/references/prompts/describe-zh.txt` | Create: Chinese content |
| `img-recog/references/prompts/extract-text-zh.txt` | Create: Chinese content |
| `img-recog/references/prompts/index.yaml` | Create: prompt index |
| `img-recog/references/templates/model.yaml.template` | Edit: add clear placeholder markers |
| `img-recog/references/templates/provider.yaml.template` | Edit: add clear placeholder markers |

## Implementation Order

1. Create feature branch from master
2. Security & model.yaml readability (SKILL.md only)
3. Config template placeholder cleanup (SKILL.md + templates)
4. Env var support (config_loader.py + .env + requirements.txt)
5. Default prompt to English (cli.py + api_caller.py)
6. Prompt preset index + bilingual prompts (index.yaml + prompt files)
7. Add-preset process in SKILL.md
8. Final review, test, report

Each step: review → test → commit.
