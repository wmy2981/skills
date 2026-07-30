---
name: wake-on-lan
description: >-
  Remote wake-up computers on a local network via Wake-on-LAN (Magic Packet).
  Manage host configurations (add, edit, remove, list) and send wake-up signals
  by host name or MAC address. Triggered whenever the user mentions "开机",
  "远程开机", "唤醒主机", "wake on lan", "WOL", "远程唤醒", "帮我把XX电脑打开",
  "服务器关了帮我开一下", "把电脑开着", or asks to start a computer on
  the local network. Also use for managing wake-up host lists.
metadata:
  skill_version: "1.0.0"
---

# Wake on LAN

Send Magic Packets via UDP broadcast to wake up WoL-compatible computers on the local network. Manage host configurations through the script — no manual YAML editing needed.

## Execution Rule

Run the user's requested command directly without pre-checking dependencies, environment variables, or configuration. If something is wrong, the script will fail with a clear error — check and fix only then.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `WOL_CONFIG_PATH` | ❌ | Custom path to `hosts.yaml` (default: `~/.wmyskills/wake-on-lan/hosts.yaml`) |

The script loads these from `scripts/.env` automatically. See `scripts/.env.example` for the template.

## Requirements

```bash
pip install pyyaml python-dotenv
```

## Usage

Script: `scripts/wol.py`

### Manage Hosts

```bash
# List all configured hosts
python scripts/wol.py list

# Add a host
python scripts/wol.py add my-pc AA:BB:CC:DD:EE:FF --ip 192.168.1.100

# Edit a host's fields
python scripts/wol.py edit my-pc --mac 00:11:22:33:44:55 --ip 192.168.1.10

# Remove a host
python scripts/wol.py remove my-pc
```

### Wake a Host

```bash
# Wake by name (from host list)
python scripts/wol.py wake my-pc

# Wake with more packets (improves reliability on lossy networks)
python scripts/wol.py wake my-pc --count 5

# Wake by raw MAC address (no config needed)
python scripts/wol.py wake-mac AA:BB:CC:DD:EE:FF

# Wake by MAC with custom broadcast
python scripts/wol.py wake-mac AA:BB:CC:DD:EE:FF --broadcast 192.168.1.255 --port 9
```

### Add Command Options

| Flag | Description |
|------|-------------|
| `--ip IP` | IP address (for display/reference) |
| `--broadcast BC` | Broadcast address (default: `255.255.255.255`) |
| `--port PORT` | UDP port (default: `9`) |
| `--count N` | Number of magic packets to send (default: `3`) |

### Wake / Wake-MAC Options

| Flag | Description |
|------|-------------|
| `--broadcast BC` | Override broadcast address |
| `--port PORT` | Override UDP port (default: `9`) |
| `--count N` | Number of packets to send (default: `3`; higher counts improve reliability) |

### Edit Options

| Flag | Description |
|------|-------------|
| `--new-name NAME` | Rename the host |
| `--mac MAC` | Change MAC address |
| `--ip IP` | Change IP address |
| `--broadcast BC` | Change broadcast address |
| `--port PORT` | Change UDP port |
| `--count N` | Change packet count |

## Output Format

All output is JSON:

```json
{"success": true, "host": "my-pc", "mac": "AA:BB:CC:DD:EE:FF", "broadcast": "255.255.255.255", "port": 9, "packets_sent": 3, "message": "Magic packet sent to AA:BB:CC:DD:EE:FF (3x via 255.255.255.255:9)"}
```

On failure:

```json
{"success": false, "error": "Host 'xyz' not found", "available_hosts": ["my-pc", "my-server"]}
```

## Notes

- The target computer's network adapter and motherboard must support WoL and have it enabled in BIOS/UEFI.
- Magic Packet is a UDP broadcast — it stays within the local subnet. Cross-subnet WoL requires directed broadcast or relay configuration.
- Host configurations are stored in `~/.wmyskills/wake-on-lan/hosts.yaml` by default. The script auto-creates this file on first run.
- Dependencies: Python 3.8+, `pyyaml`. Standard library sockets used for packet construction.
