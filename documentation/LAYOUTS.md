# BlinkSwitch Layout System

## Overview

The **Layout System** allows you to create named presets of window placement rules that automatically adapt to your screen configuration. Each layout is stored as a JSON file and can be manually activated when you have the right screens connected.

## Key Features

✅ **Resolution Independent** - Layouts work regardless of screen resolution, only orientation (horizontal/vertical) and Windows DISPLAY# matter  
✅ **Position-Aware** - Uses Windows DISPLAY# numbering (DISPLAY1, DISPLAY2, etc.) for consistent screen identification  
✅ **Auto-Deactivation** - Layouts automatically deactivate when required screens are disconnected  
✅ **Manual Activation** - You control when to switch between layouts  
✅ **File-Based** - Each layout is a simple JSON file you can edit and share  

---

## Quick Start

### 1. Check Your Current Screen Configuration

Use the `/screen-config` command or API endpoint to see your current setup:

```bash
GET http://localhost:5555/screenassign/screen-config
```

Response:
```json
{
  "screens": [
    {
      "display_number": 1,
      "orientation": "vertical",
      "width": 1080,
      "height": 1920,
      "name": "\\\\.\\DISPLAY1 (1080×1920)"
    },
    {
      "display_number": 2,
      "orientation": "horizontal",
      "width": 1920,
      "height": 1080,
      "name": "\\\\.\\DISPLAY2 (1920×1080)"
    }
  ],
  "summary": "2 screens: DISPLAY1 (vertical, 1080x1920), DISPLAY2 (horizontal, 1920x1080)"
}
```

### 2. Create a Layout File

Create a file in the `layouts/` directory (e.g., `layouts/my-coding-setup.json`):

```json
{
  "name": "My Coding Setup",
  "description": "VS Code on vertical screen, browser on horizontal",
  "version": "1.0",
  "screen_requirements": {
    "total_screens": 2,
    "screens": [
      {
        "display_number": 1,
        "orientation": "vertical",
        "description": "Main coding screen"
      },
      {
        "display_number": 2,
        "orientation": "horizontal",
        "description": "Browser and docs"
      }
    ]
  },
  "rules": [
    {
      "match_type": "exe",
      "match_value": "Code.exe",
      "target_display": 1,
      "fullscreen": false,
      "maximize": true,
      "enabled": true
    },
    {
      "match_type": "exe",
      "match_value": "vivaldi.exe",
      "target_display": 2,
      "fullscreen": true,
      "maximize": false,
      "enabled": true
    }
  ],
  "metadata": {
    "created": "2026-02-02T12:00:00",
    "author": "your-name",
    "tags": ["coding", "work"]
  }
}
```

### 3. Activate the Layout

**Via Command (in window frontend - switch_mode):**
```
Alt+Space → /layouts → Select layout → Press Enter or 'A'
```

**Via API:**
```bash
POST http://localhost:5555/screenassign/layouts/activate
Content-Type: application/json

{
  "layout_name": "my-coding-setup"
}
```

### 4. Deactivate When Done

**Via Command:**
```
Alt+Space → /layouts → Press 'D'
```

**Via API:**
```bash
POST http://localhost:5555/screenassign/layouts/deactivate
```

---

## Layout File Format

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable layout name |
| `screen_requirements` | object | Defines which screens are needed |
| `screen_requirements.total_screens` | number | Exact number of screens required |
| `screen_requirements.screens` | array | List of required screen configurations |
| `rules` | array | Window placement rules to apply |

### Screen Requirements

Each screen in `screens` array must have:

| Field | Type | Values | Description |
|-------|------|--------|-------------|
| `display_number` | number | 1, 2, 3, ... | Windows DISPLAY# (DISPLAY1 = 1, DISPLAY2 = 2, etc.) |
| `orientation` | string | "horizontal" or "vertical" | Screen orientation (width > height = horizontal) |
| `description` | string | Any text | Optional human-readable description |

### Rule Format

Each rule in `rules` array:

| Field | Type | Description |
|-------|------|-------------|
| `match_type` | string | "exe", "window_title", or "process_path" |
| `match_value` | string | What to match (e.g., "Code.exe", "Chrome") |
| `target_display` | number | Which DISPLAY# to place the window (1, 2, 3, ...) |
| `fullscreen` | boolean | Make window fullscreen (removes borders) |
| `maximize` | boolean | Maximize window within display |
| `enabled` | boolean | Whether rule is active |

