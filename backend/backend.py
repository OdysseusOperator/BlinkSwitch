import io
import os
import json
import logging
import sys
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, request, Blueprint, Response
from flask_cors import CORS

import ctypes
from typing import Optional, List, Dict, Any

from .service import ScreenAssignService
from .layout_manager import LayoutError

# Setup logging with file output
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR, f"screenassign_api_{datetime.now().strftime('%Y%m%d')}.log"
)

# Configure logging
_stderr_utf8 = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(_stderr_utf8)],
)
api_logger = logging.getLogger("ScreenAssign.API")

# Import tab manager
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from .tab_enumerators import ChromeTabManager

# Create API Blueprint for the ScreenAssign service
screenassign_api = Blueprint("screenassign_api", __name__)

# Service instance (initialized in setup_api function)
service: Optional[ScreenAssignService] = None

# Tab management (initialized in setup_api function)
chrome_tab_manager: Optional[ChromeTabManager] = None
CHROME_COMMAND_TTL = 5.0  # seconds before a queued command is considered stale

chrome_commands: List[Dict[str, Any]] = []
chrome_command_id: List[int] = [0]
chrome_commands_lock = threading.Lock()


def _require_service() -> ScreenAssignService:
    if service is None:
        raise RuntimeError("ScreenAssign service is not initialized")
    return service


def setup_api(app=None, config_path=None):
    """Set up the ScreenAssign API.

    Args:
        app (Flask, optional): Flask application to attach routes to.
            If None, returns a Blueprint.
        config_path (str, optional): Path to config file.
            If None, uses default location.

    Returns:
        Flask or Blueprint: The Flask app or Blueprint with API routes
    """
    global service, chrome_tab_manager

    api_logger.info("=== Initializing ScreenAssign API ===")
    api_logger.info(f"Log file: {LOG_FILE}")

    # Initialize the service
    service = ScreenAssignService(config_path)
    api_logger.info("ScreenAssign service initialized")

    # Initialize tab manager
    chrome_tab_manager = ChromeTabManager(ttl_seconds=10)
    api_logger.info("Tab manager initialized")

    # If app is provided, register the blueprint
    if app:
        app.register_blueprint(screenassign_api, url_prefix="/screenassign")
        return app

    return screenassign_api


@screenassign_api.route("/status", methods=["GET"])
def get_status():
    """Get the current status of the ScreenAssign service."""
    svc = _require_service()
    status = svc.get_status()
    # Ensure we have the fields expected by the frontend
    if "last_run" not in status:
        status["last_run"] = None
    if "rules_applied" not in status:
        status["rules_applied"] = 0
    if "errors" not in status:
        status["errors"] = 0
    return jsonify(status)


@screenassign_api.route("/start", methods=["POST"])
def start_service():
    """Start the ScreenAssign service."""
    svc = _require_service()
    result = svc.start()
    return jsonify({"success": result, "status": svc.get_status()})


@screenassign_api.route("/stop", methods=["POST"])
def stop_service():
    """Stop the ScreenAssign service."""
    svc = _require_service()
    result = svc.stop()
    return jsonify({"success": result, "status": svc.get_status()})


@screenassign_api.route("/restart", methods=["POST"])
def restart_service():
    """Restart the ScreenAssign service."""
    svc = _require_service()
    result = svc.restart()
    return jsonify({"success": result, "status": svc.get_status()})


@screenassign_api.route("/apply-rules", methods=["POST"])
def apply_rules():
    """Apply all rules immediately.

    Required body fields:
      - layout_name (str): name of the layout to apply
      - assignment (dict): slot->identity_key mapping,
            e.g. {"1": "-1920_0_1080_1920", "2": "0_0_1920_1080"}
    """
    data = request.json or {}
    layout_name = data.get("layout_name")
    assignment = data.get("assignment")
    if not layout_name:
        return jsonify({"error": "layout_name is required"}), 400
    if not assignment or not isinstance(assignment, dict):
        return jsonify({"error": "assignment is required (dict mapping slot numbers to identity keys x_y_W_H)"}), 400
    svc = _require_service()
    try:
        results = svc.apply_rules_now(layout_name, assignment)
        return jsonify(results)
    except LayoutError as e:
        return jsonify({"error": str(e)}), 409


@screenassign_api.route("/monitors", methods=["GET"])
def get_monitors():
    """Get all known monitors with runtime DPI information."""
    svc = _require_service()
    svc.monitor_manager.detect_monitors()
    if request.args.get("connected_only") == "true":
        # Return connected monitors with runtime DPI scale
        return jsonify(svc.monitor_manager.get_monitors_with_runtime_info())
    if request.args.get("with_status") == "true":
        # Return all monitors with connection status
        return jsonify(svc.get_monitors_with_status())
    return jsonify(svc.get_monitors())


@screenassign_api.route("/monitors/<monitor_id>", methods=["DELETE"])
def delete_monitor(monitor_id):
    """Delete a monitor by ID."""
    svc = _require_service()
    result = svc.config_manager.delete_monitor(monitor_id)
    return jsonify({"success": result})


@screenassign_api.route("/windows", methods=["GET"])
def get_windows():
    """Get all currently running windows."""
    svc = _require_service()
    return jsonify(svc.get_running_windows())


def _focus_window(hwnd: int) -> None:
    """Best-effort focus/raise a window on Windows."""
    import win32api
    import win32con
    import win32gui
    import win32process

    if hwnd <= 0:
        raise ValueError("Invalid hwnd")

    # Restore if minimized
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        # Continue with best-effort focus even if restore fails
        pass

    # Raise window
    try:
        win32gui.BringWindowToTop(hwnd)
    except Exception:
        pass

    # Windows may block SetForegroundWindow unless thread input is attached.
    try:
        foreground_hwnd = win32gui.GetForegroundWindow()
        fg_thread_id, _ = win32process.GetWindowThreadProcessId(foreground_hwnd)
        target_thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
        current_thread_id = win32api.GetCurrentThreadId()

        windll = getattr(ctypes, "windll", None)
        if windll is None:
            raise RuntimeError("ctypes.windll is not available on this platform")
        user32 = windll.user32

        # Attach current thread to the target and foreground threads.
        if fg_thread_id:
            user32.AttachThreadInput(current_thread_id, fg_thread_id, True)
        if target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, True)

        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetActiveWindow(hwnd)

        if target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)
        if fg_thread_id:
            user32.AttachThreadInput(current_thread_id, fg_thread_id, False)
    except Exception:
        # Fallback attempt
        try:
            import win32gui

            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass


