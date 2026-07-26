---
name: send-email
description: "Use when the user wants to send an email, email a file or document, send a message via email, forward information by email, or use HTML email templates."
---

# Send Email Skill

A skill for sending emails through Claude Code using SMTP.

## When to Use

Use this skill when the user asks to:
- Send an email to someone
- Email a file or document
- Send a message via email
- Forward information by email
- Use an HTML email template

## Setup

### 1. Configuration File

Copy `scripts/.env.example` to `scripts/.env` and populate it:

```bash
cp scripts/.env.example scripts/.env
# Then edit .env with your SMTP credentials
```

### 2. Python Dependencies (optional)

Install `python-dotenv` for `.env` file support:

```bash
pip install python-dotenv
```

Without it, set environment variables globally.

### 3. Data Directories

The script automatically creates the following directories in your home folder on first run:

```
~/wmy-skills/send-email/
├── templates/          # Place HTML templates here (AI reads from here)
└── msg/               # Edited messages ready to send (AI writes here)
```

## Usage

```bash
cd {this_skill_dir} && python scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

### Parameters

- `<to>`: Recipient email address (e.g., `recipient@example.com`)
- `<subject>`: Email subject line
- `<body>`: Email body content, or path to an `.html` file to send as HTML body
- `--html`: Optional flag to send body as HTML (default is plain text)
- `[attachment...]`: Optional file paths to attach

### Examples

**Send plain text email:**
```bash
cd {this_skill_dir} && python scripts/send.py user@example.com "Meeting Tomorrow" "Hi, just confirming our meeting at 3pm."
```

**Send HTML email:**
```bash
cd {this_skill_dir} && python scripts/send.py user@example.com "Weekly Report" "<h1>Weekly Report</h1><p>Here's your report...</p>" --html
```

**Send email from template (file path as body):**
```bash
cd {this_skill_dir} && python scripts/send.py user@example.com "Newsletter" ../msg/my_newsletter.html
```

**Send email with attachments:**
```bash
cd {this_skill_dir} && python scripts/send.py user@example.com "Project Files" "Please find the attached files." /path/to/file1.pdf /path/to/file2.docx
```

## Template Workflow

1. Copy an HTML template from `~/wmy-skills/send-email/templates/` to `~/wmy-skills/send-email/msg/`
2. Edit the copy with the specific content
3. Run the send command with the file path as the `<body>` argument
4. The script detects the argument is a file path, reads it as HTML, and sends

## Configuration

The skill reads SMTP credentials from environment variables (or `scripts/.env`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_HOST` | Yes | — | SMTP server hostname |
| `EMAIL_PORT` | No | `465` | SMTP server port |
| `EMAIL_USER` | Yes | — | Email address (sender) |
| `EMAIL_AUTH` | Yes | — | SMTP password/auth token |
| `EMAIL_NAME` | No | `ClaudeCode` | Sender display name |

Variable loading order:
1. System environment variables (highest priority)
2. `scripts/.env` file (if `python-dotenv` is installed)

## Error Handling

- If required environment variables are missing, the script will exit with an error message
- The script validates that `EMAIL_HOST`, `EMAIL_USER`, and `EMAIL_AUTH` are set
- If no arguments are provided, it shows the usage information

## Notes

- Uses SMTP over SSL (port 465 by default)
- Attachments are sent as binary data
- If `<body>` is a path to an existing file, it's read and sent as HTML (no need for `--html` flag)
