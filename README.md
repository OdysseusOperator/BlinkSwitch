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
./start.sh
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

Test the new Go frontend during migration on Linux:

```bash
./start_blinkswitch_new.sh
```

This rebuilds the Go frontend with `frontend-go/build.sh`, then starts it with
the backend. Go or Nix is required for the build. The window appears immediately
and stays visible after selection, Escape, or hotkey toggles. Press `Ctrl+C` in
the launch terminal to stop both processes. `--update` refreshes Python dependencies.
Testing mode leaves hotkeys and the toggle IPC socket to the normal frontend,
so you can open it with `Alt+Space` while comparing both frontends.

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