@screenassign_api.route("/focus-window-only", methods=["POST"])
def focus_window_only():
    """Bring a window to foreground WITHOUT applying rules (lightweight).

    This endpoint is optimized for quick focus operations without the overhead
    of rule application. Useful for window switchers that need fast response times.

    Payload:
      - hwnd: number|string (required)
    """
    data = request.json or {}
    hwnd_raw = data.get("hwnd")

    if hwnd_raw is None:
        return jsonify({"error": "hwnd is required"}), 400

    try:
        hwnd = int(hwnd_raw)
    except Exception:
        return jsonify({"error": "hwnd must be an integer"}), 400

    try:
        _focus_window(hwnd)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/health", methods=["GET"])
def health():
    """Basic health probe for WindowSwitcher and dashboards."""
    _require_service()
    return jsonify({"ok": True})


# ============================================================================
# SETTINGS ENDPOINTS
# ============================================================================


@screenassign_api.route("/settings", methods=["GET"])
def get_settings():
    """Get application settings.

    Returns:
        {
            "default_layout": str | null,
            "center_mouse_on_switch": bool
        }
    """
    svc = _require_service()
    settings = svc.config_manager.get_settings()
    return jsonify(settings)


@screenassign_api.route("/settings", methods=["PUT", "PATCH"])
def update_settings():
    """Update application settings.

    Request body (partial updates allowed):
        {
            "default_layout": str | null,
            "center_mouse_on_switch": bool
        }

    Response:
        {"success": true, "settings": {...}}
    """
    svc = _require_service()
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    svc.config_manager.update_settings(data)
    return jsonify({"success": True, "settings": svc.config_manager.get_settings()})


# ============================================================================
# BROWSER TAB ENDPOINTS
# ============================================================================


@screenassign_api.route("/browser-tabs", methods=["POST"])
def receive_browser_tabs():
    """Receive tab data from Chrome extension.

    Request body:
        {
            "chrome_pid": "extension_id",
            "browser_name": "Chrome" | "Edge" | "Vivaldi" | etc,
            "tabs": [{id, windowId, title, url, active, pinned, ...}],
            "timestamp": 1706000000000
        }

    Response:
        {"success": true, "tab_count": 5}
    """
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    chrome_pid = data.get("chrome_pid")
    browser_name = data.get("browser_name", "Chrome")
    tabs = data.get("tabs", [])
    timestamp = data.get("timestamp", int(time.time() * 1000))

    if not chrome_pid:
        return jsonify({"error": "chrome_pid required"}), 400

    if chrome_tab_manager:
        chrome_tab_manager.update_tabs(chrome_pid, tabs, timestamp, browser_name)
        return jsonify({"success": True, "tab_count": len(tabs)})
    else:
        return jsonify({"error": "Tab manager not initialized"}), 503


@screenassign_api.route("/browser-tabs", methods=["GET"])
def get_browser_tabs():
    """Get all browser tabs for window switcher.

    Response:
        {
            "tabs": [{type, source, id, title, url, domain, ...}],
            "count": 5,
            "available": true
        }
    """
    if not chrome_tab_manager:
        return jsonify({"tabs": [], "count": 0, "available": False})

    tabs = chrome_tab_manager.get_tabs()
    return jsonify(
        {
            "tabs": tabs,
            "count": len(tabs),
            "available": chrome_tab_manager.is_available(),
        }
    )


@screenassign_api.route("/windows-and-tabs", methods=["GET"])
def get_windows_and_tabs():
    """Get cached windows and browser tabs (optimized for window switcher).

    This endpoint returns pre-cached window data updated every 2 seconds,
    plus current browser tabs. Designed for fast window switcher performance.

    Response:
        {
            "windows": [...],
            "tabs": [...],
            "cached": true,
            "cache_age_ms": 1234,
            "timestamp": 1234567890.123
        }
    """
    import time

    start = time.time()

    svc = _require_service()
    t1 = time.time()

    # Get cached windows
    cache_data = svc.get_cached_windows_and_tabs()
    t2 = time.time()

    # Get current tabs from tab manager
    tabs = []
    if chrome_tab_manager:
        tabs = chrome_tab_manager.get_tabs()
    t3 = time.time()

    timing_msg = f"/windows-and-tabs: require_svc={1000 * (t1 - start):.1f}ms, get_cache={1000 * (t2 - t1):.1f}ms, get_tabs={1000 * (t3 - t2):.1f}ms, total={1000 * (t3 - start):.1f}ms"
    api_logger.info(timing_msg)
    print(f"[TIMING] {timing_msg}")

    return jsonify(
        {
            "windows": cache_data["windows"],
            "tabs": tabs,
            "cached": True,
            "cache_age_ms": cache_data["age_ms"],
            "timestamp": cache_data["timestamp"],
        }
    )