---

## How It Works

### Screen Matching Logic

1. **DISPLAY# Priority**: Layouts reference Windows DISPLAY numbers (1, 2, 3, etc.)
2. **Orientation Check**: Each required display must have the correct orientation
3. **Count Validation**: Exact number of screens must be connected
4. **Resolution Independent**: Changing resolution doesn't break layouts (as long as orientation stays the same)

**Example Scenarios:**

✅ **Scenario 1: Works**
- Layout requires: DISPLAY1 (vertical), DISPLAY2 (horizontal)
- You have: DISPLAY1 (1080×1920, vertical), DISPLAY2 (1920×1080, horizontal)
- **Result**: Layout activates successfully

❌ **Scenario 2: Fails**
- Layout requires: DISPLAY1 (vertical), DISPLAY2 (horizontal)
- You have: DISPLAY1 (1920×1080, horizontal), DISPLAY2 (1080×1920, vertical)
- **Result**: "DISPLAY1 is horizontal, but layout needs vertical"

✅ **Scenario 3: Resolution Change OK**
- Layout requires: DISPLAY1 (vertical)
- You had: DISPLAY1 (1080×1920, vertical)
- You change to: DISPLAY1 (1440×2560, vertical) - **still vertical!**
- **Result**: Layout continues working

❌ **Scenario 4: Auto-Deactivates**
- Layout requires: 2 screens
- You disconnect one screen
- **Result**: Layout automatically deactivates, previous rules restored

### Layout Activation Behavior

When you activate a layout:

1. **Validation**: Checks if current screens match requirements
2. **Save State**: Saves all current rules for restoration
3. **Disable Old Rules**: Disables all existing rules
4. **Create New Rules**: Creates rules from layout definition
5. **Apply Rules**: Immediately applies rules to windows

When you deactivate:

1. **Remove Layout Rules**: Deletes rules created by the layout
2. **Restore Previous**: Restores all rules that existed before activation
3. **Clear State**: Marks no layout as active

---

## Example Layouts

### Single Screen (Laptop Only)

**File:** `layouts/single-screen.json`

```json
{
  "name": "Single Screen",
  "description": "Laptop screen only - maximize everything",
  "version": "1.0",
  "screen_requirements": {
    "total_screens": 1,
    "screens": [
      {
        "display_number": 1,
        "orientation": "horizontal"
      }
    ]
  },
  "rules": [
    {
      "match_type": "exe",
      "match_value": "Code.exe",
      "target_display": 1,
      "maximize": true,
      "fullscreen": false,
      "enabled": true
    }
  ]
}
```

### Dual Horizontal Screens

**File:** `layouts/dual-horizontal.json`

```json
{
  "name": "Dual Horizontal",
  "description": "Two side-by-side monitors",
  "version": "1.0",
  "screen_requirements": {
    "total_screens": 2,
    "screens": [
      {
        "display_number": 1,
        "orientation": "horizontal"
      },
      {
        "display_number": 2,
        "orientation": "horizontal"
      }
    ]
  },
  "rules": [
    {
      "match_type": "exe",
      "match_value": "vivaldi.exe",
      "target_display": 1,
      "maximize": true,
      "fullscreen": false,
      "enabled": true
    },
    {
      "match_type": "exe",
      "match_value": "Code.exe",
      "target_display": 2,
      "maximize": true,
      "fullscreen": false,
      "enabled": true
    }
  ]
}
```

### Vertical + Horizontal Mix

**File:** `layouts/vertical-horizontal.json`

```json
{
  "name": "Vertical + Horizontal",
  "description": "Code on vertical, browser fullscreen on horizontal",
  "version": "1.0",
  "screen_requirements": {
    "total_screens": 2,
    "screens": [
      {
        "display_number": 1,
        "orientation": "vertical"
      },
      {
        "display_number": 2,
        "orientation": "horizontal"
      }
    ]
  },
  "rules": [
    {
      "match_type": "exe",
      "match_value": "Code.exe",
      "target_display": 1,
      "maximize": true,
      "fullscreen": false,
      "enabled": true
    },
    {
      "match_type": "exe",
      "match_value": "vivaldi.exe",
      "target_display": 2,
      "fullscreen": true,
      "maximize": false,
      "enabled": true
    }
  ]
}
```

