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
3. **Fuzzy search**: Type part of the command name (e.g., `/mon` for monitors)
4. **Execute**: Press `Enter` to execute the selected command

### Available Commands

#### `/monitors` - Monitor Management

Manage your known monitors (including disconnected ones).

**Features:**
- List all monitors with their resolutions and positions
- Shows PRIMARY and DISCONNECTED status
- Delete old/unused monitors

**Usage:**
1. Type `/monitors` in the fuzzy finder
2. Press `Enter` to open the monitor management view
3. Navigate with `↑` `↓` arrow keys
4. Press `d` to delete the selected monitor
5. Press `Esc` to close the view

**Example workflow:**
```
1. Press Alt+Space
2. Type: /monitors
3. Press Enter
4. Navigate to old disconnected monitor
5. Press 'd' to delete
6. Press Esc to return to window frontend
```

### Command Mode Indicators

When in **command mode** (typing `/` commands):
- **Query shows**: The command you're typing (e.g., `/monitors`)
- **Count shows**: "X commands" instead of "X windows"
- **Help text**: "Type command name | Enter to execute | Esc to close"

When in **switch_mode** (normal window switching):
- **Query shows**: Your search text for windows
- **Count shows**: "X windows"
- **Help text**: "Alt+Space to close"

### Monitor Management View

When inside `/monitors`:

- **Title**: "Monitor Management"
- **List shows**: Monitor name, resolution, position, and status
- **Connected monitors**: Yellow text (active/available)
- **Disconnected monitors**: Gray text (inactive/removed)
- **Help text**: "Press 'd' to delete | Esc to close"

## Technical Details

### Architecture

1. **Command Registry** (`commands.py`):
   - Singleton pattern for global command access
   - Fuzzy search for command names
   - Command execution with context

2. **Monitor Management View** (`commands.py`):
   - Dedicated UI view for monitor list
   - Keyboard-driven deletion with 'd' key
   - Simple navigation with arrow keys

3. **API Integration** (`window_stuff/api.py`):
   - `DELETE /screenassign/monitors/<monitor_id>` endpoint
   - Deletes monitor from configuration

4. **Window Frontend Integration** (`frontend/frontend-switcher.py`):
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
