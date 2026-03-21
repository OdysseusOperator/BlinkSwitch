import ctypes
import json
import os
import re
import requests
import sys
import threading
import time
import logging
from typing import Any, Optional
from datetime import datetime

# Import command system
from .commands import (
    get_registry,
    register_builtin_commands,
    AssignView,
    MonitorManagementView,
    LayoutManagementView,
    WindowsView,
    WindowDetailsView,
    SettingsView,
)
from .assignment import load_assignments, save_assignments
from .colors import (
    ACCENT_HIGHLIGHT,
    ACCENT_SELECTION,
    BACKGROUND,
    DIVIDER,
    INPUT_BACKGROUND,
    INPUT_BORDER,
    SCROLLBAR_HANDLE,
    SCROLLBAR_TRACK,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# Tab API configuration
TABS_API_URL = "http://127.0.0.1:5555/screenassign"  # Use IP instead of localhost for faster connection
TABS_API_TIMEOUT = 1.0  # Fast timeout - don't block UI

# Create persistent HTTP session for fast requests (avoids connection overhead)
_http_session = requests.Session()

# Setup logging - create logger manually to ensure file writing works
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(
    LOG_DIR, f"window_switcher_{datetime.now().strftime('%Y%m%d')}.log"
)


# Create logger
logger = logging.getLogger("WindowSwitcher")
logger.setLevel(logging.DEBUG)

# Create formatters and handlers
formatter = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")

# File handler - force flush after every write
file_handler = logging.FileHandler(LOG_FILE, mode="a")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
# Force immediate flush
file_handler.flush()

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Test that logging works
logger.info(f"=== Logger initialized, writing to: {LOG_FILE} ===")


def fetch_tabs_from_api() -> list[dict[str, Any]]:
    """Fetch browser tabs from Flask API.

    DEPRECATED: Use fetch_windows_and_tabs_cached() instead for better performance.
    """
    try:
        response = requests.get(
            f"{TABS_API_URL}/browser-tabs", timeout=TABS_API_TIMEOUT
        )
        if response.ok:
            data = response.json()
            return data.get("tabs", [])
    except Exception as e:
        # Silent fail - API might not be running
        print(f"Tab API unavailable: {e}")
    return []


def fetch_monitors_with_dpi() -> list[dict[str, Any]]:
    """Fetch monitor information with DPI scales from ScreenAssign API.

    Returns:
        list: List of monitor dicts with dpi_scale, position, size, etc.
    """
    try:
        response = _http_session.get(
            "http://127.0.0.1:5555/screenassign/monitors?connected_only=true",
            timeout=0.5,
        )
        if response.ok:
            monitors = response.json()
            logger.info(f"Fetched {len(monitors)} monitors with DPI info")
            for mon in monitors:
                logger.debug(
                    f"  Monitor {mon['id']}: pos=({mon['x']},{mon['y']}), "
                    f"size=({mon['width']}x{mon['height']}), dpi_scale={mon.get('dpi_scale', 1.0)}"
                )
            return monitors
    except Exception as e:
        logger.warning(f"Failed to fetch monitors: {e}")

    return []


def fetch_windows_and_tabs_cached() -> dict[str, Any]:
    """Fetch both windows and tabs from single cached endpoint (FAST).

    This uses the ScreenAssign service's pre-cached window data,
    updated every 2 seconds in the background. Much faster than
    enumerating windows on-demand.

    Returns:
        dict: {
            "windows": list,
            "tabs": list,
            "cached": bool,
            "cache_age_ms": int
        }
    """
    import time

    start = time.time()

    try:
        response = _http_session.get(
            f"{TABS_API_URL}/windows-and-tabs",
            timeout=0.5,  # Faster timeout - should be instant from cache
        )
        elapsed_ms = (time.time() - start) * 1000

        if response.ok:
            data = response.json()
            logger.info(
                f"Fetched from cache in {elapsed_ms:.0f}ms (cache age: {data.get('cache_age_ms', 0)}ms, windows: {len(data.get('windows', []))})"
            )
            return data
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        logger.warning(f"Cache API unavailable after {elapsed_ms:.0f}ms: {e}")

    # If API is unavailable, return empty result
    logger.warning("API unavailable - cannot fetch windows without backend")
    result = {
        "windows": [],
        "tabs": [],
        "cached": False,
        "cache_age_ms": 0,
    }
    logger.info(f"Fallback completed in {fallback_ms:.0f}ms")
    return result


def activate_tab_via_api(tab_id: str) -> bool:
    """Request tab activation via API (queues Chrome command only, no Win32 focus)."""
    try:
        response = requests.post(
            f"{TABS_API_URL}/activate-tab",
            json={"tab_id": tab_id},
            timeout=TABS_API_TIMEOUT,
        )
        return response.ok and response.json().get("success", False)
    except Exception as e:
        print(f"Tab activate error: {e}")
    return False


def find_browser_hwnd(tab: dict[str, Any], all_windows: list[dict[str, Any]]) -> Optional[int]:
    """Return the Win32 HWND for the browser window that owns *tab*.

    Uses the same creation-order heuristic as the backend:
    - Collect all Win32 window entries for the browser exe (sorted by hwnd ascending).
    - Collect all unique chrome windowIds for that exe (sorted ascending).
    - The index of tab's chrome_window_id in the sorted chrome list maps to the
      same index in the sorted Win32 list.

    Falls back to the first matching window if the mapping can't be resolved.
    Returns None if no window for that exe is found at all.
    """
    exe_name = tab.get("exe_name", "")
    chrome_window_id = tab.get("chrome_window_id")

    # All Win32 windows for this browser, sorted by hwnd (creation-order proxy)
    browser_wins = sorted(
        [w for w in all_windows if w.get("type") != "tab" and w.get("exe_name") == exe_name],
        key=lambda w: w.get("hwnd", 0),
    )
    if not browser_wins:
        return None

    if chrome_window_id is None or len(browser_wins) == 1:
        return browser_wins[0].get("hwnd")

    # All unique chrome windowIds for this exe across all tabs, sorted ascending
    chrome_win_ids: list[int] = sorted({
        int(t["chrome_window_id"])
        for t in all_windows
        if t.get("type") == "tab" and t.get("exe_name") == exe_name
        and t.get("chrome_window_id") is not None
    })

    try:
        idx = chrome_win_ids.index(chrome_window_id)
    except ValueError:
        idx = 0

    idx = min(idx, len(browser_wins) - 1)
    return browser_wins[idx].get("hwnd")


def fetch_layouts() -> list[dict[str, Any]]:
    """Fetch available layouts from API."""
    try:
        response = _http_session.get(
            f"{TABS_API_URL}/layouts",
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            layouts = response.json()
            logger.info(f"Fetched {len(layouts)} layouts")
            return layouts
    except Exception as e:
        logger.warning(f"Failed to fetch layouts: {e}")
    return []


def fetch_screen_config() -> dict[str, Any]:
    """Fetch current screen configuration from API."""
    try:
        response = _http_session.get(
            f"{TABS_API_URL}/screen-config",
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            config = response.json()
            logger.info(f"Fetched screen config: {len(config.get('monitors', []))} monitors")
            return config
    except Exception as e:
        logger.warning(f"Failed to fetch screen config: {e}")
    return {"monitors": []}


def fetch_layout_data(name: str) -> Optional[dict[str, Any]]:
    """Fetch full layout data dict (including 'data' key) from GET /layouts/<name>."""
    try:
        response = _http_session.get(
            f"{TABS_API_URL}/layouts/{name}",
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            return response.json()
    except Exception as e:
        logger.warning(f"Failed to fetch layout data for '{name}': {e}")
    return None


def fetch_settings() -> dict[str, Any]:
    """Fetch application settings from API."""
    try:
        response = _http_session.get(
            f"{TABS_API_URL}/settings",
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            settings = response.json()
            logger.info(f"Fetched settings: {settings}")
            return settings
    except Exception as e:
        logger.warning(f"Failed to fetch settings: {e}")
    return {"default_layout": None, "center_mouse_on_switch": False}


def update_settings(settings_dict: dict[str, Any]) -> dict[str, Any]:
    """Update application settings via API."""
    try:
        response = _http_session.put(
            f"{TABS_API_URL}/settings",
            json=settings_dict,
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            result = response.json()
            logger.info(f"Settings updated: {result}")
            return result
        else:
            error_msg = (
                response.json().get("error", "Unknown error")
                if response.text
                else "Request failed"
            )
            logger.error(f"Failed to update settings: {error_msg}")
            return {"success": False, "error": error_msg}
    except Exception as e:
        logger.error(f"Settings update error: {e}")
        return {"success": False, "error": str(e)}


def fetch_windows() -> list[dict[str, Any]]:
    """Fetch all windows from API."""
    try:
        response = _http_session.get(
            f"{TABS_API_URL}/windows",
            timeout=TABS_API_TIMEOUT,
        )
        if response.ok:
            windows = response.json()
            logger.info(f"Fetched {len(windows)} windows")
            return windows
    except Exception as e:
        logger.warning(f"Failed to fetch windows: {e}")
    return []


def focus_window_with_retry(
    hwnd: int, max_attempts: int = 20, retry_delay_s: float = 0.05
) -> bool:
    """Focus a window with retry loop - ensures focus succeeds.

    This is the unified focus method used for both opening Screeny and selecting windows.
    Returns True if focus was achieved, False otherwise.
    """
    if hwnd <= 0:
        return False

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        for attempt in range(max_attempts):
            # Check if we already have focus
            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd == hwnd:
                print(f"Focus achieved for hwnd={hwnd} after {attempt + 1} attempts")
                return True

            # Try to focus
            try:
                SW_RESTORE = 9
                user32.ShowWindow(hwnd, SW_RESTORE)
                user32.BringWindowToTop(hwnd)

                # Attach thread input to avoid Windows foreground restrictions
                fg_pid = ctypes.c_uint(0)
                target_pid = ctypes.c_uint(0)
                fg_thread = user32.GetWindowThreadProcessId(
                    fg_hwnd, ctypes.byref(fg_pid)
                )
                target_thread = user32.GetWindowThreadProcessId(
                    hwnd, ctypes.byref(target_pid)
                )
                current_thread = kernel32.GetCurrentThreadId()

                if fg_thread:
                    user32.AttachThreadInput(current_thread, fg_thread, True)
                if target_thread:
                    user32.AttachThreadInput(current_thread, target_thread, True)

                user32.SetForegroundWindow(hwnd)
                user32.SetActiveWindow(hwnd)

                if target_thread:
                    user32.AttachThreadInput(current_thread, target_thread, False)
                if fg_thread:
                    user32.AttachThreadInput(current_thread, fg_thread, False)
            except Exception as e:
                print(f"Focus attempt {attempt + 1} error: {e}")

            time.sleep(retry_delay_s)

        print(
            f"Warning: Could not achieve focus for hwnd={hwnd} after {max_attempts} attempts"
        )
        return False
    except Exception as e:
        print(f"Focus window error: {e}")
        return False


def focus_window_async(hwnd: int) -> None:
    """Asynchronously focus a window in background thread.

    Uses the unified focus_window_with_retry method with retry loop.
    """

    def _focus_in_background():
        focus_window_with_retry(hwnd)

    thread = threading.Thread(target=_focus_in_background, daemon=True)
    thread.start()


def apply_rule_for_window_async(hwnd: int, layout_name: Optional[str]) -> None:
    """Fire-and-forget: ask the backend to apply the matching layout rule for a window.

    Called after focusing a window so that layout rules are enforced
    immediately on switch, rather than waiting
    for the background timer.
    """
    if layout_name is None:
        logger.debug(f"apply_rule_for_window_async: no active layout, skipping hwnd={hwnd}")
        return

    # Capture layout_name at call time (closure-safe)
    _layout_name = layout_name

    def _apply_in_background():
        try:
            response = _http_session.post(
                f"{TABS_API_URL}/apply-rule-for-window",
                json={"hwnd": hwnd, "layout_name": _layout_name},
                timeout=10.0,  # rules can take a few seconds (F11 + waits)
            )
            if response.ok:
                result = response.json()
                logger.info(
                    f"Rule applied for hwnd={hwnd}: matched={result.get('matched')}, "
                    f"changed={result.get('changed')}, ops={result.get('operations')}, "
                    f"msg={result.get('message')}"
                )
            else:
                logger.warning(
                    f"apply-rule-for-window returned {response.status_code} for hwnd={hwnd}"
                )
        except Exception as e:
            logger.warning(f"apply-rule-for-window failed for hwnd={hwnd}: {e}")

    thread = threading.Thread(target=_apply_in_background, daemon=True)
    thread.start()


def switch_to_window_async(
    hwnd: int,
    layout_name: Optional[str],
    center_mouse: bool,
    layout_assignment: Optional[dict] = None,
) -> None:
    """Focus a window, apply its layout rule, then optionally center the mouse."""

    def _switch_in_background():
        try:
            focus_window_with_retry(hwnd)
        except Exception as e:
            logger.warning(f"Focus failed for hwnd={hwnd}: {e}")

        try:
            if layout_name is not None:
                response = _http_session.post(
                    f"{TABS_API_URL}/apply-rule-for-window",
                    json={
                        "hwnd": hwnd,
                        "layout_name": layout_name,
                        "assignment": layout_assignment or {},
                    },
                    timeout=10.0,
                )
                if response.ok:
                    result = response.json()
                    logger.info(
                        f"Rule applied for hwnd={hwnd}: matched={result.get('matched')}, "
                        f"changed={result.get('changed')}, ops={result.get('operations')}, "
                        f"msg={result.get('message')}"
                    )
                else:
                    logger.warning(
                        f"apply-rule-for-window returned {response.status_code} for hwnd={hwnd}"
                    )
            else:
                logger.debug(
                    f"switch_to_window_async: no active layout, skipping rule apply for hwnd={hwnd}"
                )
        except Exception as e:
            logger.warning(f"apply-rule-for-window failed for hwnd={hwnd}: {e}")

        if center_mouse:
            time.sleep(0.15)
            center_mouse_on_window(hwnd)

    thread = threading.Thread(target=_switch_in_background, daemon=True)
    thread.start()


def focus_hwnd_async(hwnd: int, delay_s: float = 0.05) -> None:
    """Best-effort async focus/raise for a given hwnd (Windows).

    Deprecated: Use focus_window_async instead for unified behavior.
    """

    def _focus_in_background() -> None:
        time.sleep(max(0.0, float(delay_s)))
        focus_window_with_retry(hwnd)

    threading.Thread(target=_focus_in_background, daemon=True).start()


def center_mouse_on_window(hwnd: int) -> None:
    """Center the mouse cursor on the monitor where the window is located.

    Args:
        hwnd: Window handle
    """
    try:
        import win32gui
        import win32api
        from ctypes import windll, Structure, c_long, byref

        class POINT(Structure):
            _fields_ = [("x", c_long), ("y", c_long)]

        # Get window rect
        rect = win32gui.GetWindowRect(hwnd)
        window_x = rect[0]
        window_y = rect[1]

        # Get monitor info for the window's position
        point = POINT(window_x, window_y)
        monitor = windll.user32.MonitorFromPoint(point, 2)  # MONITOR_DEFAULTTONEAREST

        class RECT(Structure):
            _fields_ = [
                ("left", c_long),
                ("top", c_long),
                ("right", c_long),
                ("bottom", c_long),
            ]

        class MONITORINFO(Structure):
            _fields_ = [
                ("cbSize", c_long),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", c_long),
            ]

        monitor_info = MONITORINFO()
        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)

        if windll.user32.GetMonitorInfoA(monitor, byref(monitor_info)):
            # Calculate center of monitor
            center_x = (monitor_info.rcMonitor.left + monitor_info.rcMonitor.right) // 2
            center_y = (monitor_info.rcMonitor.top + monitor_info.rcMonitor.bottom) // 2

            # Move mouse cursor to center
            win32api.SetCursorPos((center_x, center_y))
            logger.info(f"Mouse centered on monitor at ({center_x}, {center_y})")
    except Exception as e:
        logger.warning(f"Failed to center mouse: {e}")


class HotkeyThread(threading.Thread):
    def __init__(self, on_toggle, debounce_s: float = 0.25):
        super().__init__(daemon=True)
        self._on_toggle = on_toggle
        self._debounce_s = debounce_s
        self._stop = threading.Event()
        self._last_fire = 0.0
        self._listener = None

    def stop(self) -> None:
        self._stop.set()
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass

    def run(self) -> None:
        try:
            from pynput import keyboard
        except Exception as e:
            print(f"pynput keyboard import failed: {e}")
            return

        def _fire_toggle() -> None:
            now = time.time()
            if now - self._last_fire < self._debounce_s:
                return
            self._last_fire = now
            print("HOTKEY PRESSED")
            self._on_toggle()

        try:
            # Use GlobalHotKeys which properly handles modifier combinations
            # without sending spurious key events
            self._listener = keyboard.GlobalHotKeys({"<alt>+<space>": _fire_toggle})
            self._listener.start()
            print("Alt+Space hotkey registered using pynput.GlobalHotKeys")
        except Exception as e:
            print(f"hotkey registration failed: {e}")
            return

        while not self._stop.is_set():
            time.sleep(0.1)


def main() -> None:
    logger.info("=== Starting Window Switcher ===")
    logger.info(f"Log file: {LOG_FILE}")

    # Load slot→monitor assignments from disk
    assignments: dict[str, dict[str, str]] = load_assignments()
    logger.info(f"Loaded assignments: {assignments}")

    # Pre-warm the HTTP connection to avoid first-request delay
    # Retry multiple times with exponential backoff if backend is not ready yet
    max_retries = 10
    retry_delay = 0.5  # Start with 0.5 seconds

    for attempt in range(max_retries):
        try:
            logger.info(
                f"Pre-warming HTTP connection (attempt {attempt + 1}/{max_retries})..."
            )
            _http_session.get("http://127.0.0.1:5555/screenassign/health", timeout=2)
            logger.info("HTTP connection established")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Could not connect to backend: {e}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * 1.5, 5
                )  # Exponential backoff, max 5 seconds
            else:
                logger.error(
                    "FATAL: Could not connect to backend after multiple retries!"
                )
                logger.error(
                    "Make sure ScreenAssign service is running on 127.0.0.1:5555"
                )
                sys.exit(1)

    # Fetch monitor DPI info at startup and cache it locally
    # This is a one-time fetch - the data comes from ScreenAssign's runtime cache
    logger.info("Fetching monitor DPI information from ScreenAssign...")
    monitors_with_dpi = None

    for attempt in range(3):  # Retry up to 3 times for monitor fetch
        monitors_with_dpi = fetch_monitors_with_dpi()
        if monitors_with_dpi:
            break
        if attempt < 2:
            logger.warning(
                f"Could not fetch monitor info (attempt {attempt + 1}/3), retrying..."
            )
            time.sleep(1)

    if not monitors_with_dpi:
        logger.error("FATAL: Could not fetch monitor DPI info from ScreenAssign!")
        logger.error("Make sure ScreenAssign service is running on 127.0.0.1:5555")
        sys.exit(1)
    logger.info(f"Cached {len(monitors_with_dpi)} monitors locally")

    # Register built-in commands
    # Frontend-owned active_layout state (str | None — layout filename stem)
    active_layout: Optional[str] = None

    # Global error surfacing state — defined here (before raylib block) so that
    # activate_layout_tracked (also defined here) can reference it safely.
    # Using a mutable container avoids the need for 'nonlocal' across the try boundary.
    _error_state: dict = {"last_error": None, "error_timestamp": 0.0}

    def activate_layout_tracked(layout_name: str) -> dict:
        nonlocal active_layout
        try:
            layout_assignment = assignments.get(layout_name, {})
            response = _http_session.post(
                f"{TABS_API_URL}/apply-rules",
                json={"layout_name": layout_name, "assignment": layout_assignment},
                timeout=15.0,
            )
            if response.ok:
                result = response.json()
                active_layout = layout_name
                logger.info(f"Active layout set to: {layout_name}")
                logger.info(
                    f"apply-rules on activate: applied={result.get('applied')}, "
                    f"failed={result.get('failed')}"
                )
                return {"success": True}

            error = f"Activation failed ({response.status_code})"
            try:
                payload = response.json()
                error = payload.get("error") or payload.get("message") or error
            except Exception:
                pass
            logger.warning(f"apply-rules on activate returned {response.status_code}: {error}")
            _error_state["last_error"] = error
            _error_state["error_timestamp"] = time.time()
            logger.warning(f"UI error surfaced: {error}")
            return {"success": False, "error": error}
        except Exception as e:
            logger.warning(f"apply-rules on activate failed: {e}")
            _error_state["last_error"] = str(e)
            _error_state["error_timestamp"] = time.time()
            logger.warning(f"UI error surfaced: {e}")
            return {"success": False, "error": str(e)}

    def deactivate_layout_tracked() -> dict:
        nonlocal active_layout
        prev = active_layout
        active_layout = None
        logger.info(f"Active layout cleared (was: {prev})")
        return {"success": True, "deactivated": prev or "layout"}

    register_builtin_commands(
        fetch_monitors_fn=fetch_monitors_with_dpi,
        fetch_layouts_fn=fetch_layouts,
        activate_layout_fn=activate_layout_tracked,
        deactivate_layout_fn=deactivate_layout_tracked,
        get_active_layout_name_fn=lambda: active_layout,
        fetch_windows_fn=fetch_windows,
        fetch_settings_fn=fetch_settings,
        update_settings_fn=update_settings,
        fetch_layout_data_fn=fetch_layout_data,
        fetch_screen_config_fn=fetch_screen_config,
        get_assignment_fn=lambda layout_name: assignments.get(layout_name, {}),
    )
    logger.info("Built-in commands registered")

    # Set default layout locally (no HTTP activation call — backend is stateless)
    try:
        settings = fetch_settings()
        default_layout = settings.get("default_layout")
        if default_layout:
            active_layout = default_layout
            logger.info(f"Default layout set locally: {default_layout}")
    except Exception as e:
        logger.warning(f"Could not read default layout from settings: {e}")

    try:
        from raylib import rl
        import tkinter as tk

        # Font configuration
        FONT_SIZE = 24

        # Create overlay windows for dimming background (one per monitor)
        overlay_windows = []
        overlay_visible = [False]

        def create_overlay():
            """Create fullscreen transparent overlays for all monitors."""
            nonlocal overlay_windows
            try:
                # Create one overlay window per monitor
                monitor_count = rl.GetMonitorCount()

                for monitor_idx in range(monitor_count):
                    monitor_pos = rl.GetMonitorPosition(monitor_idx)
                    monitor_width = rl.GetMonitorWidth(monitor_idx)
                    monitor_height = rl.GetMonitorHeight(monitor_idx)

                    # Create overlay window for this monitor
                    overlay = tk.Toplevel() if overlay_windows else tk.Tk()
                    overlay.title(
                        "__SCREENY_WINDOW_SWITCHER_UNIQUE_MARKER__"
                    )  # Protect from rule assignments
                    overlay.attributes("-alpha", 0.5)  # 50% transparent
                    overlay.attributes("-topmost", True)
                    overlay.overrideredirect(True)  # Remove window decorations
                    overlay.configure(bg="black")

                    # Position on this monitor
                    overlay.geometry(
                        f"{monitor_width}x{monitor_height}+{int(monitor_pos.x)}+{int(monitor_pos.y)}"
                    )

                    # Start hidden
                    overlay.withdraw()

                    overlay_windows.append(overlay)

                print(
                    f"Created {len(overlay_windows)} overlay windows (one per monitor)"
                )
            except Exception as e:
                print(f"Overlay creation error: {e}")

        def show_overlay(
            monitor_x=None, monitor_y=None, monitor_width=None, monitor_height=None
        ):
            """Show the dimming overlay on all monitors."""
            if overlay_windows:
                try:
                    for overlay in overlay_windows:
                        overlay.deiconify()
                        overlay.lift()
                        overlay.attributes("-topmost", True)
                    overlay_visible[0] = True
                    print(f"Overlays shown on {len(overlay_windows)} monitors")
                except Exception as e:
                    print(f"Show overlay error: {e}")

        def hide_overlay():
            """Hide the dimming overlay on all monitors."""
            if overlay_windows:
                try:
                    for overlay in overlay_windows:
                        overlay.withdraw()
                    overlay_visible[0] = False
                    print("Overlays hidden")
                except Exception as e:
                    print(f"Hide overlay error: {e}")

        def update_overlay():
            """Process overlay events (call this in main loop)."""
            if overlay_windows:
                try:
                    for overlay in overlay_windows:
                        overlay.update()
                except Exception as e:
                    print(f"Overlay update error: {e}")

        print("Initializing Raylib...")
        rl.SetConfigFlags(
            rl.FLAG_WINDOW_UNDECORATED
            | rl.FLAG_WINDOW_TOPMOST
            | rl.FLAG_MSAA_4X_HINT
            | rl.FLAG_WINDOW_HIGHDPI  # Handle Windows DPI scaling correctly
        )
        window_width = 720
        window_height = 430
        help_text_y = 404

        rl.InitWindow(
            window_width,
            window_height,
            b"__SCREENY_WINDOW_SWITCHER_UNIQUE_MARKER__",
        )

        rl.SetTargetFPS(60)

        # Create overlays after Raylib is initialized (need monitor info)
        create_overlay()

        # Center window on primary monitor initially
        # (will be repositioned when opened based on mouse position)
        try:
            primary_width = rl.GetMonitorWidth(0)
            primary_height = rl.GetMonitorHeight(0)
            primary_pos = rl.GetMonitorPosition(0)
            actual_width = rl.GetScreenWidth()
            actual_height = rl.GetScreenHeight()

            initial_x = int(primary_pos.x + (primary_width - actual_width) / 2)
            initial_y = int(primary_pos.y + (primary_height - actual_height) / 2)
            rl.SetWindowPosition(initial_x, initial_y)
            print(f"Window initially centered at ({initial_x}, {initial_y})")
        except Exception as e:
            print(f"Could not center window initially: {e}")

        print("Raylib initialized")

        toggle_requested = threading.Event()

        # Initialize with actual current mouse position
        try:
            import mouse

            initial_pos = mouse.get_position()
            current_mouse_pos = [initial_pos[0], initial_pos[1]]
            print(f"Initial mouse position: {current_mouse_pos}")
        except Exception:
            current_mouse_pos = [0, 0]  # Fallback if mouse module unavailable

        # Keep-alive thread to maintain HTTP connection
        def keep_connection_alive():
            """Periodically ping the API to keep connection alive."""
            while True:
                try:
                    time.sleep(30)  # Ping every 30 seconds
                    _http_session.get(f"{TABS_API_URL}/status", timeout=1)
                except Exception:
                    pass  # Silent failure - will reconnect when needed

        keep_alive_thread = threading.Thread(target=keep_connection_alive, daemon=True)
        keep_alive_thread.start()

        # Rules apply timer — owned by the frontend so we can suppress it while
        # the overlay is open (prevents focus theft from fullscreen rule application)
        RULES_APPLY_INTERVAL = 5  # seconds between apply_rules calls

        def rules_apply_loop():
            """Periodically call POST /apply-rules on the backend.

            Skips a tick if the switcher overlay is currently visible to avoid
            SetForegroundWindow calls (from fullscreen rules) stealing focus
            away from the user mid-interaction.
            Also skips if no layout is active (active_layout is None).
            """
            last_apply = 0.0
            while True:
                time.sleep(1)
                if active_layout is None:
                    # No layout active — nothing to apply
                    continue
                if window_visible:
                    # Overlay is open — skip this tick, don't steal focus
                    continue
                now = time.time()
                if now - last_apply < RULES_APPLY_INTERVAL:
                    continue
                last_apply = now
                # Capture layout_name and assignment at tick time
                layout_name_now = active_layout
                layout_assignment_now = assignments.get(layout_name_now, {})
                try:
                    response = _http_session.post(
                        f"{TABS_API_URL}/apply-rules",
                        json={"layout_name": layout_name_now, "assignment": layout_assignment_now},
                        timeout=15.0,  # rules can be slow (F11 + waits)
                    )
                    if response.ok:
                        result = response.json()
                        logger.debug(
                            f"apply-rules tick: applied={result.get('applied')}, "
                            f"failed={result.get('failed')}"
                        )
                    else:
                        logger.warning(f"apply-rules tick returned {response.status_code}")
                except Exception as e:
                    logger.debug(f"apply-rules tick failed (backend may be busy): {e}")

        rules_timer_thread = threading.Thread(target=rules_apply_loop, daemon=True)
        rules_timer_thread.start()

        def request_toggle() -> None:
            # Capture mouse position immediately when hotkey is pressed
            try:
                import mouse

                pos = mouse.get_position()
                current_mouse_pos[0] = pos[0]
                current_mouse_pos[1] = pos[1]
                print(f"Hotkey at mouse: {pos}")
            except Exception as e:
                print(f"Could not get mouse pos: {e}")
            toggle_requested.set()

        hotkey_thread = HotkeyThread(on_toggle=request_toggle)
        hotkey_thread.start()
        print("Hotkey thread started")

        # Load Monaspace Neon Frozen fonts (one font per size; crisp text without scaling)
        fonts_by_size: dict[int, Any] = {}
        try:
            from raylib import ffi

            font_path = b"frontend/fonts/MonaspaceNeonFrozen-Medium.ttf"
            print(f"Attempting to load font from: {font_path}")
            print(f"File exists: {os.path.exists(font_path.decode())}")

            def load_font(size: int) -> Any:
                existing = fonts_by_size.get(size)
                if existing:
                    return existing
                try:
                    # Load with NULL codepoints to load default ASCII range (32-126)
                    f = rl.LoadFontEx(font_path, int(size), ffi.NULL, 0)
                    if f:
                        rl.SetTextureFilter(f.texture, 0)  # TEXTURE_FILTER_POINT = 0
                        fonts_by_size[int(size)] = f
                    return f
                except Exception:
                    return None

            # Common sizes used by this UI.
            Font32 = load_font(32)
            Font24 = load_font(24)
            Font20 = load_font(20)
            Font16 = load_font(16)
        except Exception as e:
            print(f"Font load error: {e}")
            import traceback

            traceback.print_exc()

        def draw_text(text, x, y, size, color):
            """Draw text with custom font or default."""

            use_font = fonts_by_size.get(int(size))
            if not use_font:
                # If size isn't preloaded, attempt a best-effort load.
                try:
                    from raylib import ffi

                    use_font = rl.LoadFontEx(
                        b"frontend/fonts/MonaspaceNeonFrozen-Medium.ttf",
                        int(size),
                        ffi.NULL,
                        0,
                    )
                    if use_font:
                        rl.SetTextureFilter(
                            use_font.texture, 0
                        )  # TEXTURE_FILTER_POINT = 0
                        fonts_by_size[int(size)] = use_font
                except Exception:
                    use_font = None

            if use_font:
                try:
                    # Create Vector2 and Color using ffi
                    from raylib import ffi

                    pos = ffi.new("Vector2*", {"x": float(x), "y": float(y)})[0]
                    # Create Color struct - ensure values are integers 0-255
                    c = ffi.new(
                        "Color*",
                        {
                            "r": int(color[0]),
                            "g": int(color[1]),
                            "b": int(color[2]),
                            "a": int(color[3]),
                        },
                    )[0]
                    rl.DrawTextEx(use_font, text, pos, float(size), 0.0, c)
                except Exception as e:
                    print(f"DrawTextEx error: {e}")
                    # Fallback to default font with default color
                    rl.DrawText(text, x, y, int(size), TEXT_PRIMARY)
            else:
                rl.DrawText(text, x, y, int(size), TEXT_PRIMARY)

        def draw_horizontal_rule(y, x=20, width=680):
            """Draw a subtle horizontal divider line."""

            rl.DrawRectangle(x, int(y), width, 1, DIVIDER)

        # Hide window initially
        try:
            rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
        except Exception as e:
            print(f"Hide error: {e}")

        window_visible = False

        # Setup overlay click handler to close when clicking outside main window
        def setup_overlay_click():
            """Bind click event to overlays to close the window."""
            if overlay_windows:

                def on_overlay_click(event):
                    nonlocal window_visible
                    window_visible = False
                    rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
                    hide_overlay()
                    print("Window hidden (overlay click)")

                # Bind click handler to all overlay windows
                for overlay in overlay_windows:
                    overlay.bind("<Button-1>", on_overlay_click)

        setup_overlay_click()

        # Windows state
        all_windows: list[dict[str, Any]] = []
        filtered: list[dict[str, Any]] = []
        query = ""
        selected = 0
        scroll_offset = 0
        list_visible_rows = 12
        max_visible_rows = 12
        is_loading = False  # Track if data is being fetched

        # Usage ordering (most-recently used apps first)
        # Kept in-memory only (no on-disk persistence).
        last_used_by_app: dict[str, int] = {}
        last_used_counter = [0]

        # Command system state
        command_registry = get_registry()
        current_view: Optional[Any] = (
            None  # Can be AssignView, MonitorManagementView, LayoutManagementView, etc.
        )

        def set_global_error(msg: str) -> None:
            """Surface an error: store globally (timed) and push to current view."""
            _error_state["last_error"] = msg
            _error_state["error_timestamp"] = time.time()
            if current_view is not None and hasattr(current_view, "set_error"):
                current_view.set_error(msg)
            logger.warning(f"UI error surfaced: {msg}")

        # Mode tracking:
        # - switch_mode (default): Normal window selection/switching (in_command_mode=False)
        # - command_mode: Fuzzy-findable commands starting with '/' (in_command_mode=True)
        in_command_mode = False
        filtered_commands: list[Any] = []

        # Text input mode for creating new layouts
        text_input_mode = False
        text_input_value = ""
        text_input_prompt = ""

        def _save_last_used() -> None:
            return

        def window_title(w: dict[str, Any]) -> str:
            t = str(w.get("title") or "").strip()
            return t if t else "(untitled)"

        def window_app(w: dict[str, Any]) -> str:
            for k in ("app_display_name", "app_name", "exe_name"):
                v = str(w.get(k) or "").strip()
                if v:
                    return v
            return "Unknown app"

        def app_key(w: dict[str, Any]) -> str:
            # Prefer a stable identifier for MRU ordering.
            for k in ("exe_name", "app_name", "app_display_name"):
                v = str(w.get(k) or "").strip()
                if v:
                    return v
            return window_app(w)

        def window_title_display(w: dict[str, Any]) -> str:
            """Best-effort display title with the app name stripped.

            Many Windows titles already include the app name (e.g. "File - VS Code").
            We try to remove a trailing/leading app segment to avoid duplication when
            rendering "app - title".
            """

            title = window_title(w)
            app = window_app(w)

            if not title or title == "(untitled)":
                return "(untitled)"
            if not app or app == "Unknown app":
                return title

            t = title.strip()
            t_lower = t.lower()

            def _strip_exe(s: str) -> str:
                s2 = (s or "").strip()
                return s2[:-4] if s2.lower().endswith(".exe") else s2

            # Build a set of app aliases so we can strip titles like:
            #   "something - Notepad" even when app is "Notepad.exe".
            aliases: list[str] = []
            for k in ("app_display_name", "app_name", "exe_name"):
                v = str(w.get(k) or "").strip()
                if v:
                    aliases.append(v)
                    v2 = _strip_exe(v)
                    if v2 and v2 != v:
                        aliases.append(v2)

            # Also include the resolved window_app (and its no-.exe form).
            if app:
                aliases.append(app.strip())
                app2 = _strip_exe(app)
                if app2 and app2 != app:
                    aliases.append(app2)

            # Dedupe, keep longest first (more specific wins).
            aliases = sorted({a for a in aliases if a}, key=len, reverse=True)

            for a in aliases:
                if t_lower == a.lower():
                    return "(untitled)"

            # Common patterns:
            #   "<doc> - <app>"  -> "<doc>"
            #   "<app> - <doc>"  -> "<doc>"
            # Includes best-effort support for Unicode dashes via escapes.
            seps = [
                " - ",
                " | ",
                " : ",
                " \u2013 ",  # en dash
                " \u2014 ",  # em dash
                " \u00b7 ",  # middle dot
                " \u2022 ",  # bullet
            ]

            for sep in seps:
                for a in aliases:
                    # Suffix: "<doc>{sep}<app>" -> "<doc>"
                    pat_suffix = re.compile(
                        re.escape(sep) + re.escape(a) + r"\s*$",
                        flags=re.IGNORECASE,
                    )
                    m = pat_suffix.search(t)
                    if m:
                        candidate = t[: m.start()].strip()
                        return candidate if candidate else "(untitled)"

                    # Prefix: "<app>{sep}<doc>" -> "<doc>"
                    pat_prefix = re.compile(
                        r"^" + re.escape(a) + re.escape(sep),
                        flags=re.IGNORECASE,
                    )
                    m = pat_prefix.search(t)
                    if m:
                        candidate = t[m.end() :].strip()
                        return candidate if candidate else "(untitled)"

            # Fallback: if the app appears in parentheses at the end.
            m = re.match(r"^(.*)\s*\((.+)\)\s*$", t)
            if m:
                tail = m.group(2).strip().lower()
                for a in aliases:
                    if tail == a.strip().lower():
                        candidate = m.group(1).strip()
                        return candidate if candidate else "(untitled)"

            return title

        def window_label(w: dict[str, Any]) -> str:
            """Generate display label for window or tab."""

            if w.get("type") == "tab":
                # Tab format: "Chrome • GitHub Issues (github.com)"
                app = w.get("app_name", "Browser")
                title = w.get("title", "Untitled")  # Already includes domain
                return f"{app} • {title}"
            else:
                # Regular window (existing logic)
                return f"{window_app(w)} - {window_title_display(w)}"

        mono_char_width_px_by_size: dict[int, float] = {}

        def mono_char_width_px(size: int) -> float:
            cached = mono_char_width_px_by_size.get(int(size))
            if cached:
                return cached
            f = fonts_by_size.get(int(size))
            if f:
                try:
                    # Measure a representative glyph for monospace sizing.
                    w = float(rl.MeasureTextEx(f, b"M", float(size), 0.0).x)
                    if w > 0:
                        mono_char_width_px_by_size[int(size)] = w
                        return w
                except Exception:
                    pass
            # Fallback heuristic
            w = float(size) * 0.6
            mono_char_width_px_by_size[int(size)] = w
            return w

        def trim_monospace(text: str, max_chars: int) -> str:
            if max_chars <= 0:
                return ""
            if len(text) <= max_chars:
                return text
            if max_chars <= 3:
                return text[:max_chars]
            return text[: max_chars - 3] + "..."

        def do_filter() -> None:
            nonlocal \
                filtered, \
                selected, \
                scroll_offset, \
                in_command_mode, \
                filtered_commands
            q = query.strip().lower()

            # Check if we're in command mode (query starts with /)
            if command_registry.is_command_query(query):
                in_command_mode = True
                filtered_commands = command_registry.search_commands(query)
                selected = 0
                scroll_offset = 0
                return

            # Normal window filtering mode
            in_command_mode = False

            # Filter out system/UWP windows but KEEP tabs
            user_windows = [
                w
                for w in all_windows
                if w.get("type") == "tab"  # Always include tabs
                or (
                    not w.get("is_system", False)
                    and not w.get("is_uwp", False)
                    and "__SCREENY_WINDOW_SWITCHER_UNIQUE_MARKER__"
                    not in (w.get("title") or "")
                )
            ]

            if not q:
                filtered = user_windows
            else:
                tmp: list[dict[str, Any]] = []
                for w in user_windows:
                    hay = (window_title(w) + " " + window_app(w)).lower()
                    if q in hay:
                        tmp.append(w)
                filtered = tmp

            # Order: most-recently used app first; then alphabetically by label.
            filtered.sort(
                key=lambda w: (
                    -int(last_used_by_app.get(app_key(w), 0)),
                    window_label(w).lower(),
                )
            )

            # Move the most recently used app (first in list) to the back
            # This way you don't switch back to the app you just came from
            if filtered and last_used_by_app:
                # Find the app with the highest MRU counter (most recent)
                max_mru = max(last_used_by_app.values()) if last_used_by_app else 0
                # Check if first item is the most recent
                if (
                    filtered
                    and last_used_by_app.get(app_key(filtered[0]), 0) == max_mru
                ):
                    # Move it to the back
                    filtered = filtered[1:] + [filtered[0]]

            selected = 0
            scroll_offset = 0

        print("Entering main loop...")
        while True:
            try:
                if toggle_requested.is_set():
                    toggle_requested.clear()
                    window_visible = not window_visible
                    print(f"Window visible: {window_visible}")
                    if window_visible:
                        query = ""
                        selected = 0
                        filtered = []
                        is_loading = True

                    if window_visible:
                        # Start fetching data in background thread
                        def fetch_data_async():
                            nonlocal all_windows, filtered, is_loading
                            try:
                                # Fetch windows and tabs from single cached endpoint (FAST!)
                                data = fetch_windows_and_tabs_cached()
                                fetched_windows = data.get("windows", [])
                                tabs = data.get("tabs", [])

                                # Identify browsers that are reporting tabs
                                reporting_browsers = set()
                                if tabs:
                                    for tab in tabs:
                                        exe = tab.get("exe_name", "").lower()
                                        if exe:
                                            reporting_browsers.add(exe)
                                    print(
                                        f"Browsers reporting tabs: {reporting_browsers}"
                                    )

                                # Filter out browser windows that are reporting via extension
                                if reporting_browsers:
                                    filtered_windows = []
                                    for w in fetched_windows:
                                        exe = w.get("exe_name", "").lower()
                                        # Keep window if it's not a reporting browser
                                        if exe not in reporting_browsers:
                                            filtered_windows.append(w)
                                        else:
                                            print(
                                                f"Filtering out {w.get('app_name', 'Unknown')} window (has extension)"
                                            )
                                    fetched_windows = filtered_windows

                                # Merge tabs into window list
                                if tabs:
                                    fetched_windows.extend(tabs)
                                    print(f"Added {len(tabs)} browser tabs")

                                fetched_windows.sort(
                                    key=lambda w: (
                                        window_app(w).lower(),
                                        window_title(w).lower(),
                                    )
                                )

                                all_windows = fetched_windows
                                do_filter()
                                is_loading = False
                                print(
                                    f"Fetched {len(all_windows)} total items ({len(tabs)} tabs)"
                                )
                            except Exception as e:
                                print(f"Fetch error: {e}")
                                all_windows = []
                                filtered = []
                                is_loading = False

                        threading.Thread(target=fetch_data_async, daemon=True).start()

                        try:
                            # Use current mouse position
                            mouse_x, mouse_y = current_mouse_pos
                            logger.info(f"Using mouse position: {mouse_x}, {mouse_y}")
                            print(f"Using mouse position: {mouse_x}, {mouse_y}")

                            # Determine which monitor the mouse is on
                            current_monitor_x = 0
                            current_monitor_y = 0
                            current_monitor_width = 1920
                            current_monitor_height = 1080

                            pos_x = 0
                            pos_y = 0

                            # Window size will be determined after we know which monitor
                            # (it varies by monitor DPI)
                            actual_width = 720  # Default logical size
                            actual_height = 420

                            for monitor_idx in range(rl.GetMonitorCount()):
                                monitor_width = rl.GetMonitorWidth(monitor_idx)
                                monitor_height = rl.GetMonitorHeight(monitor_idx)
                                monitor_pos = rl.GetMonitorPosition(monitor_idx)

                                # Check if mouse is on this monitor
                                is_on_monitor = (
                                    monitor_pos.x
                                    <= mouse_x
                                    < monitor_pos.x + monitor_width
                                    and monitor_pos.y
                                    <= mouse_y
                                    < monitor_pos.y + monitor_height
                                )

                                if is_on_monitor:
                                    # Store monitor info for overlay
                                    current_monitor_x = int(monitor_pos.x)
                                    current_monitor_y = int(monitor_pos.y)
                                    current_monitor_width = monitor_width
                                    current_monitor_height = monitor_height

                                    # Find this monitor's DPI scale from our cached data
                                    dpi_scale = 1.0
                                    for mon in monitors_with_dpi:
                                        if mon["x"] == int(monitor_pos.x) and mon[
                                            "y"
                                        ] == int(monitor_pos.y):
                                            dpi_scale = mon.get("dpi_scale", 1.0)
                                            logger.debug(
                                                f"Found cached DPI for monitor: {dpi_scale}"
                                            )
                                            break

                                    # Calculate actual window size based on DPI scale
                                    # Logical size is 720x420, actual size = logical * dpi_scale
                                    actual_width = int(720 * dpi_scale)
                                    actual_height = int(420 * dpi_scale)

                                    pos_x = int(
                                        monitor_pos.x
                                        + (monitor_width - actual_width) / 2
                                    )
                                    pos_y = int(
                                        monitor_pos.y
                                        + (monitor_height - actual_height) / 2
                                    )

                                    # Comprehensive single-line log
                                    log_msg = (
                                        f"POS_CALC: mouse=({mouse_x},{mouse_y}) "
                                        f"monitor_{monitor_idx}={{pos=({monitor_pos.x},{monitor_pos.y}), size=({monitor_width}x{monitor_height})}} "
                                        f"window={{logical=(720x420), actual=({actual_width}x{actual_height}), dpi_scale={dpi_scale:.2f}}} "
                                        f"final_pos=({pos_x},{pos_y})"
                                    )
                                    logger.info(log_msg)
                                    print(log_msg)
                                    break

                            # Show overlay on all monitors
                            show_overlay()

                            rl.ClearWindowState(rl.FLAG_WINDOW_HIDDEN)

                            # Position using our pre-calculated DPI-aware coordinates
                            # DO NOT recalculate - Raylib's GetScreenWidth/Height may not
                            # reflect DPI scaling on first show, but our calculation is correct
                            rl.SetWindowPosition(pos_x, pos_y)
                            logger.info(
                                f"Window shown and positioned: calculated=({pos_x},{pos_y}), expected_size=({actual_width}x{actual_height})"
                            )
                            print(
                                f"Window shown and positioned at ({pos_x}, {pos_y}) with expected size ({actual_width}x{actual_height})"
                            )
                            # Focus Screeny window using unified focus method
                            try:
                                from raylib import ffi

                                hwnd_ptr = rl.GetWindowHandle()
                                hwnd = int(ffi.cast("uintptr_t", hwnd_ptr))
                                focus_window_with_retry(hwnd)
                            except Exception as e:
                                print(f"Focus window error: {e}")
                        except Exception as e:
                            print(f"Show error: {e}")
                            import traceback

                            traceback.print_exc()
                    else:
                        try:
                            rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
                            hide_overlay()
                            print("Window hidden")
                        except Exception as e:
                            print(f"Hide error: {e}")

                if window_visible:
                    try:
                        # Handle input based on current mode
                        if text_input_mode:
                            # Text input mode for creating new layout
                            ch = rl.GetCharPressed()
                            while ch > 0:
                                if 32 <= ch <= 126:  # Printable ASCII characters
                                    text_input_value += chr(ch)
                                ch = rl.GetCharPressed()

                            if rl.IsKeyPressed(rl.KEY_BACKSPACE) and text_input_value:
                                text_input_value = text_input_value[:-1]

                            if rl.IsKeyPressed(rl.KEY_ESCAPE):
                                # Cancel text input
                                text_input_mode = False
                                text_input_value = ""
                                logger.info("Text input cancelled")

                            if (
                                rl.IsKeyPressed(rl.KEY_ENTER)
                                and text_input_value.strip()
                            ):
                                # Submit the layout name
                                layout_name = text_input_value.strip()
                                logger.info(f"Creating layout: {layout_name}")
                                try:
                                    response = _http_session.post(
                                        f"{TABS_API_URL}/layouts",
                                        json={"name": layout_name, "description": ""},
                                        timeout=TABS_API_TIMEOUT,
                                    )
                                    if response.ok:
                                        result = response.json()
                                        logger.info(f"Layout created: {result}")
                                        if isinstance(
                                            current_view, LayoutManagementView
                                        ):
                                            current_view.error_message = (
                                                f"✓ Created: {layout_name}"
                                            )
                                            current_view.layouts = fetch_layouts()
                                            current_view.active_layout = active_layout
                                    else:
                                        error_msg = (
                                            response.json().get(
                                                "error", "Unknown error"
                                            )
                                            if response.text
                                            else "Request failed"
                                        )
                                        logger.error(
                                            f"Failed to create layout: {error_msg}"
                                        )
                                        if isinstance(
                                            current_view, LayoutManagementView
                                        ):
                                            current_view.error_message = (
                                                f"✗ Create failed: {error_msg}"
                                            )
                                except Exception as e:
                                    logger.error(f"Error creating layout: {e}")
                                    if isinstance(current_view, LayoutManagementView):
                                        current_view.error_message = (
                                            f"✗ Error: {str(e)}"
                                        )

                                # Exit text input mode
                                text_input_mode = False
                                text_input_value = ""

                        elif current_view is not None:
                            # We're in a command view
                            ch = rl.GetCharPressed()

                            # Check if view supports additional keys (layouts/windows/screens do, monitors don't)
                            if isinstance(
                                current_view,
                                (
                                    AssignView,
                                    LayoutManagementView,
                                    WindowsView,
                                    WindowDetailsView,
                                    SettingsView,
                                ),
                            ):
                                # Pass additional keys for these views
                                action = current_view.handle_input(
                                    ch,
                                    rl.IsKeyPressed(rl.KEY_DOWN),
                                    rl.IsKeyPressed(rl.KEY_UP),
                                    rl.IsKeyPressed(rl.KEY_ESCAPE),
                                    rl.IsKeyPressed(rl.KEY_BACKSPACE),
                                    rl.IsKeyPressed(rl.KEY_D),
                                    key_a=rl.IsKeyPressed(rl.KEY_A),
                                    key_enter=rl.IsKeyPressed(rl.KEY_ENTER),
                                    key_n=rl.IsKeyPressed(rl.KEY_N),
                                )
                            else:
                                # MonitorManagementView uses original signature
                                action = current_view.handle_input(
                                    ch,
                                    rl.IsKeyPressed(rl.KEY_DOWN),
                                    rl.IsKeyPressed(rl.KEY_UP),
                                    rl.IsKeyPressed(rl.KEY_ESCAPE),
                                    rl.IsKeyPressed(rl.KEY_BACKSPACE),
                                    rl.IsKeyPressed(rl.KEY_D),
                                )

                            if action:
                                if action == "close":
                                    current_view = None
                                    query = ""
                                    do_filter()
                                elif action == "refresh":
                                    # Refresh the view data
                                    if isinstance(current_view, LayoutManagementView):
                                        current_view.layouts = fetch_layouts()
                                        current_view.active_layout = active_layout
                                    elif isinstance(
                                        current_view, MonitorManagementView
                                    ):
                                        current_view.monitors = (
                                            fetch_monitors_with_dpi()
                                        )
                                elif action == "delete_layout":
                                    # Delete the selected layout file
                                    if isinstance(current_view, LayoutManagementView):
                                        layout = current_view.layouts[
                                            current_view.selected
                                        ]
                                        layout_name = layout["file_name"].replace(
                                            ".json", ""
                                        )
                                        logger.info(f"Deleting layout: {layout_name}")
                                        try:
                                            response = _http_session.delete(
                                                f"{TABS_API_URL}/layouts/{layout_name}",
                                                timeout=TABS_API_TIMEOUT,
                                            )
                                            if response.ok:
                                                logger.info(
                                                    f"Layout {layout_name} deleted successfully"
                                                )
                                                current_view.error_message = (
                                                    f"✓ Deleted: {layout['name']}"
                                                )
                                                # Refresh the layouts list
                                                current_view.layouts = fetch_layouts()
                                                current_view.active_layout = active_layout
                                                # Reset selection if needed
                                                if current_view.selected >= len(
                                                    current_view.layouts
                                                ):
                                                    current_view.selected = max(
                                                        0, len(current_view.layouts) - 1
                                                    )
                                                if current_view.scroll_offset >= len(
                                                    current_view.layouts
                                                ):
                                                    current_view.scroll_offset = max(
                                                        0,
                                                        len(current_view.layouts)
                                                        - current_view.max_visible_rows,
                                                    )
                                            else:
                                                error_msg = (
                                                    response.json().get(
                                                        "error", "Unknown error"
                                                    )
                                                    if response.text
                                                    else "Request failed"
                                                )
                                                logger.error(
                                                    f"Failed to delete layout: {error_msg}"
                                                )
                                                current_view.error_message = (
                                                    f"✗ Delete failed: {error_msg}"
                                                )
                                        except Exception as e:
                                            logger.error(f"Error deleting layout: {e}")
                                            current_view.error_message = (
                                                f"✗ Error: {str(e)}"
                                            )
                                elif action == "new_layout":
                                    # Enter text input mode for new layout name
                                    logger.info("Starting new layout creation")
                                    text_input_mode = True
                                    text_input_value = ""
                                    text_input_prompt = "Enter layout name:"
                                elif action == "window_details":
                                    # Open window details view
                                    if isinstance(current_view, WindowsView):
                                        selected_window = current_view.windows[
                                            current_view.selected
                                        ]
                                        logger.info(
                                            f"Opening details for window: {selected_window.get('title')}"
                                        )
                                        # Create window details view
                                        current_view = WindowDetailsView(
                                            selected_window,
                                            current_view.active_layout,
                                        )
                                elif action == "save":
                                    # Handle save for AssignView (slot→monitor assignment)
                                    if isinstance(current_view, AssignView):
                                        logger.info("Saving slot→monitor assignment")
                                        try:
                                            layout_name_now = current_view.layout_name or active_layout
                                            if layout_name_now:
                                                new_assignment = current_view.get_assignment()
                                                assignments[layout_name_now] = new_assignment
                                                save_assignments(assignments)
                                                logger.info(
                                                    f"Assignment saved for '{layout_name_now}': {new_assignment}"
                                                )
                                            current_view = None
                                            in_command_mode = False
                                        except Exception as e:
                                            logger.error(f"Failed to save assignment: {e}")
                                            current_view.set_error(f"Save failed: {e}")
                                    # Save window rule to active layout
                                    elif isinstance(current_view, WindowDetailsView):
                                        logger.info("Saving window rule to layout")
                                        try:
                                            rule_config = current_view.get_rule_config()
                                            layout_name = (
                                                current_view.active_layout.get(
                                                    "name", ""
                                                )
                                            )
                                            layout_file_name = (
                                                current_view.active_layout.get(
                                                    "file_name", ""
                                                )
                                            )
                                            # Remove .json extension
                                            layout_name_slug = layout_file_name.replace(
                                                ".json", ""
                                            )

                                            response = _http_session.post(
                                                f"http://127.0.0.1:5555/screenassign/layouts/{layout_name_slug}/rules",
                                                json=rule_config,
                                                timeout=2.0,
                                            )

                                            if response.ok:
                                                logger.info("Rule saved successfully")
                                                # Close the window details view
                                                current_view = None
                                                in_command_mode = False
                                            else:
                                                error_msg = (
                                                    response.json().get(
                                                        "error", "Unknown error"
                                                    )
                                                    if response.text
                                                    else "Request failed"
                                                )
                                                logger.error(
                                                    f"Failed to save rule: {error_msg}"
                                                )
                                        except Exception as e:
                                            logger.error(f"Error saving rule: {e}")

                                elif action == "delete":
                                    # Delete window rule from active layout
                                    if isinstance(current_view, WindowDetailsView):
                                        logger.info("Deleting window rule from layout")
                                        try:
                                            rule_id = current_view.existing_rule.get(
                                                "rule_id"
                                            )
                                            layout_file_name = (
                                                current_view.active_layout.get(
                                                    "file_name", ""
                                                )
                                            )
                                            layout_name_slug = layout_file_name.replace(
                                                ".json", ""
                                            )

                                            response = _http_session.delete(
                                                f"http://127.0.0.1:5555/screenassign/layouts/{layout_name_slug}/rules/{rule_id}",
                                                timeout=2.0,
                                            )

                                            if response.ok:
                                                logger.info("Rule deleted successfully")
                                                # Return to windows view with refreshed data
                                                windows = fetch_windows()
                                                full_layout = (
                                                    fetch_layout_data(active_layout)
                                                    if active_layout
                                                    else None
                                                )
                                                current_view = WindowsView(
                                                    windows, full_layout
                                                )
                                                current_view.error_message = (
                                                    "✓ Rule deleted"
                                                )
                                            else:
                                                logger.error(
                                                    f"Failed to delete rule: {response.text}"
                                                )
                                                # Stay in WindowDetailsView and show error
                                                current_view.error_message = f"❌ Delete failed: {response.status_code}"
                                        except Exception as e:
                                            logger.error(f"Error deleting rule: {e}")
                                            # Stay in WindowDetailsView and show error
                                            current_view.error_message = (
                                                f"❌ Delete error: {str(e)}"
                                            )

                                elif action.startswith("delete:"):
                                    monitor_id = action.split(":", 1)[1]
                                    logger.info(f"Deleting monitor: {monitor_id}")
                                    try:
                                        response = _http_session.delete(
                                            f"http://127.0.0.1:5555/screenassign/monitors/{monitor_id}",
                                            timeout=1.0,
                                        )
                                        if response.ok:
                                            logger.info(
                                                f"Monitor {monitor_id} deleted successfully"
                                            )
                                            # Refresh the view
                                            current_view.monitors = (
                                                fetch_monitors_with_dpi()
                                            )
                                            # Reset selection if needed
                                            if current_view.selected >= len(
                                                current_view.monitors
                                            ):
                                                current_view.selected = max(
                                                    0, len(current_view.monitors) - 1
                                                )
                                            if current_view.scroll_offset >= len(
                                                current_view.monitors
                                            ):
                                                current_view.scroll_offset = max(
                                                    0,
                                                    len(current_view.monitors)
                                                    - current_view.max_visible_rows,
                                                )
                                        else:
                                            logger.error(
                                                f"Failed to delete monitor: {response.text}"
                                            )
                                    except Exception as e:
                                        logger.error(f"Error deleting monitor: {e}")
                        else:
                            # Normal input handling
                            ch = rl.GetCharPressed()
                            while ch > 0:
                                if 32 <= ch <= 126:
                                    query += chr(ch)
                                    do_filter()
                                ch = rl.GetCharPressed()

                            if rl.IsKeyPressed(rl.KEY_BACKSPACE) and query:
                                query = query[:-1]
                                do_filter()

                            if rl.IsKeyPressed(rl.KEY_ESCAPE):
                                window_visible = False
                                rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
                                hide_overlay()
                                print("Window hidden (Esc)")

                            # Navigation - handle both command mode and window mode
                            items_to_navigate = (
                                filtered_commands if in_command_mode else filtered
                            )

                            if rl.IsKeyPressed(rl.KEY_DOWN) and items_to_navigate:
                                selected = min(selected + 1, len(items_to_navigate) - 1)
                                # Keep selected item visible
                                if selected >= scroll_offset + max_visible_rows:
                                    scroll_offset = selected - max_visible_rows + 1

                            if rl.IsKeyPressed(rl.KEY_UP) and items_to_navigate:
                                selected = max(selected - 1, 0)
                                # Keep selected item visible
                                if selected < scroll_offset:
                                    scroll_offset = selected

                        # Handle Enter key for both modes
                        if rl.IsKeyPressed(rl.KEY_ENTER) and current_view is None:
                            if in_command_mode and filtered_commands:
                                # Execute command
                                cmd = filtered_commands[selected]
                                logger.info(f"Executing command: /{cmd.name}")
                                try:
                                    result = cmd.execute({})
                                    if isinstance(
                                        result,
                                        (
                                            AssignView,
                                            MonitorManagementView,
                                            LayoutManagementView,
                                            WindowsView,
                                            WindowDetailsView,
                                            SettingsView,
                                        ),
                                    ):
                                        current_view = result
                                        query = ""
                                except Exception as e:
                                    logger.error(f"Command execution failed: {e}")
                            elif filtered:
                                w = filtered[selected]

                                # Check if this is a tab or regular window
                                if w.get("type") == "tab":
                                    tab_id = w.get("id")
                                    if tab_id:
                                        # Record MRU for ordering next time
                                        last_used_counter[0] += 1
                                        last_used_by_app[app_key(w)] = (
                                            last_used_counter[0]
                                        )
                                        _save_last_used()

                                        # Step 1: Focus the browser Win32 window from
                                        # THIS process (which currently owns the
                                        # foreground). SetForegroundWindow only works
                                        # from the foreground process — the Flask
                                        # backend can never do this reliably.
                                        browser_hwnd = find_browser_hwnd(w, all_windows)
                                        if browser_hwnd:
                                            switch_to_window_async(
                                                browser_hwnd,
                                                active_layout,
                                                False,  # don't center mouse for tab switches
                                                layout_assignment=assignments.get(active_layout, {}) if active_layout else {},
                                            )
                                        else:
                                            print(f"No browser window found for tab {tab_id}, exe={w.get('exe_name')}")

                                        # Step 2: Queue the Chrome activateTab command
                                        # so the extension navigates to the right tab.
                                        activate_tab_via_api(tab_id)
                                        print(f"Tab activation requested for {tab_id}")

                                        # Close switcher
                                        window_visible = False
                                        rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
                                        hide_overlay()
                                        print("Window hidden after tab activation")
                                else:
                                    # Regular window handling
                                    hwnd = w.get("hwnd")
                                    if hwnd is not None:
                                        # Record MRU for ordering next time.
                                        last_used_counter[0] += 1
                                        last_used_by_app[app_key(w)] = (
                                            last_used_counter[0]
                                        )
                                        _save_last_used()

                                        # Capture switch behavior before closing UI.
                                        try:
                                            settings = fetch_settings()
                                            center_mouse_on_switch = settings.get(
                                                "center_mouse_on_switch", False
                                            )
                                        except Exception as e:
                                            center_mouse_on_switch = False
                                            logger.warning(
                                                f"Failed to check mouse centering setting: {e}"
                                            )

                                        switch_to_window_async(
                                            hwnd,
                                            active_layout,
                                            center_mouse_on_switch,
                                            layout_assignment=assignments.get(active_layout, {}) if active_layout else {},
                                        )
                                        print(
                                            f"Switch requested for hwnd={hwnd} (async)"
                                        )

                                        # Close window immediately without waiting
                                        window_visible = False
                                        rl.SetWindowState(rl.FLAG_WINDOW_HIDDEN)
                                        hide_overlay()
                                        print("Window hidden after focus request")

                        # Draw
                        rl.BeginDrawing()
                        rl.ClearBackground(BACKGROUND)

                        # Draw based on current mode
                        if text_input_mode:
                            # Draw text input dialog for new layout
                            # Title
                            draw_text(
                                b"Create New Layout",
                                20,
                                16,
                                FONT_SIZE,
                                TEXT_SECONDARY,
                            )

                            # Prompt
                            draw_text(
                                text_input_prompt.encode("utf-8", errors="ignore"),
                                20,
                                60,
                                FONT_SIZE - 4,
                                TEXT_SECONDARY,
                            )

                            # Input box background
                            rl.DrawRectangle(20, 90, 680, 40, INPUT_BACKGROUND)
                            rl.DrawRectangleLines(20, 90, 680, 40, INPUT_BORDER)

                            # Input text with cursor
                            input_display = text_input_value + "_"
                            draw_text(
                                input_display.encode("utf-8", errors="ignore"),
                                30,
                                100,
                                FONT_SIZE,
                                TEXT_PRIMARY,
                            )

                            # Help text
                            draw_text(
                                b"Enter to create | Esc to cancel",
                                20,
                                help_text_y,
                                FONT_SIZE - 8,
                                TEXT_MUTED,
                            )

                        elif current_view is not None:
                            # Render current view
                            render_data = current_view.get_render_data()

                            # Draw title
                            draw_text(
                                render_data["title"].encode("utf-8", errors="ignore"),
                                20,
                                16,
                                FONT_SIZE,
                                TEXT_SECONDARY,
                            )

                            # Draw count
                            # Make count text generic based on view type
                            if isinstance(current_view, LayoutManagementView):
                                count_label = "layouts"
                            elif isinstance(current_view, AssignView):
                                count_label = "slots"
                            elif isinstance(current_view, WindowsView):
                                count_label = "windows"
                            elif isinstance(current_view, WindowDetailsView):
                                count_label = ""  # No count for details view
                            elif isinstance(current_view, SettingsView):
                                count_label = "settings"
                            else:
                                count_label = "monitors"

                            count_text = (
                                f"{render_data['total_count']} {count_label}".encode(
                                    "utf-8"
                                )
                            )
                            draw_text(
                                count_text,
                                520,
                                16,
                                FONT_SIZE - 8,
                                TEXT_MUTED,
                            )

                            base_y = 55
                            list_top_y = base_y - 10
                            list_rows = list_visible_rows
                            list_bottom_y = base_y + list_rows * 28 - 6

                            draw_horizontal_rule(list_top_y)

                            # Draw monitor items
                            for idx, item in enumerate(render_data["items"]):
                                y = base_y + idx * 28
                                is_sel = idx == render_data["selected"]

                                if is_sel:
                                    draw_text(
                                        b">", 20, y, FONT_SIZE, ACCENT_SELECTION
                                    )

                                # Color: yellow for has rule, white for no rule
                                color = (
                                    ACCENT_HIGHLIGHT
                                    if item["connected"]
                                    else TEXT_PRIMARY
                                )

                                label_x = 40 if is_sel else 38
                                right_edge_x = 690
                                avail_px = max(0, right_edge_x - label_x)
                                char_px = mono_char_width_px(FONT_SIZE)
                                max_chars = (
                                    int(avail_px / char_px) if char_px > 0 else 0
                                )
                                label_text = trim_monospace(item["label"], max_chars)

                                draw_text(
                                    label_text.encode("utf-8", errors="ignore"),
                                    label_x,
                                    y,
                                    FONT_SIZE,
                                    color,
                                )

                            draw_horizontal_rule(list_bottom_y)

                            # Draw help text (show timed error for up to 4 s)
                            _err_msg = _error_state.get("last_error")
                            _err_age = time.time() - _error_state.get("error_timestamp", 0.0)
                            if _err_msg and _err_age < 4.0:
                                _help_display = f"Error: {_err_msg}"
                                _help_color = (220, 60, 60, 255)  # red-ish
                            else:
                                _help_display = render_data["help_text"]
                                _help_color = TEXT_SECONDARY
                            draw_text(
                                (_help_display if isinstance(_help_display, bytes)
                                 else _help_display.encode("utf-8", errors="ignore")),
                                20,
                                help_text_y,
                                FONT_SIZE - 4,
                                _help_color,
                            )

                        else:
                            # Normal window/command list mode
                            draw_text(
                                b"query:", 20, 16, FONT_SIZE, TEXT_SECONDARY
                            )
                            draw_text(
                                query.encode("utf-8", errors="ignore"),
                                100,
                                16,
                                FONT_SIZE,
                                TEXT_MUTED,
                            )

                            # Draw count or loading indicator in top right
                            if is_loading:
                                count_text = b"loading..."
                            elif in_command_mode:
                                count_text = (
                                    f"{len(filtered_commands)} commands".encode("utf-8")
                                )
                            else:
                                count_text = f"{len(filtered)} windows".encode("utf-8")
                            count_width = len(
                                count_text.decode("utf-8")
                                if isinstance(count_text, bytes)
                                else count_text
                            ) * mono_char_width_px(FONT_SIZE - 8)
                            draw_text(
                                count_text,
                                int(700 - count_width),
                                16,
                                FONT_SIZE - 8,
                                TEXT_MUTED,
                            )

                            # Draw items (commands or windows) with scrolling
                            base_y = 55
                            list_top_y = base_y - 10
                            items_count = (
                                len(filtered_commands)
                                if in_command_mode
                                else len(filtered)
                            )
                            list_bottom_y = base_y + max_visible_rows * 28 - 6

                            draw_horizontal_rule(list_top_y)

                            if in_command_mode:
                                # Draw commands
                                shown = filtered_commands[
                                    scroll_offset : scroll_offset + max_visible_rows
                                ]
                                for idx, cmd in enumerate(shown):
                                    y = base_y + idx * 28
                                    actual_idx = scroll_offset + idx
                                    is_sel = actual_idx == selected
                                    if is_sel:
                                        draw_text(
                                            b">", 20, y, FONT_SIZE, ACCENT_SELECTION
                                        )

                                    label_x = 40 if is_sel else 38
                                    label_text = cmd.get_label()
                                    right_edge_x = 690
                                    avail_px = max(0, right_edge_x - label_x)
                                    char_px = mono_char_width_px(FONT_SIZE)
                                    max_chars = (
                                        int(avail_px / char_px) if char_px > 0 else 0
                                    )
                                    label_text = trim_monospace(label_text, max_chars)

                                    draw_text(
                                        label_text.encode("utf-8", errors="ignore"),
                                        label_x,
                                        y,
                                        FONT_SIZE,
                                        TEXT_PRIMARY,
                                    )
                            else:
                                # Draw windows
                                shown = filtered[
                                    scroll_offset : scroll_offset + max_visible_rows
                                ]
                                for idx, w in enumerate(shown):
                                    y = base_y + idx * 28
                                    actual_idx = scroll_offset + idx
                                    is_sel = actual_idx == selected
                                    if is_sel:
                                        draw_text(
                                            b">", 20, y, FONT_SIZE, ACCENT_SELECTION
                                        )

                                    # Trim long labels so they don't overlap the scrollbar.
                                    label_x = 40 if is_sel else 38
                                    right_edge_x = 690  # scrollbar starts at ~700
                                    avail_px = max(0, right_edge_x - label_x)
                                    char_px = mono_char_width_px(FONT_SIZE)
                                    max_chars = (
                                        int(avail_px / char_px) if char_px > 0 else 0
                                    )
                                    label_text = trim_monospace(
                                        window_label(w), max_chars
                                    )

                                    # Draw text with highlighted query matches
                                    q = query.strip().lower()
                                    if q and q in label_text.lower():
                                        # Find match position (case-insensitive)
                                        match_start = label_text.lower().find(q)
                                        match_end = match_start + len(q)

                                        # Draw text in parts: before, match, after
                                        current_x = label_x

                                        # Before match
                                        if match_start > 0:
                                            before_text = label_text[
                                                :match_start
                                            ].encode("utf-8", errors="ignore")
                                            draw_text(
                                                before_text,
                                                current_x,
                                                y,
                                                FONT_SIZE,
                                                TEXT_PRIMARY,
                                            )
                                            current_x += (
                                                len(label_text[:match_start]) * char_px
                                            )

                                        # Match (yellow)
                                        match_text = label_text[
                                            match_start:match_end
                                        ].encode("utf-8", errors="ignore")
                                        draw_text(
                                            match_text,
                                            current_x,
                                            y,
                                            FONT_SIZE,
                                            ACCENT_HIGHLIGHT,
                                        )
                                        current_x += (
                                            len(label_text[match_start:match_end])
                                            * char_px
                                        )

                                        # After match
                                        if match_end < len(label_text):
                                            after_text = label_text[match_end:].encode(
                                                "utf-8", errors="ignore"
                                            )
                                            draw_text(
                                                after_text,
                                                current_x,
                                                y,
                                                FONT_SIZE,
                                                TEXT_PRIMARY,
                                            )
                                    else:
                                        # No match or no query - draw normally
                                        label = label_text.encode(
                                            "utf-8", errors="ignore"
                                        )
                                        draw_text(
                                            label,
                                            label_x,
                                            y,
                                            FONT_SIZE,
                                            TEXT_PRIMARY,
                                        )

                            draw_horizontal_rule(list_bottom_y)

                            # Draw scrollbar indicator
                            if items_count > max_visible_rows:
                                scrollbar_y = list_top_y
                                scrollbar_height = list_bottom_y - list_top_y + 1
                                max_scroll_offset = items_count - max_visible_rows
                                scroll_ratio = (
                                    scroll_offset / max_scroll_offset
                                    if max_scroll_offset > 0
                                    else 0
                                )
                                handle_height = max(
                                    18,
                                    (max_visible_rows / items_count)
                                    * scrollbar_height,
                                )
                                handle_y = scrollbar_y + (
                                    scroll_ratio
                                    * max(0, scrollbar_height - handle_height)
                                )
                                rl.DrawRectangle(
                                    700,
                                    int(scrollbar_y),
                                    8,
                                    int(scrollbar_height),
                                    SCROLLBAR_TRACK,
                                )
                                rl.DrawRectangle(
                                    700,
                                    int(handle_y),
                                    8,
                                    int(handle_height),
                                    SCROLLBAR_HANDLE,
                                )

                            # Draw help text (show timed error for up to 4 s)
                            _err_msg = _error_state.get("last_error")
                            _err_age = time.time() - _error_state.get("error_timestamp", 0.0)
                            if _err_msg and _err_age < 4.0:
                                help_text = f"Error: {_err_msg}".encode("utf-8", errors="ignore")
                                _help_color = (220, 60, 60, 255)
                            elif in_command_mode:
                                help_text = b"Type command name | Enter to execute | Esc to close"
                                _help_color = TEXT_SECONDARY
                            else:
                                help_text = b"Alt+Space to close"
                                _help_color = TEXT_SECONDARY

                            draw_text(
                                help_text,
                                20,
                                help_text_y,
                                FONT_SIZE - 4,
                                _help_color,
                            )
                        rl.EndDrawing()
                    except Exception as e:
                        print(f"Draw error: {e}")
                        import traceback

                        traceback.print_exc()

                # Update overlay (process tkinter events)
                update_overlay()

                time.sleep(0.01)
            except Exception as e:
                print(f"Loop error: {e}")
                import traceback

                traceback.print_exc()
                break

    except Exception as e:
        print(f"Main error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
