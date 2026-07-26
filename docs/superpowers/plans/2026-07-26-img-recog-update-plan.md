# img-recog Skill Update — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update the img-recog skill with bilingual prompts, model.yaml readability, env-var config paths, English default prompt, and prompt preset index.

**Architecture:** Single-skill update touching SKILL.md (configuration docs + process docs), Python scripts (config_loader, cli, api_caller), reference files (prompts, templates), and a new index.yaml.

**Tech Stack:** Python 3.10+, PyYAML, openai, python-dotenv

## Global Constraints

- Python scripts target Windows (`python` not `python3`)
- Windows terminal defaults to GBK encoding — scripts must force UTF-8 stdout
- The AI must NEVER read or display `provider.yaml` contents
- `model.yaml` IS readable by AI when needed (this is a change from current behavior)
- Config default path: `~/.wmyskills/img-recog/`
- `.env` files are gitignored by name
- All prompt files are UTF-8 encoded
- Each commit message ends with `Co-Authored-By: Claude <noreply@anthropic.com>`

---

### Task 1: Update Security — model.yaml Readable

**Files:**
- Modify: `img-recog/SKILL.md` (security table + notes)

**Interfaces:**
- Consumes: current SKILL.md security wording
- Produces: updated SKILL.md with corrected security policy

- [ ] **Step 1: Edit SKILL.md security section**

Change the security table rows for `model.yaml` from **"NO — do not read this file"** to **"YES — AI may read this to understand model-to-provider mappings and defaults; must not show raw keys"**.

Also update the paragraph below the table. Current text:
```
**The AI must NEVER read or display the contents of `provider.yaml` or `model.yaml`.**
```
Change to:
```
**The AI must NEVER read or display the contents of `provider.yaml`.** These are loaded only at runtime by the Python script. If a user asks you to view or edit these files, refuse or direct them to edit the file directly.

The AI MAY read `model.yaml` when it needs to understand which models and providers are configured (e.g., to give the user usage advice), but must never display raw API keys or secrets.
```

- [ ] **Step 2: Verify the change**

```bash
cd g:/Projects/agent/wmy-skills
grep -n "model.yaml" img-recog/SKILL.md
```
Expected: Shows the security table with YES for model.yaml readability.

- [ ] **Step 3: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/SKILL.md
git commit -m "feat(img-recog): allow AI to read model.yaml when needed

Security: model.yaml is now readable by AI for understanding model
mappings and defaults. provider.yaml remains strictly forbidden.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Config Template Placeholder Cleanup

**Files:**
- Modify: `img-recog/references/templates/provider.yaml.template`
- Modify: `img-recog/references/templates/model.yaml.template`
- Modify: `img-recog/SKILL.md` (Setup section)

**Interfaces:**
- Consumes: current template files and SKILL.md Setup section
- Produces: cleaner templates with explicit placeholder markers + Setup instructions to remove placeholders

- [ ] **Step 1: Update provider.yaml.template to use explicit markers**

Edit `img-recog/references/templates/provider.yaml.template`:
Old content already has comments but let's verify and clean it up to use a consistent marker format that's easy to find and delete.

```yaml
providers:
  openai:
    base_url: https://api.openai.com/v1
    api_key: "sk-xxx...REPLACE_WITH_YOUR_API_KEY"  # TODO: 替换为你的 API key
  deepseek:
    base_url: https://api.deepseek.com/v1
    api_key: "sk-xxx...REPLACE_WITH_YOUR_API_KEY"  # TODO: 替换为你的 API key
```

- [ ] **Step 2: Update model.yaml.template**

Edit `img-recog/references/templates/model.yaml.template` to add clear placeholder markers:

```yaml
# model.yaml — Model-to-provider mapping
# After copying, review and adjust the default provider and model below.
default:
  provider: openai           # TODO: change to your preferred provider
  model: gpt-4o-mini         # TODO: change to your preferred vision model

# Optional: define available models per provider
providers:
  openai:
    models:
      - gpt-4o-mini
      - gpt-4o
  deepseek:
    models:
      - deepseek-chat
```

