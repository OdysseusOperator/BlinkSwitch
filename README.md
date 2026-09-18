# ScreenAssign

A service that automatically assigns windows to specific monitors based on configurable rules. ScreenAssign runs as a headless service and integrates with Dashboard through a REST API, with no UI dependencies required.

## Features

- Automatically detect and track connected monitors
- Define rules to place windows on specific monitors
- Match windows by executable name or window title
- Configure window state (maximize or fullscreen)
- Integrates with Dashboard via REST API
- Works as a background service

## Installation

1. Ensure Python 3.8+ is installed
2. Clone or download this repository
3. Install dependencies:
```
pip install -r requirements.txt
```

### COSMIC Wayland

Native Linux support targets the COSMIC Wayland compositor. Build the helper
before starting the backend:

```
cargo build --release --manifest-path cosmic-helper/Cargo.toml
python -m backend.backend
```

On NixOS or systems with Nix, use the provided development shell to supply
Rust and the native Wayland build dependencies:

```
nix develop
cargo build --release --manifest-path cosmic-helper/Cargo.toml
```

Create the frontend virtual environment after entering the shell so it uses
the Nix Python runtime with Tk support:

```
python -m venv --clear frontend/.venv
source frontend/.venv/bin/activate
python -m pip install -r frontend/requirements.txt
```

The helper uses COSMIC Wayland protocols for window discovery, focus,
fullscreen, maximize, and moving a window to a workspace on a selected
monitor. Set `COSMIC_HELPER` if the helper is installed elsewhere. The
protocols are currently unstable, so use a COSMIC release that provides
`zcosmic_toplevel_info_v1` and `zcosmic_toplevel_manager_v1`.

Global hotkeys are compositor-owned on Wayland. Configure the desired launch
binding in COSMIC Settings; the frontend does not install a global hook.
Raylib is forced through XWayland for overlay positioning; window discovery
and management remain native COSMIC Wayland.
For an already-running frontend, bind `Alt+Space` to the absolute executable `/home/mw/BlinkSwitch/scripts/blinkswitch-toggle` so COSMIC signals it to toggle.

## Configuration

ScreenAssign uses a JSON configuration file located at `monitors_config.json` by default. The file is created automatically when the service starts.

### JSON Configuration Structure

```json
{
  "known_monitors": [
    {
      "id": "monitor_1",
      "name": "Main Display",
      "width": 1920,
      "height": 1080,
      "x": 0,
      "y": 0,
      "is_primary": true,
      "first_detected": "2024-01-21T08:00:00",
      "last_connected": "2024-01-21T08:00:00"
    }
  ],
  "application_rules": [
    {
      "rule_id": "rule_1",
      "match_type": "exe",
      "match_value": "chrome.exe",
      "target_monitor_id": "monitor_1",
      "fullscreen": false,
      "maximize": true,
      "enabled": true,
      "last_applied": "2024-01-21T08:05:00"
    },
    {
      "rule_id": "rule_2",
      "match_type": "window_title",
      "match_value": "Microsoft Excel",
      "target_monitor_id": "monitor_2",
      "fullscreen": false,
      "maximize": true,
      "enabled": true,
      "last_applied": "2024-01-21T08:05:00"
    }
  ]
}
```

## Running as a Service

To run ScreenAssign as a background service:

```
python screenassign_service.py --daemon
```

Options:
- `--config PATH`: Path to custom config file
- `--log PATH`: Path to custom log file
- `--daemon`: Run as background service
- `--no-autostart`: Don't start service automatically

## Logs

Logs are written to `logs/screenassign_YYYYMMDD.log` by default.

## Behavior

- If a rule specifies a monitor that is not connected, the rule is ignored
- If an application specified in a rule is not running, the rule is ignored
- The service checks for windows and applies rules every 5 seconds
- The service checks for monitor changes every 30 seconds

## Architecture

ScreenAssign is designed as a headless service with no UI dependencies. All configuration and control happens through:
- The REST API endpoints for integration with Dashboard
- Signal files for simple enable/disable functionality
- The JSON configuration file for manual editing if needed

The Angular component example provided in `angular-component-example.ts` is purely for reference to show how to integrate with the Dashboard frontend.

## License

MIT