---

## API Reference

### List Available Layouts

**GET** `/screenassign/layouts`

Returns all layout files in `layouts/` directory.

**Response:**
```json
[
  {
    "name": "Dual Horizontal",
    "file_name": "dual-horizontal.json",
    "file_path": "/path/to/layouts/dual-horizontal.json",
    "description": "Two side-by-side monitors",
    "total_screens": 2
  }
]
```

### Get Layout Details

**GET** `/screenassign/layouts/<layout_name>`

Returns layout preview with compatibility check.

**Response:**
```json
{
  "name": "Dual Horizontal",
  "description": "Two side-by-side monitors",
  "can_apply": true,
  "reason": "All requirements met",
  "screen_requirements": { ... },
  "current_screen_config": [ ... ],
  "rules_count": 2
}
```

### Activate Layout

**POST** `/screenassign/layouts/activate`

```json
{
  "layout_name": "dual-horizontal"
}
```

**Response:**
```json
{
  "success": true,
  "layout": "Dual Horizontal",
  "rules_applied": 2,
  "message": "Layout 'Dual Horizontal' activated successfully"
}
```

### Deactivate Current Layout

**POST** `/screenassign/layouts/deactivate`

**Response:**
```json
{
  "success": true,
  "deactivated": "Dual Horizontal",
  "message": "Layout 'Dual Horizontal' deactivated successfully"
}
```

### Get Active Layout

**GET** `/screenassign/layouts/active`

Returns currently active layout info, or `null` if none active.

**Response:**
```json
{
  "name": "Dual Horizontal",
  "file_name": "dual-horizontal.json",
  "activated_at": "2026-02-02T12:00:00",
  "rules_created": 2,
  "display_map": {
    "1": "monitor_123",
    "2": "monitor_456"
  },
  "screen_summary": "2 screens: DISPLAY1 (horizontal), DISPLAY2 (horizontal)"
}
```

### Get Current Screen Configuration

**GET** `/screenassign/screen-config`

Returns current connected screens with DISPLAY# and orientation.

**Response:**
```json
{
  "screens": [
    {
      "display_number": 1,
      "orientation": "horizontal",
      "monitor_id": "monitor_123",
      "width": 1920,
      "height": 1080,
      "name": "\\\\.\\DISPLAY1 (1920×1080)"
    }
  ],
  "summary": "1 screen: DISPLAY1 (horizontal, 1920x1080)"
}
```

---

## Commands

Use these commands in the window frontend (Alt+Space opens switch_mode):

### `/layouts`

Opens the Layout Management view where you can:
- **Enter** or **A**: Activate the selected layout
- **D**: Deactivate the current layout
- **↑/↓**: Navigate through layouts
- **Esc**: Close the view

Active layouts are marked with `[ACTIVE]`.

### `/screen-config`

Shows your current screen configuration with:
- DISPLAY numbers
- Orientations
- Resolutions

Use this to understand how to write your layout files.

---

## Troubleshooting

### Layout Won't Activate

**Problem:** "Screen configuration doesn't match layout requirements"

**Solutions:**
1. Run `/screen-config` to see your current setup
2. Check your layout's `screen_requirements.screens` array
3. Verify DISPLAY numbers and orientations match

**Example Fix:**
```json
// Before (wrong DISPLAY#)
"screens": [
  {"display_number": 1, "orientation": "vertical"}
]

// After (correct DISPLAY#)
"screens": [
  {"display_number": 2, "orientation": "vertical"}
]
```

### Layout Keeps Auto-Deactivating

**Problem:** Layout deactivates unexpectedly

**Causes:**
- Screen disconnected
- Screen orientation changed (e.g., rotated from landscape to portrait)
- Wrong total_screens count

**Fix:** Ensure all required screens stay connected and maintain their orientation.

### Rules Not Applying

**Problem:** Layout activates but windows don't move

**Solutions:**
1. Check that applications are actually running
2. Verify `match_value` in rules matches exactly (case-sensitive for `.exe` names)
3. Try `match_type: "window_title"` for partial matching
4. Check logs: `logs/screenassign_*.log`

---

## Best Practices

### 1. **Name Your Layouts Descriptively**

