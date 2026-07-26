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

DATA_DIR = pathlib.Path.home() / "wmy-skills" / "send-email"


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


def resolve_body(body_arg):
    """If body_arg is a path to an existing file, read it as HTML content.
    Returns (body_text, is_html) tuple.
    """
    path = pathlib.Path(body_arg)
    if path.is_file():
        return path.read_text(encoding="utf-8"), True
    # Warn if it looks like a file path but doesn't exist
    if (
        path.suffix in (".html", ".htm")
        or path.is_absolute()
        or "/" in body_arg
        or "\\" in body_arg
        or body_arg.startswith(".")
    ):
        print(
            f"Warning: '{body_arg}' looks like a file path but was not found. "
            "Sending as plain text.",
            file=sys.stderr,
        )
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

    if is_html:
        body = body_arg
    else:
        body, detected_html = resolve_body(body_arg)
        is_html = detected_html

    send(to, subject, body, is_html, attachments)
    print("OK")
