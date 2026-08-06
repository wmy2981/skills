---
name: linkgo
description: >-
  Manage a remote LinkGo v3 instance via its HTTP API. Use when the user wants
  to list/add/edit/delete service cards, modify page settings, upload icons,
  change or reset passwords, export/import config, or query debug info on the
  LinkGo navigation page. Also triggers for "导航页", "服务卡片", "LinkGo",
  "add card", "edit card", "sublink" and similar card management tasks.
metadata:
  skill_version: "2.0.2"
---

# LinkGo v3 Remote Management

Manage service cards, page configuration, icons, and system settings on a [LinkGo v3](https://github.com/ommi2/LinkGo) navigation page via its HTTP API.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `LINKGO_HOST` | ✅ | Instance address, e.g. `http://192.168.1.100:80` |
| `LINKGO_PASSWORD` | ✅ | Admin password |

The script loads these from `~/.wmyskills/.env` (shared across skills) automatically; a `scripts/.env` in the script directory takes priority if present. Use `scripts/.env.example` as the template — add the variables to `~/.wmyskills/.env`, never overwriting an existing file.

## Requirements

No external dependencies (stdlib only).

## Usage

Script: `scripts/linkgo.py`

### Connectivity

```bash
python scripts/linkgo.py ping
```

### Query Cards

```bash
# List enabled cards (default)
python scripts/linkgo.py list

# List all cards (including disabled)
python scripts/linkgo.py list --all

# Query a specific card by id
python scripts/linkgo.py list --id my-service
```

### Card Management

```bash
# Add a card (JSON string)
python scripts/linkgo.py add '{"id":"my-service","title":"My Service","href":"http://example.com","icon":"static/icon/link.svg","displayAddress":"example.com","description":"Service description","status":1}'

# Edit a card (merge fields by id)
python scripts/linkgo.py edit my-service '{"title":"New Title","href":"http://new.example.com"}'

# Delete a card
python scripts/linkgo.py delete my-service

# Enable / disable
python scripts/linkgo.py enable my-service
python scripts/linkgo.py disable my-service
```

### Page Settings

```bash
python scripts/linkgo.py page '{"title":"New Title","searchEnabled":0}'
```

### Icons

```bash
# Upload one or more icons (multi-file supported)
python scripts/linkgo.py upload-icon /path/to/icon.svg /path/to/another.png

# List available icons
python scripts/linkgo.py icons
```

### Config Export / Import

```bash
# Export config to file
python scripts/linkgo.py export -o backup.json

# Export to stdout
python scripts/linkgo.py export

# Import config (overwrites all data)
python scripts/linkgo.py import backup.json

# Reset to default config
python scripts/linkgo.py reset
```

### Password & Debug

```bash
# Change admin password
python scripts/linkgo.py change-password <old_password> <new_password>

# Reset password to a random 8-char one (server-local only, 127.0.0.1)
python scripts/linkgo.py reset-password

# Debug info
python scripts/linkgo.py debug
```

## Service Card Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | ✅ | string | Unique identifier, **alphanumeric only**, immutable after creation |
| `title` | ✅ | string | Display title, supports variable substitution |
| `href` | ✅ | string | Click target URL, supports `javascript:` protocol |
| `icon` | ❌ | string | Icon path (e.g. `static/icon/home.svg`), available after upload |
| `displayAddress` | ❌ | string | Address text shown on the card |
| `description` | ❌ | string | Description text, supports variable substitution and HTML |
| `status` | ❌ | int | `1`=enabled (default), `0`=disabled |

### Parameterized Syntax (description only)

| Syntax | Description | Example |
|--------|-------------|---------|
| `{link:URL,text}` | Plain link | `{link:https://example.com,Example}` |
| `{sublink:URL,text}` | Blue bold link | `{sublink:https://example.com,Details}` |
| `{modallink:URL,title,text}` | Iframe modal link | `{modallink:http://x:8080,Service,View}` |
| `{tip:content}` | Search keyword hint (invisible) | `{tip:keyword1 keyword2}` |
| `{page_info}` | Page info placeholder (selectable text) | `{page_info}` |

### Static Variables

| Variable | Replaced with | Example |
|----------|---------------|---------|
| `{project_name}` | Project name | `LinkGo` |
| `{project_version}` | Project version | `v3_20250823` |
| `{addr_prefit}` | `地址：` label | `{addr_prefit}` → `地址：` |
| `{space}` | Three spaces | `Line 1{space}Line 2` |
| `{icon_path}` | Icon directory | `{icon_path}myicon.svg` → `/static/icon/myicon.svg` |
| `{api_path}` | API directory | `{api_path}` → `/api/` |
| `{static_path}` | Static directory | `{static_path}` → `/static/` |
| `{pages_path}` | Pages directory | `{pages_path}` → `/pages/` |

### Dynamic Variables (auto-replaced by frontend per page)

| Variable | Description | Example |
|----------|-------------|---------|
| `{host}` | Hostname + port | `localhost:8080` |
| `{hostname}` | Hostname only | `localhost` |
| `{port}` | Port | `8080` |
| `{protocol}` | Protocol (`http`/`https`) | `http` |
| `{pathname}` | Current URL path | `/index.html` |
| `{href}` | Full URL | `http://localhost:8080/index.html` |
| `%s` | Alias of `{host}` | `localhost:8080` |

## Important Notes

- **Edit is incremental** — only pass the fields you want to change; others stay as-is
- **Backup before import/reset** — both operations **overwrite all data** and are irreversible
- Icon upload limit: 1MB per file; supported formats: SVG/PNG/JPG/JPEG/GIF/WEBP/ICO
- `reset` clears all custom cards
- `reset-password` only works on the server host itself (the API accepts `127.0.0.1` only); `LINKGO_HOST` must point at `http://127.0.0.1` for it
- Password change auto-updates the server's `config.php`
- After `change-password` / `reset-password`, guide the user to update `LINKGO_PASSWORD` in `~/.wmyskills/.env` (and `scripts/.env` if present — it takes priority); the stored password becomes invalid and further commands will fail with 401

## Reference

For the full LinkGo v3 API reference, variable substitution system, frontend modules, and deployment config, read `references/api_doc.md`.
