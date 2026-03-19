# Layout / Monitor Assignment Redesign

## Problem Statement

The current layout system uses Windows `DISPLAY#` connector names (e.g. `DISPLAY1`, `DISPLAY3`)
as logical slot numbers for assigning windows to screens. This breaks in several real-world
scenarios:

1. **Non-sequential connector IDs.** When a laptop is docked with one external monitor,
   Windows may report `DISPLAY1` (external, left) and `DISPLAY3` (laptop/primary, right).
   `DISPLAY2` is an inactive adapter slot. The current code expects `DISPLAY1` and `DISPLAY2`,
   so layout slot 2 never matches — windows that should go to the laptop screen are silently
   dropped.

2. **Lid-close / lid-open.** Closing the lid removes one monitor. Opening it adds one back,
   potentially with a different `DISPLAY#`. Any cached slot mapping is now wrong.

3. **Dock / undock.** Plugging into a dock can add 1–3 monitors. Connector IDs may shift.

4. **Identical-resolution monitors.** Two `1920×1080` monitors cannot be distinguished by
   resolution alone. The current secondary fingerprint (`width×height`) would alias them.

### Root cause (confirmed via Win32 inspection)

```
DISPLAY1  StateFlags=1 (active)   → external MSI monitor, x=-1920
DISPLAY2  StateFlags=0 (inactive) → empty adapter slot, no physical display
DISPLAY3  StateFlags=5 (active)   → laptop panel, x=0 (primary)
SM_CMONITORS = 2
```

`screeninfo.get_monitors()` correctly returns 2 monitors, but names them `DISPLAY1` and
`DISPLAY3`. The layout file contains `"display_number": 2`, which never matches `DISPLAY3`.

---

## Goals

- Layout slot numbers must be **positional** (left-to-right order of physical screens),
  not tied to Windows connector IDs.
- The system must work correctly after lid-close/open, dock/undock, and reboots.
- Identical-resolution monitors must be distinguishable by position.
- Existing layout JSON files should be migrated automatically, with no data loss.
- The user must be able to **explicitly override** slot→monitor assignment when auto-detection
  produces the wrong result (e.g. mirrored desk setup where "left" is subjective).

---

## Design

### 1. Positional slot numbering

After `detect_monitors()`, sort connected monitors by their `x` coordinate (ascending,
i.e. left-to-right). Assign slot numbers 1, 2, 3 … in that order.

```
Example (2 monitors):
  DISPLAY1  x=-1920  width=1080  height=1920  → slot 1  (leftmost)
  DISPLAY3  x=0      width=1920  height=1080  → slot 2  (rightmost)
```

Ties (monitors at the same `x`, e.g. stacked vertically) are broken by `y` coordinate
(top-to-bottom). A monitor at `(0, -1080)` sorts before `(0, 0)`.

This mapping is **ephemeral** — recomputed on every `detect_monitors()` call. It is never
persisted to disk.

### 2. Layout schema changes

#### Before (current)
```json
"screen_requirements": {
  "total_screens": 2,
  "screens": [
    { "display_number": 1, "orientation": "vertical" },
    { "display_number": 2, "orientation": "horizontal" }
  ]
},
"rules": [
  { "target_display": 1, ... },
  { "target_display": 2, ... }
]
```

#### After (redesigned)
```json
"schema_version": 2,
"screen_requirements": {
  "total_screens": 2,
  "screens": [
    { "slot": 1, "orientation": "vertical",   "description": "Leftmost screen" },
    { "slot": 2, "orientation": "horizontal", "description": "Main/right screen" }
  ]
},
"rules": [
  { "target_slot": 1, ... },
  { "target_slot": 2, ... }
]
```

Key differences:
- `display_number` → `slot` (positional, 1-based)
- `target_display` → `target_slot`
- `schema_version: 2` added at the root

#### Migration

On load, if `schema_version` is absent (or 1), the layout manager automatically rewrites
`display_number` → `slot` and `target_display` → `target_slot` in memory. A backup is saved
to `<name>.json.backup` before any in-place migration writes.

### 3. `/monitors` API response changes

The `/monitors?connected_only=true` endpoint must return the positional slot alongside each
monitor so the frontend can display "Slot 1 (left)" and "Slot 2 (right)".

#### Current response item
```json
{
  "id": "monitor_77150378",
  "name": "\\.\DISPLAY1 (1080×1920)",
  "width": 1080, "height": 1920,
  "x": -1920, "y": 0,
  "is_primary": false,
  "dpi_scale": 1.0
}
```

