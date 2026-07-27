# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This is a collection of **Claude Code agent skills**. Each skill is a self-contained directory following this pattern:

```
skill-name/
├── SKILL.md       # Skill definition — trigger keywords, usage, docs
├── scripts/       # Python/shell scripts that power the skill
│   ├── .env       # Environment variable template (gitignored by name)
│   └── *.py
└── references/    # Reference docs, config templates
```

Each `SKILL.md` contains frontmatter (`name`, `description`) used for skill discovery and triggering.

## Skill Conventions

- A **skill with scripts** uses `scripts/.env` for environment variables (gitignored). Scripts load it at startup via `python-dotenv`. The tracked template is `scripts/.env.example` — every skill that needs env vars **must commit a `.env.example`** so contributors know what to configure.
- No explicit env var means the skill expects config through the agent conversation or system env vars.
- Dependencies: listed inline in `SKILL.md` under a "Requirements" section — install via `pip install`.
- Python scripts target Windows (`python` not `python3`).
- **Runtime data** (configs, templates, output files) produced by a skill must be stored in `~/.wmyskills/<skill-name>/`. Scripts resolve the path via `pathlib.Path.home() / ".wmyskills" / "<skill-name>"`. Do not hardcode absolute paths or store runtime data inside the repo.

## Common Commands

```bash
# Install dependencies for a skill (read from requirements.txt or SKILL.md Requirements)
pip install -r <skill>/requirements.txt          # if requirements.txt exists

# Check skill script syntax
python -m py_compile <skill>/scripts/*.py

# Validate SKILL.md frontmatter
python -c "import yaml; yaml.safe_load(open('fun-asr/SKILL.md').read().split('---')[1])"
```

Dependencies are declared in each skill's `SKILL.md` under **Requirements** or in a `requirements.txt`. When a new skill is added, update nothing — the convention is self-documenting.

## Windows UTF-8 Support

Python scripts that output user-facing Chinese/emoji text must add UTF-8 console support (force stdout/stderr to UTF-8 and run `chcp 65001`). Scripts producing only ASCII or JSON for machine consumption may skip it.

## Skill Development

When developing or modifying a skill in this repo:
- **Focus on the current repo only.** Ignore any skill with the same name that may already be installed in Claude Code's local skill registry — work against the files in this repository.
- Treat the repo's version as canonical; don't assume the installed skill's behavior or configuration matches this repo's code.

## Git Workflow

- Push via SSH (remote is `git@github.com:wmy2981/wmy-skills.git`)
- Working tree is on a network share (G: drive mapped to `//WMY-SERVER/...`)
