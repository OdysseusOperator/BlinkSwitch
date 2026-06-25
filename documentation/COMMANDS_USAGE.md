# BlinkSwitch Commands System

## Overview

The BlinkSwitch window frontend supports two primary modes:

1. **Switch Mode** (default): Normal window selection and switching mode
2. **Command Mode**: Fuzzy-findable commands starting with `/` for system management features

## Modes

### Switch Mode (Default)

This is the normal window selection and switching mode. When you press `Alt+Space`:
- Type to fuzzy search through open windows
- Press `Enter` to switch to the selected window
- Shows "X windows" in the count
- Help text: "Alt+Space to close"

### Command Mode

Access system management features by typing commands starting with `/`.

## Usage

### Accessing Commands

1. **Open BlinkSwitch**: Press `Alt+Space` to open the window frontend (enters switch_mode)
2. **Type a command**: Start typing `/` to enter command mode
3. **Fuzzy search**: Type part of the command name (e.g., `/assign` for monitor assignment)
4. **Execute**: Press `Enter` to execute the selected command

### Available Commands

#### `/assign` - Monitor Assignment

Assign physical monitors to layout slots. The monitor number overlay appears on screen while this view is open.

**Features:**
- List layout slots and connected monitors
- Show numbered monitor overlays for matching digit keys
- Save slot-to-monitor assignments per layout

**Usage:**
1. Type `/assign` in the fuzzy finder
2. Press `Enter` to open the assignment view
3. Navigate slots with `↑` `↓` arrow keys
4. Press `1`-`9` to assign the matching monitor number
5. Press `S` to save or `Esc` to cancel

### Command Mode Indicators

When in **command mode** (typing `/` commands):
- **Query shows**: The command you're typing (e.g., `/assign`)
- **Count shows**: "X commands" instead of "X windows"
- **Help text**: "Type command name | Enter to execute | Esc to close"

When in **switch_mode** (normal window switching):
- **Query shows**: Your search text for windows
- **Count shows**: "X windows"
- **Help text**: "Alt+Space to close"

### Assign View

When inside `/assign`:

- **Title**: "Assign Monitors to Slots"
- **List shows**: Layout slots followed by the monitor legend
- **Screen overlay**: Numbered labels appear centered on each monitor
- **Help text**: "1-9 assign monitor | Up/Down navigate | S save | Esc cancel"

## Technical Details

### Architecture

1. **Command Registry** (`commands.py`):
   - Singleton pattern for global command access
   - Fuzzy search for command names
   - Command execution with context

2. **Assign View** (`commands.py`):
   - Dedicated UI view for slot-to-monitor assignment
   - Digit-driven assignment with `1`-`9`
   - Save or cancel workflow

3. **Window Frontend Integration** (`frontend/frontend-switcher.py`):
   - Detects `/` prefix to enter command mode
   - Routes input to appropriate view
   - Manages view lifecycle

### Adding New Commands

To add a new command:

```python
from commands import get_registry

def my_command_handler(context):
    # Your command logic here
    return result  # Can return a View object

# Register the command
registry = get_registry()
registry.register(
    "mycommand",
    "Description of my command",
    my_command_handler,
    category="Custom"
)
```

## Future Enhancements

Potential future commands:
- `/rules` - Manage application window placement rules
- `/settings` - Configure BlinkSwitch preferences
- `/help` - Show keyboard shortcuts and tips
- `/reload` - Reload configuration without restart
