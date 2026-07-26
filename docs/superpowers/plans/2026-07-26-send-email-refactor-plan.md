# Send-Email Skill Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `send_email` skill → `send-email` with `.env` support, dynamic sender name, template workflow, and code/data separation.

**Architecture:** Single Python script (`send.py`) enhanced with `python-dotenv` for `.env` loading, `EMAIL_NAME` for dynamic sender display name, file-path body detection for template workflow. User data stored in `~/wmy-skills/send-email/{templates,msg/}` (resolved via `Path.home()`).

**Tech Stack:** Python 3 (stdlib: `smtplib`, `email.*`, `pathlib`, `os`, `sys`), optional `python-dotenv`

## Global Constraints

- Script must dynamically resolve user home directory via `pathlib.Path.home()` or `os.path.expanduser("~")` — no hardcoded paths
- `python-dotenv` is a soft dependency; script works without it if env vars are set system-wide
- All script references updated from `send_email` to `send-email`
- SKILL.md frontmatter `name` must use hyphens, not underscores: `send-email`
- Data directory (`~/wmy-skills/send-email/`) created automatically by script on startup

---

### Task 1: Create feature branch + rename directory

**Files:**
- Rename: `send_email/` → `send-email/`

- [ ] **Step 1: Create and switch to feature branch**

```bash
cd g:/Projects/agent/wmy-skills
git checkout -b feat/refactor-send-email
```
Expected: Switched to new branch `feat/refactor-send-email`

- [ ] **Step 2: Rename directory with git mv**

```bash
git mv send_email send-email
```
Expected: directory renamed, git tracks the move

- [ ] **Step 3: Verify no stale references remain in repo**

```bash
git status
```
Expected: only change is renamed directory

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: rename send_email to send-email"

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 2: Update SKILL.md

**Files:**
- Modify: `send-email/SKILL.md`

**Guidance from skill-creator:**
- `name` uses hyphens only: `send-email`
- `description` starts with "Use when...", describes triggering conditions only (not workflow)
- Add `EMAIL_NAME` to config table, template workflow section, `.env` setup section

- [ ] **Step 1: Rewrite SKILL.md**

Old frontmatter:
```yaml
name: send_email
description: "Send emails via SMTP from ClaudeCode. ..."
```

New frontmatter:
```yaml
name: send-email
description: "Use when the user wants to send an email, email a file or document, send a message via email, forward information by email, or use HTML email templates."
```

Full updated SKILL.md:

```markdown
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

Copy `scripts/.env` from the skill directory and populate it:

```bash
cp send-email/scripts/.env send-email/scripts/.env
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
```

- [ ] **Step 2: Verify the file**

```bash
python -c "import yaml; yaml.safe_load(open('send-email/SKILL.md').split('---')[1])"
```
Expected: no YAML errors

- [ ] **Step 3: Commit**

```bash
git add send-email/SKILL.md
git commit -m "docs(send-email): update SKILL.md with new name, config, template workflow"

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 3: Enhance send.py

**Files:**
- Modify: `send-email/scripts/send.py`

**Changes:**
1. Add `python-dotenv` loading at startup (optional, silent if missing)
2. Read `EMAIL_NAME` for sender display name (default `"ClaudeCode"`)
3. Body argument: if it's a path to an existing file, read its content and send as HTML
4. Auto-create data directories (`~/wmy-skills/send-email/templates/`, `~/wmy-skills/send-email/msg/`)
5. Update usage string

- [ ] **Step 1: Write enhanced send.py**

```python
#!/usr/bin/env python3
"""Send email via SMTP. Reads credentials from environment variables or .env.
Environment:
  EMAIL_HOST - SMTP host
  EMAIL_PORT - SMTP port (default 465)
  EMAIL_USER - SMTP username
  EMAIL_AUTH - SMTP password
  EMAIL_NAME - Sender display name (default "ClaudeCode")

Usage: send.py <to> <subject> <body> [--html] [attachment...]
  --html: send body as HTML (default is plain text)
  If <body> is a path to an existing .html file, it is read and sent as HTML.
"""
import sys
import os
import smtplib
import pathlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Optional dotenv support
try:
    from dotenv import load_dotenv
    env_path = pathlib.Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
except ImportError:
    pass

DATA_DIR = pathlib.Path.home() / "wmy-skills" / "send-email"


def ensure_data_dirs():
    """Create data directories in user home if they don't exist."""
    (DATA_DIR / "templates").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "msg").mkdir(parents=True, exist_ok=True)


def get_config():
    host = os.environ.get("EMAIL_HOST", "")
    user = os.environ.get("EMAIL_USER", "")
    password = os.environ.get("EMAIL_AUTH", "")
    port_str = os.environ.get("EMAIL_PORT", "465")
    sender_name = os.environ.get("EMAIL_NAME", "ClaudeCode")

    if not all([host, user, password]):
        raise RuntimeError(
            "Missing environment variables: "
            "EMAIL_HOST, EMAIL_USER, EMAIL_AUTH are required"
        )
    return {
        "host": host,
        "port": int(port_str),
        "user": user,
        "password": password,
        "sender_name": sender_name,
    }


def resolve_body(body_arg):
    """If body_arg is a path to an existing file, read it as HTML content.
    Returns (body_text, is_html) tuple.
    """
    path = pathlib.Path(body_arg)
    if path.is_file():
        return path.read_text(encoding="utf-8"), True
    return body_arg, False


def send(to, subject, body, is_html=False, attachments=None):
    cfg = get_config()
    msg = MIMEMultipart("alternative")
    msg["From"] = f'{cfg["sender_name"]} <{cfg["user"]}>'
    msg["To"] = to
    msg["Subject"] = subject

    subtype = "html" if is_html else "plain"
    msg.attach(MIMEText(body, subtype, "utf-8"))

    if attachments:
        for path_str in attachments:
            attach_path = pathlib.Path(path_str)
            with open(attach_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{attach_path.name}"',
                )
                msg.attach(part)

    server = smtplib.SMTP_SSL(cfg["host"], cfg["port"])
    server.login(cfg["user"], cfg["password"])
    server.send_message(msg)
    server.quit()


if __name__ == "__main__":
    ensure_data_dirs()

    args = sys.argv[1:]
    is_html = False

    if "--html" in args:
        is_html = True
        args.remove("--html")

    if len(args) < 3:
        print(
            "Usage: send.py <to> <subject> <body> [--html] [attachment...]\n"
            "  If <body> is a file path, it is read and sent as HTML."
        )
        sys.exit(1)

    to = args[0]
    subject = args[1]
    body_arg = args[2]
    attachments = args[3:] if len(args) > 3 else None

    body, detected_html = resolve_body(body_arg)
    is_html = is_html or detected_html

    send(to, subject, body, is_html, attachments)
    print("OK")
```

