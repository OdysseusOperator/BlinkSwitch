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

## Dashboard Integration

ScreenAssign integrates with the Dashboard through a REST API. To use it within the Dashboard:

1. Ensure the Dashboard backend (Flask) is running
2. Import and initialize the ScreenAssign API in your Flask app:

```python
from window_stuff.api import setup_api

# Initialize the API with your Flask app
setup_api(app)
```

This will add the following endpoints to your Dashboard backend:

- `GET /screenassign/status`: Get service status
- `POST /screenassign/start`: Start the service
- `POST /screenassign/stop`: Stop the service
- `POST /screenassign/restart`: Restart the service
- `POST /screenassign/apply-rules`: Apply rules immediately
- `GET /screenassign/monitors`: Get all known monitors
- `GET /screenassign/rules`: Get all rules
- `POST /screenassign/rules`: Add/update a rule
- `DELETE /screenassign/rules/<rule_id>`: Delete a rule
- `GET /screenassign/windows`: Get all currently running windows

## Signal File

The service checks for a signal file at `../signalFiles/screenassign.flag`. If this file doesn't exist, the service will pause and not apply any rules. This allows you to easily disable the service temporarily without stopping it.

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
