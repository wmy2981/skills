#!/usr/bin/env python3
"""Send email via SMTP. Reads credentials from environment variables.
Environment:
  EMAIL_HOST - SMTP host
  EMAIL_PORT - SMTP port
  EMAIL_USER - SMTP username
  EMAIL_AUTH - SMTP password

Usage: send.py <to> <subject> <body> [--html] [attachment...]
  --html: send body as HTML (default is plain text)
"""
import sys, os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def get_config():
    host = os.environ.get("EMAIL_HOST", "")
    user = os.environ.get("EMAIL_USER", "")
    password = os.environ.get("EMAIL_AUTH", "")
    port_str = os.environ.get("EMAIL_PORT", "465")

    if not all([host, user, password]):
        raise RuntimeError(
            "Missing environment variables: "
            "EMAIL_HOST, EMAIL_USER, EMAIL_AUTH are required"
        )
    return {
        'host': host,
        'port': int(port_str),
        'user': user,
        'password': password,
    }

def send(to, subject, body, is_html=False, attachments=None):
    cfg = get_config()
    msg = MIMEMultipart('alternative')
    msg['From'] = f'ClaudeCode <{cfg["user"]}>'
    msg['To'] = to
    msg['Subject'] = subject

    subtype = 'html' if is_html else 'plain'
    msg.attach(MIMEText(body, subtype, 'utf-8'))

    if attachments:
        for path in attachments:
            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
                msg.attach(part)

    server = smtplib.SMTP_SSL(cfg['host'], cfg['port'])
    server.login(cfg['user'], cfg['password'])
    server.send_message(msg)
    server.quit()

if __name__ == '__main__':
    args = sys.argv[1:]
    is_html = False

    if '--html' in args:
        is_html = True
        args.remove('--html')

    if len(args) < 3:
        print("Usage: send.py <to> <subject> <body> [--html] [attachment...]")
        sys.exit(1)

    to = args[0]
    subject = args[1]
    body = args[2]
    attachments = args[3:] if len(args) > 3 else None
    send(to, subject, body, is_html, attachments)
    print('OK')
