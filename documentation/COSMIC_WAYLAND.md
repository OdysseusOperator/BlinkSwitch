# COSMIC Wayland Support

BlinkSwitch's Linux window-management backend targets the COSMIC Wayland
compositor. Platform-specific window operations live in
`backend/platforms/cosmic/` and use the Rust `cosmic-helper/`; shared service and
API code lives in `backend/service.py` and `backend/backend.py`. COSMIC output
enumeration and output scale metadata live in
`backend/platforms/cosmic/monitor_provider.py`; shared monitor registration and
identity handling live in `backend/monitor_manager.py`.

The backend does not use X11, XWayland, or `wmctrl` for window management. The
planned mouse-centering integration will use permission-controlled `libei`
input rather than an unrestricted synthetic-input tool. The frontend overlay
itself uses XWayland, as described below.

## Setup

Build the helper from the repository root:

```sh
cargo build --release --manifest-path cosmic-helper/Cargo.toml
./start.sh
```

Nix users can provide the required Rust and native libraries reproducibly. The
launcher enters the repository shell automatically:

```sh
cargo build --release --manifest-path cosmic-helper/Cargo.toml
./start.sh
```

`start.sh` enters the repository shell automatically when Nix is available. It
creates the shared root `.venv` with `uv`, installs `requirements.txt`, then
starts backend and frontend together.

The backend launches `cosmic-helper` automatically. Set `COSMIC_HELPER` to an
executable path when using a system or separately built helper.

## Supported operations

- Enumerate COSMIC toplevels, outputs, workspaces, and compositor state.
- Focus a window.
- Request maximize or unmaximize.
- Move a window to a workspace on a selected output.
- Request fullscreen on a selected output.
- Pointer centering is reserved for the planned RemoteDesktop portal and
  `libei` integration; it is currently skipped on Wayland.

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
