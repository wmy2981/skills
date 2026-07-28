#!/usr/bin/env python3
"""
Wake on LAN — manage and wake remote hosts via Magic Packet.

Subcommands:
  list                        List configured hosts
  add <name> <mac> [options]  Add a host
  remove <name>               Remove a host
  edit <name> [options]       Edit a host's fields
  wake <name> [options]       Wake a host by name
  wake-mac <mac> [options]    Wake by raw MAC address

Environment variables:
  WOL_CONFIG_PATH  - Custom path to hosts.yaml (default: ~/.wmyskills/wake-on-lan/hosts.yaml)
"""

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")
if sys.platform == "win32":
    os.system("chcp 65001 > nul")

# ─── Defaults ─────────────────────────────────────────────────

DEFAULT_CONFIG = Path.home() / ".wmyskills" / "wake-on-lan" / "hosts.yaml"
DEFAULT_PORT = 9
DEFAULT_BROADCAST = "255.255.255.255"
DEFAULT_PACKET_COUNT = 3


# ─── Config helpers ───────────────────────────────────────────

def _resolve_config() -> Path:
    """Return config path from env var or default."""
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
    env_path = os.environ.get("WOL_CONFIG_PATH", "").strip()
    return Path(env_path) if env_path else DEFAULT_CONFIG


def _ensure_config(config_path: Path) -> Path:
    """Create an empty hosts.yaml if one doesn't exist."""
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("hosts: []\n")
    return config_path


def load_config(config_path: Path) -> dict:
    """Load hosts.yaml. Exits on error."""
    try:
        import yaml
    except ImportError:
        print(json.dumps({"success": False, "error": "pyyaml is not installed. Run: pip install pyyaml"}))
        sys.exit(1)
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"hosts": []}
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Failed to load config: {e}"}))
        sys.exit(1)


def save_config(config_path: Path, config: dict):
    """Save hosts.yaml."""
    import yaml
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _find_host(config: dict, name: str):
    """Find host entry by name (case-insensitive). Returns dict or None."""
    target = name.lower()
    for host in config.get("hosts", []):
        if host.get("name", "").lower() == target:
            return host
    return None


# ─── Magic Packet helpers ─────────────────────────────────────

def normalize_mac(mac: str) -> str:
    """Normalize MAC to colon-separated uppercase."""
    mac = mac.strip().upper().replace("-", ":")
    parts = mac.split(":")
    if len(parts) != 6 or not all(len(p) == 2 and int(p, 16) <= 255 for p in parts):
        raise ValueError(f"Invalid MAC address: {mac}")
    return ":".join(parts)


def mac_to_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(":", ""))


def build_magic_packet(mac: str) -> bytes:
    """Construct WoL Magic Packet: 6x 0xFF + 16x MAC."""
    mac_bytes = mac_to_bytes(mac)
    return b"\xff" * 6 + mac_bytes * 16


def send_magic_packet(mac: str, broadcast: str, port: int, count: int) -> int:
    """Send `count` magic packets via UDP broadcast. Raises OSError on failure."""
    packet = build_magic_packet(mac)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        for _ in range(count):
            sock.sendto(packet, (broadcast, port))
    finally:
        sock.close()
    return count


# ─── Output helper ────────────────────────────────────────────

def _out(**kwargs):
    print(json.dumps(kwargs, ensure_ascii=False))


# ─── Subcommands ──────────────────────────────────────────────

def cmd_list(config):
    """List all configured hosts."""
    hosts = config.get("hosts", [])
    if not hosts:
        _out(success=False, error="No hosts configured")
        return
    entries = []
    for h in hosts:
        entries.append({
            "name": h.get("name", ""),
            "mac": h.get("mac", ""),
            "ip": h.get("ip", ""),
            "broadcast": h.get("broadcast", DEFAULT_BROADCAST),
            "port": h.get("port", DEFAULT_PORT),
            "packet_count": h.get("packet_count", DEFAULT_PACKET_COUNT),
        })
    _out(success=True, hosts=entries)


def cmd_add(config_path, config, args):
    """Add a new host."""
    hosts = config.setdefault("hosts", [])
    if _find_host(config, args.name):
        _out(success=False, error=f"Host '{args.name}' already exists")
        return
    try:
        mac = normalize_mac(args.mac)
    except ValueError as e:
        _out(success=False, error=str(e))
        return
    entry = {"name": args.name, "mac": mac}
    if args.ip:
        entry["ip"] = args.ip
    if args.broadcast:
        entry["broadcast"] = args.broadcast
    if args.port is not None:
        if args.port < 1 or args.port > 65535:
            _out(success=False, error=f"Invalid port: {args.port} (must be 1-65535)")
            return
        entry["port"] = args.port
    if args.count is not None:
        if args.count < 1 or args.count > 100:
            _out(success=False, error=f"Invalid packet count: {args.count} (must be 1-100)")
            return
        entry["packet_count"] = args.count
    hosts.append(entry)
    save_config(config_path, config)
    _out(success=True, message=f"Host '{args.name}' added", host=entry)


def cmd_remove(config_path, config, args):
    """Remove a host by name."""
    hosts = config.get("hosts", [])
    before = len(hosts)
    config["hosts"] = [h for h in hosts if h.get("name", "").lower() != args.name.lower()]
    if len(config["hosts"]) == before:
        _out(success=False, error=f"Host '{args.name}' not found")
        return
    save_config(config_path, config)
    _out(success=True, message=f"Host '{args.name}' removed")


