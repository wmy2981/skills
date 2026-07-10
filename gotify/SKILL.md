---
name: gotify
description: >
  Send and manage Gotify push notifications, applications, clients, and messages via the Gotify REST API.
  Use this skill whenever the user mentions "gotify", "push notification", "自托管通知", "消息推送",
  sending alerts, managing Gotify apps/clients, checking message history, toggling Gotify plugins,
  or verifying Gotify server health. Also trigger for "发通知到gotify", "gotify推送", "gotify消息",
  "通知服务", or any command that mentions a Gotify server instance.
metadata:
  skill_version: "1.0.0"
---

# Gotify Skill

Send and manage push notifications on a self-hosted Gotify server using its REST API v2.0.2.

## Environment Variables

> 💡 Environment variables can be configured via `scripts/.env` template. The script loads it automatically.

| Variable | Required | Purpose |
|---|---|---|
| `GOTIFY_URL` | ✅ | Server base URL, e.g. `https://gotify.example.com` |
| `GOTIFY_CLIENT_TOKEN` | ✅ | Client token — used to manage apps, clients, read messages |
| `GOTIFY_APP_TOKEN` | ✅ | Application token — used to send messages |

If a token is missing, the script will fail with a clear error. Tokens can also be passed per-call via `--token`.

## Script Location

```
scripts/gotify_client.py
```

All commands are run via this single CLI script. No Python dependencies beyond stdlib (`websocket-client` only for `ws-subscribe`).

## Commands

### 🔔 Send a Notification

The most common operation — use `send` to push a message to all subscribers.

```bash
python3 scripts/gotify_client.py send \
  --message "Deployment succeeded" \
  --title "CI/CD Alert" \
  --priority 5
```

| Flag | Required | Description |
|---|---|---|
| `--message` / `-m` | ✅ | Message body (markdown supported) |
| `--title` / `-t` | | Notification title |
| `--priority` / `-p` | | 0–10 (0=lowest, 10=urgent; default 0) |
| `--extras` | | JSON string for plugin-specific data |
| `--token` | | Override app token |

**Priority levels:**
- 0: silent (no notification sound)
- 1–3: normal
- 4–7: high
- 8–10: urgent / alarm-like

**Extras example** (for Firebase push):
```bash
python3 scripts/gotify_client.py send -m "Hello" --extras '{"firebase":{"priority":"high"}}'
```

### 📱 Applications (Message Sources)

Applications represent bots/scripts that send messages.

```bash
# List all applications
python3 scripts/gotify_client.py list-apps

# Create a new application
python3 scripts/gotify_client.py create-app \
  --name "Backup Bot" \
  --description "Backup notifications" \
  --default-priority 3

# Delete an application
python3 scripts/gotify_client.py delete-app --id 5
```

> **Note:** The returned `token` field from `create-app` is the app token for sending messages. Store it securely.

### 📲 Clients (Receiving Devices)

Clients represent devices/subscribers that receive notifications.

```bash
# List all clients
python3 scripts/gotify_client.py list-clients

# Create a new client
python3 scripts/gotify_client.py create-client --name "iPhone"

# Delete a client
python3 scripts/gotify_client.py delete-client --id 3
```

### 📬 Messages

```bash
# List recent messages (default: 30)
python3 scripts/gotify_client.py list-messages --limit 50

# Pagination — get messages after ID 100
python3 scripts/gotify_client.py list-messages --since 100

# Delete a single message
python3 scripts/gotify_client.py delete-message --id 42

# Bulk delete: all messages with ID < 500
python3 scripts/gotify_client.py delete-messages --before 500

# Bulk delete from a specific app
python3 scripts/gotify_client.py delete-messages --app-id 3 --before 500
```

### 🔌 Plugins

```bash
# List installed plugins
python3 scripts/gotify_client.py list-plugins

# Enable a plugin
python3 scripts/gotify_client.py toggle-plugin --id 1

# Disable a plugin
python3 scripts/gotify_client.py toggle-plugin --id 1 --disable
```

### ❤️ Server Health & Version

```bash
# Health check
python3 scripts/gotify_client.py health

# Version info
python3 scripts/gotify_client.py version
```

### 📡 Real-Time WebSocket Stream

Subscribe to live messages (requires `pip install websocket-client`):

```bash
python3 scripts/gotify_client.py ws-subscribe
```

Output is one JSON object per received message. Useful for monitoring but rarely needed in automated agent tasks.

## Typical Agent Workflows

### 1. One-off alert notification
```
用户: "服务器 CPU 超过 90%，发个通知到 Gotify"
→ python3 scripts/gotify_client.py send -m "⚠️ CPU > 90%" --title "Server Alert" --priority 7
```

### 2. List apps and check what's sending
```
用户: "Gotify 上有哪些应用在发消息？"
→ python3 scripts/gotify_client.py list-apps
```

### 3. Read recent notifications
```
用户: "最近 Gotify 上推了什么通知？"
→ python3 scripts/gotify_client.py list-messages --limit 10
```

### 4. Create app + retrieve token
```
用户: "帮我创建一个 Gotify 应用叫 deploy-bot"
→ python3 scripts/gotify_client.py create-app --name "deploy-bot" --description "Deploy notifications"
→ 返回结果包含 token，告知用户保存
```

## Gotify REST API Key Concepts

- **App token** (`GOTIFY_APP_TOKEN`): for **sending** messages — used in `/message`
- **Client token** (`GOTIFY_CLIENT_TOKEN`): for **managing** apps/clients/messages — used everywhere else
- Token is passed via `X-Gotify-Key` header (script handles this automatically)
- Gotify server can be deployed via Docker, binary, or Helm

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `GOTIFY_URL not set` | Missing env var | Set `GOTIFY_URL=https://your-server` |
| `401 Unauthorized` | Wrong/missing token | Check which token type is needed; verify env var |
| `403 Forbidden` | Client token used on send | Use app token (`GOTIFY_APP_TOKEN`) for `/message` |
| `Connection refused` | Server down | `python3 scripts/gotify_client.py health` |
| `No app token` | `GOTIFY_APP_TOKEN` not set | Set the env var or pass `--token` |