def _activate_browser_window(exe_name: str, chrome_window_id: Optional[int] = None) -> bool:
    """Activate and focus a browser window by executable name.

    When *chrome_window_id* is provided the function attempts to map it to the
    correct Win32 window by correlating Chrome window-creation order (ascending
    chrome windowId) with Win32 HWND creation order (ascending HWND).  This
    avoids focusing the wrong Edge/Chrome window when multiple browser windows
    are open.

    Args:
        exe_name: Browser executable name (e.g., "msedge.exe", "chrome.exe")
        chrome_window_id: Chrome extension windowId of the target window, if known.

    Returns:
        True if browser window was found and focused, False otherwise
    """
    try:
        svc = _require_service()
        window_manager = svc.window_manager

        all_windows = window_manager.get_all_windows()

        # Collect all Win32 windows belonging to this browser exe, sorted by
        # HWND ascending (a reasonable proxy for creation order).
        browser_windows = sorted(
            [w for w in all_windows if w.get("exe_name") == exe_name],
            key=lambda w: w.get("hwnd", 0),
        )

        if not browser_windows:
            api_logger.warning(f"No window found for {exe_name}")
            return False

        # Default: first window
        target_window = browser_windows[0]

        if chrome_window_id is not None and chrome_tab_manager is not None:
            # Determine the 0-based index of this chrome window among all chrome
            # windows for this browser (sorted by chrome windowId ascending).
            idx = chrome_tab_manager.get_chrome_window_index(chrome_window_id, exe_name)
            if 0 <= idx < len(browser_windows):
                target_window = browser_windows[idx]
                api_logger.info(
                    f"Matched chrome_window_id={chrome_window_id} to Win32 window "
                    f"index {idx} (hwnd={target_window.get('hwnd')})"
                )
            else:
                api_logger.warning(
                    f"chrome_window_id={chrome_window_id} index {idx} out of range "
                    f"({len(browser_windows)} Win32 windows); falling back to first"
                )

        browser_hwnd = target_window.get("hwnd")
        if not browser_hwnd:
            api_logger.warning(f"No hwnd on matched window for {exe_name}")
            return False
        api_logger.info(f"Activating browser window: {exe_name} (hwnd={browser_hwnd})")
        _focus_window(int(browser_hwnd))
        return True

    except Exception as e:
        api_logger.error(f"Error activating browser window: {e}")
        return False


@screenassign_api.route("/activate-tab", methods=["POST"])
def activate_tab():
    """Queue a tab activation command for Chrome extension.

    Request body:
        {"tab_id": "chrome_123" | "edge_456" | etc}

    Response:
        {"success": true, "queued": true}
    """
    data = request.json
    if not data or "tab_id" not in data:
        return jsonify({"error": "tab_id required"}), 400

    tab_id = data["tab_id"]

    if not chrome_tab_manager:
        return jsonify({"error": "Tab manager not initialized"}), 503

    # Look up the tab
    tab = chrome_tab_manager.get_tab_by_id(tab_id)
    if not tab:
        return jsonify({"error": "Tab not found"}), 404

    # Queue the activateTab command for the extension to pick up.
    # Win32 window focus is handled by the frontend process (which owns the
    # foreground) — doing it here from Flask would always fail silently because
    # SetForegroundWindow requires the calling process to be the foreground owner.
    with chrome_commands_lock:
        chrome_command_id[0] += 1
        chrome_commands.append(
            {
                "id": chrome_command_id[0],
                "action": "activateTab",
                "tabId": tab["chrome_tab_id"],
                "windowId": tab["chrome_window_id"],
                "timestamp": time.time(),
            }
        )

    return jsonify({"success": True, "queued": True})


@screenassign_api.route("/chrome-commands", methods=["GET"])
def get_chrome_commands():
    """Get pending commands for Chrome extension (polled every 500ms).

    Stale commands (older than CHROME_COMMAND_TTL seconds) are discarded here
    so a temporarily-offline extension never fires ghost activations on reconnect.

    Response:
        {"commands": [{id, action, tabId, windowId, timestamp}]}
    """
    now = time.time()
    with chrome_commands_lock:
        global chrome_commands
        # Drop commands that are too old
        chrome_commands = [
            c for c in chrome_commands
            if now - c.get("timestamp", 0) < CHROME_COMMAND_TTL
        ]
        return jsonify({"commands": list(chrome_commands)})


@screenassign_api.route("/chrome-commands/<int:cmd_id>", methods=["DELETE"])
def acknowledge_chrome_command(cmd_id):
    """Extension acknowledges command execution.

    Response:
        {"success": true}
    """
    with chrome_commands_lock:
        global chrome_commands
        chrome_commands = [c for c in chrome_commands if c["id"] != cmd_id]

    return jsonify({"success": True})


@screenassign_api.route("/focus-window", methods=["POST"])
def focus_window():
    """Bring a window to foreground and optionally apply rules.

    Payload:
      - hwnd: number|string (required)
      - apply_rules: bool (optional, default true)
      - layout_name: string (required if apply_rules is true)
      - assignment: dict (required if apply_rules is true)
            e.g. {"1": "-1920_0_1080_1920", "2": "0_0_1920_1080"}
    """
    data = request.json or {}
    hwnd_raw = data.get("hwnd")
    apply_rules_flag = data.get("apply_rules", True)
    layout_name = data.get("layout_name")
    assignment = data.get("assignment")

    if hwnd_raw is None:
        return jsonify({"error": "hwnd is required"}), 400

    if apply_rules_flag and not layout_name:
        return jsonify({"error": "layout_name is required when apply_rules is true"}), 400

    if apply_rules_flag and (not assignment or not isinstance(assignment, dict)):
        return jsonify({"error": "assignment is required when apply_rules is true (dict mapping slot numbers to identity keys x_y_W_H)"}), 400

    try:
        hwnd = int(hwnd_raw)
    except Exception:
        return jsonify({"error": "hwnd must be an integer"}), 400

    try:
        _focus_window(hwnd)
        if apply_rules_flag:
            checked_layout_name = str(layout_name)
            results = _require_service().apply_rules_now(checked_layout_name, assignment)  # type: ignore[arg-type]
            return jsonify({"success": True, "rules": results})
        return jsonify({"success": True})
    except LayoutError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/apply-rule-for-window", methods=["POST"])
def apply_rule_for_window():
    """Apply the matching layout rule to a single window.

    Only applies the rule that matches the given window — much faster than
    applying all rules globally. Intended for immediate post-switch rule
    enforcement.

    Payload:
      - hwnd: number|string (required) — window handle to apply rules to
      - layout_name: string (required) — layout whose rules to apply

    Response:
      - matched (bool): whether a rule was found for this window
      - changed (bool): whether any operations were performed
      - operations (list): operations performed (e.g. ["move", "fullscreen"])
      - rule_id (str|null): the matched rule id
      - message (str): human-readable summary
    """
    data = request.json or {}
    hwnd_raw = data.get("hwnd")
    layout_name = data.get("layout_name")
    assignment = data.get("assignment")

    if hwnd_raw is None:
        return jsonify({"error": "hwnd is required"}), 400

    if not layout_name:
        return jsonify({"error": "layout_name is required"}), 400

    if not assignment:
        return jsonify(
            {
                "error": (
                    "assignment is required: provide a dict mapping slot numbers to "
                    "monitor identity keys (x_y_W_H), "
                    "e.g. {\"1\": \"-1920_0_1080_1920\", \"2\": \"0_0_1920_1080\"}"
                )
            }
        ), 400

    try:
        hwnd = int(hwnd_raw)
    except Exception:
        return jsonify({"error": "hwnd must be an integer"}), 400

    try:
        result = _require_service().apply_rules_for_window(hwnd, layout_name, assignment)
        return jsonify(result)
    except LayoutError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/layouts", methods=["GET"])