Good:
- `coding-dual-vertical.json`
- `presentation-mode.json`
- `work-from-home-setup.json`

Bad:
- `layout1.json`
- `test.json`
- `asdf.json`

### 2. **Add Helpful Descriptions**

```json
{
  "name": "Deep Work Mode",
  "description": "Distraction-free: Code fullscreen on main, docs on secondary",
  "screen_requirements": {
    "screens": [
      {
        "display_number": 1,
        "orientation": "vertical",
        "description": "Primary vertical 27-inch for code"
      }
    ]
  }
}
```

### 3. **Use Specific Match Values**

```json
// Good: Specific application
{"match_type": "exe", "match_value": "Code.exe"}

// Better: Multiple apps with individual rules
[
  {"match_type": "exe", "match_value": "Code.exe", "target_display": 1},
  {"match_type": "exe", "match_value": "WindowsTerminal.exe", "target_display": 1}
]
```

### 4. **Test Layouts Before Committing**

1. Create the layout file
2. Use `/screen-config` to verify your setup
3. Activate via `/layouts` command
4. Check that windows move correctly
5. Test deactivation and reactivation

### 5. **Version Control Your Layouts**

Layouts are just JSON files - commit them to Git!

```bash
cd BlinkSwitch/layouts
git add my-coding-setup.json
git commit -m "Add coding setup layout for dual vertical screens"
```

---

## Advanced Tips

### Handling Multiple Identical Applications

If you have multiple Chrome windows and want them on different displays:

```json
{
  "rules": [
    {
      "match_type": "window_title",
      "match_value": "Gmail",
      "target_display": 1,
      "maximize": true
    },
    {
      "match_type": "window_title",
      "match_value": "GitHub",
      "target_display": 2,
      "maximize": true
    }
  ]
}
```

### Sharing Layouts Between Machines

Layouts are portable as long as:
- DISPLAY# positions match (e.g., both machines have vertical as DISPLAY1)
- Orientations match
- Screen counts match

**Resolution differences are OK!** A layout for 1920×1080 works on 2560×1440 if orientation matches.

---

## Migration Guide

### From Old Rules to Layouts

**Old Way** (manually creating rules):
1. Create rule for Chrome → Monitor 1
2. Create rule for VS Code → Monitor 2
3. Manually enable/disable rules when screens change

**New Way** (using layouts):
1. Create `layouts/work.json` with all rules
2. Activate with `/layouts` when at work desk
3. System auto-deactivates when you unplug external monitor
4. Rules automatically restored

### Converting Existing Setup to Layout

1. Export your current rules:
   ```bash
   GET /screenassign/rules
   ```

2. Check your screen config:
   ```bash
   GET /screenassign/screen-config
   ```

3. Create a layout file combining both:
   ```json
   {
     "name": "My Current Setup",
     "screen_requirements": {
       "total_screens": 2,
       "screens": [/* from screen-config */]
     },
     "rules": [/* from /rules endpoint */]
   }
   ```

4. Activate and test!

---

## FAQ

**Q: Can I have multiple layouts active at once?**  
A: No, only one layout can be active at a time. Deactivate the current layout before activating another.

**Q: What happens to my old rules when I activate a layout?**  
A: They're saved and automatically restored when you deactivate the layout.

**Q: Can layouts work with different resolutions?**  
A: Yes! Layouts only care about DISPLAY# and orientation, not resolution.

**Q: What if I plug in a third monitor?**  
A: If your layout requires exactly 2 screens and you have 3, it won't activate. Update `total_screens` or create a new layout.

**Q: Can I edit layout files while the system is running?**  
A: Yes! Changes take effect the next time you activate the layout.

**Q: Do layouts work across different machines?**  
A: Yes, as long as the DISPLAY# numbers and orientations match.

---

## File Locations

- **Layout files:** `BlinkSwitch/layouts/*.json`
- **Example layouts:** Included in distribution
- **Logs:** `BlinkSwitch/logs/screenassign_*.log`
- **Configuration:** `BlinkSwitch/monitors_config.json`

---

## Support

For issues or questions:
1. Check logs in `BlinkSwitch/logs/`
2. Run `/screen-config` to debug screen detection
3. Verify layout JSON syntax at jsonlint.com
4. Create an issue on GitHub with layout file and logs

---

**Happy layout-ing!** 🖥️✨
