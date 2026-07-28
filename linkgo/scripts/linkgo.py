#!/usr/bin/env python3
"""LinkGo v3 remote management CLI.

Manages service cards, page config, icons, and settings on a LinkGo v3
navigation page via its HTTP API.
Requires env vars: LINKGO_HOST, LINKGO_PASSWORD
"""

import argparse
import json
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─── Config (set by _init_env) ─────────────────────────────

BASE_URL = ""
PASSWORD = ""


def _init_env():
    """Load .env and set globals BASE_URL / PASSWORD. Exit on failure."""
    global BASE_URL, PASSWORD
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    BASE_URL = os.environ.get("LINKGO_HOST", "").rstrip("/")
    PASSWORD = os.environ.get("LINKGO_PASSWORD", "")
    if not BASE_URL or not PASSWORD:
        print("Error: environment variables LINKGO_HOST and LINKGO_PASSWORD must be set", file=sys.stderr)
        sys.exit(1)


API_URL: str = ""  # set in _init_env after BASE_URL is known


# ─── HTTP helpers ─────────────────────────────────────────────

def _request(method: str, path: str, data: Optional[dict] = None,
             headers: Optional[dict] = None, auth_header: bool = False) -> dict:
    """Unified HTTP request returning JSON dict."""
    url = f"{API_URL}{path}"
    hdrs = {"Content-Type": "application/json"}
    if auth_header:
        hdrs["X-Admin-Password"] = PASSWORD
    if headers:
        hdrs.update(headers)

    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = Request(url, data=body, headers=hdrs, method=method)

    try:
        with urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)
    except (URLError, json.JSONDecodeError) as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def api_get(path: str, auth: bool = False) -> dict:
    return _request("GET", path, auth_header=auth)


def api_post(path: str, data: dict, auth: bool = False) -> dict:
    return _request("POST", path, data=data, auth_header=auth)


def load_full_data() -> dict:
    """Load full config (including disabled cards). Exit on error."""
    raw = api_get("/load_data.php", auth=True)
    if raw.get("error"):
        print(f"Error: cannot load data — {raw['error']}", file=sys.stderr)
        sys.exit(1)
    return raw


def save_data(data: dict) -> dict:
    """Save full config via update_json.php."""
    payload = {"password": PASSWORD, "content": json.dumps(data, ensure_ascii=False)}
    return api_post("/update_json.php", payload)


def output(obj):
    """Pretty-print JSON."""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


# ─── Subcommands ────────────────────────────────────────────────

