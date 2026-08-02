---
name: zurl
description: >-
  Manage a Zurl short link service — create, update, delete, search, and list
  short URLs, and fetch URL metadata. Trigger whenever the user asks to
  "shorten this link", "generate a short URL", "create a short link",
  "短链接", "缩短", "短链", manage short links, or pastes a long URL and
  asks to make it shorter. Do NOT skip this skill just because the user didn't
  explicitly say "短链接" or "short URL" — even "帮我缩短这个链接" or "把这个
  网址变短" should trigger it. Any request involving URL shortening, short
  link management, or batch URL operations should use this skill.
metadata:
  skill_version: "1.0.0"
---

# Zurl Short Link Management

Manage short URLs via the [Zurl](https://github.com/zurl) service API.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Important Rules

1. **API URL from env var only** — `ZURL_APIURL` must be set; never hardcode the API address.
2. **Auto-generate short code** — When the user asks to shorten a URL without specifying a code, the script auto-generates a 4-character random code (letters + digits).
3. **No title on creation** — Pass empty string `""` for title on new short links so Zurl auto-fetches the page title. Do NOT fill in a title yourself.
4. **Display all domains** — After creating/updating a short link, always show all configured display domains (from `ZURL_DISPLAY_URLS`; the script's `short_links` field contains the full URLs).
5. **QR code domain** — If generating a QR code, use the first domain from `ZURL_DISPLAY_URLS` as the QR content (unless the user specifies one).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ZURL_APIURL` | ✅ | API base URL, e.g. `http://192.168.1.100:3088` |
| `ZURL_TOKEN` | ❌ | API auth token (required if server has auth enabled) |
| `ZURL_DISPLAY_URLS` | ❌ | Comma-separated display domain list; defaults to `ZURL_APIURL` |

The script loads these from `~/.wmyskills/.env` (shared across skills) automatically; a `scripts/.env` in the script directory takes priority if present. Use `scripts/.env.example` as the template — add the variables to `~/.wmyskills/.env`, never overwriting an existing file.

## Requirements

```bash
pip install python-dotenv
```

## Usage

Script: `scripts/zurl_api.py`

### Create a Short URL

```bash
python scripts/zurl_api.py shorten <long_url> [short_code] [title] [description] [ttl_days]
```

| Arg | Required | Description |
|-----|----------|-------------|
| `long_url` | ✅ | Original long URL |
| `short_code` | ❌ | Custom short code; auto-generated (4 chars) if omitted |
| `title` | ❌ | Title (leave empty to auto-fetch) |
| `description` | ❌ | Description |
| `ttl_days` | ❌ | Time-to-live in days |

### Update a Short URL

```bash
python scripts/zurl_api.py update <id> [long_url] [short_code] [title] [description] [ttl_days]
```

| Arg | Required | Description |
|-----|----------|-------------|
| `id` | ✅ | URL database ID (from list/search results) |
| `long_url` | ❌ | New long URL |
| `short_code` | ❌ | New short code |
| `title` | ❌ | New title |
| `description` | ❌ | New description |
| `ttl_days` | ❌ | New TTL in days |

> The script skips `None` (unset) arguments — they are not sent to the API. If the API requires `long_url` or `short_code`, omitting them causes a 422 error. Pass `""` (empty string) to clear a field. `short_code` must be non-empty; an empty value is skipped to avoid a 500 error from the API.

### Edit a Short URL (key=value style)

```bash
# Update specific fields using -o key=value (repeatable)
python scripts/zurl_api.py edit <id> -o long_url=https://new.url -o title="New Title"
```

| Arg | Required | Description |
|-----|----------|-------------|
| `id` | ✅ | URL database ID (from list/search results) |
| `-o` / `--option` | ✅ | `key=value` pair (repeatable). Keys: `long_url`, `short_code`, `title`, `description`, `ttl_days` |

This is an alternative to `update` that uses `-o key=value` pairs instead of positional arguments. Only the fields you specify with `-o` will be changed — unspecified fields are left untouched (unlike `update` where omitted positional args skip sending, but empty `""` clears the field).

### Delete Short URLs

```bash
# Delete by short code
python scripts/zurl_api.py delete <short_code>

# Batch delete by short codes (comma-separated)
python scripts/zurl_api.py delete-batch code1,code2,code3
```

> `delete-batch` accepts short codes (slugs) — the script looks up the corresponding database IDs across all pages, then deletes them. Codes that don't match any URL are silently skipped.

### List & Search

```bash
# List short URLs (paginated)
python scripts/zurl_api.py list [page] [limit]

# Search
python scripts/zurl_api.py search <keyword> [filter_type]
```

`filter_type`: `all` (default) / `long_url` / `short_url` / `title`

### Get URL Metadata

```bash
python scripts/zurl_api.py metadata <url>
```

Returns the target page's title and description.

## Display to User

After creating or updating a short link, parse the JSON response and present the result to the user using the `short_links` field (configured via `ZURL_DISPLAY_URLS`). Example:

```
✅ Short URL created

Short Links:
  https://short.example.com/abc123
  https://s.example.com/abc123

Original URL: https://very-long-url.com/page
Title: Page Title
```

> The actual domains come from `ZURL_DISPLAY_URLS` — the example above is illustrative.

## API Endpoints Verified

| Endpoint | Method | Status |
|----------|--------|--------|
| `/api/shorten_url` | POST JSON | ✅ |
| `/api/update_url/{id}` | POST JSON | ✅ |
| `/api/delete/url` | POST form | ✅ |
| `/api/delete/urls` | POST JSON | ✅ |
| `/api/urls` | GET | ✅ |
| `/api/search` | POST JSON | ✅ |
| `/api/get_url_metadata` | POST form | ✅ |

## Response Format

The script outputs JSON to stdout.

**Success** (commands that include `short_links`):
```json
{"code": 200, "msg": "...", "data": {"short_url": "abc123", "long_url": "...", ...}, "short_links": ["https://s.example/abc123", ...]}
```
The `short_links` field is added by `shorten`, `update`, `list`, and `search`. Other commands (`delete`, `delete-batch`, `metadata`) return the raw API response without it.

**Success** (commands without `short_links`):
```json
{"code": 200, "msg": "...", "data": {...}}
```

**Failure**:
```json
{"error": true, "status": 4XX, "detail": {...}}
```
