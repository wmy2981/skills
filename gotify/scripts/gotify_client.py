#!/usr/bin/env python3
"""
Gotify CLI Client — wraps Gotify REST API v2.0.2 for agent use.

Environment variables:
  GOTIFY_URL          - Server base URL (e.g. https://gotify.example.com)
  GOTIFY_CLIENT_TOKEN - Client token (device/subscription mgmt)
  GOTIFY_APP_TOKEN    - App token (send messages)

Usage:
  python gotify_client.py <command> [options]
"""

import argparse
import json
import os
import sys
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _base_url():
    url = os.environ.get("GOTIFY_URL", "").rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    if not url:
        print(json.dumps({"error": "GOTIFY_URL environment variable not set"}))
        sys.exit(1)
    return url


def _headers(token=None):
    h = {"Content-Type": "application/json"}
    t = token or os.environ.get("GOTIFY_APP_TOKEN") or os.environ.get("GOTIFY_CLIENT_TOKEN")
    if not t:
        print(json.dumps({"error": "No token available — set GOTIFY_APP_TOKEN or GOTIFY_CLIENT_TOKEN"}))
        sys.exit(1)
    h["X-Gotify-Key"] = t
    return h


def _request(method, path, token=None, body=None, params=None):
    url = _base_url() + path
    if params:
        qs = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        if qs:
            url += "?" + qs
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {"status": "ok"}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            err = json.loads(body)
        except Exception:
            err = {"error": body}
        err["http_status"] = e.code
        print(json.dumps(err, indent=2))
        sys.exit(1)
    except urllib.error.URLError as e:
        print(json.dumps({"error": str(e.reason)}))
        sys.exit(1)


def _out(data):
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


# ── Commands ────────────────────────────────────────────────────────────────

def cmd_send(args):
    body = {"message": args.message}
    if args.title:
        body["title"] = args.title
    if args.priority is not None:
        body["priority"] = args.priority
    if args.extras:
        body["extras"] = json.loads(args.extras)
    token = args.token or os.environ.get("GOTIFY_APP_TOKEN")
    if not token:
        print(json.dumps({"error": "No app token (set GOTIFY_APP_TOKEN or use --token)"}))
        sys.exit(1)
    _out(_request("POST", "/message", token=token, body=body))


def cmd_list_apps(args):
    _out(_request("GET", "/application", token=os.environ.get("GOTIFY_CLIENT_TOKEN")))


def cmd_create_app(args):
    body = {"name": args.name}
    if args.description:
        body["description"] = args.description
    if args.default_priority is not None:
        body["defaultPriority"] = args.default_priority
    if args.image:
        body["image"] = args.image
    if args.internal:
        body["internal"] = True
    _out(_request("POST", "/application", token=os.environ.get("GOTIFY_CLIENT_TOKEN"), body=body))


def cmd_delete_app(args):
    _request("DELETE", f"/application/{args.id}", token=os.environ.get("GOTIFY_CLIENT_TOKEN"))
    _out({"status": "deleted", "id": args.id})


def cmd_list_clients(args):
    _out(_request("GET", "/client", token=os.environ.get("GOTIFY_CLIENT_TOKEN")))


def cmd_create_client(args):
    _out(_request("POST", "/client", token=os.environ.get("GOTIFY_CLIENT_TOKEN"), body={"name": args.name}))


def cmd_delete_client(args):
    _request("DELETE", f"/client/{args.id}", token=os.environ.get("GOTIFY_CLIENT_TOKEN"))
    _out({"status": "deleted", "id": args.id})


def cmd_list_messages(args):
    params = {"limit": args.limit, "since": args.since}
    token = args.token or os.environ.get("GOTIFY_CLIENT_TOKEN")
    _out(_request("GET", "/message", token=token, params=params))


def cmd_delete_message(args):
    _request("DELETE", f"/message/{args.id}", token=os.environ.get("GOTIFY_CLIENT_TOKEN"))
    _out({"status": "deleted", "id": args.id})


def cmd_delete_messages(args):
    # --before is required by the argparse definition, but guard against
    # edge cases where argparse could pass None (e.g. future refactors).
    if args.before is None:
        print(json.dumps({"error": "--before is required"}))
        sys.exit(1)
    params = {"before": args.before}
    if args.app_id is not None:
        params["appid"] = args.app_id
    _request("DELETE", "/message", token=os.environ.get("GOTIFY_CLIENT_TOKEN"), params=params)
    _out({"status": "bulk_deleted"})


def cmd_list_plugins(args):
    _out(_request("GET", "/plugin", token=os.environ.get("GOTIFY_CLIENT_TOKEN")))