- [ ] **Step 3: Update SKILL.md Setup section**

In the Setup section, after the `cp` commands, enhance the instructions to explicitly tell users to delete placeholder content:

```
After copying, edit each file to replace placeholder values (marked with `TODO` comments) with your actual API keys and remove those comments. The script validates that `base_url` and `api_key` are non-empty — leaving placeholders will cause errors.
```

- [ ] **Step 4: Verify**

```bash
cd g:/Projects/agent/wmy-skills
cat img-recog/references/templates/provider.yaml.template
cat img-recog/references/templates/model.yaml.template
grep -A5 "After copying" img-recog/SKILL.md
```

- [ ] **Step 5: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/references/templates/ img-recog/SKILL.md
git commit -m "feat(img-recog): add explicit placeholder markers in config templates

Templates now have clear REPLACE_WITH markers. SKILL.md setup
instructions explicitly tell users to remove placeholder content.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Env-Var Support for Custom Config Paths

**Files:**
- Modify: `img-recog/scripts/config_loader.py`
- Modify: `img-recog/scripts/requirements.txt`
- Create: `img-recog/scripts/.env`

**Interfaces:**
- Consumes: `~/.wmyskills/img-recog/` as default config dir
- Produces: env-var overrides via `img-recog_PROVIDER_FILE`, `img-recog_MODEL_FILE`

- [ ] **Step 1: Add python-dotenv to requirements.txt**

Edit `img-recog/scripts/requirements.txt`:
```
openai>=1.0.0
pyyaml>=6.0
requests>=2.28
python-dotenv>=1.0.0
```

- [ ] **Step 2: Create scripts/.env template**

Create `img-recog/scripts/.env`:
```env
# Optional: override config file paths
# Defaults to ~/.wmyskills/img-recog/{provider,model}.yaml
# img-recog_PROVIDER_FILE=C:/path/to/provider.yaml
# img-recog_MODEL_FILE=C:/path/to/model.yaml
```

- [ ] **Step 3: Update config_loader.py to support .env and env vars**

Edit `img-recog/scripts/config_loader.py`:

1. Add `from dotenv import load_dotenv` at top
2. Add a `_resolve_config_path(name: str) -> str` helper function
3. Load `.env` from two locations early in `load_provider_config` and `load_model_config`
4. Use env vars to override PROVIDER_FILE and MODEL_FILE

The changes:

At the top of the file, after imports, add env loading:
```python
from dotenv import load_dotenv

# Load .env files (lowest priority: scripts/.env, then config dir)
_script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_script_dir, ".env"))
load_dotenv(os.path.join(CONFIG_DIR, ".env"))
```

Change PROVIDER_FILE and MODEL_FILE to use env-var overrides:
```python
CONFIG_DIR = os.path.expanduser("~/.wmyskills/img-recog")
PROVIDER_FILE = os.environ.get("img-recog_PROVIDER_FILE",
                               os.path.join(CONFIG_DIR, "provider.yaml"))
MODEL_FILE = os.environ.get("img-recog_MODEL_FILE",
                            os.path.join(CONFIG_DIR, "model.yaml"))
```

The `load_dotenv` calls must happen before the file path variables are used, so put them right after `CONFIG_DIR` definition but before `PROVIDER_FILE` and `MODEL_FILE`.

- [ ] **Step 4: Verify syntax**

```bash
cd g:/Projects/agent/wmy-skills
python -m py_compile img-recog/scripts/config_loader.py
```
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/scripts/config_loader.py img-recog/scripts/requirements.txt img-recog/scripts/.env
git commit -m "feat(img-recog): add env-var support for config file paths

Support img-recog_PROVIDER_FILE and img-recog_MODEL_FILE env vars
via .env files. Default paths to ~/.wmyskills/img-recog/ unchanged.
Adds python-dotenv dependency.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Default Prompt to English

**Files:**
- Modify: `img-recog/scripts/img-recog_cli.py`
- Modify: `img-recog/scripts/api_caller.py`

**Interfaces:**
- Consumes: current Chinese default prompt strings
- Produces: English default prompt strings

