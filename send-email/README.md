# Send Email Skill

Send emails via SMTP from Claude Code. Supports plain text, HTML, attachments, and HTML templates.

## Directory Structure

**Code (this repo):**

```
send-email/
├── SKILL.md          # Skill definition
├── README.md         # This file
└── scripts/
    ├── .env.example  # Environment variables template (copy to .env)
    └── send.py       # Email sending script
```

**Data (your home directory):**

```
~/.wmyskills/send-email/
├── templates/        # HTML email templates (copy from here)
└── msg/             # Edited messages to send (edit here)
```

## Setup

1. **Configure credentials:**

   Copy and edit the `.env.example`:

   ```bash
   cd send-email/scripts
   cp .env.example .env
   # Edit .env with your SMTP credentials
   ```

   Or set environment variables globally:

   ```bash
   export EMAIL_HOST=smtp.example.com
   export EMAIL_PORT=465
   export EMAIL_USER=you@example.com
   export EMAIL_AUTH=your_password
   export EMAIL_NAME="Your Name"
   ```

2. **Install optional dependency:**

   ```bash
   pip install python-dotenv
   ```

## Usage

```bash
python scripts/send.py <to> <subject> <mode> <body> [attachment...]
```

### Modes

| Mode | Purpose |
|------|---------|
| `--text` | Plain text email |
| `--html` | Inline HTML string |
| `--file` | HTML from file |

### Examples

**Plain text:**
```bash
python scripts/send.py user@example.com "Hello" --text "Just saying hi"
```

**Inline HTML:**
```bash
python scripts/send.py user@example.com "Report" --html "<b>Summary</b><p>Content</p>"
```

**HTML from file:**
```bash
# 1. Copy template, 2. Edit, 3. Send with --file:
cp ~/.wmyskills/send-email/templates/default.html ~/.wmyskills/send-email/msg/my_email.html
python scripts/send.py user@example.com "Subject" --file ../msg/my_email.html
```

**With attachments (any mode):**
```bash
python scripts/send.py user@example.com "Files" --text "See attached" file1.pdf file2.docx
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_HOST` | — | SMTP server hostname |
| `EMAIL_PORT` | `465` | SMTP server port |
| `EMAIL_USER` | — | Sender email address |
| `EMAIL_AUTH` | — | SMTP password / app token |
| `EMAIL_NAME` | `ClaudeCode` | Sender display name |

## Troubleshooting

- **"Connection refused / timeout"** — `EMAIL_HOST` or `EMAIL_PORT` may be wrong
- **"Authentication failed"** — `EMAIL_USER`/`EMAIL_AUTH` may be wrong; some providers require an app-specific password