#### New response item
```json
{
  "id": "monitor_77150378",
  "name": "\\.\DISPLAY1 (1080×1920)",
  "width": 1080, "height": 1920,
  "x": -1920, "y": 0,
  "is_primary": false,
  "dpi_scale": 1.0,
  "slot": 1,
  "slot_label": "Slot 1 (leftmost)"
}
```

### 4. Slot→monitor resolution at rule-apply time

When a layout rule has `"target_slot": 2`, the runtime must resolve slot 2 to a physical
monitor ID. Resolution order:

1. **Explicit override** (persisted in `monitors_config.json` under `settings.slot_overrides`):
   ```json
   "slot_overrides": {
     "dual-screen-home": { "1": "monitor_77150378", "2": "monitor_51e9fcfb" }
   }
   ```
   If an override exists for this layout + slot, use it directly.

2. **Auto positional**: use the slot→monitor map computed from the current `detect_monitors()`
   result (left-to-right sort). If slot 2 maps to `monitor_51e9fcfb`, use that.

3. **Error**: slot out of range (e.g. layout needs slot 3 but only 2 monitors connected) →
   raise `LayoutError` — layout cannot be applied.

### 5. `/screen-assign` endpoint (new)

Allows the user to explicitly bind layout slots to physical monitors. Useful when:
- Two monitors have the same resolution and position detection is ambiguous.
- User has a non-standard desk arrangement where "left" is not slot 1.

```
POST /screen-assign
Body: {
  "layout_name": "dual-screen-home",
  "assignments": {
    "1": "monitor_77150378",
    "2": "monitor_51e9fcfb"
  }
}
Response 200: { "saved": true }

DELETE /screen-assign/<layout_name>
Response 200: { "cleared": true }
```

Overrides are stored in `monitors_config.json` → `settings.slot_overrides`.

### 6. `LayoutMatcher` changes

Replace `extract_display_number()` / DISPLAY#-based logic with slot-based logic.

#### New method: `get_slot_map() -> Dict[int, str]`

```python
def get_slot_map(self) -> Dict[int, str]:
    """Return {slot_number: monitor_id} sorted left-to-right by x coordinate."""
    self.monitor_manager.detect_monitors()
    connected = self.monitor_manager.get_all_connected_monitors()  # id → screeninfo Monitor
    sorted_monitors = sorted(connected.items(), key=lambda kv: (kv[1].x, kv[1].y))
    return {i + 1: monitor_id for i, (monitor_id, _) in enumerate(sorted_monitors)}
```

#### Updated `matches_requirements()`

- Check `total_screens` against `len(slot_map)` (unchanged logic, just uses slot_map).
- For each required screen, check that `slot` ≤ `len(slot_map)`.
- Check orientation by looking up the monitor for that slot and comparing `width > height`.

#### Updated `build_display_map()` → `build_slot_map()`

Returns `{slot: monitor_id}` instead of `{display_number: monitor_id}`.

#### Removed

- `extract_display_number()` — no longer needed.
- `get_screen_configuration()` — replaced by `get_slot_map()` + inline orientation checks.

### 7. `layout_manager.py` changes

