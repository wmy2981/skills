# CLAUDE.md

## Repository Structure

This is a collection of **agent skills**. Each skill is a self-contained directory following this pattern:

```
skill-name/
├── SKILL.md           # Skill definition — trigger keywords, usage, docs (English)
├── scripts/           # Python scripts that power the skill
│   ├── .env.example   # Environment variable template (mandatory if env vars needed)
│   ├── .env           # Local config (gitignored)
│   └── *.py
└── references/        # Reference docs, config templates (optional)
```

Root-level files:
- `LIST.md` — tracks skill readiness: `[x]` = ready, `[]` = WIP
- `README.md` — bilingual skill index with descriptions
- `CLAUDE.md` — this file, conventions for AI agent development

## Skill Conventions

### SKILL.md
- **Written in English.** Description frontmatter includes both English and Chinese trigger keywords.
- Most skills include an **Execution Rule** near the top: run the user's command directly without pre-checking; fix on failure.
- Dependencies listed under a **Requirements** section (pip install).
- Content under 500 lines; use `references/` for large reference docs.

### Scripts
- **English output** — all user-facing text, argparse help, and JSON keys must be English.
- **`python` not `python3`** — Windows target.
- **Environment variables** loaded via `python-dotenv` from `~/.wmyskills/.env` (shared across skills) and `scripts/.env` (per-skill). The tracked template is `scripts/.env.example`.
- **`load_dotenv()`** always uses explicit paths, script dir first then user global — `load_dotenv` never overrides existing values, so the earlier load (script dir) takes priority: `load_dotenv(dotenv_path=Path(__file__).parent / ".env")` then `load_dotenv(dotenv_path=Path.home() / ".wmyskills" / ".env")`
- **`--help` must work without env vars** — env initialization goes after `argparse.parse_args()`.
- **`import subprocess`** required for `chcp 65001` call.

### Runtime Data
Configs, templates, and output files produced at runtime go in `~/.wmyskills/<skill-name>/`. Resolve with `Path.home() / ".wmyskills" / "<skill-name>"`. Never store runtime data inside the repo.

## Common Commands

```bash
# Install dependencies
pip install -r <skill>/requirements.txt          # if requirements.txt exists
pip install pyyaml python-dotenv                 # common across skills

# Check script syntax
python -m py_compile <skill>/scripts/*.py

# Validate SKILL.md frontmatter
python -c "import yaml; yaml.safe_load(open('<skill>/SKILL.md').read().split('---')[1])"

# Test script entry point
python <skill>/scripts/<script>.py --help
```

Dependencies are declared in each skill's `SKILL.md` under **Requirements** or in a `requirements.txt`. When adding a new skill, update `LIST.md` and `README.md`.

## Windows UTF-8 Support

Python scripts that output user-facing Chinese/emoji text must add UTF-8 console support. Standard pattern (placed after imports, before any code):

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
```

Scripts producing only ASCII or JSON for machine consumption may skip it.

## Skill Development Checklist

When developing or modifying a skill:

1. **SKILL.md** — English, with description trigger keywords, Execution Rule, Requirements
2. **Script** — `python` not `python3`, English output, UTF-8 support, `--help` without env vars
3. **`.env.example`** — created if the script needs env vars
4. **Runtime data** — stored in `~/.wmyskills/<skill-name>/`, not in the repo
5. **Tests** — `py_compile` syntax check + `--help` smoke test
6. **`LIST.md`** — updated readiness status
7. **`README.md`** — update if adding/removing a skill
8. **Commit** — after all checks pass

## Git Workflow

- Push via SSH (remote is `git@github.com:wmy2981/wmy-skills-py.git`)
- Working tree is on a network share (G: drive mapped to `//WMY-SERVER/...`)
- Commits follow Conventional Commits: `type(scope): lowercase description` in English