- [ ] **Step 1: Change default prompt in img-recog_cli.py**

In `img-recog/scripts/img-recog_cli.py`, line 29:
```python
# Change from:
return "请详细描述这张图片的内容"
# Change to:
return "Please describe this image in detail"
```

- [ ] **Step 2: Change default prompt in api_caller.py**

In `img-recog/scripts/api_caller.py`, line 8 (function signature default):
```python
# Change from:
prompt: str = "请详细描述这张图片的内容",
# Change to:
prompt: str = "Please describe this image in detail",
```

- [ ] **Step 3: Verify syntax**

```bash
cd g:/Projects/agent/wmy-skills
python -m py_compile img-recog/scripts/img-recog_cli.py
python -m py_compile img-recog/scripts/api_caller.py
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/scripts/img-recog_cli.py img-recog/scripts/api_caller.py
git commit -m "fix(img-recog): change default prompt from Chinese to English

Default description prompt is now English. Users can still use
--prompt @references/prompts/describe-zh.txt for Chinese.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Bilingual Prompt Presets + index.yaml

**Files:**
- Modify: `img-recog/references/prompts/describe.txt`
- Modify: `img-recog/references/prompts/extract-text.txt`
- Create: `img-recog/references/prompts/describe-zh.txt`
- Create: `img-recog/references/prompts/extract-text-zh.txt`
- Create: `img-recog/references/prompts/index.yaml`

**Interfaces:**
- Consumes: current Chinese prompt content
- Produces: English prompts in existing files, Chinese prompts in new -zh files, index.yaml listing all prompts

- [ ] **Step 1: Update describe.txt to English**

Write `img-recog/references/prompts/describe.txt`:
```
Please describe this image in detail. Include the main subjects, their arrangement, colors, text content (if any), and any notable details.
```

- [ ] **Step 2: Create describe-zh.txt (Chinese version)**

Write `img-recog/references/prompts/describe-zh.txt`:
```
请详细描述这张图片的内容，包括主要主体、布局、颜色、文字内容（如有）以及任何值得注意的细节。
```

- [ ] **Step 3: Update extract-text.txt to English**

Write `img-recog/references/prompts/extract-text.txt`:
```
Extract all text from this image. Preserve the original layout, line breaks, and formatting as much as possible. Return only the extracted text.
```

- [ ] **Step 4: Create extract-text-zh.txt (Chinese version)**

Write `img-recog/references/prompts/extract-text-zh.txt`:
```
请提取图中所有文字，尽量保留原始布局、换行和格式。仅返回提取出的文字内容。
```

- [ ] **Step 5: Create index.yaml**

Write `img-recog/references/prompts/index.yaml`:
```yaml
# Prompt presets index — read this first when the skill loads
# to learn what prompt presets are available.
prompts:
  - name: describe.txt
    lang: en
    use_when: "User asks to look at, see, describe, or analyze an image (default)"
  - name: describe-zh.txt
    lang: zh
    use_when: "用户要求描述、查看、分析图片内容时（默认中文提示词）"
  - name: extract-text.txt
    lang: en
    use_when: "User asks to read text, extract text, or OCR from an image"
  - name: extract-text-zh.txt
    lang: zh
    use_when: "用户要求提取文字、读取文字、OCR图片时"
```

- [ ] **Step 6: Verify files**

```bash
cd g:/Projects/agent/wmy-skills
ls -la img-recog/references/prompts/
python -c "import yaml; data=yaml.safe_load(open('img-recog/references/prompts/index.yaml','r')); print(f'{len(data[\"prompts\"])} prompts loaded')"
```
Expected: 4 prompt files + index.yaml. YAML parses without error.

- [ ] **Step 7: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/references/prompts/
git commit -m "feat(img-recog): add bilingual prompt presets and index.yaml

Existing prompts converted to English. Chinese versions in -zh.txt files.
index.yaml provides structured metadata for AI to discover presets.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Update SKILL.md — index.yaml Loading + Add-Preset Process

**Files:**
- Modify: `img-recog/SKILL.md`

**Interfaces:**
- Consumes: current SKILL.md structure
- Produces: SKILL.md with index.yaml loading instruction, add-preset process, updated prompt examples

- [ ] **Step 1: Add index.yaml loading instruction**

In SKILL.md, in the Reference Files section or as a new subsection under Usage, add:

```markdown
### Prompt Presets

