---
name: send_email
description: "Send emails via SMTP from ClaudeCode. Use this skill whenever the user wants to send an email, message someone via email, or attach files to an email. Supports plain text, HTML, and attachments."
---

# Send Email Skill

A skill for sending emails through ClaudeCode using SMTP.

## When to Use

Use this skill when the user asks to:
- Send an email to someone
- Email a file or document
- Send a message via email
- Forward information by email

## Usage

```bash
cd {this_skill_dir} && python3 scripts/send.py <to> <subject> <body> [--html] [attachment...]
```

### Parameters

- `<to>`: Recipient email address (e.g., `recipient@example.com`)
- `<subject>`: Email subject line
- `<body>`: Email body content
- `--html`: Optional flag to send body as HTML (default is plain text)
- `[attachment...]`: Optional file paths to attach

### Examples

**Send plain text email:**
```bash
cd {this_skill_dir} && python3 scripts/send.py user@example.com "Meeting Tomorrow" "Hi, just confirming our meeting at 3pm."
```

**Send HTML email:**
```bash
cd {this_skill_dir} && python3 scripts/send.py user@example.com "Weekly Report" "<h1>Weekly Report</h1><p>Here's your report...</p>" --html
```

**Send email with attachments:**
```bash
cd {this_skill_dir} && python3 scripts/send.py user@example.com "Project Files" "Please find the attached files." /path/to/file1.pdf /path/to/file2.docx
```

## Configuration

The skill reads SMTP credentials from environment variables:

| Variable | Description |
|----------|-------------|
| `EMAIL_HOST` | SMTP server hostname |
| `EMAIL_PORT` | SMTP server port |
| `EMAIL_USER` | Email address (sender) |
| `EMAIL_AUTH` | SMTP password/auth token |

## Error Handling

- If required environment variables are missing, the script will exit with an error message
- The script validates that `EMAIL_HOST`, `EMAIL_USER`, and `EMAIL_AUTH` are set
- If no arguments are provided, it shows the usage information

## Notes

- Emails are sent from "ClaudeCode" as the display name
- Uses SMTP over SSL (port 465 by default)
- Attachments are sent as binary data