- `_apply_layout_rule(rule, display_map)`:
  - Use `rule["target_slot"]` (with fallback to `rule.get("target_display")` for v1 layouts
    that haven't been migrated yet).
  - Lookup: `monitor_id = display_map[target_slot]`.
  - The `display_map` parameter is renamed `slot_map`.

- `can_apply_layout(layout_name)`:
  - Gets slot map from `LayoutMatcher.get_slot_map()`.
  - Checks `total_screens` and per-slot orientation.

- `ensure_layout_can_apply(layout_name)`:
  - No change needed; calls `can_apply_layout()` which is updated above.

### 8. `monitor_fingerprint.py` changes

The fingerprint system is kept, but the **primary fingerprint** changes:

#### Current primary: `DISPLAY{N}_{W}x{H}`

This is brittle — connector number changes on dock/undock.

#### New primary: `{W}x{H}@({x},{y})`  — resolution + position

Position (x, y) is stable within a given physical setup. If the user moves a monitor,
they expect layout matching to reconsider anyway.

#### New secondary (fallback): `{W}x{H}`  — resolution only

Keeps compatibility with configs migrated from another machine.

```python
def _generate_primary_fp(self, monitor_data: Dict) -> str:
    w, h = monitor_data["width"], monitor_data["height"]
    x, y = monitor_data.get("x", 0), monitor_data.get("y", 0)
    return f"{w}x{h}@({x},{y})"

def _generate_secondary_fp(self, monitor_data: Dict) -> str:
    return f"{monitor_data['width']}x{monitor_data['height']}"
```

Existing monitors in `monitors_config.json` will have their fingerprints regenerated on
the next `detect_monitors()` call via `add_monitor()` → `save_config()`.

---

## Migration Plan

### Step 1 — Update `MonitorFingerprint`

- Change `_generate_connector_resolution_fp` to use position+resolution instead of
  DISPLAY# + resolution.
- Keep secondary fingerprint as `{W}x{H}`.
- Bump internal comment noting the change; no version field needed (regenerated on detect).

### Step 2 — Update `LayoutMatcher`

- Add `get_slot_map()`.
- Rewrite `matches_requirements()` to use slots.
- Add `build_slot_map()` (replaces `build_display_map()`).
- Keep `build_display_map()` as a deprecated alias that calls `build_slot_map()`.

### Step 3 — Update `layout_manager.py`

- Load layout: detect `schema_version`. If v1, rewrite field names in-memory.
- `_apply_layout_rule`: use `target_slot` (with v1 fallback).
- `can_apply_layout`: use `get_slot_map()`.

### Step 4 — Update `backend.py`

- Add `POST /screen-assign` and `DELETE /screen-assign/<name>` endpoints.
- Update `GET /monitors?connected_only=true` to include `slot` and `slot_label`.
- Update `GET /screen-config` to return slot-based config.

### Step 5 — Migrate layout JSON files

- For each `*.json` in `backend/layouts/`, if `schema_version` is missing:
  - Write `.json.backup` copy.
  - Replace `display_number` → `slot` in `screen_requirements.screens`.
  - Replace `target_display` → `target_slot` in each rule.
  - Add `"schema_version": 2` at root.
  - Save in-place.

One-time migration script: `backend/migrate_layouts.py` (run manually or on first startup).

### Step 6 — Update `frontend-switcher.py`

- Layout activation already sends `POST /apply-rules` and reads `200 OK` before setting
  `active_layout` (fixed in Bug 1). No changes needed for slot logic — the frontend only
  cares about layout names, not slot numbers.
- If the frontend ever renders slot assignments, it should read `slot` from
  `GET /monitors?connected_only=true`.

### Step 7 — Verify and test

After each step, run:
```
python -m compileall backend
```

Manual smoke test sequence:
1. Start backend with 2 monitors connected.
2. `GET /monitors?connected_only=true` — verify `slot` fields present and correct.
3. `POST /apply-rules {"layout_name": "dual-screen-home"}` — verify 200, windows move to
   correct physical screens.
4. Close lid (1 monitor). Repeat step 3 — verify 409 with a clear error message.
5. Reopen lid. Repeat step 3 — verify 200 again.
6. Verify `monitors_config.json` has updated fingerprints (no DISPLAY# in primary FP).

---

## Files Changed

| File | Change |
|---|---|
| `backend/monitor_fingerprint.py` | New primary FP: position+resolution instead of DISPLAY# |
| `backend/layout_matcher.py` | Add `get_slot_map()`, rewrite slot-based matching, remove DISPLAY# logic |
| `backend/layout_manager.py` | Use `target_slot`, v1→v2 in-memory migration, update `can_apply_layout` |
| `backend/backend.py` | `/screen-assign` endpoints, add `slot`/`slot_label` to `/monitors` response |
| `backend/layouts/dual-screen-home.json` | Migrate to schema_version 2 |
| `backend/migrate_layouts.py` | One-time migration script for all layout files |

Files **not** changed in this redesign:
- `backend/config_manager.py` — only gains `slot_overrides` under `settings` (additive)
- `backend/monitor_manager.py` — no changes needed; `detect_monitors()` already works
- `backend/service.py` — no changes needed
- `frontend/frontend-switcher.py` — no changes needed

---

## Open Questions

1. **Vertical stacking.** If two monitors have the same `x` (stacked vertically), the
   tiebreak is `y` (top first). Should "top" be slot 1 or slot 2? Current proposal: top=1.
   This is configurable via the override mechanism if the user prefers otherwise.

2. **Three+ monitors.** The slot system scales naturally (slot 1, 2, 3 left-to-right).
   Layouts specify `total_screens: N` to opt into a specific monitor count. No special
   handling needed.

3. **Primary monitor as fixed slot.** Some users may want "primary monitor is always slot 1"
   regardless of physical position. Not planned — positional ordering is more predictable
   and aligns with the `SM_CMONITORS` model.

4. **Config backward compatibility.** Monitors in `monitors_config.json` will have their
   fingerprints regenerated on first run after the update. Old `DISPLAY#`-based fingerprints
   will be replaced silently. IDs are preserved because `add_monitor()` checks existing
   fingerprints before assigning a new UUID.