def cmd_list(args):
    """List service cards."""
    if args.all:
        raw = load_full_data()
    else:
        raw = api_get("/get_show_data.php")

    services = raw.get("services", raw.get("data", {}).get("services", []))
    if args.enabled:
        services = [s for s in services if s.get("status", 1) == 1]

    if args.id:
        found = [s for s in services if s.get("id") == args.id]
        if found:
            output(found[0])
        else:
            print(f"Error: card id='{args.id}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        output(services)


def cmd_add(args):
    """Add a service card."""
    try:
        card = json.loads(args.json)
    except json.JSONDecodeError:
        print("Error: invalid JSON", file=sys.stderr)
        sys.exit(1)
    if not isinstance(card, dict):
        print("Error: card JSON must be an object", file=sys.stderr)
        sys.exit(1)
    if "id" not in card:
        print("Error: card JSON is missing 'id' field", file=sys.stderr)
        sys.exit(1)
    card_id = str(card["id"])

    data = load_full_data()
    existing = [str(s.get("id", "")) for s in data.get("services", [])]
    if card_id in existing:
        print(f"Error: id '{card_id}' already exists — use edit or choose another id", file=sys.stderr)
        sys.exit(1)

    card["id"] = card_id
    data.setdefault("services", []).append(card)
    result = save_data(data)
    output(result)
    print(f"✓ Card '{card.get('title', card_id)}' added")


def cmd_edit(args):
    """Edit a service card (merge fields by id)."""
    try:
        patch = json.loads(args.json)
    except json.JSONDecodeError:
        print("Error: invalid JSON", file=sys.stderr)
        sys.exit(1)
    if not isinstance(patch, dict):
        print("Error: patch JSON must be an object", file=sys.stderr)
        sys.exit(1)
    data = load_full_data()

    found = False
    for s in data.get("services", []):
        if str(s.get("id", "")) == args.id:
            for k, v in patch.items():
                if k != "id":
                    s[k] = v
            found = True
            break

    if not found:
        print(f"Error: card id='{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    print(f"✓ Card '{args.id}' updated")


def cmd_delete(args):
    """Delete a service card."""
    data = load_full_data()
    before = len(data.get("services", []))
    data["services"] = [s for s in data.get("services", []) if str(s.get("id", "")) != args.id]
    after = len(data["services"])

    if before == after:
        print(f"Error: card id='{args.id}' not found", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    print(f"✓ Card '{args.id}' deleted")


def cmd_enable(args):
    """Enable a service card."""
    _set_status(args.id, 1)


def cmd_disable(args):
    """Disable a service card."""
    _set_status(args.id, 0)


def _set_status(card_id: str, status: int):
    data = load_full_data()
    found = False
    for s in data.get("services", []):
        if str(s.get("id", "")) == card_id:
            s["status"] = status
            found = True
            break

    if not found:
        print(f"Error: card id='{card_id}' not found", file=sys.stderr)
        sys.exit(1)

    result = save_data(data)
    output(result)
    label = "enabled" if status == 1 else "disabled"
    print(f"✓ Card '{card_id}' {label}")


def cmd_page(args):
    """Update page settings."""
    try:
        patch = json.loads(args.json)
    except json.JSONDecodeError:
        print("Error: invalid JSON", file=sys.stderr)
        sys.exit(1)
    if not isinstance(patch, dict):
        print("Error: page JSON must be an object", file=sys.stderr)
        sys.exit(1)
    data = load_full_data()

    page = data.get("page", {})
    page.update(patch)
    data["page"] = page

    result = save_data(data)
    output(result)
    print("✓ Page settings updated")


def cmd_upload_icon(args):
    """Upload an icon file."""
    filepath = args.filepath
    if not os.path.isfile(filepath):
        print(f"Error: file not found — {filepath}", file=sys.stderr)
        sys.exit(1)

    filename = os.path.basename(filepath)
    ext = os.path.splitext(filename)[1].lower()
    allowed = {".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
    if ext not in allowed:
        print(f"Error: unsupported format {ext}; allowed: {', '.join(sorted(allowed))}", file=sys.stderr)
        sys.exit(1)

    size = os.path.getsize(filepath)
    if size > 1 * 1024 * 1024:
        print(f"Error: file too large ({size} bytes), max 1MB", file=sys.stderr)
        sys.exit(1)

    # Build multipart/form-data manually
    boundary = "----LinkGoBoundary" + str(os.getpid())
    with open(filepath, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="icons"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{API_URL}/upload_icon.php"
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("X-Admin-Password", PASSWORD)

    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            output(result)
            if result.get("success"):
                uploaded = result.get("uploaded", [])
                print(f"✓ Uploaded {len(uploaded)} file(s)")
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"Upload failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_icons(args):
    """List available icons."""
    result = api_get("/get_icons.php", auth=True)
    output(result)


def cmd_export(args):
    """Export full config to file or stdout."""
    data = load_full_data()
    formatted = json.dumps(data, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted)
        print(f"✓ Exported to {args.output}")
    else:
        print(formatted)


def cmd_import(args):
    """Import config file (overwrites all data)."""
    with open(args.filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = save_data(data)
    output(result)
    print("✓ Config imported")


def cmd_reset(args):
    """Reset to default config (clears all cards)."""
    payload = {"password": PASSWORD, "content": "INITIALIZE_WEB_JSON"}
    result = api_post("/update_json.php", payload)
    output(result)
    print("✓ Config reset to default")


def cmd_change_password(args):
    """Change admin password."""
    result = api_post("/change_password.php", {
        "old_password": args.old_password,
        "new_password": args.new_password,
    })
    output(result)
    if result.get("success"):
        print("✓ Password changed")
    else:
        print(f"✗ Password change failed: {result.get('msg', result.get('error', 'unknown error'))}", file=sys.stderr)
        sys.exit(1)


def cmd_debug(args):
    """Get debug info."""
    result = api_get("/debugInfo.php")
    output(result)


def cmd_ping(args):
    """Connectivity test."""
    try:
        result = api_get("/get_show_data.php")
        services = result.get("data", result).get("services", [])
        print(f"✓ Connected — {len(services)} service card(s)")
    except Exception as e:
        print(f"✗ Connection failed: {e}", file=sys.stderr)
        sys.exit(1)


# ─── CLI Entry Point ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="linkgo",
        description="LinkGo v3 remote management CLI",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list
    p = sub.add_parser("list", help="List service cards")
    p.add_argument("--all", action="store_true", help="Show all cards (including disabled)")
    p.add_argument("--enabled", action="store_true", help="Show only enabled cards (default)")
    p.add_argument("--id", help="Query card by id")
    p.set_defaults(func=cmd_list)

    # add
    p = sub.add_parser("add", help="Add a service card")
    p.add_argument("json", help='Card JSON, e.g. \'{"id":"x","title":"X",...}\'')
    p.set_defaults(func=cmd_add)

    # edit
    p = sub.add_parser("edit", help="Edit a service card")
    p.add_argument("id", help="Target card id")
    p.add_argument("json", help='Fields to update, e.g. \'{"title":"New Title"}\'')
    p.set_defaults(func=cmd_edit)

    # delete
    p = sub.add_parser("delete", help="Delete a service card")
    p.add_argument("id", help="Target card id")
    p.set_defaults(func=cmd_delete)

    # enable / disable
    p = sub.add_parser("enable", help="Enable a service card")
    p.add_argument("id", help="Target card id")
    p.set_defaults(func=cmd_enable)

    p = sub.add_parser("disable", help="Disable a service card")
    p.add_argument("id", help="Target card id")
    p.set_defaults(func=cmd_disable)

    # page
    p = sub.add_parser("page", help="Update page settings")
    p.add_argument("json", help='Page fields JSON')
    p.set_defaults(func=cmd_page)

    # upload-icon
    p = sub.add_parser("upload-icon", help="Upload an icon file")
    p.add_argument("filepath", help="Path to icon file")
    p.set_defaults(func=cmd_upload_icon)

    # icons
    p = sub.add_parser("icons", help="List available icons")
    p.set_defaults(func=cmd_icons)

    # export
    p = sub.add_parser("export", help="Export config to file")
    p.add_argument("-o", "--output", help="Output file path (default: stdout)")
    p.set_defaults(func=cmd_export)

    # import
    p = sub.add_parser("import", help="Import config file (overwrites all data)")
    p.add_argument("filepath", help="Config file path")
    p.set_defaults(func=cmd_import)

    # reset
    p = sub.add_parser("reset", help="Reset to default config")
    p.set_defaults(func=cmd_reset)

    # change-password
    p = sub.add_parser("change-password", help="Change admin password")
    p.add_argument("old_password", help="Current password")
    p.add_argument("new_password", help="New password")
    p.set_defaults(func=cmd_change_password)

    # debug
    p = sub.add_parser("debug", help="Get debug info")
    p.set_defaults(func=cmd_debug)

    # ping
    p = sub.add_parser("ping", help="Connectivity test")
    p.set_defaults(func=cmd_ping)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    _init_env()
    global API_URL
    API_URL = f"{BASE_URL}/api"

    args.func(args)


if __name__ == "__main__":
    main()
