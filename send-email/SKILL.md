---
name: send-email
description: "Use when the user wants to send an email, email a file or document, send a message via email, forward information by email, or use HTML email templates."
---

# Send Email Skill

Send emails via SMTP from Claude Code. Supports plain text, HTML, attachments, and template-based workflow.

## Setup

### 1. Install Dependencies

```bash
pip install python-dotenv
```

`python-dotenv` is optional — without it, set environment variables through the system (e.g., export in shell profile, IDE config, CI secrets).

### 2. Configure Credentials

Choose one of the following:

**Option A — `.env` file (recommended):**

Copy `scripts/.env.example` to `scripts/.env` and fill in your SMTP credentials:

```bash
cp scripts/.env.example scripts/.env
# Edit .env with your SMTP credentials
```

**Option B — System environment variables:**

```bash
export EMAIL_HOST=smtp.example.com
export EMAIL_PORT=465
export EMAIL_USER=you@example.com
export EMAIL_AUTH=your_password
export EMAIL_NAME="Your Name"
```

Variable loading order: system env vars take precedence over `.env` file.

### 3. Data Directories

The script automatically creates these in your home folder on first run:

```
~/wmy-skills/send-email/
├── templates/     # HTML email templates (AI reads from here)
└── msg/           # Edited messages ready to send (AI writes here)
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_HOST` | Yes | — | SMTP server hostname |
| `EMAIL_PORT` | No | `465` | SMTP server port |
| `EMAIL_USER` | Yes | — | Sender email address |
| `EMAIL_AUTH` | Yes | — | SMTP password / app token |
| `EMAIL_NAME` | No | `ClaudeCode` | Sender display name |

## Usage

```bash
cd send-email && python scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

- `<body>`: plain text, HTML string, or path to an `.html` file (auto-detected)
- `--html`: force HTML mode if body isn't a file path
- `[attachment...]`: one or more file paths to attach

### Examples

**Send plain text:**
```bash
python scripts/send.py user@example.com "Hello" "Just saying hi"
```

**Send from template file:**
```bash
# AI copies template → edits → runs:
python scripts/send.py user@example.com "Newsletter" ../msg/my_newsletter.html
```

**With attachment:**
```bash
python scripts/send.py user@example.com "Files" "See attached" report.pdf
```

## Template Workflow

1. Copy a `.html` from `~/wmy-skills/send-email/templates/` to `~/wmy-skills/send-email/msg/`
2. Edit the copy with your content
3. Run `send.py` with the file path as `<body>` — script reads it and sends as HTML

## Notes

- Uses SMTP over SSL (port 465)
- Attachments sent as binary
- Body file path → auto HTML (no `--html` needed)
