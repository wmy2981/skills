# LocalSend CLI — Complete Reference

> LocalSend CLI is the interactive terminal client shipped with LocalSend
> **v1.18.0** (2026-08-10), the first release after the Rust rewrite of
> LocalSend's core networking. It shares the same Rust protocol core
> (`packages/core`) as the Flutter desktop app, implements **LocalSend
> Protocol v2.2**, and is the **first ever official CLI** for LocalSend.

**Scope of this document:** full usage, invocation, environment variables,
configuration files, TUI interaction, relationship/conflicts with the
LocalSend desktop app, and installation on Windows / Linux / macOS. Written
for building a skill on top of the CLI. Facts were verified against the
v1.18.0 source tree (`localsend-cli/origin/`) and a live Windows install.

---

## 1. What it is

| | |
|---|---|
| Binary name | `localsend-cli` (Rust crate); on Windows the asset is `localsend.exe` |
| Version | 1.18.0 (matches app version; `app/pubspec.yaml` ↔ `cli/Cargo.toml` are CI-enforced to match) |
| Protocol | LocalSend Protocol **v2.2** (HTTP + UDP multicast discovery) |
| Technology | Rust (Tokio, clap, crossterm, ratatui TUI), edition 2024, rust 1.97.1 pinned via `rust-toolchain.toml` |
| License | Apache-2.0 |
| First release | v1.18.0 (2026-08-10), "feat(cli): initial CLI release" |
| Upstream | https://github.com/localsend/localsend (repo layout: `cli/` crate, `packages/core/` protocol library) |
| Release assets | GitHub releases, prefixed `LocalSend-CLI-<version>-<os>-<arch>` |

The CLI is a **terminal UI (TUI)** program, not a scriptable headless
daemon. There is **no non-interactive send mode** (no
`send --to <ip> <file>` command): files are always sent through the
interactive device list.

---

## 2. Installation

There are **no package-manager distributions** (no crates.io crate, no
Homebrew tap, no winget entry for the CLI — the winget package
`LocalSend.LocalSend` installs the GUI app only). Installation is either a
**manual download of the release asset** or **building from source**.

All CLI assets (v1.18.0):

| Platform | Asset name | Contents |
|---|---|---|
| Windows | `LocalSend-CLI-1.18.0-windows-x86-64.exe` / `...-windows-arm-64.exe` | Single self-contained exe (no zip, no installer) |
| Linux | `LocalSend-CLI-1.18.0-linux-x86-64.tar.gz` / `...-linux-arm-64.tar.gz` | tar.gz containing one `localsend-cli` binary (exec bit preserved) |
| macOS | `LocalSend-CLI-1.18.0-macos-arm-64.tar.gz` / `...-macos-x86-64.tar.gz` | tar.gz containing `localsend-cli`, **Developer ID signed + notarized** |

Download: `https://github.com/localsend/localsend/releases` → expand the
asset list of the latest release (or `gh release download v1.18.0 --repo
localsend/localsend --pattern "LocalSend-CLI-*"`).

### Windows

```powershell
# 1. Download LocalSend-CLI-1.18.0-windows-x86-64.exe
# 2. Put it anywhere on PATH (or add its folder to PATH), e.g.:
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\Programs\localsend-cli"
Move-Item .\LocalSend-CLI-1.18.0-windows-x86-64.exe "$env:LOCALAPPDATA\Programs\localsend-cli\localsend.exe"
# 3. Verify
localsend --version
```

Notes:
- Rename to `localsend.exe` (or `localsend-cli.exe`) for a short command.
- **Signing:** the project's code-signing policy says official Windows
  artifacts are signed via SignPath (certificate: *SignPath Foundation*),
  but **none of the v1.18.0 Windows assets are Authenticode-signed in
  practice** — verified `Get-AuthenticodeSignature` → `NotSigned` on both
  the downloaded CLI exe and `localsend_app.exe` extracted from the
  1.18.0 Windows zip. SmartScreen may warn; verify the SHA-256 against the
  release if paranoid.
