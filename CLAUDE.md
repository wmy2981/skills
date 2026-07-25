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

- A **skill with scripts** uses `scripts/.env` as an env-var template (copy to populate). Scripts load it at startup.
- No explicit env var means the skill expects config through the agent conversation or system env vars.
- Dependencies: listed inline in `SKILL.md` under a "Requirements" section — install via `pip install`.
- Python scripts target Windows (`python` not `python3`).

## Common Commands

```bash
# Install dependencies for a specific skill
pip install -r <skill>/requirements.txt   # if requirements.txt exists
pip install ebooklib beautifulsoup4 lxml   # epub-book-pipeline
pip install boto3                          # s3
pip install requests                       # many skills

# Check skill script syntax
python -m py_compile <skill>/scripts/*.py
```

## Git Workflow

- Commit messages in Chinese
- Push via SSH (remote is `git@github.com:wmy2981/wmy-skills.git`)
- Working tree is on a network share (G: drive mapped to `//WMY-SERVER/...`)