def cmd_toggle_plugin(args):
    body = {"enabled": not args.disable}
    _out(_request("PATCH", f"/plugin/{args.id}", token=os.environ.get("GOTIFY_CLIENT_TOKEN"), body=body))


def cmd_health(args):
    _out(_request("GET", "/health"))


def cmd_version(args):
    _out(_request("GET", "/version"))


def cmd_ws_subscribe(args):
    """Real-time message stream via WebSocket (requires websocket-client)."""
    try:
        import websocket
    except ImportError:
        print(json.dumps({"error": "pip install websocket-client first"}))
        sys.exit(1)
    base = _base_url().replace("https://", "wss://").replace("http://", "ws://")
    token = args.token or os.environ.get("GOTIFY_CLIENT_TOKEN") or os.environ.get("GOTIFY_APP_TOKEN")
    if not token:
        print(json.dumps({"error": "No token available"}))
        sys.exit(1)
    url = f"{base}/stream?token={token}"
    print(f"Connecting: {url}")

    def on_message(ws, message):
        print(json.dumps(json.loads(message), indent=2, ensure_ascii=False, default=str))

    def on_error(ws, error):
        print(json.dumps({"ws_error": str(error)}), file=sys.stderr)

    def on_close(ws, code, reason):
        print(json.dumps({"ws_closed": code, "reason": reason}))

    def on_open(ws):
        print(json.dumps({"ws_connected": True}))

    ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error,
                                on_close=on_close, on_open=on_open)
    ws.run_forever()


# ── CLI Parser ──────────────────────────────────────────────────────────────

def main():
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    parser = argparse.ArgumentParser(description="Gotify CLI Client")
    sub = parser.add_subparsers(dest="command", required=True)

    # send
    p = sub.add_parser("send", help="Send notification")
    p.add_argument("--message", "-m", required=True, help="Message (markdown OK)")
    p.add_argument("--title", "-t", default=None, help="Title")
    p.add_argument("--priority", "-p", type=int, default=None, help="Priority 0-10")
    p.add_argument("--extras", default=None, help="Extra JSON data")
    p.add_argument("--token", default=None, help="Override app token")
    p.set_defaults(func=cmd_send)

    # list-apps
    sub.add_parser("list-apps", help="List applications").set_defaults(func=cmd_list_apps)

    # create-app
    p = sub.add_parser("create-app", help="Create application")
    p.add_argument("--name", required=True)
    p.add_argument("--description", "-d", default=None)
    p.add_argument("--default-priority", type=int, default=None)
    p.add_argument("--image", default=None)
    p.add_argument("--internal", action="store_true")
    p.set_defaults(func=cmd_create_app)

    # delete-app
    p = sub.add_parser("delete-app", help="Delete application")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=cmd_delete_app)

    # list-clients
    sub.add_parser("list-clients", help="List clients").set_defaults(func=cmd_list_clients)

    # create-client
    p = sub.add_parser("create-client", help="Create client")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_create_client)

    # delete-client
    p = sub.add_parser("delete-client", help="Delete client")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=cmd_delete_client)

    # list-messages
    p = sub.add_parser("list-messages", help="List messages")
    p.add_argument("--limit", type=int, default=30, help="1-200")
    p.add_argument("--since", type=int, default=0, help="Message ID offset")
    p.add_argument("--token", default=None, help="Override token")
    p.set_defaults(func=cmd_list_messages)

    # delete-message
    p = sub.add_parser("delete-message", help="Delete one message")
    p.add_argument("--id", type=int, required=True)
    p.set_defaults(func=cmd_delete_message)

    # delete-messages
    p = sub.add_parser("delete-messages", help="Bulk delete messages")
    p.add_argument("--app-id", type=int, default=None)
    p.add_argument("--before", type=int, required=True, help="Delete all with ID < before")
    p.set_defaults(func=cmd_delete_messages)

    # list-plugins
    sub.add_parser("list-plugins", help="List plugins").set_defaults(func=cmd_list_plugins)

    # toggle-plugin
    p = sub.add_parser("toggle-plugin", help="Enable/disable plugin")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--disable", action="store_true")
    p.set_defaults(func=cmd_toggle_plugin)

    # health / version
    sub.add_parser("health", help="Server health check").set_defaults(func=cmd_health)
    sub.add_parser("version", help="Server version").set_defaults(func=cmd_version)

    # ws-subscribe
    p = sub.add_parser("ws-subscribe", help="Real-time WebSocket stream")
    p.add_argument("--token", default=None)
    p.set_defaults(func=cmd_ws_subscribe)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