- The release notes mention the EXE installer was not yet published
  (#3270) at 1.18.0.

### Linux

```bash
tar -xzf LocalSend-CLI-1.18.0-linux-x86-64.tar.gz
sudo install -m 755 localsend-cli /usr/local/bin/
localsend --version
```

### macOS

```bash
tar -xzf LocalSend-CLI-1.18.0-macos-arm-64.tar.gz
sudo mv localsend-cli /usr/local/bin/
```

The macOS binaries are Developer ID signed (`Developer ID Application: Tien
Do Nam (3W7H4PYMCV)`) and notarized. Bare binaries cannot be stapled, so
Gatekeeper fetches the notarization ticket online on first run (requires
network).

### Build from source

```bash
git clone https://github.com/localsend/localsend
cd localsend
# rust-toolchain.toml pins channel 1.97.1 (auto-installed by rustup)
cargo build --release --package localsend-cli
# binary at target/release/localsend-cli(.exe)
```

Windows builds via CI additionally run `Renaming` step producing the
`LocalSend-CLI-<version>-windows-<arch>.exe` asset name; the release
workflow builds Linux (x86-64 + arm-64 on GitHub runners) and the
`compile_mac_cli.sh` script builds both macOS arches and signs/notarizes.

---

## 3. Command-line usage

```
Usage: localsend [OPTIONS]

Options:
      --alias <ALIAS>              Device name shown to other devices
                                   [default: config.toml, else the hostname]
                                   [env: LOCALSEND_ALIAS=]
      --port <PORT>                Port of the HTTP server
                                   [default: config.toml, else 53317]
                                   [env: LOCALSEND_PORT=]
      --destination <DESTINATION>  Directory where received files are saved
                                   [default: config.toml, else the Downloads folder]
                                   [env: LOCALSEND_DESTINATION=]
  -f, --file <PATH>                File to send: opens the device list on start,
                                   selecting a device starts the transfer (repeatable)
  -h, --help                       Print help
  -V, --version                    Print version
```

### Two operating modes

**1. Receive / always-on mode** — run with no arguments:

```bash
localsend
```

Starts the HTTP server (TLS) + multicast discovery and shows the status
banner; the terminal becomes the "app window". Incoming requests are shown
in real time and answered interactively. This is the CLI equivalent of
leaving the desktop app open.

**2. Send mode** — run with `-f`/`--file` (repeatable):

```bash
localsend -f photo.jpg -f report.pdf
```

On start it opens the **device list** instead of the idle banner; the first
discovered/paired device gets hotkey `1`, the second `2`, … (up to `9`).
Press the hotkey to start the transfer. **The program exits automatically
when the transfer ends** (`Ctrl+C` meanwhile closes the list and quits).
`-f` values are validated to be existing files (`Not a file: ...` error
otherwise).

### Environment variables

| Variable | Meaning | Notes |
|---|---|---|
| `LOCALSEND_ALIAS` | Device name shown to peers | overrides config.toml |
| `LOCALSEND_PORT` | HTTP server port (default `53317`) | overrides config.toml |
| `LOCALSEND_DESTINATION` | Receive directory (default system Downloads) | overrides config.toml; `~/` is expanded |
| `XDG_CONFIG_HOME` | Overrides the config directory root | CLI uses `$XDG_CONFIG_HOME/localsend-cli`; relative values are ignored per XDG spec |

**Precedence (all settings):** command-line flag > environment variable >
`config.toml` > built-in default.

### TUI reference

Banner (idle mode) shows: alias, port, destination, config dir, and the
listening URLs (`https://<ip>:<port>` per IPv4 address; IPv6 collapsed per
scope with `(+N more)`).

| Key | Action |
|---|---|
| `1`–`9` | Send the preselected/picked files to device #N (discovered/paired list order) |
| `D` | Open/close the device list (paired + discovered sections) |
| `W` then `S` | Toggle **share via link**: serve files to browsers over plain HTTP |
| `W` then `R` | Toggle **receive via link**: let browsers upload files over plain HTTP |
| `Y` / `N` / `P` | Accept / Decline / Accept-**and-Pair** an incoming request |
| `Ctrl+C` | Cancel current transfer/request; when idle → quit |

In the **file picker** (opened when no `-f` was given and a hotkey is
pressed): arrow keys / Enter select the file to send. In the **device
list**: arrows navigate, `Enter` sends, `P` pairs/unpairs, `Esc`/`D` closes.

Event lines (one-letter prefixes in the log): `D` discovery, `S` sending,
`R` receiving.

---

## 4. Configuration & persistent data

All persistent files live in **one directory**, used on every OS:

```
$XDG_CONFIG_HOME/localsend-cli/     # or ~/.config/localsend-cli
├── config.toml     # user-edited settings (commented template auto-written on first run)
├── identity.pem    # this device's TLS certificate + private key (self-signed)
└── paired-v2.json  # paired devices (machine-written, atomic write-then-rename)
```

> The path deliberately uses `~/.config` on **all** platforms (terminal
> convention, even on macOS) and the `-cli` suffix keeps it **separate from
> the Flutter app's** data — see §6.

### config.toml

```toml
# Command-line flags and environment variables take precedence.
#alias = "My Device"        # default: hostname (trimmed of trailing ".local")
#port = 53317               # default: 53317
#destination = "~/Downloads"  # default: system Downloads folder; "~" expands
```

Unknown keys are rejected (`serde(deny_unknown_fields)`) — an invalid file
fails startup with a descriptive error.

### identity.pem

- Contains a self-signed certificate + private key (RSA, generated by
  `rcgen`). The device identity on the network is the **uppercase-hex
  SHA-256 of the certificate DER** ("fingerprint").
- Generated on first run, reused forever; on Unix it is written with mode
  `0600` (owner-only).
- **Deleting it resets the identity**: peers will see this device as a new,
  unpaired device (all pairings involving it become stale on both sides).

### paired-v2.json

- Map `fingerprint → {alias, channels[]}`; `channels` are the ranked HTTP
  addresses the device was last reachable at (used for the probe stage of
  startup discovery).
- Versioned (`version: 1`); a newer-format file fails with an explicit
  error. Written atomically (temp file + rename).
- **Paired devices are auto-accepted** when they send files (no prompt).
  Pair with `P` when accepting a request, or `P` in the device list.

---

## 5. Protocol & security model

- **HTTP + TLS with mutual client certificates** (same as the desktop app).
  Peers are identified by the SHA-256 fingerprint of their client cert DER;
  a register request whose payload fingerprint disagrees with the presented
  cert is dropped entirely.
- **No receive PIN** (`pin: None`); requests are answered interactively.
- **Checksums verified on receive** by default (`verify_checksums: true`).
- **Multicast discovery**: UDP group `224.0.0.167:53317` (+ IPv6
  `ff12::fd3a:e420`), **announce-only** — responses come back over HTTP as
  a unicast register request to the announcing device. One socket per
  interface (`SO_REUSEADDR` + `IP_MULTICAST_IF`); multicast loopback stays
  on, so two instances on one host see each other (own messages are dropped
  by fingerprint).
- **Staged discovery on start:** (1) announce this device, (2) probe paired
  devices' stored channels, (3) fall back to scanning local subnets when
  nothing was confirmed.
- Multicast failure is **not fatal** (warns `Multicast unavailable: ...` and
  keeps collecting devices that contact us over HTTP).
- The device registers itself as `device_type: Headless`, `device_model:
  "CLI"`, protocol `Https`.
- **Compatibility:** the Rust core serves **only v2 protocol** endpoints
  and does not parse v1 multicast messages. The CLI therefore interoperates
  with **v1.18.0+ devices only** (same Rust core) — it cannot talk to
  LocalSend ≤ v1.17.0 (old Flutter app, Android/iOS versions older than
  1.18.0). Upgrade peers or use the GUI app for v1 devices.
- File naming on receive: sender filename is sanitized (path-collapsed,
  illegal chars removed) and collisions become `name (1).ext`, `name (2).ext`.
- Sizes/speeds shown in **decimal units** (1 KB = 1000 B).

---

## 6. Relationship with the LocalSend desktop app

Both ship from the same release, share the Rust core, and can coexist on
one machine — but they are **two separate programs with separate
identities**:

### Two executables (Windows example)

| Executable | What it is |
|---|---|
| `localsend.exe` (CLI asset) | Rust CLI — the subject of this document |
| `localsend_app.exe` (app zip asset) | Flutter GUI app (v1.18.0+60), Rust core behind FRB bindings |

The desktop app zip also contains `flutter_windows.dll`, `data/`,
`rust_lib_localsend_app.dll` etc.; the CLI exe is fully standalone.
Verified: the 1.18.0 Windows zip contains **only** `localsend_app.exe`
(no CLI exe, no `settings.json` — the `settings.json` next to the exe on a
portable install is created at runtime) — download the `LocalSend-CLI-*`
asset separately.

### Key differences / conflicts

| Aspect | Desktop app | CLI | Conflict? |
|---|---|---|---|
| Config dir | `%APPDATA%\LocalSend\settings.json` (Windows) / portable `settings.json` next to exe when present; `~/.config/localsend`-style elsewhere | `~/.config/localsend-cli/` | no — separate dirs |
| Identity (cert) | stored in settings (`flutter.ls_security_context`, incl. private key) | `identity.pem` | **no — separate identities**: the same machine shows up twice with the same alias but different fingerprints (verified live: GUI `7030332D…`, CLI `9705057B…`) |
| Paired devices / favorites | app settings | `paired-v2.json` | **not shared** — pairing done in the GUI does not auto-accept CLI requests and vice versa |
| Default port | `53317` | `53317` | **yes — port conflict**: both bind the same HTTP port. Running both at once → the second one fails with a bind error (`TcpListener::bind` error propagates → startup fails). Workaround: give the CLI a different port (`--port` / `LOCALSEND_PORT` / `config.toml`); discovery announces carry that port, so transfers still work |
| Discovery | multicast 224.0.0.167:53317 | same group | running both → every peer sees two devices; both instances see each other on the same host (loopback) |
| Protocol | v2.2 (Rust core) | v2.2 | compatible — the 1.18.0 GUI and the CLI can transfer files with each other (e.g. `localsend` on this PC and the GUI on the same PC) |

### The app's own CLI arguments

The GUI app accepts start arguments (unrelated to the CLI's flags): pass
file paths to pre-select them, `--text <text>` / `-t <text>` to start a text
share, and `--share <SharedMedia JSON>` for a full share payload
(handled by `LoadSelectionFromArgsAction` in the app source).

---

## 7. Worked examples

```bash
# Receive files into ~/Downloads (default), keep running:
localsend

# Receive into a custom dir:
localsend --destination "D:\incoming"
# or: set LOCALSEND_DESTINATION=D:\incoming

# Send two files, exit when the transfer finishes:
localsend -f a.jpg -f b.pdf

# Run a second instance next to the GUI app on a different port:
localsend --port 53318 --alias "WMY-PC-cli"
```

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Error: failed to bind ... 53317` (startup error) | Desktop app (or another CLI) already uses port 53317 → set `--port 53318` or change `config.toml`. |
| `Not a file: <path>` | `-f`/`--file` got a non-file (directory, missing file). |
| `Invalid config file: ...` | config.toml has unknown keys / bad TOML — the first-run template is a safe reference. |
| `Invalid identity file: ...` | identity.pem corrupted → delete it; a fresh identity is generated (peers will treat you as new/unpaired). |
| `paired-v2.json has version N, but this build supports only version 1` | File written by a newer CLI build — downgrade or delete the file. |
| `Multicast unavailable: ...` | UDP multicast blocked (VPN, restricted network) — discovery degrades to HTTP-only (devices that announce to you still show up). |
| Device not visible | Firewall blocking 53317/TCP + UDP 53317; or peer runs protocol v1 (≤1.17.0) which the CLI cannot see. |
| Transfer rejected | Peer didn't accept; use paired devices for auto-accept. |

---

## 9. Source map (for skill development)

`cli/` crate (~3.8k lines), all Rust:

| File | Contents |
|---|---|
| `src/main.rs` | clap `Args` definition (flags/env vars) + tokio bootstrap |
| `src/app/mod.rs` | central event loop, key handling, startup (server + staged discovery), shutdown |
| `src/app/discovery.rs`, `devices.rs`, `sending.rs`, `receive.rs`, `status.rs`, `web_link.rs` | discovery handling, device list logic, send/receive sessions, web share/receive toggles |
| `src/storage/config.rs` | config.toml load/resolve (precedence chain), first-run template |
| `src/storage/identity.rs` | cert/key load-or-generate, fingerprint, register/multicast DTOs |
| `src/storage/paired.rs` | paired-v2.json CRUD + atomic save, versioning |
| `src/device_list.rs` | device list TUI widget (pair/unpair/send outcomes) |
| `src/picker.rs` | file picker TUI (ratatui-explorer) |
| `src/send_task.rs` | upload session management |
| `src/ui.rs`, `banner.rs`, `slots.rs`, `util.rs` | log UI, banner render, hotkey slot assignment, helpers (unique_path, formatters) |

Protocol implementation lives in `packages/core/` (HTTP server v2 +
multicast discovery + crypto); the CLI only wires it to the terminal.

## 10. References

- Upstream repo: https://github.com/localsend/localsend
- Releases: https://github.com/localsend/localsend/releases
- Code signing policy: https://github.com/localsend/localsend/blob/main/CODE_SIGNING.md
- Changelog: https://localsend.org/changelog
- Local clone used for this document: `localsend-cli/origin/` (v1.18.0 tag)