Every time this skill loads, first read `references/prompts/index.yaml` to learn what prompt presets are available. Each preset has a `name`, `lang` (en/zh), and `use_when` describing when to use it.

Available presets:
```

(Then list them dynamically based on index.yaml content or reference the file.)

- [ ] **Step 2: Add "Adding a Prompt Preset" section**

Add a new section at the bottom of SKILL.md:

```markdown
## Adding a Prompt Preset

To add a new prompt preset:

1. Create `{name}.txt` (English) and `{name}-zh.txt` (Chinese) in `references/prompts/`
2. Add an entry for each to `references/prompts/index.yaml` with `name`, `lang`, and `use_when` fields
3. Update the usage examples and preset listing in this SKILL.md
```

- [ ] **Step 3: Update prompt usage examples**

Update the examples section to use English prompts as defaults and show Chinese variants:

```bash
# Default (English) description
python scripts/img-recog_cli.py --img photo.jpg --prompt @references/prompts/describe.txt

# Chinese description
python scripts/img-recog_cli.py --img scan.png --prompt @references/prompts/describe-zh.txt

# Extract text (English)
python scripts/img-recog_cli.py --img scan.png --prompt @references/prompts/extract-text.txt

# Extract text (Chinese)
python scripts/img-recog_cli.py --img scan.png --prompt @references/prompts/extract-text-zh.txt
```

- [ ] **Step 4: Verify**

```bash
cd g:/Projects/agent/wmy-skills
grep -c "index.yaml" img-recog/SKILL.md
grep -c "Adding a Prompt Preset" img-recog/SKILL.md
```
Expected: at least 1 for index.yaml, at least 1 for Adding a Prompt Preset.

- [ ] **Step 5: Commit**

```bash
cd g:/Projects/agent/wmy-skills
git add img-recog/SKILL.md
git commit -m "docs(img-recog): add index.yaml loading and add-preset process

SKILL.md now instructs AI to read index.yaml on load, documents
the process for adding new prompt presets, and updates examples
to reflect bilingual prompts.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: Final Review and Test

**Files:**
- All modified files
- Verify: syntax, consistency, completeness

- [ ] **Step 1: Full syntax check**

```bash
cd g:/Projects/agent/wmy-skills
python -m py_compile img-recog/scripts/img-recog_cli.py
python -m py_compile img-recog/scripts/api_caller.py
python -m py_compile img-recog/scripts/config_loader.py
python -m py_compile img-recog/scripts/image_handler.py
python -m py_compile img-recog/scripts/output_formatter.py
```

- [ ] **Step 2: Verify SKILL.md security section**

Check that:
- provider.yaml is marked NO
- model.yaml is marked YES
- No mention of "AI must never read model.yaml"

- [ ] **Step 3: Verify all prompt files exist**

```bash
cd g:/Projects/agent/wmy-skills
ls img-recog/references/prompts/
```
Expected: index.yaml, describe.txt, describe-zh.txt, extract-text.txt, extract-text-zh.txt

- [ ] **Step 4: Verify env var loading in config_loader.py**

```bash
cd g:/Projects/agent/wmy-skills
grep -n "load_dotenv\|img-recog_" img-recog/scripts/config_loader.py
```
Expected: shows load_dotenv calls and img-recog_PROVIDER_FILE / img-recog_MODEL_FILE usage.

- [ ] **Step 5: Verify default prompt is English**

```bash
cd g:/Projects/agent/wmy-skills
grep -n "Please describe this image" img-recog/scripts/img-recog_cli.py img-recog/scripts/api_caller.py
```
Expected: both files contain the English string.

- [ ] **Step 6: Check git log**

```bash
cd g:/Projects/agent/wmy-skills
git log --oneline feat/update-img-recog
```

- [ ] **Step 7: Report completion**

Summarize all changes made, files modified/created, and branch state.
