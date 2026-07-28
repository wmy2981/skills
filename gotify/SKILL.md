---
name: gotify
description: >-
  Send and manage Gotify push notifications, applications, clients, and messages
  via the Gotify REST API. Use this skill whenever the user mentions "gotify",
  "push notification", "自托管通知", "消息推送", sending alerts, managing
  Gotify apps/clients, checking message history, toggling Gotify plugins,
  or verifying Gotify server health. Also trigger for "发通知到gotify",
  "gotify推送", "gotify消息", "通知服务", or any command mentioning a
  Gotify server instance.
metadata:
  skill_version: "1.0.0"
---

# Gotify CLI Client

Send and manage push notifications on a self-hosted [Gotify](https://gotify.net/) server via its REST API v2.0.2.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GOTIFY_URL` | ✅ | Server base URL, e.g. `https://gotify.example.com` |
| `GOTIFY_CLIENT_TOKEN` | ✅ | Client token — manage apps, clients, read messages |
| `GOTIFY_APP_TOKEN` | ✅ | Application token — send messages |

The script loads these from `scripts/.env` automatically. See `scripts/.env.example` for the template. Missing tokens produce a clear error; tokens can also be passed per-call via `--token`.

## Requirements

```bash
# Core — stdlib only (no install needed)
# WebSocket (optional, for ws-subscribe only):
pip install websocket-client
```

## Usage

Script: `scripts/gotify_client.py`

```
python scripts/gotify_client.py <command> [options]
```

### 🔔 Send a Notification

```bash
python scripts/gotify_client.py send \
  --message "Deployment succeeded" \
  --title "CI/CD Alert" \
  --priority 5
```

| Flag | Required | Description |
|------|----------|-------------|
| `--message` / `-m` | ✅ | Message body (markdown supported) |
| `--title` / `-t` | | Notification title |
| `--priority` / `-p` | | 0–10 (0=silent, 10=urgent; default 0) |
| `--extras` | | JSON string for plugin-specific data |
| `--token` | | Override app token |

**Extras example** (Firebase push config):
```bash
python scripts/gotify_client.py send -m "Hello" --extras '{"firebase":{"priority":"high"}}'
```

### 📱 Applications (Message Sources)

```bash
# List all applications
python scripts/gotify_client.py list-apps

# Create a new application
python scripts/gotify_client.py create-app \
  --name "Backup Bot" \
  --description "Backup notifications" \
  --default-priority 3

# Delete an application
python scripts/gotify_client.py delete-app --id 5
```

> The returned `token` from `create-app` is the app token for sending messages. Store it securely.

### 📲 Clients (Receiving Devices)

```bash
# List all clients
python scripts/gotify_client.py list-clients

# Create a new client
python scripts/gotify_client.py create-client --name "iPhone"

# Delete a client
python scripts/gotify_client.py delete-client --id 3
```

### 📬 Messages

```bash
# List recent messages (default: 30)
python scripts/gotify_client.py list-messages --limit 50

# Pagination — get messages after ID 100
python scripts/gotify_client.py list-messages --since 100

# Delete a single message
python scripts/gotify_client.py delete-message --id 42

# Bulk delete: all messages with ID < 500
python scripts/gotify_client.py delete-messages --before 500

# Bulk delete from a specific app
python scripts/gotify_client.py delete-messages --app-id 3 --before 500
```

### 🔌 Plugins

```bash
# List installed plugins
python scripts/gotify_client.py list-plugins

# Enable a plugin
python scripts/gotify_client.py toggle-plugin --id 1

# Disable a plugin
python scripts/gotify_client.py toggle-plugin --id 1 --disable
```

### ❤️ Server Health & Version

```bash
# Health check
python scripts/gotify_client.py health

# Version info
python scripts/gotify_client.py version
```

### 📡 Real-Time WebSocket Stream

Subscribe to live messages (requires `websocket-client`):

```bash
pip install websocket-client
python scripts/gotify_client.py ws-subscribe
```

Output is one JSON object per received message.

## API Key Concepts

- **App token** (`GOTIFY_APP_TOKEN`): for **sending** messages via `/message`
- **Client token** (`GOTIFY_CLIENT_TOKEN`): for **managing** apps/clients/messages everywhere else
- Token is passed via `X-Gotify-Key` header (script handles this automatically)

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `GOTIFY_URL not set` | Missing env var | Set `GOTIFY_URL=https://your-server` |
| `401 Unauthorized` | Wrong/missing token | Check which token type is needed; verify env var |
| `403 Forbidden` | Client token used on send | Use app token for `/message` |
| `Connection refused` | Server down | Run `health` to verify |
| `No app token` | Token not configured | Set `GOTIFY_APP_TOKEN` or use `--token` |