def cmd_edit(config_path, config, args):
    """Edit a host's fields."""
    host = _find_host(config, args.name)
    if not host:
        _out(success=False, error=f"Host '{args.name}' not found")
        return
    changed = []
    if args.mac is not None:
        try:
            host["mac"] = normalize_mac(args.mac)
        except ValueError as e:
            _out(success=False, error=str(e))
            return
        changed.append("mac")
    if args.ip is not None:
        host["ip"] = args.ip
        changed.append("ip")
    if args.broadcast is not None:
        host["broadcast"] = args.broadcast
        changed.append("broadcast")
    if args.port is not None:
        if args.port < 1 or args.port > 65535:
            _out(success=False, error=f"Invalid port: {args.port} (must be 1-65535)")
            return
        host["port"] = args.port
        changed.append("port")
    if args.count is not None:
        if args.count < 1 or args.count > 100:
            _out(success=False, error=f"Invalid packet count: {args.count} (must be 1-100)")
            return
        host["packet_count"] = args.count
        changed.append("packet_count")
    if args.new_name is not None:
        host["name"] = args.new_name
        changed.append("name")
    if not changed:
        _out(success=False, error="No fields to update")
        return
    save_config(config_path, config)
    _out(success=True, message=f"Host '{args.name}' updated", fields_updated=changed, host=host)


def cmd_wake(config, args):
    """Wake a host by name."""
    host = _find_host(config, args.name)
    if not host:
        available = [h.get("name") for h in config.get("hosts", [])]
        _out(success=False, error=f"Host '{args.name}' not found", available_hosts=available)
        return
    mac = host.get("mac", "")
    broadcast = args.broadcast or host.get("broadcast", DEFAULT_BROADCAST)
    port = args.port or host.get("port", DEFAULT_PORT)
    count = args.count or host.get("packet_count", DEFAULT_PACKET_COUNT)

    try:
        mac = normalize_mac(mac)
    except ValueError as e:
        _out(success=False, error=str(e))
        return

    try:
        sent = send_magic_packet(mac, broadcast, port, count)
    except OSError as e:
        _out(success=False, error=f"Failed to send magic packet: {e}")
        return
    _out(
        success=True,
        host=host.get("name", args.name),
        mac=mac,
        broadcast=broadcast,
        port=port,
        packets_sent=sent,
        message=f"Magic packet sent to {mac} ({sent}x via {broadcast}:{port})",
    )


def cmd_wake_mac(args):
    """Wake by raw MAC address."""
    mac = args.mac
    broadcast = args.broadcast or DEFAULT_BROADCAST
    port = args.port or DEFAULT_PORT
    count = args.count or DEFAULT_PACKET_COUNT

    try:
        mac = normalize_mac(mac)
    except ValueError as e:
        _out(success=False, error=str(e))
        return

    try:
        sent = send_magic_packet(mac, broadcast, port, count)
    except OSError as e:
        _out(success=False, error=f"Failed to send magic packet: {e}")
        return
    _out(
        success=True,
        host="raw-mac",
        mac=mac,
        broadcast=broadcast,
        port=port,
        packets_sent=sent,
        message=f"Magic packet sent to {mac} ({sent}x via {broadcast}:{port})",
    )


# ─── CLI ──────────────────────────────────────────────────────

def main():
    config_path = _ensure_config(_resolve_config())
    config = load_config(config_path)

    parser = argparse.ArgumentParser(
        description="Wake on LAN — manage and wake remote hosts via Magic Packet",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # list
    sub.add_parser("list", help="List configured hosts").set_defaults(func=lambda a: cmd_list(config))

    # add
    p = sub.add_parser("add", help="Add a host")
    p.add_argument("name", help="Host name")
    p.add_argument("mac", help="MAC address (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)")
    p.add_argument("--ip", help="IP address (for display)")
    p.add_argument("--broadcast", help="Broadcast address (default: 255.255.255.255)")
    p.add_argument("--port", type=int, help=f"UDP port (default: {DEFAULT_PORT})")
    p.add_argument("--count", type=int, help=f"Packet count (default: {DEFAULT_PACKET_COUNT})")
    p.set_defaults(func=lambda a: cmd_add(config_path, config, a))

    # remove
    p = sub.add_parser("remove", help="Remove a host")
    p.add_argument("name", help="Host name to remove")
    p.set_defaults(func=lambda a: cmd_remove(config_path, config, a))

    # edit
    p = sub.add_parser("edit", help="Edit a host's fields")
    p.add_argument("name", help="Host name to edit")
    p.add_argument("--new-name", help="Rename the host")
    p.add_argument("--mac", help="New MAC address")
    p.add_argument("--ip", help="New IP address")
    p.add_argument("--broadcast", help="New broadcast address")
    p.add_argument("--port", type=int, help="New UDP port")
    p.add_argument("--count", type=int, help="New packet count")
    p.set_defaults(func=lambda a: cmd_edit(config_path, config, a))

    # wake
    p = sub.add_parser("wake", help="Wake a host by name")
    p.add_argument("name", help="Host name to wake")
    p.add_argument("--broadcast", help="Override broadcast address")
    p.add_argument("--port", type=int, help="Override UDP port")
    p.add_argument("--count", type=int, help=f"Number of packets to send (default: {DEFAULT_PACKET_COUNT})")
    p.set_defaults(func=lambda a: cmd_wake(config, a))

    # wake-mac
    p = sub.add_parser("wake-mac", help="Wake by raw MAC address")
    p.add_argument("mac", help="MAC address (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)")
    p.add_argument("--broadcast", help=f"Broadcast address (default: {DEFAULT_BROADCAST})")
    p.add_argument("--port", type=int, help=f"UDP port (default: {DEFAULT_PORT})")
    p.add_argument("--count", type=int, help=f"Number of packets to send (default: {DEFAULT_PACKET_COUNT})")
    p.set_defaults(func=lambda a: cmd_wake_mac(a))

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
