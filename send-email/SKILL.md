---
name: send-email
description: "Use when the user wants to send an email, email a file or document, send a message via email, forward information by email, or use HTML email templates. Trigger on any email-related request — including 'email this to...', 'forward this to...', 'send the report to...', 'attach this file and send'. Do NOT use for non-email communication like Slack or SMS."
---

# Send Email Skill

Send emails via SMTP from Claude Code. Supports plain text, HTML, attachments, and template-based workflow.

## Action

Run the script directly — **do not** check configuration beforehand. The script already handles missing credentials and connection errors with clear messages, so pre-checking wastes time without adding value. Send first; if it fails, the error tells you exactly what to fix.

```bash
cd ~/.claude/skills/send-email && python scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

- `<body>`: plain text, HTML string, or path to an `.html` file (auto-detected)
- `--html`: force HTML mode if body isn't a file path
- `[attachment...]`: one or more file paths to attach

### Examples

**Plain text:**
```bash
python scripts/send.py user@example.com "Hello" "Just saying hi"
```

**From template file:**
```bash
python scripts/send.py user@example.com "Newsletter" ../msg/my_newsletter.html
```

**With attachment:**
```bash
python scripts/send.py user@example.com "Files" "See attached" report.pdf
```

## Template Workflow

All templates and message HTML files **must** be stored in these directories:

| Directory | Purpose |
|-----------|---------|
| `~/wmy-skills/send-email/templates/` | Read-only HTML templates |
| `~/wmy-skills/send-email/msg/` | Edited messages to send |

1. Copy a template from `templates/` to `msg/`
2. Edit the copy with your content
3. Run `send.py` with the `msg/` file path as `<body>`

## On Error

If sending fails, check the following:

**Missing or wrong credentials** — verify `~/.claude/skills/send-email/scripts/.env` has the correct SMTP settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | — | SMTP server hostname |
| `EMAIL_PORT` | `465` | SMTP server port |
| `EMAIL_USER` | — | Sender email address |
| `EMAIL_AUTH` | — | SMTP password / app token |
| `EMAIL_NAME` | `ClaudeCode` | Sender display name |

**Connection refused / timeout** — `EMAIL_HOST` or `EMAIL_PORT` may be wrong; check with your provider.

**Authentication failed** — `EMAIL_USER`/`EMAIL_AUTH` may be wrong; some providers require an app-specific password.
