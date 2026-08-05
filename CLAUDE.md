# CLAUDE.md

## Repository Structure

This is a collection of **agent skills**. Each skill is a self-contained directory following this pattern:

```
skill-name/
├── SKILL.md           # Skill definition — trigger keywords, usage, docs
├── scripts/           # Helper scripts that power the skill
│   ├── .env.example   # Environment variable template (mandatory if env vars needed)
│   └── ...            # Script files
└── references/        # Reference docs, config templates (optional)
```

Root-level files:
- `README.md` — bilingual skill index with descriptions
- `CLAUDE.md` — this file, conventions for AI agent development

## Skill Conventions

### SKILL.md
- **Written in English.**
- **Must** load the `skill-creator` skill and follow its instructions.
- Include an **Execution Rule** near the top: run the user's command directly without pre-checking; fix on failure. (Default)
- List dependencies under a **Requirements** section.
- Keep content under 500 lines; use `references/` for large reference docs.
- **Environment variable setup**: when guiding the user to configure env vars, prefer the **shared global file** `~/.wmyskills/.env`. Read `scripts/.env.example` first, then add or update the env vars that skill needs in `~/.wmyskills/.env`.Do not run `cp .env.example path/to/.env` directly to avoid overwritting origin.

### Scripts
- **English output** — all user-facing text, argparse help, and JSON keys must be English.
- **`load_dotenv`** — always load with explicit paths: `scripts/.env` (per-skill) first, then `~/.wmyskills/.env` (shared global). Since `load_dotenv` never overrides existing values, the earlier load takes priority. The tracked template is `scripts/.env.example`:
  ```python
  load_dotenv(dotenv_path=Path(__file__).parent / ".env")       # per-skill
  load_dotenv(dotenv_path=Path.home() / ".wmyskills" / ".env")  # shared global
  ```
- **`--help` must work without env vars** — env initialization goes after `argparse.parse_args()`.

### Runtime Data
Configs, templates, and output files produced at runtime go in `~/.wmyskills/<skill-name>/`. Never store runtime data inside skill folders.

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

## Windows UTF-8 Support

Python scripts that may output non-ASCII text — e.g. echoing user-provided filenames or content, allowed even though default output is English — must add UTF-8 console support. Standard pattern (placed after imports, before any code):

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
```

## Skill Development Checklist

When developing or modifying a skill:

- [ ] **SKILL.md** — English, with trigger keywords, Execution Rule, Requirements
- [ ] **Script** — English output, UTF-8 support, `--help` without env vars
- [ ] **`.env.example`** — created if the script needs env vars
- [ ] **Runtime data** — stored in `~/.wmyskills/<skill-name>/`, not in the repo
- [ ] **Tests** — `py_compile` syntax check + `--help` smoke test
- [ ] **`README.md`** — update if adding/removing a skill
- [ ] **Commit** — after all checks pass

## Git Workflow

- Commits follow Conventional Commits: `type(scope): lowercase description` in English