def get_layouts():
    """Get all available layout files.

    Response:
        [
            {
                "name": "Coding Setup",
                "file_name": "coding.json",
                "file_path": "/path/to/layouts/coding.json",
                "description": "VS Code on vertical, Vivaldi on horizontal",
                "total_screens": 2
            }
        ]
    """
    try:
        svc = _require_service()
        layouts = svc.layout_manager.list_layouts()
        return jsonify(layouts)
    except Exception as e:
        api_logger.error(f"Error listing layouts: {str(e)}")
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/layouts/<layout_name>", methods=["GET"])
def get_layout(layout_name):
    """Get details of a specific layout.

    Response:
        {
            "name": "Coding Setup",
            "description": "...",
            "can_apply": true,
            "reason": "All requirements met",
            "screen_requirements": {...},
            "current_screen_config": [...],
            "rules_count": 2
        }
    """
    try:
        svc = _require_service()
        preview = svc.layout_manager.get_layout_preview(layout_name)
        return jsonify(preview)
    except Exception as e:
        api_logger.error(f"Error getting layout {layout_name}: {str(e)}")
        return jsonify({"error": str(e)}), 404


@screenassign_api.route("/layouts/<layout_name>", methods=["DELETE"])
def delete_layout(layout_name):
    """Delete a layout file.

    Response:
        {
            "success": true,
            "message": "Layout 'coding' deleted successfully"
        }
    """
    try:
        svc = _require_service()
        layout_file = svc.layout_manager.layouts_dir / f"{layout_name}.json"

        if not layout_file.exists():
            return jsonify({"error": f"Layout '{layout_name}' not found"}), 404

        # Delete the file
        layout_file.unlink()
        api_logger.info(f"Deleted layout file: {layout_file}")

        return jsonify(
            {"success": True, "message": f"Layout '{layout_name}' deleted successfully"}
        )
    except Exception as e:
        api_logger.error(f"Error deleting layout {layout_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/layouts", methods=["POST"])
def create_layout():
    """Create a new layout from current screen configuration.

    Payload:
        {
            "name": "My Layout",
            "description": "Optional description"
        }

    Response:
        {
            "success": true,
            "message": "Layout 'My Layout' created successfully",
            "file_name": "my-layout.json",
            "file_path": "/path/to/layouts/my-layout.json"
        }
    """
    data = request.json or {}
    layout_name = data.get("name")
    description = data.get("description", "")

    if not layout_name:
        return jsonify({"error": "name is required"}), 400

    try:
        svc = _require_service()
        result = svc.layout_manager.create_layout_from_current_config(
            layout_name, description
        )

        if result.get("success"):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        api_logger.error(f"Error creating layout: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


@screenassign_api.route("/screen-config", methods=["GET"])
def get_screen_config():
    """Get current screen configuration.

    Returns connected monitors with identity_key fields for use in slot assignment.

    Response:
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
                }
            ]
        }
    """
    try:
        svc = _require_service()
        monitors = svc.monitor_manager.get_monitors_with_runtime_info()
        matcher = svc.layout_manager.matcher
        for m in monitors:
            m["orientation"] = matcher.get_orientation(m["width"], m["height"])
        return jsonify({"monitors": monitors})
    except Exception as e:
        api_logger.error(f"Error getting screen config: {str(e)}")
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/layouts/<layout_name>/rules", methods=["POST"])
def add_rule_to_layout(layout_name):
    """Add a rule to a layout file.

    Payload:
        {
            "match_type": "exe",
            "match_value": "chrome.exe",
            "target_slot": 2,
            "fullscreen": false,
            "maximize": true
        }

    Response:
        {
            "success": true,
            "rule_id": "rule_abc123",
            "message": "Rule added to layout 'coding'"
        }
    """
    data = request.json or {}

    # Validate required fields
    if not data.get("match_type") or not data.get("match_value"):
        return jsonify({"error": "match_type and match_value are required"}), 400

    target_slot = data.get("target_slot")
    if not target_slot:
        return jsonify({"error": "target_slot is required"}), 400

    if not isinstance(target_slot, int) or target_slot < 1:
        return jsonify({"error": "target_slot must be a positive integer"}), 400

    try:
        svc = _require_service()
        layout_file = svc.layout_manager.layouts_dir / f"{layout_name}.json"

        if not layout_file.exists():
            return jsonify({"error": f"Layout '{layout_name}' not found"}), 404

        # Load layout
        with open(layout_file, "r", encoding="utf-8") as f:
            layout_data = json.load(f)

        # Validate target_slot exists in screen_requirements
        required_slots = [
            s["slot"]
            for s in layout_data.get("screen_requirements", {}).get("screens", [])
        ]
        if target_slot not in required_slots:
            return jsonify(
                {
                    "error": f"Slot {target_slot} not in layout requirements. "
                    f"Available slots: {required_slots}"
                }
            ), 400

        # Check if a rule already exists for this window (any match type)
        # Import the matching function
        from .layout_manager import find_matching_rule_for_window

        # Create window_data for matching based on the incoming rule
        window_data = {
            "exe_name": data.get("match_value")
            if data.get("match_type") == "exe"
            else None,
            "title": data.get("match_value")
            if data.get("match_type") == "window_title"
            else None,
            "process_path": data.get("match_value")
            if data.get("match_type") == "process_path"
            else None,
        }

        if "rules" not in layout_data:
            layout_data["rules"] = []

        existing_rule = find_matching_rule_for_window(window_data, layout_data["rules"])

        if existing_rule:
            # UPDATE existing rule
            rule_id = existing_rule["rule_id"]
            for i, rule in enumerate(layout_data["rules"]):
                if rule.get("rule_id") == rule_id:
                    layout_data["rules"][i].update(
                        {
                            "match_type": data.get("match_type"),
                            "match_value": data.get("match_value"),
                            "target_slot": target_slot,
                            "maximize": data.get("maximize", False),
                            "skip_popups": data.get("skip_popups", False),
                        }
                    )
                    layout_data["rules"][i].pop("fullscreen", None)
                    layout_data["rules"][i].pop("target_display", None)  # remove v1 key if present
                    api_logger.info(
                        f"Updated existing rule {rule_id} in layout {layout_name}"
                    )
                    break
            message = f"Rule updated for '{data.get('match_value')}'"
        else:
            # CREATE new rule
            import uuid

            rule_id = f"rule_{uuid.uuid4().hex[:8]}"

            rule = {
                "rule_id": rule_id,
                "match_type": data.get("match_type"),
                "match_value": data.get("match_value"),
                "target_slot": target_slot,
                "maximize": data.get("maximize", False),
                "skip_popups": data.get("skip_popups", False),
            }

            layout_data["rules"].append(rule)
            api_logger.info(f"Added new rule {rule_id} to layout {layout_name}")
            message = f"Rule added to layout '{layout_name}'"

        # Save layout file
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)

        api_logger.info(f"Added rule {rule_id} to layout {layout_name}")

        return jsonify(
            {
                "success": True,
                "rule_id": rule_id,
                "message": message,
            }
        )
    except Exception as e:
        api_logger.error(f"Error adding rule to layout {layout_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/layouts/<layout_name>/rules/<rule_id>", methods=["DELETE"])
