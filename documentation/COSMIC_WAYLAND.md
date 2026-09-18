# COSMIC Wayland Support

BlinkSwitch's Linux backend is native Wayland support for the COSMIC
compositor. It does not use X11, XWayland, `wmctrl`, or synthetic pointer
input.

## Setup

Build the helper from the repository root:

```sh
cargo build --release --manifest-path cosmic-helper/Cargo.toml
python -m backend.backend
```

Nix users can provide the required Rust and native libraries reproducibly:

```sh
nix develop
cargo build --release --manifest-path cosmic-helper/Cargo.toml
```

The shell provides Python with Tk support for the Raylib frontend overlays.
Recreate the frontend environment after entering the shell:

```sh
python -m venv --clear frontend/.venv
source frontend/.venv/bin/activate
python -m pip install -r frontend/requirements.txt
```

The backend launches `cosmic-helper` automatically. Set `COSMIC_HELPER` to an
executable path when using a system or separately built helper.

## Supported operations

- Enumerate COSMIC toplevels, outputs, workspaces, and compositor state.
- Focus a window.
- Request maximize or unmaximize.
- Move a window to a workspace on a selected output.
- Request fullscreen on a selected output.

Wayland does not provide arbitrary client-side window coordinates. COSMIC's
workspace/output operation is therefore the supported equivalent of moving a
window between monitors.

COSMIC's toplevel protocols are unstable and requests are compositor policy
decisions. The helper returns the request result; subsequent state snapshots
are the source of truth.

Global hotkeys must be configured in COSMIC Settings because Wayland does not
provide a general client-side global shortcut API used by this project.

The Raylib frontend is forced through XWayland because its monitor-number
overlay requires positionable windows. Window discovery and management remain
native COSMIC Wayland through the helper.

The frontend starts hidden and listens on a local Unix socket. Configure the
COSMIC `Alt+Space` shortcut to run:

```sh
/home/mw/BlinkSwitch/scripts/blinkswitch-toggle
```
