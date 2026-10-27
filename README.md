# BlinkSwitch

BlinkSwitch is a desktop window switcher and monitor-assignment service. A
Flask backend manages windows, monitors, layouts, and browser tabs; a Python
Raylib frontend provides the switcher and command palette.

## Installation

Install Python 3.11+ and [uv](https://docs.astral.sh/uv/), then run one launcher
from the repository root:

Windows:

```bat
start.bat
```

Linux:

```bash
./start.sh       # Python frontend + backend
./start_go.sh    # Rebuild Go frontend + start Go frontend and backend
```

The launcher creates one root `.venv`, installs `requirements.txt` with `uv`,
starts the backend, waits for its health endpoint, and starts the frontend.
Backend and frontend remain separate processes and are stopped together.
If a healthy BlinkSwitch backend is already running, the launcher reuses it and
leaves it running when the new frontend exits.

Use `--update` to reinstall dependencies after changing `requirements.txt`:

```bash
./start.sh --update
# Windows: start.bat --update
```

The old `start_assigner.bat` and `start_switcher.bat` names remain as
compatibility wrappers for `start.bat`.

## COSMIC Wayland

Linux support targets the COSMIC Wayland compositor. `start.sh` automatically
enters the repository Nix development shell when Nix is available. Build the
Rust helper once before the first launch:

```bash
cargo build --release --manifest-path cosmic-helper/Cargo.toml
./start.sh
```

Without Nix, install Rust, Tk, Raylib's native libraries, and the required
Wayland/X11 development libraries through the host distribution first. The
frontend uses XWayland for positionable overlay windows; window discovery and
management remain native COSMIC Wayland operations.

Global hotkeys are compositor-owned on Wayland. Configure `Alt+Space` in COSMIC
Settings to run:

```text
/home/mw/BlinkSwitch/scripts/blinkswitch-toggle
```

## Layouts

Layouts live in `layouts/*.json`. Current layout schema uses positional `slot`
values and `target_slot` rule fields. The frontend supplies a slot-to-monitor
assignment using each monitor's `identity_key`; the backend does not persist
that assignment.

See `documentation/LAYOUTS.md` for the schema and API examples.

## Browser Tabs

The optional browser extension sends local tab data to the backend on port
`5555`. Load `extensions/chromebased-browser` as an unpacked extension, then
start BlinkSwitch with `start.bat` or `./start.sh`.

## Development

Linux has two launchers: `start.sh` for Python and `start_go.sh` for Go.
The Go launcher rebuilds with `frontend-go/build.sh` (requires Go or Nix), then
uses the same shared environment and backend supervisor as the normal launcher.

```bash
./start_go.sh --keep-open                 # Side-by-side migration testing
./start_go.sh --keep-open --render-check  # Native Wayland scaling diagnostics
./start_go.sh --update                    # Refresh Python dependencies
./start_go.sh --toggle                    # Toggle an already-running Go frontend
```

Without `--keep-open`, the Go frontend starts hidden and registers toggle IPC.
Keep-open mode shows it immediately, disables hiding, and leaves hotkeys and the
toggle socket to the normal frontend for comparison. Press `Ctrl+C` in the launch
terminal to stop processes started by that launcher; a reused backend stays running.

```bash
ruff check .
python -m py_compile scripts/start_blinkswitch.py
```

Backend health endpoint:

```text
http://127.0.0.1:5555/screenassign/health
```

## Documentation

All project documentation lives under `documentation/`:

- `documentation/COSMIC_WAYLAND.md` for Linux platform behavior
- `documentation/INTERNALS.md` for backend architecture
- `documentation/LAYOUTS.md` for layout schemas and APIs
- `documentation/COMMANDS_USAGE.md` for frontend commands
- `documentation/hotkey-suppression-options.md` for hotkey design notes