def delete_rule_from_layout(layout_name, rule_id):
    """Delete a rule from a layout file.

    Path Parameters:
        layout_name: Name of the layout (without .json extension)
        rule_id: ID of the rule to delete

    Response:
        {
            "success": true,
            "message": "Rule deleted from layout 'coding'"
        }
    """
    try:
        svc = _require_service()
        layout_file = svc.layout_manager.layouts_dir / f"{layout_name}.json"

        if not layout_file.exists():
            return jsonify({"error": f"Layout '{layout_name}' not found"}), 404

        # Load layout
        with open(layout_file, "r", encoding="utf-8") as f:
            layout_data = json.load(f)

        # Find and remove rule
        rules = layout_data.get("rules", [])
        original_count = len(rules)
        layout_data["rules"] = [r for r in rules if r.get("rule_id") != rule_id]

        if len(layout_data["rules"]) == original_count:
            return jsonify({"error": f"Rule '{rule_id}' not found"}), 404

        # Save layout file
        with open(layout_file, "w", encoding="utf-8") as f:
            json.dump(layout_data, f, indent=2, ensure_ascii=False)

        api_logger.info(f"Deleted rule {rule_id} from layout {layout_name}")

        return jsonify(
            {"success": True, "message": f"Rule deleted from layout '{layout_name}'"}
        )

    except Exception as e:
        api_logger.error(f"Error deleting rule from layout {layout_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500


@screenassign_api.route("/ui", methods=["GET"])
def screen_assign_ui():
    """Endpoint to load the ScreenAssign management UI."""
    from flask import Response

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ScreenAssign Management</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: 'Roboto', Arial, sans-serif;
                margin: 0;
                padding: 20px;
                color: #333;
            }
            h1 {
                color: #1976d2;
                margin-bottom: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            .card {
                background: white;
                border-radius: 4px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .status {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 4px;
                color: white;
                font-weight: bold;
            }
            .running {
                background-color: #4caf50;
            }
            .paused {
                background-color: #ff9800;
            }
            .stopped {
                background-color: #f44336;
            }
            button {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                margin-right: 8px;
            }
            button:hover {
                background: #1565c0;
            }
            button:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                text-align: left;
                padding: 8px;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f5f5f5;
            }
            .loading {
                text-align: center;
                padding: 20px;
            }
            .error {
                color: #f44336;
                padding: 10px;
            }
            .monitor-card {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 15px;
                margin-bottom: 15px;
            }
            .monitor-card.connected {
                border-color: #4caf50;
            }
            .flex-space-between {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .tabs {
                display: flex;
                margin-bottom: 20px;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                border-bottom: 2px solid transparent;
            }
            .tab.active {
                border-bottom: 2px solid #1976d2;
                font-weight: bold;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .actions {
                margin-top: 20px;
                display: flex;
                justify-content: flex-end;
            }
            .form-row {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }
            select, input {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                justify-content: center;
                align-items: center;
            }
            .modal-content {
                background: white;
                border-radius: 4px;
                padding: 20px;
                width: 500px;
                max-width: 90%;
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            .modal-header h2 {
                margin: 0;
            }
            .close {
                font-size: 24px;
                cursor: pointer;
                background: none;
                border: none;
                color: #666;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>ScreenAssign Management</h1>
            
            <div class="card" id="statusCard">
                <h2>Status</h2>
                <div id="statusLoading" class="loading">Loading status...</div>
                <div id="statusContent" style="display: none;">
                    <div class="flex-space-between">
                        <div>
                            <p><strong>Status:</strong> <span id="statusText" class="status"></span></p>
                            <p><strong>Last Run:</strong> <span id="lastRun"></span></p>
                            <p><strong>Rules Applied:</strong> <span id="rulesApplied"></span></p>
                            <p><strong>Errors:</strong> <span id="errors"></span></p>
                        </div>
                        <div>
                            <button id="startBtn">Start</button>
                            <button id="stopBtn">Stop</button>
                            <button id="applyRulesBtn">Apply Rules</button>
                            <button id="refreshStatusBtn">Refresh</button>
                        </div>
                    </div>
                </div>
                <div id="statusError" class="error" style="display: none;"></div>
            </div>
            
            <div class="card">
                <div class="tabs">
                    <div class="tab active" data-tab="rules">Rules</div>
                    <div class="tab" data-tab="monitors">Monitors</div>
                    <div class="tab" data-tab="windows">Windows</div>
                </div>
                
                <div id="rulesTab" class="tab-content active">
                    <div id="rulesLoading" class="loading">Loading rules...</div>
                    <div id="rulesContent" style="display: none;">
                        <table id="rulesTable">
                            <thead>
                                <tr>
                                    <th>Match Type</th>
                                    <th>Match Value</th>
                                    <th>Target Monitor</th>
                                    <th>Window State</th>
                                    <th>Enabled</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="rulesList"></tbody>
                        </table>
                        
                        <div class="actions">
                            <button id="addRuleBtn">Add New Rule</button>
                        </div>
                    </div>
                    <div id="rulesError" class="error" style="display: none;"></div>
                </div>
                
                <div id="monitorsTab" class="tab-content">
                    <div id="monitorsLoading" class="loading">Loading monitors...</div>
                    <div id="monitorsContent" style="display: none;">
                        <div id="monitorsList"></div>
                        
                        <div class="actions">
                            <button id="refreshMonitorsBtn">Refresh Monitors</button>
                        </div>
                    </div>
                    <div id="monitorsError" class="error" style="display: none;"></div>
                </div>
                
                <div id="windowsTab" class="tab-content">
                    <div id="windowsLoading" class="loading">Loading windows...</div>
                    <div id="windowsContent" style="display: none;">
                        <table id="windowsTable">
                            <thead>
                                <tr>
                                    <th>Title</th>
                                    <th>Application</th>
                                    <th>Monitor</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="windowsList"></tbody>
                        </table>
                        
                        <div class="actions">
                            <button id="refreshWindowsBtn">Refresh Windows</button>
                        </div>
                    </div>
                    <div id="windowsError" class="error" style="display: none;"></div>
                </div>
            </div>
        </div>
        
        <!-- Add Rule Modal -->
        <div class="modal" id="addRuleModal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Add New Rule</h2>
                    <button class="close" id="closeAddRuleModal">&times;</button>
                </div>
                <form id="addRuleForm">
                    <div class="form-row">
                        <label for="matchType">Match Type:</label>
                        <select id="matchType" required>
                            <option value="exe">Application (.exe)</option>
                            <option value="window_title">Window Title</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label for="matchValue">Match Value:</label>
                        <select id="matchValue" required>
                            <option value="">Select...</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label for="targetMonitor">Target Monitor:</label>
                        <select id="targetMonitor" required>
                            <option value="">Select...</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label for="windowState">Window State:</label>
                        <select id="windowState" required>
                            <option value="normal">Normal</option>
                            <option value="maximize" selected>Maximized</option>
                            <option value="fullscreen">Fullscreen</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label>
                            <input type="checkbox" id="enabledRule" checked>
                            Enabled
                        </label>
                    </div>
                    <div class="actions">
                        <button type="button" id="cancelAddRuleBtn">Cancel</button>
                        <button type="submit">Save Rule</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            // Helper function to format dates
            function formatDate(dateString) {
                if (!dateString) return 'Never';
                return new Date(dateString).toLocaleString();
            }
            
            // Helper function to show a section and hide loading/error states
            function showSection(section, isLoading = false, error = null) {
                const loadingEl = document.getElementById(`${section}Loading`);
                const contentEl = document.getElementById(`${section}Content`);
                const errorEl = document.getElementById(`${section}Error`);
                
                if (isLoading) {
                    loadingEl.style.display = 'block';
                    contentEl.style.display = 'none';
                    errorEl.style.display = 'none';
                } else if (error) {
                    loadingEl.style.display = 'none';
                    contentEl.style.display = 'none';
                    errorEl.style.display = 'block';
                    errorEl.textContent = `Error: ${error}`;
                } else {
                    loadingEl.style.display = 'none';
                    contentEl.style.display = 'block';
                    errorEl.style.display = 'none';
                }
            }
            
            // Global state
            const state = {
                monitors: [],
                rules: [],
                windows: [],
                monitorMap: {},
                appNames: [],
                windowTitles: []
            };
            
            // Load status
            async function loadStatus() {
                showSection('status', true);
                try {
                    const response = await fetch('/status');
                    if (!response.ok) throw new Error('Network response was not ok');
                    const data = await response.json();
                    
                    // Update status display
                    const statusText = document.getElementById('statusText');
                    const lastRun = document.getElementById('lastRun');
                    const rulesApplied = document.getElementById('rulesApplied');
                    const errors = document.getElementById('errors');
                    
                    statusText.textContent = data.status;
                    lastRun.textContent = formatDate(data.last_run);
                    rulesApplied.textContent = data.rules_applied || '0';
                    errors.textContent = data.errors || '0';
                    
                    // Set status class
                    statusText.className = 'status';
                    if (data.status === 'running') {
                        statusText.classList.add('running');
                    } else if (data.status === 'paused') {
                        statusText.classList.add('paused');
                    } else {
                        statusText.classList.add('stopped');
                    }
                    
                    // Update button states
                    document.getElementById('startBtn').disabled = data.status === 'running';
                    document.getElementById('stopBtn').disabled = data.status === 'stopped';
                    document.getElementById('applyRulesBtn').disabled = data.status !== 'running';
                    
                    showSection('status', false);
                } catch (error) {
                    showSection('status', false, error.message);
                }
            }
            
            // Load monitors
            async function loadMonitors() {
                showSection('monitors', true);
                try {
                    const response = await fetch('/monitors');
                    if (!response.ok) throw new Error('Network response was not ok');
                    
                    const statusResponse = await fetch('/status');
                    const statusData = await statusResponse.json();
                    
                    const monitors = await response.json();
                    state.monitors = monitors;
                    
                    // Update monitor map
                    state.monitorMap = {};
                    monitors.forEach(m => state.monitorMap[m.id] = m.name);
                    
                    const monitorsList = document.getElementById('monitorsList');
                    monitorsList.innerHTML = '';
                    
                    if (monitors.length === 0) {
                        monitorsList.innerHTML = '<p>No monitors detected yet.</p>';
                    } else {
                        // Get connected monitor IDs
                        const connectedMonitors = [];
                        if (statusData.monitors) {
                            statusData.monitors.forEach(m => connectedMonitors.push(m.id));
                        }
                        
                        // Display each monitor
                        monitors.forEach(monitor => {
                            const isConnected = connectedMonitors.includes(monitor.id);
                            const monitorEl = document.createElement('div');
                            monitorEl.className = `monitor-card ${isConnected ? 'connected' : ''}`;
                            
                            monitorEl.innerHTML = `
                                <div class="flex-space-between">
                                    <h3>${monitor.name}</h3>
                                    <span>${isConnected ? 'Connected' : 'Disconnected'}</span>
                                </div>
                                <p><strong>Resolution:</strong> ${monitor.width}×${monitor.height}</p>
                                <p><strong>Position:</strong> (${monitor.x}, ${monitor.y})</p>
                                <p><strong>Primary:</strong> ${monitor.is_primary ? 'Yes' : 'No'}</p>
                                <p><strong>First Detected:</strong> ${formatDate(monitor.first_detected)}</p>
                      <p><strong>Last Connected:</strong> n/a</p>
                            `;
                            
                            monitorsList.appendChild(monitorEl);
                        });
                        
                        // Update monitor selector in add rule form
                        const monitorSelector = document.getElementById('targetMonitor');
                        monitorSelector.innerHTML = '<option value="">Select...</option>';
                        monitors.forEach(monitor => {
                            const option = document.createElement('option');
                            option.value = monitor.id;
                            option.textContent = `${monitor.name} ${connectedMonitors.includes(monitor.id) ? '' : '(Disconnected)'}`;
                            monitorSelector.appendChild(option);
                        });
                    }
                    
                    showSection('monitors', false);
                } catch (error) {
                    showSection('monitors', false, error.message);
                }
            }
            
            // Load rules
            async function loadRules() {
                showSection('rules', true);
                try {
                    const response = await fetch('/rules');
                    if (!response.ok) throw new Error('Network response was not ok');
                    
                    const rules = await response.json();
                    state.rules = rules;
                    
                    const rulesList = document.getElementById('rulesList');
                    rulesList.innerHTML = '';
                    
                    if (rules.length === 0) {
                        const tr = document.createElement('tr');
                        tr.innerHTML = '<td colspan="6" style="text-align: center;">No rules configured yet.</td>';
                        rulesList.appendChild(tr);
                    } else {
                        // Display each rule
                        rules.forEach(rule => {
                            const tr = document.createElement('tr');
                            
                            // Determine window state
                            let windowState = 'Normal';
                            if (rule.fullscreen) windowState = 'Fullscreen';
                            else if (rule.maximize) windowState = 'Maximized';
                            
                            // Monitor name
                            const monitorName = state.monitorMap[rule.target_monitor_id] || 'Unknown Monitor';
                            
                            tr.innerHTML = `
                                <td>${rule.match_type === 'exe' ? 'Application' : 'Window Title'}</td>
                                <td>${rule.match_value}</td>
                                <td>${monitorName}</td>
                                <td>${windowState}</td>
                                <td>${rule.enabled ? 'Yes' : 'No'}</td>
                                <td>
                                    <button class="delete-rule" data-id="${rule.rule_id}">Delete</button>
                                </td>
                            `;
                            
                            rulesList.appendChild(tr);
                        });
                        
                        // Add event listeners to delete buttons
                        const deleteButtons = document.querySelectorAll('.delete-rule');
                        deleteButtons.forEach(button => {
                            button.addEventListener('click', async (e) => {
                                const ruleId = e.target.getAttribute('data-id');
                                if (confirm('Are you sure you want to delete this rule?')) {
                                    try {
                                        const response = await fetch(`/rules/${ruleId}`, {
                                            method: 'DELETE'
                                        });
                                        if (!response.ok) throw new Error('Network response was not ok');
                                        loadRules();
                                    } catch (error) {
                                        alert(`Error deleting rule: ${error.message}`);
                                    }
                                }
                            });
                        });
                    }
                    
                    showSection('rules', false);
                } catch (error) {
                    showSection('rules', false, error.message);
                }
            }
            
            // Load windows
            async function loadWindows() {
                showSection('windows', true);
                try {
                    const response = await fetch('/windows');
                    if (!response.ok) throw new Error('Network response was not ok');
                    
                    const windows = await response.json();
                    state.windows = windows;
                    
                    // Extract unique app names and window titles
                    state.appNames = [...new Set(windows.map(w => w.app_name).filter(Boolean))];
                    state.windowTitles = [...new Set(windows.map(w => w.title).filter(Boolean))];
                    
                    const windowsList = document.getElementById('windowsList');
                    windowsList.innerHTML = '';
                    
                    if (windows.length === 0) {
                        const tr = document.createElement('tr');
                        tr.innerHTML = '<td colspan="4" style="text-align: center;">No windows detected.</td>';
                        windowsList.appendChild(tr);
                    } else {
                        // Display each window
                        windows.forEach(window => {
                            const tr = document.createElement('tr');
                            
                            // Monitor name
                            const monitorName = state.monitorMap[window.monitor_id] || 'Unknown';
                            
                            tr.innerHTML = `
                                <td>${window.title}</td>
                                <td>${window.app_name || 'Unknown'}</td>
                                <td>${monitorName}</td>
                                <td>
                                    <button class="create-rule-exe" data-exe="${window.app_name}">Rule by App</button>
                                    <button class="create-rule-title" data-title="${window.title}">Rule by Title</button>
                                </td>
                            `;
                            
                            windowsList.appendChild(tr);
                        });
                        
                        // Add event listeners to create rule buttons
                        const createRuleExeButtons = document.querySelectorAll('.create-rule-exe');
                        createRuleExeButtons.forEach(button => {
                            button.addEventListener('click', (e) => {
                                const exe = e.target.getAttribute('data-exe');
                                openAddRuleModal('exe', exe);
                            });
                        });
                        
                        const createRuleTitleButtons = document.querySelectorAll('.create-rule-title');
                        createRuleTitleButtons.forEach(button => {
                            button.addEventListener('click', (e) => {
                                const title = e.target.getAttribute('data-title');
                                openAddRuleModal('window_title', title);
                            });
                        });
                        
                        // Update match value selectors
                        updateMatchValueSelector();
                    }
                    
                    showSection('windows', false);
                } catch (error) {
                    showSection('windows', false, error.message);
                }
            }
            
            // Update match value selector based on match type
            function updateMatchValueSelector() {
                const matchType = document.getElementById('matchType').value;
                const matchValue = document.getElementById('matchValue');
                
                // Clear existing options
                matchValue.innerHTML = '<option value="">Select...</option>';
                
                // Add options based on type
                const options = matchType === 'exe' ? state.appNames : state.windowTitles;
                options.forEach(value => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value;
                    matchValue.appendChild(option);
                });
            }
            
            // Open add rule modal
            function openAddRuleModal(matchType = 'exe', matchValue = '') {
                // Set initial values
                document.getElementById('matchType').value = matchType;
                updateMatchValueSelector();
                
                // Set match value if provided
                if (matchValue) {
                    const matchValueSelect = document.getElementById('matchValue');
                    // Add the value if it doesn't exist
                    let exists = false;
                    for (let i = 0; i < matchValueSelect.options.length; i++) {
                        if (matchValueSelect.options[i].value === matchValue) {
                            exists = true;
                            break;
                        }
                    }
                    
                    if (!exists) {
                        const option = document.createElement('option');
                        option.value = matchValue;
                        option.textContent = matchValue;
                        matchValueSelect.appendChild(option);
                    }
                    
                    matchValueSelect.value = matchValue;
                }
                
                // Show modal
                document.getElementById('addRuleModal').style.display = 'flex';
            }
            
            // Close add rule modal
            function closeAddRuleModal() {
                document.getElementById('addRuleModal').style.display = 'none';
            }
            
            // Tab switching
            function setupTabs() {
                const tabs = document.querySelectorAll('.tab');
                tabs.forEach(tab => {
                    tab.addEventListener('click', () => {
                        // Update active tab
                        tabs.forEach(t => t.classList.remove('active'));
                        tab.classList.add('active');
                        
                        // Update active content
                        const tabContents = document.querySelectorAll('.tab-content');
                        tabContents.forEach(content => content.classList.remove('active'));
                        
                        const tabName = tab.getAttribute('data-tab');
                        document.getElementById(`${tabName}Tab`).classList.add('active');
                        
                        // Load content if needed
                        if (tabName === 'monitors') {
                            loadMonitors();
                        } else if (tabName === 'rules') {
                            loadRules();
                        } else if (tabName === 'windows') {
                            loadWindows();
                        }
                    });
                });
            }
            
            // Initialize
            document.addEventListener('DOMContentLoaded', () => {
                // Set up event listeners for service control
                document.getElementById('startBtn').addEventListener('click', async () => {
                    try {
                        const response = await fetch('/start', { method: 'POST' });
                        if (!response.ok) throw new Error('Failed to start service');
                        loadStatus();
                    } catch (error) {
                        alert(`Error starting service: ${error.message}`);
                    }
                });
                
                document.getElementById('stopBtn').addEventListener('click', async () => {
                    try {
                        const response = await fetch('/stop', { method: 'POST' });
                        if (!response.ok) throw new Error('Failed to stop service');
                        loadStatus();
                    } catch (error) {
                        alert(`Error stopping service: ${error.message}`);
                    }
                });
                
                document.getElementById('applyRulesBtn').addEventListener('click', async () => {
                    try {
                        const response = await fetch('/apply-rules', { method: 'POST' });
                        if (!response.ok) throw new Error('Failed to apply rules');
                        loadStatus();
                    } catch (error) {
                        alert(`Error applying rules: ${error.message}`);
                    }
                });
                
                document.getElementById('refreshStatusBtn').addEventListener('click', loadStatus);
                document.getElementById('refreshMonitorsBtn').addEventListener('click', loadMonitors);
                document.getElementById('refreshWindowsBtn').addEventListener('click', loadWindows);
                
                // Set up add rule modal
                document.getElementById('addRuleBtn').addEventListener('click', () => openAddRuleModal());
                document.getElementById('closeAddRuleModal').addEventListener('click', closeAddRuleModal);
                document.getElementById('cancelAddRuleBtn').addEventListener('click', closeAddRuleModal);
                
                // Match type change handler
                document.getElementById('matchType').addEventListener('change', updateMatchValueSelector);
                
                // Add rule form submission
                document.getElementById('addRuleForm').addEventListener('submit', async (e) => {
                    e.preventDefault();
                    
                    const matchType = document.getElementById('matchType').value;
                    const matchValue = document.getElementById('matchValue').value;
                    const targetMonitorId = document.getElementById('targetMonitor').value;
                    const windowState = document.getElementById('windowState').value;
                    const enabled = document.getElementById('enabledRule').checked;
                    
                    if (!matchValue || !targetMonitorId) {
                        alert('Please fill all required fields');
                        return;
                    }
                    
                    try {
                        // Create rule object
                        const rule = {
                            match_type: matchType,
                            match_value: matchValue,
                            target_monitor_id: targetMonitorId,
                            fullscreen: windowState === 'fullscreen',
                            maximize: windowState === 'maximize',
                            enabled: enabled
                        };
                        
                        const response = await fetch('/rules', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(rule)
                        });
                        
                        if (!response.ok) throw new Error('Failed to add rule');
                        
                        closeAddRuleModal();
                        loadRules();
                    } catch (error) {
                        alert(`Error adding rule: ${error.message}`);
                    }
                });
                
                // Set up tabs
                setupTabs();
                
                // Load initial data
                loadStatus();
                loadRules();
            });
        </script>
    </body>
    </html>
    """

    return Response(html, mimetype="text/html")


# If run directly, start a Flask server
if __name__ == "__main__" or __name__ == "backend.backend":
    from flask import Flask
    import sys

    # Set up logging
    _stdout_utf8 = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(_stdout_utf8)],
    )

    # Create Flask app
    app = Flask(__name__)

    # Enable CORS for all routes
    CORS(app, resources={r"/*": {"origins": "*"}})

    # Set up API
    setup_api(app)

    # Start the service
    _require_service().start()

    # If this is the main module (not imported), run the app
    if __name__ == "__main__":
        print("Starting ScreenAssign API server at http://localhost:5555")
        app.run(host="127.0.0.1", port=5555, debug=True)
