#!/usr/bin/env python3
"""Send email via SMTP. Reads credentials from environment variables or .env.
Environment:
  EMAIL_HOST - SMTP host
  EMAIL_PORT - SMTP port (default 465)
  EMAIL_USER - SMTP username
  EMAIL_AUTH - SMTP password
  EMAIL_NAME - Sender display name (default "ClaudeCode")

Usage:
  send.py <to> <subject> --text <body>
  send.py <to> <subject> --html <html_string>
  send.py <to> <subject> --file <file.html>
  [attachment...] can be appended to any form.
"""
import os
import pathlib
import re
import smtplib
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Force UTF-8 on Windows terminals (default GBK)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Optional dotenv support
try:
    from dotenv import load_dotenv
    env_path = pathlib.Path(__file__).resolve().parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path)
except ImportError:
    pass

DATA_DIR = pathlib.Path.home() / ".wmyskills" / "send-email"


def ensure_data_dirs():
    """Create data directories in user home if they don't exist."""
    (DATA_DIR / "templates").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "msg").mkdir(parents=True, exist_ok=True)


def get_config():
    return {
        "host": os.environ.get("EMAIL_HOST", ""),
        "port": int(os.environ.get("EMAIL_PORT", "465")),
        "user": os.environ.get("EMAIL_USER", ""),
        "password": os.environ.get("EMAIL_AUTH", ""),
        "sender_name": os.environ.get("EMAIL_NAME") or "ClaudeCode",
    }


def decode_escapes(text):
    """Decode escape sequences like \\n, \\t from CLI args into real characters.

    Implemented with regex instead of codecs.decode(unicode_escape), which
    would decode non-ASCII text as latin-1 and corrupt Chinese content.
    """
    return re.sub(
        r"\\([nrt\\])",
        lambda m: {"n": "\n", "r": "\r", "t": "\t", "\\": "\\"}[m.group(1)],
        text,
    )


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
            if not attach_path.is_file():
                print(f"Error: attachment not found: {attach_path}", file=sys.stderr)
                sys.exit(1)
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

    if len(args) < 4:
        print(
            "Usage:\n"
            "  send.py <to> <subject> --text <body>\n"
            "  send.py <to> <subject> --html <html_string>\n"
            "  send.py <to> <subject> --file <file.html>\n"
            "  [attachment...] can be appended to any form."
        )
        sys.exit(1)

    to = args[0]
    subject = args[1]
    mode = args[2]
    body_arg = args[3]
    attachments = args[4:] if len(args) > 4 else None

    if mode == "--text":
        body = decode_escapes(body_arg)
        is_html = False
    elif mode == "--html":
        body = decode_escapes(body_arg)
        is_html = True
    elif mode == "--file":
        file_path = pathlib.Path(body_arg).expanduser()
        if not file_path.is_file():
            print(f"Error: file not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        body = file_path.read_text(encoding="utf-8")
        is_html = True
    else:
        print(f"Error: unknown mode '{mode}'. Use --text, --html, or --file.", file=sys.stderr)
        sys.exit(1)

    send(to, subject, body, is_html, attachments)
    print("OK")
