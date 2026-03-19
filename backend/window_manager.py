import logging
import win32gui
import win32con
import win32api
import win32process
import psutil
import os
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from datetime import datetime
from typing import Any, cast
from .monitor_manager import MonitorManager
from .config_manager import ConfigManager


# SendInput structures for keyboard simulation
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]


def _press_key(hex_key_code):
    """Press a key using SendInput."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(hex_key_code, 0, 0, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def _release_key(hex_key_code):
    """Release a key using SendInput."""
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(hex_key_code, 0, 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


class WindowManager:
    """Manages window detection and movement to specified monitors."""

    def __init__(self, config_manager=None, monitor_manager=None, layout_manager=None):
        """Initialize the window manager.

        Args:
            config_manager (ConfigManager, optional): Configuration manager instance.
                If None, creates a new instance.
            monitor_manager (MonitorManager, optional): Monitor manager instance.
                If None, creates a new instance.
            layout_manager (LayoutManager, optional): Layout manager instance.
                Required for rule-based window management.
        """
        self.logger = logging.getLogger("ScreenAssign.WindowManager")

        if config_manager is None:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = config_manager

        if monitor_manager is None:
            self.monitor_manager = MonitorManager(self.config_manager)
        else:
            self.monitor_manager = monitor_manager

        self.layout_manager = layout_manager

        # Classification (we tag; we don't hide).
        # These sets are intentionally conservative; add more as you observe windows in the wild.
        self.system_classnames = {
            "Progman",  # Desktop
            "WorkerW",  # Desktop background host
            "Shell_TrayWnd",  # Taskbar
            "Shell_SecondaryTrayWnd",  # Secondary taskbar
        }
        self.system_titles = {
            "Program Manager",
        }
        self.system_process_names = {
            "SystemSettings.exe",
            "SearchUI.exe",
            "StartMenuExperienceHost.exe",
            "ShellExperienceHost.exe",
            "RuntimeBroker.exe",
            "dwm.exe",
            "sihost.exe",
            "ctfmon.exe",
            "taskhostw.exe",
        }

        # WinSwitcher-style excluded windows (applies to the window list only; rules still act
        # only on matched windows).
        # NOTE: do not include ApplicationFrameHost.exe (keep UWP visible).
        self.excluded_window_filenames = {
            "SystemSettings.exe",
            "TextInputHost.exe",
            "HxOutlook.exe",
            "ShellExperienceHost.exe",
        }

        # Cache for expensive per-exe lookups (e.g. version info FileDescription)
        self._app_display_name_cache: dict[str, str] = {}

    def _get_window_rect(self, hwnd: int):
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            return left, top, right - left, bottom - top
        except Exception:
            return 0, 0, 0, 0

    def _enum_top_level_windows(self) -> list[int]:
        hwnds: list[int] = []

        def _cb(hwnd, lparam):
            try:
                # Only consider real top-level windows
                if not win32gui.IsWindow(hwnd):
                    return True

                if not win32gui.IsWindowVisible(hwnd):
                    return True

                hwnds.append(hwnd)
            except Exception:
                # Keep enumeration resilient
                pass
            return True

        win32gui.EnumWindows(_cb, None)
        return hwnds

    def get_all_windows(self):
        """Get all visible windows.

        Returns:
            list: List of window information dictionaries
        """
        windows: list[dict] = []

        for hwnd in self._enum_top_level_windows():
            try:
                title = win32gui.GetWindowText(hwnd)
                class_name = self.get_window_class(hwnd)

                is_minimized = False
                try:
                    is_minimized = bool(win32gui.IsIconic(hwnd))
                except Exception:
                    is_minimized = False

                pid = self.get_window_pid(hwnd)
                process_path = self.get_process_path_from_pid(pid)
                exe_name = self._exe_name_from_path(process_path)

                is_uwp = self.is_uwp_window(class_name=class_name, exe_name=exe_name)
                is_system = self.is_system_window(
                    title=title, class_name=class_name, exe_name=exe_name
                )

                # Exclude the Window Switcher itself by unique marker
                if "__SCREENY_WINDOW_SWITCHER_UNIQUE_MARKER__" in title:
                    continue

                # WinSwitcher: exclude some known junk windows by exe filename.
                if exe_name and exe_name in self.excluded_window_filenames:
                    continue

                # WinSwitcher behavior: ignore empty-title windows.
                # Exception: keep system windows even if title is empty so they can be targeted by rules.
                if not (title and title.strip()):
                    if not is_system:
                        continue

                left, top, width, height = self._get_window_rect(hwnd)

                app_display_name = self.get_app_display_name(process_path)

                window_info = {
                    "hwnd": hwnd,
                    "title": title,
                    # Backwards-compatible field used by rules/UI; make it stable (exe name).
                    "app_name": exe_name,
                    "class_name": class_name,
                    "pid": pid,
                    "process_path": process_path,
                    "exe_name": exe_name,
                    "app_display_name": app_display_name,
                    "is_system": is_system,
                    "is_uwp": is_uwp,
                    "is_minimized": is_minimized,
                    "position": (left, top, width, height),
                    "is_maximized": self.is_window_maximized(hwnd),
                    "monitor_id": self.get_window_monitor_id(hwnd),
                }

                windows.append(window_info)
            except Exception as e:
                self.logger.debug(
                    f"Error getting window info for hwnd={hwnd}: {str(e)}"
                )

        return windows

    def get_window_pid(self, hwnd: int) -> int | None:
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return int(pid) if pid else None
        except Exception:
            return None

    def get_process_path_from_pid(self, pid: int | None) -> str | None:
        if not pid:
            return None
        try:
            return psutil.Process(pid).exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        except Exception:
            pass

        # Fallback: ask Windows for the module filename
        try:
            hproc = win32api.OpenProcess(
                win32con.PROCESS_QUERY_LIMITED_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            try:
                exe_path = win32process.GetModuleFileNameEx(hproc, 0)
                return exe_path or None
            finally:
                win32api.CloseHandle(hproc)
        except Exception:
            return None

    def _exe_name_from_path(self, process_path: str | None) -> str | None:
        if not process_path:
            return None
        try:
            return Path(process_path).name
        except Exception:
            return os.path.basename(process_path)

    def get_app_display_name(self, process_path: str | None) -> str | None:
        """Best-effort human name for an exe.

        Uses the Windows version resource FileDescription when available, otherwise
        falls back to the exe filename.
        """
        if not process_path:
            return None

        cached = self._app_display_name_cache.get(process_path)
        if cached is not None:
            return cached

        title: str | None = None
        try:
            langs_any: Any = win32api.GetFileVersionInfo(
                process_path, r"\VarFileInfo\Translation"
            )
            langs = cast(list[tuple[int, int]], langs_any) if langs_any else []
            if langs:
                lang, codepage = langs[0]
                key = r"StringFileInfo\%04x%04x\FileDescription" % (lang, codepage)
                raw_title: Any = win32api.GetFileVersionInfo(process_path, key)
                if isinstance(raw_title, str):
                    title = raw_title
                elif raw_title:
                    title = str(raw_title)
        except Exception:
            title = None

        if not title:
            title = self._exe_name_from_path(process_path) or process_path

        # Ensure cache always stores a string
        title_str = str(title)
        self._app_display_name_cache[process_path] = title_str
        return title_str

    def is_system_window(
        self, title: str | None, class_name: str | None, exe_name: str | None
    ) -> bool:
        t = (title or "").strip()
        if t and t in self.system_titles:
            return True
        if class_name and class_name in self.system_classnames:
            return True
        if exe_name and exe_name in self.system_process_names:
            return True
        return False

    def is_uwp_window(self, class_name: str | None, exe_name: str | None) -> bool:
        if class_name in {"ApplicationFrameWindow", "Windows.UI.Core.CoreWindow"}:
            return True
        if exe_name and exe_name.lower() == "applicationframehost.exe":
            return True
        return False

    def get_window_class(self, hwnd):
        """Get the window class name.

        Args:
            hwnd (int): Window handle

        Returns:
            str: Window class name or None on error
        """
        try:
            return win32gui.GetClassName(hwnd)
        except Exception:
            return None

    def get_process_name(self, hwnd):
        """Get the process name for a window.

        Args:
            hwnd (int): Window handle

        Returns:
            str: Process name or None on error
        """
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return None

            try:
                return psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            # Fallback: ask Windows for the module filename
            try:
                hproc = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_LIMITED_INFORMATION
                    | win32con.PROCESS_VM_READ,
                    False,
                    pid,
                )
                try:
                    exe_path = win32process.GetModuleFileNameEx(hproc, 0)
                    if exe_path:
                        return os.path.basename(exe_path)
                finally:
                    win32api.CloseHandle(hproc)
            except Exception:
                return None
        except Exception as e:
            self.logger.debug(f"Failed to get process name from window handle: {e}")
            return None

    def is_window_maximized(self, hwnd):
        """Check if a window is maximized.

        Args:
            hwnd (int): Window handle

        Returns:
            bool: True if maximized, False otherwise
        """
        try:
            placement = win32gui.GetWindowPlacement(hwnd)
            return placement[1] == win32con.SW_SHOWMAXIMIZED
        except Exception:
            return False

    def get_window_monitor_id(self, hwnd):
        """Get the ID of the monitor containing a window.

        Args:
            hwnd (int): Window handle

        Returns:
            str: Monitor ID or None if not found
        """
        try:
            rect = win32gui.GetWindowRect(hwnd)
            window_center_x = (rect[0] + rect[2]) // 2
            window_center_y = (rect[1] + rect[3]) // 2

            return self.monitor_manager.get_monitor_by_position(
                window_center_x, window_center_y
            )
        except Exception:
            return None

    def is_window_on_monitor(self, hwnd, monitor_id):
        """Check if window is on the specified monitor.

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID

        Returns:
            bool: True if window is on target monitor
        """
        current_monitor_id = self.get_window_monitor_id(hwnd)
        return current_monitor_id == monitor_id

    def is_window_in_correct_state(
        self, hwnd, monitor_id, monitor, maximize
    ):
        """Check if window is in the desired state (position + maximize).

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            monitor: Monitor object (screeninfo)
            maximize (bool): Should be maximized

        Returns:
            bool: True if window matches desired state exactly
        """
        if not self.is_window_on_monitor(hwnd, monitor_id):
            return False

        is_max = self.is_window_maximized(hwnd)
        return is_max if maximize else not is_max

    # NOTE: We intentionally do not keep a broad "ignore" filter anymore.
    # Listing should be close to what WinSwitcher would enumerate: visible + title,
    # with a small exception for system windows so they can still be rule-targeted.

    def move_window_to_monitor(self, hwnd, monitor_id, maximize=True):
        """Move a window to a specific monitor.

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            maximize (bool): Whether to maximize the window

        Returns:
            bool: True if successful, False otherwise
        """
        monitor = self.monitor_manager.get_connected_monitor(monitor_id)
        if not monitor:
            self.logger.warning(f"Monitor {monitor_id} is not connected")
            return False

        if maximize:
            self.move_and_maximize_window(hwnd, monitor)
        else:
            # Just move without changing size
            current_placement = win32gui.GetWindowPlacement(hwnd)
            win32gui.MoveWindow(
                hwnd,
                monitor.x,
                monitor.y,
                current_placement[4][2] - current_placement[4][0],  # width
                current_placement[4][3] - current_placement[4][1],  # height
                True,
            )

        return True

    def move_and_maximize_window(self, hwnd, monitor):
        """Move a window to a monitor and maximize it.

        Args:
            hwnd (int): Window handle
            monitor: Monitor object
        """
        # First restore the window to clear any weird maximized state
        # (e.g., if user accidentally moved a maximized window)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Move to monitor center (so Windows knows which monitor to maximize on)
        win32gui.MoveWindow(
            hwnd, monitor.x, monitor.y, monitor.width, monitor.height, True
        )

        # Now maximize on the correct monitor
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    # ============================================================================
    # NEW REFACTORED FUNCTIONS - Separate Move and Maximize
    # ============================================================================

    def move_window(self, hwnd, monitor):
        """Move window to target monitor (restores first if maximized).

        Args:
            hwnd (int): Window handle
            monitor: Monitor object with x, y, width, height
        """
        window_title = win32gui.GetWindowText(hwnd)

        # Restore window first (clears maximized state)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # Move to monitor - use full monitor size for clean positioning
        win32gui.MoveWindow(
            hwnd, monitor.x, monitor.y, monitor.width, monitor.height, True
        )

        self.logger.info(
            f"Moved '{window_title}' to monitor at ({monitor.x}, {monitor.y})"
        )

    def maximize_window(self, hwnd, monitor):
        """Maximize window on specified monitor.

        Args:
            hwnd (int): Window handle
            monitor: Monitor object (for logging/verification)
        """
        window_title = win32gui.GetWindowText(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.logger.info(f"Maximized '{window_title}'")

    def apply_window_rule(self, hwnd, monitor_id, maximize=False):
        """Apply positioning rule to window with smart state checking.

        Only performs operations that are needed to reach desired state.
        Checks if window is already in correct position/state before taking action.

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            maximize (bool): Should be maximized

        Returns:
            dict: Result with keys:
                - 'changed' (bool): True if any operations were performed
                - 'operations' (list): List of operations performed (e.g., ['move', 'maximize'])
        """
        window_title = win32gui.GetWindowText(hwnd)
        monitor = self.monitor_manager.get_connected_monitor(monitor_id)

        if not monitor:
            self.logger.warning(f"Monitor {monitor_id} not connected")
            return {"changed": False, "operations": []}

        # Check if already in correct state
        if self.is_window_in_correct_state(hwnd, monitor_id, monitor, maximize):
            self.logger.debug(
                f"Window '{window_title}' already in correct state, skipping"
            )
            return {"changed": False, "operations": []}

        operations = []

        # Step 1: Check if window needs to move to different monitor
        needs_move = not self.is_window_on_monitor(hwnd, monitor_id)

        if needs_move:
            self.logger.info(f"Moving '{window_title}' to monitor {monitor_id}")
            self.move_window(hwnd, monitor)
            operations.append("move")
            time.sleep(0.3)  # Let move settle

        # Step 2: Apply maximize / normal state
        current_maximized = self.is_window_maximized(hwnd)

        if maximize:
            if not current_maximized:
                self.logger.info(f"Maximizing '{window_title}'")
                self.maximize_window(hwnd, monitor)
                operations.append("maximize")
        else:
            # Un-maximize if needed (already done by move_window if we moved)
            if current_maximized and not needs_move:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                operations.append("restore")

        return {"changed": True, "operations": operations}

    def apply_rules_for_window(self, hwnd: int, layout_name: str, assignment: dict) -> dict:
        """Apply rules to a single window identified by hwnd.

        Finds a matching rule for the given window and applies it.
        Much faster than apply_rules() -- only processes one window.

        Args:
            hwnd: Window handle to apply rules to
            layout_name: Name of the layout whose rules to apply
            assignment:  Slot->identity_key mapping from the frontend

        Returns:
            dict with keys:
              - 'matched' (bool): True if a rule was found for this window
              - 'changed' (bool): True if any operations were performed
              - 'operations' (list): Operations performed
              - 'rule_id' (str|None): The matched rule id, if any
              - 'message' (str): Human-readable summary
        """
        if not self.layout_manager:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": "No layout_manager configured",
            }

        try:
            rules = self.layout_manager.get_rules_for_layout(layout_name, assignment)
        except Exception as e:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": f"Could not load rules for layout '{layout_name}': {e}",
            }
        if not rules:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": f"No rules found in layout '{layout_name}'",
            }

        # Build window info for this hwnd
        try:
            title = win32gui.GetWindowText(hwnd)
            class_name = self.get_window_class(hwnd)
            pid = self.get_window_pid(hwnd)
            process_path = self.get_process_path_from_pid(pid)
            exe_name = self._exe_name_from_path(process_path)
            is_minimized = bool(win32gui.IsIconic(hwnd))
        except Exception as e:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": f"Could not inspect window hwnd={hwnd}: {e}",
            }

        if is_minimized:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": "Window is minimized — skipping rule application",
            }

        def _norm_exe(s: str) -> str:
            s = (s or "").strip().lower()
            return s if s.endswith(".exe") else (s + ".exe" if s else s)

        # Find the first matching rule for this window
        matched_rule = None
        for rule in rules:
            match_type = rule.get("match_type")
            match_value = (rule.get("match_value") or "").strip()
            mv_lower = match_value.lower()

            if match_type == "exe":
                if _norm_exe(exe_name) == _norm_exe(mv_lower):
                    matched_rule = rule
                    break
            elif match_type == "window_title":
                if mv_lower and mv_lower in (title or "").lower():
                    matched_rule = rule
                    break
            elif match_type == "process_path":
                if mv_lower and mv_lower == (process_path or "").lower():
                    matched_rule = rule
                    break

        if not matched_rule:
            return {
                "matched": False,
                "changed": False,
                "operations": [],
                "rule_id": None,
                "message": f"No rule matched window '{title}' (exe={exe_name})",
            }

        target_monitor_id = matched_rule.get("target_monitor_id")
        if not self.monitor_manager.is_monitor_connected(target_monitor_id):
            return {
                "matched": True,
                "changed": False,
                "operations": [],
                "rule_id": matched_rule.get("rule_id"),
                "message": f"Target monitor {target_monitor_id} is not connected",
            }

        self.logger.info(
            f"Applying rule '{matched_rule.get('rule_id')}' to window '{title}' (hwnd={hwnd})"
        )

        result = self.apply_window_rule(
            hwnd,
            target_monitor_id,
            maximize=matched_rule.get("maximize", False),
        )

        return {
            "matched": True,
            "changed": result["changed"],
            "operations": result["operations"],
            "rule_id": matched_rule.get("rule_id"),
            "message": (
                f"Applied: {', '.join(result['operations'])}"
                if result["changed"]
                else "Window already in correct state"
            ),
        }

    def apply_rules(self, layout_name: str, assignment: dict):
        """Apply window placement rules from the specified layout.

        Args:
            layout_name: Name of the layout whose rules to apply
            assignment:  Slot->identity_key mapping from the frontend

        Returns:
            dict: Summary of applied rules
        """
        # First, make sure monitors are detected
        self.monitor_manager.detect_monitors()

        if not self.layout_manager:
            self.logger.warning("No layout_manager configured - cannot apply rules")
            return {
                "applied": 0,
                "skipped_no_monitor": 0,
                "skipped_no_window": 0,
                "failed": 0,
                "details": [],
            }

        try:
            rules = self.layout_manager.get_rules_for_layout(layout_name, assignment)
        except Exception as e:
            self.logger.error(f"Could not load rules for layout '{layout_name}': {e}")
            return {
                "applied": 0,
                "skipped_no_monitor": 0,
                "skipped_no_window": 0,
                "failed": 0,
                "details": [],
            }

        if not rules:
            self.logger.debug(f"No rules found in layout '{layout_name}'")
            return {
                "applied": 0,
                "skipped_no_monitor": 0,
                "skipped_no_window": 0,
                "failed": 0,
                "details": [],
            }

        # Get all windows
        windows = self.get_all_windows()

        # Track results
        results = {
            "applied": 0,
            "skipped_no_monitor": 0,
            "skipped_no_window": 0,
            "failed": 0,
            "details": [],
        }

        # Apply each rule (no need to check "enabled" - layout active = all rules active)
        for rule in rules:
            target_monitor_id = rule.get("target_monitor_id")
            if not self.monitor_manager.is_monitor_connected(target_monitor_id):
                self.logger.debug(
                    f"Skipping rule {rule['rule_id']}: target monitor not connected"
                )
                results["skipped_no_monitor"] += 1
                results["details"].append(
                    {
                        "rule_id": rule["rule_id"],
                        "result": "skipped_no_monitor",
                        "message": f"Target monitor {target_monitor_id} is not connected",
                    }
                )
                continue

            # Find matching windows
            matching_windows = []
            match_type = rule.get("match_type")
            match_value = rule.get("match_value")

            mv = (match_value or "").strip()
            mv_lower = mv.lower()

            def _norm_exe(s: str) -> str:
                s = (s or "").strip().lower()
                if s.endswith(".exe"):
                    return s
                return s + ".exe" if s else s

            for window in windows:
                if match_type == "exe":
                    exe_name = (
                        window.get("exe_name") or window.get("app_name") or ""
                    ).strip()
                    if _norm_exe(exe_name) == _norm_exe(mv_lower):
                        matching_windows.append(window)
                elif match_type == "window_title":
                    title = (window.get("title") or "").lower()
                    if mv_lower and mv_lower in title:
                        matching_windows.append(window)
                elif match_type == "process_path":
                    process_path = (window.get("process_path") or "").lower()
                    if mv_lower and mv_lower == process_path:
                        matching_windows.append(window)

            if not matching_windows:
                self.logger.debug(
                    f"Skipping rule {rule['rule_id']}: no matching windows"
                )
                results["skipped_no_window"] += 1
                results["details"].append(
                    {
                        "rule_id": rule["rule_id"],
                        "result": "skipped_no_window",
                        "message": f"No windows match {match_type}={match_value}",
                    }
                )
                continue

            # Apply the rule to all matching windows
            for window in matching_windows:
                try:
                    # Only apply to windows that are currently not minimized.
                    # This lets users temporarily opt-out by minimizing.
                    if window.get("is_minimized"):
                        self.logger.debug(
                            f"Skipping minimized window: {window.get('title') or '(untitled)'}"
                        )
                        continue

                    # Skip windows with empty titles (system windows, popups)
                    window_title = window.get("title", "").strip()
                    if not window_title:
                        self.logger.debug(
                            f"Skipping window with empty title (hwnd={window['hwnd']})"
                        )
                        continue

                    # Skip "Program Manager" (Windows Desktop)
                    if window_title == "Program Manager":
                        self.logger.debug(f"Skipping Program Manager (Windows Desktop)")
                        continue

                    # Apply rule with smart state checking
                    result = self.apply_window_rule(
                        window["hwnd"],
                        target_monitor_id,
                        maximize=rule.get("maximize", False),
                    )

                    if result["changed"]:
                        results["applied"] += 1
                        operations_str = ", ".join(result["operations"])
                        self.logger.info(
                            f"Applied rule to '{window['title']}': {operations_str}"
                        )
                    else:
                        # Window already in correct state - just debug log
                        self.logger.debug(
                            f"Window '{window['title']}' already in correct state"
                        )

                except Exception as e:
                    self.logger.error(
                        f"Error applying rule {rule['rule_id']} to window: {str(e)}"
                    )
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "rule_id": rule["rule_id"],
                            "result": "error",
                            "message": str(e),
                        }
                    )

        return results
