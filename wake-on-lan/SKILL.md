---
name: wake-on-lan
description: >
  远程唤醒局域网内的计算机（Wake on LAN），发送 Magic Packet 启动远程主机。
  触发场景：用户提到"开机""远程开机""唤醒主机""wake on lan""WOL""远程唤醒"或需要启动局域网内的设备。
  也适用于"帮我把XX电脑打开""服务器关了帮我开一下""把电脑开着"等日常表述。
  支持按主机名或 MAC 地址唤醒，支持唤醒后在线验证。
metadata:
  skill_version: "0.1.0"
---

# Wake on LAN

通过 UDP 广播发送 Magic Packet，远程唤醒局域网内支持 WoL 的计算机。

## Files

| File | Path | Description |
|------|------|-------------|
| wol.py | `scripts/wol.py` | Core script — builds & sends Magic Packet |
| hosts.yaml | `skills/wake-on-lan/references/hosts.yaml` | Host configuration (name, MAC, IP, etc.) |

## Quick Start

### Wake by host name (from config)

```bash
python3 scripts/wol.py --host <name>
```

### Wake by raw MAC address

```bash
python3 scripts/wol.py --mac AA:BB:CC:DD:EE:FF
```

### Wake + verify online

```bash
python3 scripts/wol.py --host <name> --verify
```

### List configured hosts

```bash
python3 scripts/wol.py --list
```

## Command Reference

| Flag | Description |
|------|-------------|
| `--host NAME` | Host name (case-insensitive lookup in hosts.yaml) |
| `--mac MAC` | Raw MAC address, supports `XX:XX:XX:XX:XX:XX` or `XX-XX-XX-XX-XX-XX` |
| `--broadcast IP` | Override broadcast address (with `--mac`, default `255.255.255.255`) |
| `--port PORT` | Override UDP port (with `--mac`, default `9`) |
| `-n / --count N` | Number of magic packets to send (with `--mac`, default `3`) |
| `--verify` | After sending, ping the host's IP to check if it comes online |
| `--list` | Print all configured hosts as JSON and exit |
| `--config PATH` | Custom path to hosts.yaml |

## hosts.yaml Format

```yaml
hosts:
  - name: "my-pc"
    mac: "00:11:22:33:44:55"
    ip: "192.168.1.100"             # optional — used by --verify to ping
    broadcast: "192.168.1.255"      # optional — default 255.255.255.255
    port: 9                         # optional — default 9
    packet_count: 3                 # optional — default 3
```

**Fields:**

- **name** (required) — Human-friendly identifier. Case-insensitive matching.
- **mac** (required) — Network adapter MAC address.
- **ip** (optional) — Host IP for `--verify` ping check. If omitted, verification is skipped.
- **broadcast** (optional) — Subnet broadcast address. Default `255.255.255.255`.
- **port** (optional) — UDP port. Default `9`.
- **packet_count** (optional) — How many Magic Packets to send. Default `3`. Sending multiple packets improves reliability on lossy networks.

## Output Format

All output is JSON to stdout:

```json
{
  "success": true,
  "host": "my-pc",
  "mac": "00:11:22:33:44:55",
  "broadcast": "192.168.1.255",
  "port": 9,
  "packets_sent": 3,
  "online": true,
  "message": "Host 'my-pc' is online"
}
```

On failure:

```json
{
  "success": false,
  "error": "Host 'xyz' not found in config",
  "available_hosts": ["my-pc", "my-server"]
}
```

## Agent Workflow

1. Receive user request (e.g. "wake up my PC").
2. Determine whether to use `--host` (by name from config) or `--mac` (direct MAC).
3. Run `python3 scripts/wol.py ...`.
4. Parse the JSON output.
5. Report the result to the user in natural language.

## Notes

- The host's network adapter and motherboard must support WoL and have it enabled in BIOS/UEFI.
- Magic Packet is a UDP broadcast — it stays within the local subnet. Cross-subnet WoL requires directed broadcast or relay configuration.
- `--verify` sends up to 3 pings (5 s apart). A negative result does not mean failure — the host may simply be slow to boot.
- Dependencies: Python 3.8+, `pyyaml`. Standard library sockets are used for packet construction.
