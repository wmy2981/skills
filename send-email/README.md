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
~/.wmy-skills/send-email/
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
python scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

### Examples

**Basic text email:**

```bash
python scripts/send.py user@example.com "Hello" "Just saying hi"
```

**HTML email:**

```bash
python scripts/send.py user@example.com "Report" "<h1>Report</h1><p>Content</p>" --html
```

**From a template file:**

```bash
# 1. Copy template
cp ~/.wmy-skills/send-email/templates/default.html ~/.wmy-skills/send-email/msg/my_email.html
# 2. Edit the file with your content
# 3. Send it — script detects file path and sends as HTML
python scripts/send.py user@example.com "Subject" ../msg/my_email.html
```

**With attachments:**

```bash
python scripts/send.py user@example.com "Files" "See attached" file1.pdf file2.docx
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_HOST` | Yes | — | SMTP server hostname |
| `EMAIL_PORT` | No | `465` | SMTP server port |
| `EMAIL_USER` | Yes | — | Sender email address |
| `EMAIL_AUTH` | Yes | — | SMTP password / app token |
| `EMAIL_NAME` | No | `ClaudeCode` | Sender display name |

## Template Workflow

1. Copy a `.html` template from `~/.wmy-skills/send-email/templates/` to `~/.wmy-skills/send-email/msg/`
2. Edit the copy to fill in your content
3. Call `send.py` with the file path as the `<body>` argument
4. The script detects the file path, reads it, and sends as HTML

## Troubleshooting

- **"Missing environment variables"**: Ensure `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_AUTH` are set
- **SSL errors**: Verify `EMAIL_PORT` matches your SMTP provider (465 for SSL, 587 for TLS)
- **Authentication failed**: Check your credentials; some providers require an app-specific password
