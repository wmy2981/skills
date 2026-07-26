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

- `<body>`: plain text, short HTML string (`--html`), or path to an `.html` file (auto-detected)
- `--html`: force HTML mode if body isn't a file path. Only for short one-line HTML.
- `[attachment...]`: one or more file paths to attach

**HTML content rule:** Long/complex HTML must be saved as a file first. Use `~/.wmyskills/send-email/msg/` — the only directory allowed for sending HTML files. Do NOT save HTML files in the repo, /tmp, downloads folder, or anywhere else. Reason: the file path is passed as `<body>` to send.py, which reads it by path and only resolves correctly from this directory.

### Examples

**Plain text:**
```bash
python scripts/send.py user@example.com "Hello" "Just saying hi"
```

**HTML from file (required for long/complex HTML):**
```bash
# Write the HTML to ~/.wmyskills/send-email/msg/, then send:
python scripts/send.py user@example.com "Newsletter" ../msg/my_newsletter.html
```

**Short inline HTML (one line only):**
```bash
python scripts/send.py user@example.com "Alert" "<b>Server is down</b>" --html
```

**With attachment:**
```bash
python scripts/send.py user@example.com "Files" "See attached" report.pdf
```

## File Storage Rules

**Violating these rules is a bug.** Every email HTML file must go through the designated directories:

| Directory | Purpose |
|-----------|---------|
| `~/.wmyskills/send-email/templates/` | Read-only HTML templates. Copy from here, do not edit in place. |
| `~/.wmyskills/send-email/msg/` | The ONLY directory for sending HTML files. Save edited HTML here, pass the path as `<body>`. |

**Rules:**
- All email HTML files **must** be saved in `~/.wmyskills/send-email/msg/` before sending
- Do NOT save HTML in the repo directory, /tmp, Downloads, Desktop, or any other location
- Do NOT create a different directory structure — send.py discovers files relative to this path
- The repo stores code, not runtime data. Runtime data goes in `~/.wmyskills/<skill-name>/`

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
