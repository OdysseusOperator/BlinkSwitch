# BlinkSwitch Backend Internals

## Overview

BlinkSwitch is a desktop window-management tool with a Flask HTTP backend and a
Python/Raylib overlay frontend. Windows is the primary platform; the backend also
has an experimental Linux COSMIC Wayland implementation.

Window-management code is separated by platform: `backend/platforms/windows/`
contains the Win32 adapter, and `backend/platforms/cosmic/` contains the COSMIC
Wayland adapter, which communicates with the Rust `cosmic-helper/`. Shared window
state types live in `backend/platforms/common.py`; the platform package selects
which adapter to construct. Shared orchestration lives in `backend/service.py`,
and HTTP/API behavior lives in `backend/backend.py`. Window focus is routed through
the service and implemented by each adapter.

Monitor-specific OS operations are also behind providers under
`backend/platforms/windows/` and `backend/platforms/cosmic/`; shared monitor
registration, identity, and position lookup remain in `backend/monitor_manager.py`.
A `MonitorProviderProtocol` allows tests and callers to inject a provider. The
frontend is largely shared, but the Linux COSMIC setup uses XWayland for its
overlay and a Unix socket for toggling. `start.bat` and `start.sh` provide the
same shared-venv startup workflow on Windows and Linux.

---

## Monitor Identity Keys

Physical monitors are identified by a stable positional key:

```
x_y_W_H
```

Examples:
- `-1920_0_1080_1920` — a vertical monitor at x=-1920, y=0, 1080 wide, 1920 tall
- `0_0_1920_1080`     — the primary horizontal monitor

`GET /monitors?connected_only=true` returns each monitor's `identity_key` field so
the frontend can display them and let the user assign slots.

---

## Layout Schema Versions

### v1 (legacy, no longer written to disk)

```json
{
  "screen_requirements": {
    "screens": [{"display_number": 1, "orientation": "vertical"}]
  },
  "rules": [{"target_display": 2, ...}]
}
```

### v2 (current)

```json
{
  "schema_version": 2,
  "screen_requirements": {
    "screens": [{"slot": 1, "orientation": "vertical"}]
  },
  "rules": [{"target_slot": 2, ...}]
}
```

`layout_manager.py:load_layout()` migrates v1 JSON **in memory** (never writes
back to disk). The on-disk migration script is responsible for writing v2 to disk.
`validate_layout()` only understands v2 field names.

---

## Slot→Monitor Assignment

The backend is **stateless with respect to assignments**. Every call that needs to
resolve a slot to a physical monitor must include the assignment dict:

```json
{
  "assignment": {
    "1": "-1920_0_1080_1920",
    "2": "0_0_1920_1080"
  }
}
```

Keys are slot numbers (strings); values are `identity_key` strings.

The frontend persists the assignment locally (e.g. a JSON file) and sends it on
every relevant API call. The backend never stores it.

### Endpoints that require `assignment`

| Endpoint | Field required? |
|---|---|
| `POST /apply-rules` | always |
| `POST /apply-rule-for-window` | always |
| `POST /focus-window` (with `apply_rules=true`) | when `apply_rules=true` |

All return `400 Bad Request` if `assignment` is missing or empty.

---

## Resolution Path

```
Frontend POST /apply-rules
  │  { layout_name, assignment }
  │
  ▼
backend.py → service.apply_rules_now(layout_name, assignment)
  │
  ▼
layout_manager.ensure_layout_can_apply(layout_name, assignment)
  └── layout_matcher.build_slot_map(assignment)
        1. detect_monitors()
        2. build identity_key → monitor_id map from live topology
        3. resolve each slot in assignment → monitor_id
        4. raise LayoutError if any key unmatched
  │
  ▼
window_manager.apply_rules(layout_name, assignment)
  └── layout_manager.get_rules_for_layout(layout_name, assignment)
        returns list of (rule, monitor_id) pairs
  └── for each open window, match rule → move/resize window
```

---

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `layout_matcher.py` | Defines `LayoutError`; `build_slot_map(assignment)` resolves slots to monitor IDs; `get_orientation()` utility |
| `layout_manager.py` | Loads/validates/lists layout JSON files; v1→v2 in-memory migration; re-exports `LayoutError`; `get_rules_for_layout()`, `can_apply_layout()`, `ensure_layout_can_apply()` all take `assignment` |
| `monitor_manager.py` | Shared monitor registration, identity, and topology; delegates enumeration and scaling to a platform provider |
| `platforms/windows/window_manager.py` | Windows window enumeration, rule application, and focus implementation |
| `platforms/cosmic/window_manager.py` | COSMIC Wayland window operations through `cosmic-helper/` |
| `platforms/windows/monitor_provider.py` | Windows monitor enumeration and DPI scale detection |
| `platforms/cosmic/monitor_provider.py` | COSMIC output enumeration and output scale metadata |
| `platforms/monitor_provider.py` | `screeninfo` fallback provider |
| `platforms/contracts.py` | Structural protocols for window managers and monitor providers |
| `service.py` | Shared service orchestration; provides rule-application entry points over platform-specific managers |
| `backend.py` | Flask HTTP API; validates payloads and routes calls to `service`; includes some Win32-specific focus fallback |
| `config_manager.py` | Persists monitor fingerprint data to disk (JSON) |
| `monitor_fingerprint.py` | Generates stable monitor IDs from hardware attributes |

---

## `GET /screen-config` Response

```json
{
  "monitors": [
    {
      "id": "monitor_77150378",
      "x": -1920,
      "y": 0,
      "width": 1080,
      "height": 1920,
      "identity_key": "-1920_0_1080_1920",
      "orientation": "vertical",
      "dpi_scale": 1.0
    },
    {
      "id": "monitor_12345678",
      "x": 0,
      "y": 0,
      "width": 1920,
      "height": 1080,
      "identity_key": "0_0_1920_1080",
      "orientation": "horizontal",
      "dpi_scale": 1.0
    }
  ]
}
```

---

## Why DISPLAY# Was Removed

Windows can report non-contiguous adapter slot numbers (e.g. `DISPLAY1` and
`DISPLAY3` with `DISPLAY2` being an inactive adapter). The old system matched
`display_number: 2` from layout JSON to `DISPLAY2`, which never matched anything
when two monitors appeared as `DISPLAY1`/`DISPLAY3`.

The fix is to stop using DISPLAY# entirely. Physical monitors are now matched by
their positional geometry (`identity_key`), which is stable as long as the monitor
is plugged into the same port at the same resolution.
