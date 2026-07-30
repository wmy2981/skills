---
name: send-email
description: "Use when the user wants to send an email, email a file or document, send a message via email, forward information by email, or use HTML email templates. Trigger on any email-related request — including 'email this to...', 'forward this to...', 'send the report to...', 'attach this file and send'. Do NOT use for non-email communication like Slack or SMS."
---

# Send Email Skill

Send emails via SMTP from Claude Code. Supports plain text, HTML, attachments, and template-based workflow.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

```bash
python scripts/send.py <to> <subject> <mode> <body> [attachment...]
```

### Modes

| Mode | Purpose | Example Body |
|------|---------|-------------|
| `--text` | Plain text email | `"Just saying hi"` |
| `--html` | Inline HTML string | `"<b>Alert</b>"` |
| `--file` | HTML from file | `~/.wmyskills/send-email/msg/my.html` |

Long/complex HTML **must** use `--file` with a file inside `~/.wmyskills/send-email/msg/`.

### Examples

**Plain text:**
```bash
python scripts/send.py user@example.com "Hello" --text "Just saying hi"
```

**Inline HTML (short):**
```bash
python scripts/send.py user@example.com "Alert" --html "<b>Server is down</b>"
```

**HTML from file (long/complex HTML):**
```bash
python scripts/send.py user@example.com "Newsletter" --file ~/.wmyskills/send-email/msg/my_newsletter.html
```

**With attachment (any mode):**
```bash
python scripts/send.py user@example.com "Files" --text "See attached" report.pdf
```

## File Storage Rules

**Violating these rules is a bug.** Every email HTML file must go through the designated directories:

| Directory | Purpose |
|-----------|---------|
| `~/.wmyskills/send-email/templates/` | Read-only HTML templates. Copy from here, do not edit in place. |
| `~/.wmyskills/send-email/msg/` | The ONLY directory for `--file` HTML files. Save here, then pass the path. |

**Rules:**
- All email HTML files **must** be saved in `~/.wmyskills/send-email/msg/` before sending with `--file`
- Do NOT save HTML in the repo directory, /tmp, Downloads, Desktop, or any other location
- Do NOT create a different directory structure — send.py discovers files relative to this path
- The repo stores code, not runtime data. Runtime data goes in `~/.wmyskills/<skill-name>/`

## Security

**Never read, display, or share the contents of `scripts/.env`.** It contains SMTP credentials. Use the table below only as a reference for which variables exist — do not read the actual `.env` file.

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | — | SMTP server hostname |
| `EMAIL_PORT` | `465` | SMTP server port |
| `EMAIL_USER` | — | Sender email address |
| `EMAIL_AUTH` | — | SMTP password / app token |
| `EMAIL_NAME` | `ClaudeCode` | Sender display name |

## On Error

If sending fails:

**Connection refused / timeout** — `EMAIL_HOST` or `EMAIL_PORT` may be wrong; check with your provider.

**Authentication failed** — `EMAIL_USER`/`EMAIL_AUTH` may be wrong; some providers require an app-specific password.

**smtplib exception** — missing or incorrect env vars; SMTP exceptions are not caught and will print a traceback. Check `EMAIL_HOST`, `EMAIL_USER`, and `EMAIL_AUTH` are set correctly.

**"file not found" / "attachment not found"** — the path to the HTML file or attachment is invalid. Check the path and try again.

## Notes

- Escape sequences (`\n`, `\t`, etc.) in `--text` and `--html` body arguments are decoded automatically
- No `argparse` is used — arguments are positional and order-sensitive
- The `EMAIL_PORT` defaults to `465` (SSL); STARTTLS (587) is not supported
- The `--file` mode path supports `~` for home directory expansion