- [ ] **Step 2: Verify script parses without syntax errors**

```bash
python -m py_compile send-email/scripts/send.py
```
Expected: no output (success)

- [ ] **Step 3: Verify script shows usage when run without args**

```bash
cd send-email && python scripts/send.py 2>&1 || true
```
Expected: prints usage message and exits (can't actually send without config)

- [ ] **Step 4: Verify data directories were created**

```bash
ls -la ~/wmy-skills/send-email/
ls -la ~/wmy-skills/send-email/templates/
ls -la ~/wmy-skills/send-email/msg/
```
Expected: both directories exist

- [ ] **Step 5: Commit**

```bash
git add send-email/scripts/send.py
git commit -m "feat(send-email): add dotenv, EMAIL_NAME, template file detection, data dirs"

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 4: Create .env template

**Files:**
- Create: `send-email/scripts/.env`

- [ ] **Step 1: Write .env template**

```
# SMTP Configuration
EMAIL_HOST=smtp.example.com
EMAIL_PORT=465
EMAIL_USER=your_email@example.com
EMAIL_AUTH=your_password_or_app_token
EMAIL_NAME=Your Name
```

- [ ] **Step 2: Commit**

```bash
git add send-email/scripts/.env
git commit -m "chore(send-email): add .env template"

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 5: Create default HTML template in user data dirs

**Files:**
- Create: `~/wmy-skills/send-email/templates/default.html`

- [ ] **Step 1: Create default.html template**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
        .footer { border-top: 2px solid #eee; padding-top: 10px; margin-top: 20px; font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2><!-- SUBJECT --></h2>
        </div>
        <div class="content">
            <!-- CONTENT -->
        </div>
        <div class="footer">
            <p>Sent via Claude Code</p>
        </div>
    </div>
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
# Template lives outside repo, just verify it exists
ls -la ~/wmy-skills/send-email/templates/default.html
```
Expected: file exists

---

### Task 6: Create README.md

**Files:**
- Create: `send-email/README.md`

- [ ] **Step 1: Write README.md**

```markdown
# Send Email Skill

Send emails via SMTP from Claude Code. Supports plain text, HTML, attachments, and HTML templates.

## Directory Structure

**Code (this repo):**
```
send-email/
├── SKILL.md          # Skill definition
├── README.md         # This file
└── scripts/
    ├── .env          # Environment variables template
    └── send.py       # Email sending script
```

**Data (your home directory):**
```
~/wmy-skills/send-email/
├── templates/        # HTML email templates (copy from here)
└── msg/             # Edited messages to send (edit here)
```

## Setup

1. **Configure credentials:**

   Copy and edit the `.env` template:
   ```bash
   cp scripts/.env scripts/.env
   # Edit with your SMTP credentials
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
cp ~/wmy-skills/send-email/templates/default.html ~/wmy-skills/send-email/msg/my_email.html
# 2. Edit the file with your content
# 3. Send it
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

1. Copy a `.html` template from `~/wmy-skills/send-email/templates/` to `~/wmy-skills/send-email/msg/`
2. Edit the copy to fill in your content
3. Call `send.py` with the file path as the `<body>` argument
4. The script detects the file path, reads it, and sends as HTML

## Troubleshooting

- **"Missing environment variables"**: Ensure `EMAIL_HOST`, `EMAIL_USER`, `EMAIL_AUTH` are set
- **SSL errors**: Verify `EMAIL_PORT` matches your SMTP provider (465 for SSL, 587 for TLS)
- **Authentication failed**: Check your credentials; some providers require an app-specific password
```

- [ ] **Step 2: Commit**

```bash
git add send-email/README.md
git commit -m "docs(send-email): add README with setup and usage guide"

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

### Task 7: Final review — check everything works together

- [ ] **Step 1: Verify git log shows clean commits**

```bash
cd g:/Projects/agent/wmy-skills
git log --oneline
```
Expected: commits for each step

- [ ] **Step 2: Verify script syntax**

```bash
python -m py_compile send-email/scripts/send.py
```
Expected: no output (success)

- [ ] **Step 3: Verify no stale references to old name**

```bash
grep -r "send_email" send-email/ --include="*.md" --include="*.py" || echo "No stale references found"
```
Expected: no stale references

- [ ] **Step 4: Verify data dirs exist**

```bash
ls -d ~/wmy-skills/send-email/templates ~/wmy-skills/send-email/msg
```
Expected: both exist

- [ ] **Step 5: Verify SKILL.md frontmatter parses**

```bash
python -c "import yaml; d=yaml.safe_load(open('send-email/SKILL.md').read().split('---')[1]); print(d['name'])"
```
Expected: `send-email`

- [ ] **Step 6: Present completion report to user**
