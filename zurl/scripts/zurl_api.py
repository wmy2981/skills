#!/usr/bin/env python3
"""
Zurl short link management API client.

Manages short URLs via the Zurl REST API.
Environment variables:
  ZURL_APIURL       - API base URL (required)
  ZURL_TOKEN        - API auth token (optional)
  ZURL_DISPLAY_URLS - Comma-separated display domains (optional)
"""

import json
import os
import random
import string
import sys
import subprocess
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    subprocess.run("chcp 65001", shell=True, capture_output=True)
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = ""
DISPLAY_URLS: list[str] = []


def _init_env():
    """Load .env and set globals. Exit on failure."""
    global BASE_URL, DISPLAY_URLS
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    BASE_URL = os.environ.get("ZURL_APIURL", "").rstrip("/")
    if not BASE_URL:
        print("Error: ZURL_APIURL environment variable is not set", file=sys.stderr)
        sys.exit(1)
    raw_display = os.environ.get("ZURL_DISPLAY_URLS", "").strip()
    DISPLAY_URLS = (
        [u.strip() for u in raw_display.split(",") if u.strip()]
        if raw_display
        else [BASE_URL]
    )


class ZurlAPI:
    def __init__(self):
        self.token = os.environ.get("ZURL_TOKEN", "")

    def _request(self, method, path, data=None, content_type="application/json"):
        """Send HTTP request."""
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": content_type}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        if data and content_type == "application/json":
            body = json.dumps(data).encode("utf-8")
        elif data and content_type == "application/x-www-form-urlencoded":
            body = urllib.parse.urlencode(data).encode("utf-8")
        else:
            body = None

        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode("utf-8")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    return {"error": True, "detail": "API returned unexpected format"}
                return result
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                return {"error": True, "status": e.code, "detail": err_json}
            except json.JSONDecodeError:
                return {"error": True, "status": e.code, "detail": err_body}
        except (urllib.error.URLError, json.JSONDecodeError) as e:
            return {"error": True, "detail": str(e)}

    @staticmethod
    def _generate_short_code(length=4):
        """Generate random short code (letters + digits)."""
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    def _expand_urls(self, short_url):
        """Expand short_url to full URLs across all display domains."""
        return [f"{domain}/{short_url}" for domain in DISPLAY_URLS]

    @staticmethod
    def _is_success(result):
        """Check if API response indicates success."""
        if result.get("error"):
            return False
        code = result.get("code", result.get("status", 0))
        return code == 200

    @staticmethod
    def _extract_items(result, field="data"):
        """Extract item list from API response."""
        data = result.get(field, {})
        if isinstance(data, dict):
            return data.get("urls", data.get("items", []))
        return data if isinstance(data, list) else []

    def shorten(self, long_url, short_url=None, title=None, description=None, ttl_days=None):
        """Create a short URL."""
        if not short_url:
            short_url = self._generate_short_code()
        payload = {"long_url": long_url, "short_url": short_url}
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if ttl_days is not None:
            payload["ttl_days"] = ttl_days
        result = self._request("POST", "/api/shorten_url", payload)
        if self._is_success(result):
            actual_short = result.get("data", {}).get("short_url", short_url)
            result["short_links"] = self._expand_urls(actual_short)
        return result

    def update(self, url_id, **kwargs):
        """Update a short URL. Pass None to leave unchanged; pass "" to clear a field."""
        allowed = ("long_url", "short_url", "title", "description", "ttl_days")
        payload = {}
        for k, v in kwargs.items():
            if k not in allowed or v is None:
                continue
            if k == "short_url" and v == "":
                continue  # empty short_url causes 500 from API
            payload[k] = v
        result = self._request("POST", f"/api/update_url/{url_id}", payload)
        if self._is_success(result):
            actual_short = kwargs.get("short_url") or result.get("data", {}).get("short_url", "")
            if actual_short:
                result["short_links"] = self._expand_urls(actual_short)
        return result

    def delete(self, short_url):
        """Delete a single short URL."""
        return self._request("POST", "/api/delete/url",
                             {"short_url": short_url},
                             content_type="application/x-www-form-urlencoded")

    def delete_batch(self, ids):
        """Batch delete short URLs by IDs."""
        return self._request("POST", "/api/delete/urls", {"ids": ids})

    def list_urls(self, page=1, limit=10):
        """List short URLs."""
        result = self._request("GET", f"/api/urls?page={page}&limit={limit}")
        if self._is_success(result):
            for item in self._extract_items(result):
                s = item.get("short_url", "")
                if s:
                    item["short_links"] = self._expand_urls(s)
        return result

    def search(self, keyword, filter_type="all"):
        """Search short URLs."""
        payload = {"keyword": keyword, "filter": filter_type}
        result = self._request("POST", "/api/search", payload)
        if self._is_success(result):
            for item in self._extract_items(result):
                s = item.get("short_url", "")
                if s:
                    item["short_links"] = self._expand_urls(s)
        return result

    def get_metadata(self, url):
        """Get URL metadata (title + description)."""
        return self._request("POST", "/api/get_url_metadata",
                             {"url": url},
                             content_type="application/x-www-form-urlencoded")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zurl short link management")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # shorten
    p = sub.add_parser("shorten", help="Create a short URL")
    p.add_argument("long_url", help="Original long URL")
    p.add_argument("short_code", nargs="?", help="Custom short code (auto-generated if omitted)")
    p.add_argument("title", nargs="?", help="Title (leave empty to auto-fetch)")
    p.add_argument("description", nargs="?", help="Description")
    p.add_argument("ttl_days", nargs="?", type=int, help="Time-to-live in days")

    # update
    p = sub.add_parser("update", help="Update a short URL")
    p.add_argument("id", type=int, help="URL ID from list/search results")
    p.add_argument("long_url", nargs="?", help="New long URL")
    p.add_argument("short_code", nargs="?", help="New short code")
    p.add_argument("title", nargs="?", help="New title")
    p.add_argument("description", nargs="?", help="New description")
    p.add_argument("ttl_days", nargs="?", type=int, help="New TTL in days")

    # delete
    p = sub.add_parser("delete", help="Delete a short URL by code")
    p.add_argument("short_code", help="Short URL code to delete")

    # delete-batch
    p = sub.add_parser("delete-batch", help="Batch delete short URLs by codes (comma-separated)")
    p.add_argument("codes", help="Comma-separated short URL codes")

    # list
    p = sub.add_parser("list", help="List short URLs")
    p.add_argument("page", nargs="?", type=int, default=1, help="Page number (default: 1)")
    p.add_argument("limit", nargs="?", type=int, default=10, help="Results per page (default: 10)")

    # search
    p = sub.add_parser("search", help="Search short URLs")
    p.add_argument("keyword", help="Search keyword")
    p.add_argument("filter_type", nargs="?", default="all",
                   choices=["all", "long_url", "short_url", "title"],
                   help="Filter scope (default: all)")

    # metadata
    p = sub.add_parser("metadata", help="Get URL metadata (title + description)")
    p.add_argument("url", help="Target URL")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    _init_env()
    api = ZurlAPI()

    if args.command == "shorten":
        print(json.dumps(api.shorten(args.long_url, args.short_code, args.title, args.description, args.ttl_days), ensure_ascii=False))
    elif args.command == "update":
        print(json.dumps(api.update(args.id, long_url=args.long_url, short_url=args.short_code,
                                    title=args.title, description=args.description, ttl_days=args.ttl_days), ensure_ascii=False))
    elif args.command == "delete":
        print(json.dumps(api.delete(args.short_code), ensure_ascii=False))
    elif args.command == "delete-batch":
        _delete_batch(api, args.codes)
    elif args.command == "list":
        print(json.dumps(api.list_urls(args.page, args.limit), ensure_ascii=False))
    elif args.command == "search":
        print(json.dumps(api.search(args.keyword, args.filter_type), ensure_ascii=False))
    elif args.command == "metadata":
        print(json.dumps(api.get_metadata(args.url), ensure_ascii=False))


def _delete_batch(api, codes_str):
    """Batch delete: lookup IDs from short codes across all pages, then delete."""
    codes = [x.strip() for x in codes_str.split(",")]
    url_map = {}
    page = 1
    limit = 100
    while True:
        result = api.list_urls(page, limit)
        if not api._is_success(result):
            break
        items = result.get("data", {}).get("urls", [])
        for u in items:
            url_map[u["short_url"]] = u["id"]
        if len(items) < limit:
            break
        page += 1
    ids = [url_map[s] for s in codes if s in url_map]
    if ids:
        print(json.dumps(api.delete_batch(ids), ensure_ascii=False))
    else:
        print(json.dumps({"error": True, "detail": "No matching short URLs found"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
