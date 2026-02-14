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
                    "is_fullscreen": self.is_window_fullscreen(hwnd),
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

    def is_window_fullscreen(self, hwnd):
        """Check if a window is in fullscreen mode.

        Args:
            hwnd (int): Window handle

        Returns:
            bool: True if in fullscreen mode, False otherwise
        """
        try:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

            # Convert to unsigned if negative
            if style < 0:
                style = style & 0xFFFFFFFF

            # Check window style flags
            has_popup = bool(style & win32con.WS_POPUP)
            has_caption = bool(style & win32con.WS_CAPTION)
            has_border = bool(style & win32con.WS_THICKFRAME)

            # TEST: Try detection without WS_POPUP requirement
            # Original logic: is_fullscreen = has_popup and not has_caption and not has_border
            # New logic: Drop WS_POPUP requirement (modern apps might not use it)
            is_fullscreen = not has_caption and not has_border

            return is_fullscreen
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
        self, hwnd, monitor_id, monitor, maximize, fullscreen
    ):
        """Check if window is in the desired state (position + maximize/fullscreen).

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            monitor: Monitor object (screeninfo)
            maximize (bool): Should be maximized
            fullscreen (bool): Should be fullscreen

        Returns:
            bool: True if window matches desired state exactly
        """
        # Check 1: Is it on the correct monitor?
        if not self.is_window_on_monitor(hwnd, monitor_id):
            return False

        # Check 2: Does state match?
        if fullscreen:
            # For fullscreen: Must be fullscreen (no caption/thickframe)
            return self.is_window_fullscreen(hwnd)
        elif maximize:
            # For maximize: Must be maximized and NOT fullscreen
            is_max = self.is_window_maximized(hwnd)
            is_full = self.is_window_fullscreen(hwnd)
            return is_max and not is_full
        else:
            # For normal: Must NOT be maximized or fullscreen
            is_max = self.is_window_maximized(hwnd)
            is_full = self.is_window_fullscreen(hwnd)
            return not is_max and not is_full

    # NOTE: We intentionally do not keep a broad "ignore" filter anymore.
    # Listing should be close to what WinSwitcher would enumerate: visible + title,
    # with a small exception for system windows so they can still be rule-targeted.

    def move_window_to_monitor(self, hwnd, monitor_id, maximize=True, fullscreen=False):
        """Move a window to a specific monitor.

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            maximize (bool): Whether to maximize the window
            fullscreen (bool): Whether to make the window fullscreen

        Returns:
            bool: True if successful, False otherwise
        """
        monitor = self.monitor_manager.get_connected_monitor(monitor_id)
        if not monitor:
            self.logger.warning(f"Monitor {monitor_id} is not connected")
            return False

        if fullscreen:
            self.move_and_fullscreen_window(hwnd, monitor)
        elif maximize:
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
    # NEW REFACTORED FUNCTIONS - Separate Move, Maximize, and Fullscreen
    # ============================================================================

    def move_window(self, hwnd, monitor):
        """Move window to target monitor (restores first if maximized/fullscreen).

        Args:
            hwnd (int): Window handle
            monitor: Monitor object with x, y, width, height
        """
        window_title = win32gui.GetWindowText(hwnd)

        # Restore window first (clears maximized/fullscreen state)
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

        If window is currently fullscreen, exits fullscreen first.

        Args:
            hwnd (int): Window handle
            monitor: Monitor object (for logging/verification)
        """
        window_title = win32gui.GetWindowText(hwnd)

        # If currently fullscreen, exit first
        if self.is_window_fullscreen(hwnd):
            self.logger.info(f"'{window_title}' is fullscreen, exiting before maximize")
            # Send F11 to exit fullscreen
            self.fullscreen_window(hwnd, wait_time=0.6)

        # Maximize
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        self.logger.info(f"Maximized '{window_title}'")

    def fullscreen_window(self, hwnd, wait_time=0.6):
        """Send F11 to window to toggle fullscreen state.

        This function toggles the fullscreen state - if window is fullscreen,
        it exits; if normal, it enters fullscreen.

        Args:
            hwnd (int): Window handle
            wait_time (float): Seconds to wait for fullscreen animation (default 0.6s)
        """
        window_title = win32gui.GetWindowText(hwnd)

        # DEBUG: Log style BEFORE sending F11
        style_before = None
        try:
            style_before = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if style_before < 0:
                style_before = style_before & 0xFFFFFFFF
            has_caption_before = bool(style_before & win32con.WS_CAPTION)
            has_border_before = bool(style_before & win32con.WS_THICKFRAME)
            has_popup_before = bool(style_before & win32con.WS_POPUP)
            self.logger.info(
                f"[DEBUG] '{window_title}' BEFORE F11: style=0x{style_before:08X} "
                f"POPUP={has_popup_before} CAPTION={has_caption_before} BORDER={has_border_before}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to get style before F11: {e}")

        # Save original foreground
        try:
            original_fg = win32gui.GetForegroundWindow()
        except Exception:
            original_fg = None

        # Set window as foreground (required for SendInput)
        # Retry several times because Windows can be finicky about focus
        foreground_success = False
        for attempt in range(3):
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.1)  # Brief wait

                # Verify it worked
                current_fg = win32gui.GetForegroundWindow()
                if current_fg == hwnd:
                    foreground_success = True
                    self.logger.debug(
                        f"SetForegroundWindow succeeded for '{window_title}' (attempt {attempt + 1})"
                    )
                    break
                else:
                    if attempt < 2:
                        self.logger.debug(
                            f"Focus not obtained, retrying... (attempt {attempt + 1})"
                        )
                        time.sleep(0.2)
            except Exception as e:
                if attempt < 2:
                    self.logger.debug(
                        f"SetForegroundWindow failed (attempt {attempt + 1}): {e}"
                    )
                    time.sleep(0.2)
                else:
                    self.logger.warning(
                        f"Failed to set foreground for '{window_title}' after {attempt + 1} attempts: {e}"
                    )

        if not foreground_success:
            self.logger.warning(
                f"Could not obtain focus for '{window_title}' - F11 may not work correctly"
            )

        # Send F11
        VK_F11 = 0x7A
        _press_key(VK_F11)
        time.sleep(0.05)
        _release_key(VK_F11)

        self.logger.info(
            f"Sent F11 to '{window_title}', waiting {wait_time}s for transition"
        )

        # CRITICAL: Wait for fullscreen animation to complete
        time.sleep(wait_time)

        # DEBUG: Log style AFTER waiting
        try:
            style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if style_after < 0:
                style_after = style_after & 0xFFFFFFFF
            has_caption_after = bool(style_after & win32con.WS_CAPTION)
            has_border_after = bool(style_after & win32con.WS_THICKFRAME)
            has_popup_after = bool(style_after & win32con.WS_POPUP)

            style_changed = (style_before is not None) and (style_before != style_after)
            self.logger.info(
                f"[DEBUG] '{window_title}' AFTER F11: style=0x{style_after:08X} "
                f"POPUP={has_popup_after} CAPTION={has_caption_after} BORDER={has_border_after} "
                f"(changed={style_changed})"
            )

            # Log what the detection function sees
            is_fullscreen_now = self.is_window_fullscreen(hwnd)
            self.logger.info(
                f"[DEBUG] Detection result: is_fullscreen={is_fullscreen_now}"
            )
        except Exception as e:
            self.logger.warning(f"Failed to get style after F11: {e}")

        # Restore original foreground (after animation completes)
        if original_fg and original_fg != hwnd:
            try:
                win32gui.SetForegroundWindow(original_fg)
                self.logger.debug("Restored original foreground window")
            except Exception:
                pass

    # ============================================================================
    # END NEW FUNCTIONS
    # ============================================================================

    def move_and_fullscreen_window(self, hwnd, monitor):
        """Move window to a monitor and make it fullscreen by sending F11.

        FULLSCREEN DETECTION EXPLANATION:
        ---------------------------------
        Modern applications (browsers, terminals) draw their own custom titlebars
        in the client area. The "proper way" to fullscreen them is to send F11,
        which tells the app to enter its native fullscreen mode.

        We detect fullscreen by checking window style bits:

        NON-FULLSCREEN window has these style bits SET:
          - WS_CAPTION (0x00C00000) - Has titlebar
          - WS_THICKFRAME (0x00040000) - Has resize border
          Example style: 0x17CF0000 (normal window with chrome)

        FULLSCREEN window has these bits REMOVED:
          - No WS_CAPTION
          - No WS_THICKFRAME
          Example style: 0x170B0000 (fullscreen, no visible chrome)

        Note: Modern apps KEEP WS_MINIMIZEBOX and WS_MAXIMIZEBOX bits even in
        fullscreen mode, so we don't check those. We only check CAPTION and THICKFRAME.

        When the app responds to F11, it removes these style bits itself.

        APPROACH: Use SendInput to simulate real F11 keypress
        --------------------------------------------------------
        Apps with custom titlebars don't respond to SendMessage/PostMessage.
        We need to use SendInput to simulate a real keyboard event.

        1. Save original foreground window
        2. Check if already fullscreen (test min/max box bits)
        3. Move and maximize to target monitor
        4. SetForegroundWindow (required for SendInput to work)
        5. Send F11 via SendInput (press + release)
        6. Restore original foreground window
        7. Verify style bits changed

        Args:
            hwnd (int): Window handle
            monitor: Monitor object
        """
        window_title = win32gui.GetWindowText(hwnd)

        # Step 1: Save original foreground window so we can restore it after
        try:
            original_fg = win32gui.GetForegroundWindow()
        except Exception:
            original_fg = None

        # Step 2: Get the current window style (convert to unsigned 32-bit)
        current_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # CRITICAL: Convert signed to unsigned for proper bit checking
        if current_style < 0:
            current_style = current_style & 0xFFFFFFFF

        # Check if window is already in fullscreen mode
        # Modern apps (browsers, terminals) with custom titlebars show fullscreen by:
        # - Removing WS_CAPTION (no titlebar)
        # - Removing WS_THICKFRAME (no resize borders)
        # They KEEP min/max boxes in the style bits even though they're not visible
        has_caption = bool(current_style & win32con.WS_CAPTION)
        has_thickframe = bool(current_style & win32con.WS_THICKFRAME)

        # A window is considered fullscreen if it has neither caption nor thickframe
        is_already_fullscreen = not has_caption and not has_thickframe

        if is_already_fullscreen:
            self.logger.debug(
                f"[FULLSCREEN] {window_title} already in fullscreen mode (style: 0x{current_style:08X}), skipping F11"
            )
            return

        self.logger.info(f"[FULLSCREEN] Starting fullscreen for: {window_title}")
        self.logger.info(
            f"[FULLSCREEN] Current style: 0x{current_style:08X} (not fullscreen)"
        )

        # Step 3: Move and maximize the window to the target monitor
        self.logger.info(
            f"[FULLSCREEN] Moving to monitor: ({monitor.x}, {monitor.y}, {monitor.width}x{monitor.height})"
        )
        self.move_and_maximize_window(hwnd, monitor)
        time.sleep(0.2)  # Let window settle

        # Step 4: Set foreground window (required for SendInput to work)
        self.logger.info(f"[FULLSCREEN] Setting foreground window for SendInput")
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            self.logger.warning(
                f"[FULLSCREEN] Failed to set foreground window: {e} - F11 may not work"
            )

        time.sleep(0.2)  # Let focus settle

        # Step 5: Send F11 key via SendInput (simulates real keyboard input)
        self.logger.info(f"[FULLSCREEN] Sending F11 via SendInput")
        VK_F11 = 0x7A

        _press_key(VK_F11)
        time.sleep(0.05)
        _release_key(VK_F11)
        time.sleep(0.3)  # Wait for app to respond to F11

        # Step 6: Restore original foreground window
        if original_fg and original_fg != hwnd:
            self.logger.debug(
                f"[FULLSCREEN] Restoring original foreground window: {original_fg}"
            )
            try:
                win32gui.SetForegroundWindow(original_fg)
            except Exception as e:
                self.logger.debug(
                    f"[FULLSCREEN] Could not restore foreground window: {e}"
                )

        # Step 7: Verify fullscreen was applied
        style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        if style_after < 0:
            style_after = style_after & 0xFFFFFFFF

        has_caption_after = bool(style_after & win32con.WS_CAPTION)
        has_thickframe_after = bool(style_after & win32con.WS_THICKFRAME)

        if not has_caption_after and not has_thickframe_after:
            self.logger.info(
                f"[FULLSCREEN] SUCCESS: Entered fullscreen mode (style: 0x{style_after:08X})"
            )
        else:
            self.logger.warning(
                f"[FULLSCREEN] FAILED: Window may not be fullscreen (style: 0x{style_after:08X}) - app may not support F11"
            )

    def apply_window_rule(self, hwnd, monitor_id, maximize=False, fullscreen=False):
        """Apply positioning rule to window with smart state checking.

        Only performs operations that are needed to reach desired state.
        Checks if window is already in correct position/state before taking action.

        Args:
            hwnd (int): Window handle
            monitor_id (str): Target monitor ID
            maximize (bool): Should be maximized
            fullscreen (bool): Should be fullscreen

        Returns:
            dict: Result with keys:
                - 'changed' (bool): True if any operations were performed
                - 'operations' (list): List of operations performed (e.g., ['move', 'fullscreen'])
        """
        window_title = win32gui.GetWindowText(hwnd)
        monitor = self.monitor_manager.get_connected_monitor(monitor_id)

        if not monitor:
            self.logger.warning(f"Monitor {monitor_id} not connected")
            return {"changed": False, "operations": []}

        # Check if already in correct state
        if self.is_window_in_correct_state(
            hwnd, monitor_id, monitor, maximize, fullscreen
        ):
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

        # Step 2: Check current state vs desired state
        current_fullscreen = self.is_window_fullscreen(hwnd)
        current_maximized = self.is_window_maximized(hwnd)

        # Scenario A: Want fullscreen
        if fullscreen:
            if not current_fullscreen:
                self.logger.info(f"Fullscreening '{window_title}'")
                # If currently maximized, position might be correct already
                if not current_maximized:
                    self.maximize_window(hwnd, monitor)
                    operations.append("maximize")
                    time.sleep(0.2)
                self.fullscreen_window(hwnd, wait_time=1.5)
                operations.append("fullscreen")

                # Wait additional time for window to fully update its style
                time.sleep(0.5)

                # Verify fullscreen was applied
                style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                if style_after < 0:
                    style_after = style_after & 0xFFFFFFFF
                has_caption = bool(style_after & win32con.WS_CAPTION)
                has_thickframe = bool(style_after & win32con.WS_THICKFRAME)

                if has_caption or has_thickframe:
                    self.logger.warning(
                        f"Window '{window_title}' may not be fullscreen (style: 0x{style_after:08X}) - app may not support F11"
                    )

        # Scenario C: Want maximize (but currently fullscreen)
        elif maximize:
            if current_fullscreen:
                self.logger.info(
                    f"Exiting fullscreen for '{window_title}' (needs maximize)"
                )
                self.fullscreen_window(hwnd, wait_time=0.6)  # Toggle off
                operations.append("exit_fullscreen")

            if not current_maximized or current_fullscreen:
                self.logger.info(f"Maximizing '{window_title}'")
                self.maximize_window(hwnd, monitor)
                operations.append("maximize")

        # Normal state: Neither maximize nor fullscreen
        else:
            # Exit fullscreen if needed
            if current_fullscreen:
                self.logger.info(
                    f"Exiting fullscreen for '{window_title}' (rule wants normal)"
                )
                self.fullscreen_window(hwnd, wait_time=0.6)
                operations.append("exit_fullscreen")

            # Un-maximize if needed (already done by move_window if we moved)
            if current_maximized and not needs_move:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                operations.append("restore")

        return {"changed": True, "operations": operations}

    def apply_rules(self):
        """Apply window placement rules from active layout.

        Returns:
            dict: Summary of applied rules
        """
        # First, make sure monitors are detected
        self.monitor_manager.detect_monitors()

        # Get rules from active layout (if any)
        if not self.layout_manager:
            self.logger.warning("No layout_manager configured - cannot apply rules")
            return {
                "applied": 0,
                "skipped_no_monitor": 0,
                "skipped_no_window": 0,
                "failed": 0,
                "details": [],
            }

        rules = self.layout_manager.get_active_rules()

        if not rules:
            self.logger.debug("No active layout - no rules to apply")
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
                    rule_fullscreen = rule.get("fullscreen", False)
                    rule_maximize = rule.get("maximize", False)

                    result = self.apply_window_rule(
                        window["hwnd"],
                        target_monitor_id,
                        maximize=rule_maximize,
                        fullscreen=rule_fullscreen,
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
