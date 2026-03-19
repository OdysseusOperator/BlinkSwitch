import os
import time
import json
import logging
import threading
from datetime import datetime

from .config_manager import ConfigManager
from .layout_manager import LayoutManager
from .monitor_manager import MonitorManager
from .window_manager import WindowManager


class ScreenAssignService:
    """Main service class for the ScreenAssign application."""

    def __init__(self, config_path=None):
        """Initialize the ScreenAssign service.

        Args:
            config_path (str, optional): Path to the config file. If None, uses default location.
        """
        self.logger = logging.getLogger("ScreenAssign.Service")

        # Initialize managers
        self.config_manager = ConfigManager(config_path)
        self.monitor_manager = MonitorManager(self.config_manager)

        # Layouts directory is in backend/layouts
        layouts_dir = os.path.join(os.path.dirname(__file__), "layouts")
        self.layout_manager = LayoutManager(
            self.config_manager, self.monitor_manager, layouts_dir=layouts_dir
        )
        self.window_manager = WindowManager(
            self.config_manager, self.monitor_manager, self.layout_manager
        )

        # Service state
        self.running = False
        self.service_thread = None
        self.status = {
            "status": "stopped",
            "last_run": None,
            "monitors": [],
            "rules_applied": 0,
            "errors": 0,
        }

        # Window/tab cache for fast window switcher access
        self.cached_windows = []
        self.cache_timestamp = 0
        self.cache_lock = threading.Lock()

        # No longer using signal files - service runs when started
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def start(self):
        """Start the ScreenAssign service."""
        if self.running:
            self.logger.warning("Service already running")
            return False

        self.running = True
        self.status["status"] = "starting"
        self._save_status()

        # Start the service thread
        self.service_thread = threading.Thread(target=self._service_loop)
        self.service_thread.daemon = True
        self.service_thread.start()

        self.logger.info("Service started")
        return True

    def stop(self):
        """Stop the ScreenAssign service."""
        if not self.running:
            self.logger.warning("Service not running")
            return False

        self.running = False
        self.status["status"] = "stopping"
        self._save_status()

        # Wait for thread to exit
        if self.service_thread:
            self.service_thread.join(timeout=5)

        self.status["status"] = "stopped"
        self._save_status()

        self.logger.info("Service stopped")
        return True

    def restart(self):
        """Restart the ScreenAssign service."""
        self.stop()
        return self.start()

    def get_status(self):
        """Get the current service status.

        Returns:
            dict: Service status information
        """
        return self.status

    def apply_rules_now(self, layout_name: str, assignment: dict):
        """Apply all rules immediately.

        Args:
            layout_name: Name of the layout whose rules to apply
            assignment:  Slot→identity_key mapping from the frontend,
                         e.g. {"1": "-1920_0_1080_1920", "2": "0_0_1920_1080"}

        Returns:
            dict: Results of rule application
        """
        # Update connected monitors
        self.monitor_manager.detect_monitors()

        self.layout_manager.ensure_layout_can_apply(layout_name, assignment)

        # Apply all rules
        results = self.window_manager.apply_rules(layout_name, assignment)

        # Update status
        self.status["last_run"] = datetime.now().isoformat()
        self.status["rules_applied"] = results["applied"]
        self.status["errors"] = results["failed"]
        self._save_status()

        return results

    def apply_rules_for_window(self, hwnd: int, layout_name: str, assignment: dict) -> dict:
        """Apply rules to a single window identified by hwnd.

        Args:
            hwnd: Window handle
            layout_name: Name of the layout whose rules to apply
            assignment:  Slot→identity_key mapping from the frontend

        Returns:
            dict: Result of rule application for that window
        """
        self.monitor_manager.detect_monitors()
        self.layout_manager.ensure_layout_can_apply(layout_name, assignment)
        return self.window_manager.apply_rules_for_window(hwnd, layout_name, assignment)

    def _service_loop(self):
        """Main service loop that runs in a separate thread.

        Note: rule application (apply_rules) is intentionally NOT driven from
        here.  The frontend owns that timer so it can suppress rule ticks while
        the switcher overlay is visible, preventing focus theft.
        Use POST /apply-rules from the frontend to trigger rule application.
        """
        check_interval = 1  # seconds - check frequently for cache updates
        window_cache_interval = 2  # seconds - faster updates for window switcher
        monitor_detect_interval = 30  # seconds
        last_monitor_detect = 0
        last_window_cache_update = 0

        self.status["status"] = "running"
        self._save_status()

        while self.running:
            try:
                current_time = time.time()

                # Update window cache for window switcher (every 2 seconds)
                if current_time - last_window_cache_update >= window_cache_interval:
                    try:
                        windows = self.window_manager.get_all_windows()
                        with self.cache_lock:
                            self.cached_windows = windows
                            self.cache_timestamp = current_time
                        last_window_cache_update = current_time
                        self.logger.debug(
                            f"Updated window cache: {len(windows)} windows"
                        )
                    except Exception as e:
                        self.logger.error(f"Error updating window cache: {str(e)}")

                # Periodically detect monitors
                if current_time - last_monitor_detect >= monitor_detect_interval:
                    monitor_ids = self.monitor_manager.detect_monitors()
                    self.status["monitors"] = [
                        self.config_manager.get_monitor(monitor_id)
                        for monitor_id in monitor_ids
                    ]
                    last_monitor_detect = current_time

            except Exception as e:
                self.logger.error(f"Error in service loop: {str(e)}")
                self.status["status"] = "error"
                self.status["error_message"] = str(e)
                self._save_status()

            # Sleep before next check
            time.sleep(check_interval)

    def _save_status(self):
        """Save current status to the status file."""
        # Status is kept in-memory only - no disk persistence needed.
        return

    # API methods for Dashboard integration

    def get_monitors(self):
        """Get all known monitors.

        Returns:
            list: All known monitors from config
        """
        return self.config_manager.get_all_monitors()

    def get_monitors_with_status(self):
        """Get all known monitors with connection status.

        Returns:
            list: All monitors with 'connected' field added
        """
        self.monitor_manager.detect_monitors()
        connected_ids = set(self.monitor_manager.get_connected_monitor_ids())

        all_monitors = self.config_manager.get_all_monitors()
        for monitor in all_monitors:
            monitor["connected"] = monitor["id"] in connected_ids

        return all_monitors

    def get_connected_monitors(self):
        """Get currently connected monitors.

        Returns:
            list: Currently connected monitors
        """
        self.monitor_manager.detect_monitors()
        connected_ids = self.monitor_manager.get_connected_monitor_ids()
        return [
            self.config_manager.get_monitor(monitor_id) for monitor_id in connected_ids
        ]

    def get_running_windows(self):
        """Get all currently running windows.

        Returns:
            list: Window information dictionaries
        """
        return self.window_manager.get_all_windows()

    def get_cached_windows_and_tabs(self):
        """Get cached windows for fast window switcher access.

        Returns:
            dict: {
                "windows": list of window dicts,
                "timestamp": float (unix timestamp),
                "age_ms": int (milliseconds since cache update)
            }
        """
        with self.cache_lock:
            current_time = time.time()
            age_ms = (
                int((current_time - self.cache_timestamp) * 1000)
                if self.cache_timestamp > 0
                else 0
            )
            return {
                "windows": self.cached_windows.copy(),
                "timestamp": self.cache_timestamp,
                "age_ms": age_ms,
            }
