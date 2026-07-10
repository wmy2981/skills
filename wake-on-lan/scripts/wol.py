#!/usr/bin/env python3
"""
Wake on LAN - Send Magic Packet to wake up remote hosts.

Usage:
    python3 wol.py --host <name>          # wake by host name (from hosts.yaml)
    python3 wol.py --mac <MAC>            # wake by raw MAC address
    python3 wol.py --list                 # list all configured hosts
    python3 wol.py --host <name> --verify # wake + ping check
    python3 wol.py --host <name> -n 5     # override packet count

Options:
    --config PATH   Path to hosts.yaml (default: references/hosts.yaml next to this script)
    --host NAME     Host name to look up in config
    --mac  MAC      Raw MAC address (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)
    --broadcast IP  Override broadcast address (with --mac only)
    --port  PORT    Override UDP port (with --mac only, default 9)
    -n, --count N   Number of magic packets to send (with --mac only, default 3)
    --verify        After sending, ping the host's IP to check if it comes online
    --list          List all configured hosts and exit
"""

import argparse
import json
import socket
import struct
import subprocess
import sys
import time
import ipaddress
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent / "references"
DEFAULT_CONFIG = DEFAULT_CONFIG_DIR / "hosts.yaml"
DEFAULT_PORT = 9
DEFAULT_BROADCAST = "255.255.255.255"
DEFAULT_PACKET_COUNT = 3
VERIFY_RETRIES = 3
VERIFY_INTERVAL = 5  # seconds between pings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_mac(mac: str) -> str:
    """Normalize MAC to colon-separated uppercase hex."""
    mac = mac.strip().upper().replace("-", ":")
    parts = mac.split(":")
    if len(parts) != 6 or not all(len(p) == 2 and int(p, 16) <= 255 for p in parts):
        raise ValueError(f"Invalid MAC address: {mac}")
    return ":".join(parts)


def mac_to_bytes(mac: str) -> bytes:
    return bytes.fromhex(mac.replace(":", ""))


def build_magic_packet(mac: str) -> bytes:
    """Construct a WoL Magic Packet: 6x 0xFF + 16x MAC."""
    mac_bytes = mac_to_bytes(mac)
    return b"\xff" * 6 + mac_bytes * 16


def send_magic_packet(mac: str, broadcast: str, port: int, count: int) -> int:
    """Send `count` magic packets via UDP broadcast. Returns packets sent."""
    packet = build_magic_packet(mac)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        for _ in range(count):
            sock.sendto(packet, (broadcast, port))
    finally:
        sock.close()
    return count


def ping_host(ip: str, retries: int = VERIFY_RETRIES, interval: float = VERIFY_INTERVAL) -> bool:
    """Ping the target IP. Returns True if reachable within retries."""
    for attempt in range(retries):
        try:
            # -c 1: one packet, -W 2: 2s timeout
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", ip],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(interval)
    return False


def load_config(config_path: Path) -> dict:
    """Load hosts.yaml and return the parsed dict."""
    try:
        import yaml
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "pyyaml is not installed. Run: pip install pyyaml",
        }))
        sys.exit(1)

    if not config_path.exists():
        print(json.dumps({
            "success": False,
            "error": f"Config file not found: {config_path}",
        }))
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def find_host(config: dict, name: str):
    """Find a host entry by name (case-insensitive). Returns dict or None."""
    name_lower = name.lower()
    for host in config.get("hosts", []):
        if host.get("name", "").lower() == name_lower:
            return host
    return None


def make_result(**kwargs) -> str:
    """Return a JSON string."""
    return json.dumps(kwargs, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_list(config: dict):
    """List all configured hosts."""
    hosts = config.get("hosts", [])
    if not hosts:
        print(make_result(success=False, error="No hosts configured"))
        return

    entries = []
    for h in hosts:
        entries.append({
            "name": h.get("name", "unknown"),
            "mac": h.get("mac", ""),
            "ip": h.get("ip", ""),
            "broadcast": h.get("broadcast", DEFAULT_BROADCAST),
            "port": h.get("port", DEFAULT_PORT),
            "packet_count": h.get("packet_count", DEFAULT_PACKET_COUNT),
        })
    print(make_result(success=True, hosts=entries))


def action_wake(config: dict, host_name: str = None, mac: str = None,
                broadcast: str = None, port: int = None, count: int = None,
                verify: bool = False):
    """Send magic packet and optionally verify."""
    if host_name:
        host = find_host(config, host_name)
        if not host:
            available = [h.get("name") for h in config.get("hosts", [])]
            print(make_result(
                success=False,
                error=f"Host '{host_name}' not found in config",
                available_hosts=available,
            ))
            return
        mac = host.get("mac", "")
        broadcast = broadcast or host.get("broadcast", DEFAULT_BROADCAST)
        port = port or host.get("port", DEFAULT_PORT)
        count = count or host.get("packet_count", DEFAULT_PACKET_COUNT)
        target_ip = host.get("ip", "")
        resolved_name = host.get("name", host_name)
    else:
        # Raw MAC mode
        if not mac:
            print(make_result(success=False, error="Either --host or --mac is required"))
            return
        broadcast = broadcast or DEFAULT_BROADCAST
        port = port or DEFAULT_PORT
        count = count or DEFAULT_PACKET_COUNT
        target_ip = ""
        resolved_name = "raw-mac"

    try:
        mac = normalize_mac(mac)
    except ValueError as e:
        print(make_result(success=False, error=str(e)))
        return

    # Validate broadcast IP
    try:
        ipaddress.ip_address(broadcast)
    except ValueError:
        print(make_result(success=False, error=f"Invalid broadcast address: {broadcast}"))
        return

    # Send
    sent = send_magic_packet(mac, broadcast, port, count)

    result = {
        "success": True,
        "host": resolved_name,
        "mac": mac,
        "broadcast": broadcast,
        "port": port,
        "packets_sent": sent,
        "message": f"Magic packet sent to {mac} ({sent}x via {broadcast}:{port})",
    }

    # Verify
    if verify and target_ip:
        result["message"] += " — verifying..."
        online = ping_host(target_ip)
        result["online"] = online
        if online:
            result["message"] = f"Host '{resolved_name}' is online"
        else:
            result["message"] = f"Magic packet sent but host '{resolved_name}' did not respond to ping (IP: {target_ip}). It may need more time or WoL may not be enabled."
    elif verify and not target_ip:
        result["verify_skipped"] = True
        result["message"] += " — verify requested but no IP configured for this host"

    print(make_result(**result))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Wake on LAN — send Magic Packet to wake remote hosts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="Path to hosts.yaml config file")
    parser.add_argument("--host", type=str, default=None,
                        help="Host name to wake (looked up in config)")
    parser.add_argument("--mac", type=str, default=None,
                        help="Raw MAC address (XX:XX:XX:XX:XX:XX)")
    parser.add_argument("--broadcast", type=str, default=None,
                        help="Override broadcast address")
    parser.add_argument("--port", type=int, default=None,
                        help="Override UDP port (default 9)")
    parser.add_argument("-n", "--count", type=int, default=None,
                        help="Number of magic packets to send (default 3)")
    parser.add_argument("--verify", action="store_true",
                        help="Ping the host after sending to verify it's online")
    parser.add_argument("--list", action="store_true",
                        help="List all configured hosts and exit")

    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    if args.list:
        action_list(config)
    elif args.host or args.mac:
        action_wake(
            config,
            host_name=args.host,
            mac=args.mac,
            broadcast=args.broadcast,
            port=args.port,
            count=args.count,
            verify=args.verify,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
