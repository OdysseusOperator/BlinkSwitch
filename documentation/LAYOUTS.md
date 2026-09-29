# BlinkSwitch Layouts

Layouts are named JSON presets containing screen requirements and window rules.
They live in `layouts/*.json` and are activated from the frontend command
palette or the REST API.

## Current Model

- Screens use 1-based positional `slot` values, not Windows `DISPLAY#` IDs.
- Rules use `target_slot` to select a screen.
- The frontend maps slots to live monitor `identity_key` values.
- The backend resolves that assignment for each rule application and does not
  persist it.
- Legacy `display_number` and `target_display` fields are migrated in memory;
  new files must use the current names.

Monitor identity keys use `x_y_width_height`, for example:

```text
-1920_0_1080_1920
0_0_1920_1080
```

## Layout File

```json
{
  "name": "Coding Setup",
  "description": "Code on the vertical screen; browser on the horizontal screen",
  "schema_version": 2,
  "screen_requirements": {
    "total_screens": 2,
    "screens": [
      {"slot": 1, "orientation": "vertical", "description": "Code"},
      {"slot": 2, "orientation": "horizontal", "description": "Browser"}
    ]
  },
  "rules": [
    {
      "rule_id": "rule_code",
      "match_type": "exe",
      "match_value": "Code.exe",
      "target_slot": 1,
      "maximize": true,
      "fullscreen": false
    },
    {
      "rule_id": "rule_browser",
      "match_type": "exe",
      "match_value": "vivaldi.exe",
      "target_slot": 2,
      "maximize": false,
      "fullscreen": true
    }
  ]
}
```

Required fields:

| Field | Meaning |
| --- | --- |
| `name` | Human-readable layout name |
| `schema_version` | Current value is `2` |
| `screen_requirements.total_screens` | Number of required slots |
| `screen_requirements.screens` | Required slot and orientation definitions |
| `rules` | Window placement rules |

Rule fields:

| Field | Values |
| --- | --- |
| `match_type` | `exe`, `window_title`, or `process_path` |
| `match_value` | Value used by the selected matcher |
| `target_slot` | 1-based layout slot |
| `target_workspace` | Optional 1-based workspace or virtual desktop |
| `maximize` | Whether to maximize the window |
| `fullscreen` | Whether to request fullscreen |

Rules in an active layout are active. The old `enabled` field is not part of
the current rule model.

## Activation

From the frontend:

```text
Alt+Space -> /layouts -> select layout -> Enter or A
```

Via API:

```http
POST /screenassign/layouts/activate
Content-Type: application/json
```

```json
{"layout_name": "coding-setup"}
```

Deactivate from `/layouts` with `D`, or call:

```http
POST /screenassign/layouts/deactivate
```

Before applying rules, the backend validates the layout's required slot count;
slot presence; and orientation. If the current topology does not satisfy the
layout, activation fails without applying its rules.

## Assignment API

The frontend obtains connected monitors from:

```http
GET /screenassign/monitors?connected_only=true
```

Each monitor includes an `identity_key`. Assignment payloads map slot strings
to those keys:

```json
{
  "assignment": {
    "1": "-1920_0_1080_1920",
    "2": "0_0_1920_1080"
  }
}
```

Rule application endpoints require this assignment when applying a layout:

- `POST /screenassign/apply-rules`
- `POST /screenassign/apply-rule-for-window`
- `POST /screenassign/focus-window` when `apply_rules` is true

The assignment view is available through `/assign` in the frontend command
palette. It lets users map connected monitors to layout slots and stores the
selection in frontend preferences.

## Platform Notes

On Windows, slots are resolved to physical monitors through the Windows
monitor provider. On COSMIC, slots resolve to native Wayland outputs and
workspace operations are handled by `cosmic-helper`. The Raylib overlay uses
XWayland on COSMIC because it needs positionable windows.
