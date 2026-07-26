# Send-Email Skill Refactor Design

## Overview

Refactor the existing `send_email` skill to `send-email`, separating code (repo) from user data (home directory), adding `.env` support, dynamic sender name, and a template-based email workflow.

## Directory Structure

### Code (in repo: `g:\Projects\agent\wmy-skills\`)

```
send-email/                      # renamed from send_email
├── SKILL.md                     # updated skill definition
├── README.md                    # new usage documentation
└── scripts/
    ├── .env                     # env var template (gitignored by name per repo convention)
    ├── send.py                  # enhanced sending script
```

### Data (in user home directory — dynamically resolved at runtime)

```
~/wmy-skills/send-email/
├── templates/                   # read-only HTML templates (AI copies from here)
│   └── default.html
└── msg/                         # edited messages ready to send (AI places files here)
    └── ...
```

Script resolves the user's home directory via `os.path.expanduser("~")` / `pathlib.Path.home()` — no paths are hardcoded.

## Environment Variables

Loaded from `scripts/.env` via `python-dotenv` at startup.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_HOST` | Yes | — | SMTP server hostname |
| `EMAIL_PORT` | No | `465` | SMTP server port |
| `EMAIL_USER` | Yes | — | Sender email address |
| `EMAIL_AUTH` | Yes | — | SMTP password / app token |
| `EMAIL_NAME` | No | `ClaudeCode` | Sender display name |

## Script Enhancements

### `send.py`

**Changes from current:**
1. Load `.env` from `scripts/.env` via `python-dotenv` (optional — no error if missing or no dotenv installed)
2. `EMAIL_NAME` replaces hardcoded `"ClaudeCode"` in the `From` header
3. Template workflow: if `<body>` argument is a path to an existing `.html` file, read its content and send as HTML body
4. Data directory: script creates `~/wmy-skills/send-email/{templates,msg}/` if they don't exist
5. Usage string updated to reflect all capabilities

**CLI unchanged:**
```bash
python scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

### Template Workflow

1. AI copies a `.html` from `~/wmy-skills/send-email/templates/` to `~/wmy-skills/send-email/msg/`
2. AI edits the copy with specific content
3. AI runs: `python scripts/send.py user@example.com "Subject" ../msg/{filename}`
4. Script detects body is a file path → reads as HTML body → sends

## SKILL.md Updates

- Frontmatter name: `send_email` → `send-email`
- Description: updated
- Usage docs: updated with all parameters and template workflow
- Config table: add `EMAIL_NAME`
- Add template section
- Add `.env` setup section

## README.md (new)

Standalone guide covering:
- Setup (`.env`, Python dependencies)
- Basic usage
- Template workflow
- Directory layout (code vs data)
- Troubleshooting

## No New Dependencies

- `python-dotenv` — optional soft dependency; script works without it if env vars are set system-wide
- All other imports (`smtplib`, `email.*`, `os`, `sys`, `pathlib`) are stdlib

## Implementation Order

1. Rename directory `send_email` → `send-email` (git mv)
2. Update `SKILL.md` frontmatter and content
3. Enhance `send.py` (dotenv, EMAIL_NAME, template flow, data dirs)
4. Create `scripts/.env` template
5. Create `README.md`
6. Create data dirs in home
7. Review and test each step
8. Commit per step
