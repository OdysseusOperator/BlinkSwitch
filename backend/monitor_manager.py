import logging
import ctypes
from screeninfo import get_monitors
from .config_manager import ConfigManager
from .monitor_fingerprint import MonitorFingerprint


class MonitorManager:
    """Manages detection and tracking of connected monitors."""

    def __init__(self, config_manager=None):
        """Initialize the monitor manager.

        Args:
            config_manager (ConfigManager, optional): Configuration manager instance.
                If None, creates a new instance.
        """
        self.logger = logging.getLogger("ScreenAssign.MonitorManager")

        if config_manager is None:
            self.config_manager = ConfigManager()
        else:
            self.config_manager = config_manager

        # Monitor fingerprint utility for stable identification
        self.fingerprint_manager = MonitorFingerprint()

        # Map of monitor IDs to currently connected monitors
        self.connected_monitors = {}

        # Used to reduce log noise (only log monitor list changes at INFO)
        self._last_detected_ids = None

    def detect_monitors(self):
        """Detect all currently connected monitors and update the configuration.

        Returns:
            list: List of detected monitor IDs
        """
        try:
            monitors = get_monitors()
            detected_ids = []

            for monitor in monitors:
                monitor_data = {
                    "name": self._generate_monitor_name(monitor),
                    "width": monitor.width,
                    "height": monitor.height,
                    "x": monitor.x,
                    "y": monitor.y,
                    "is_primary": hasattr(monitor, "is_primary") and monitor.is_primary,
                }

                # Add or update the monitor in config (WITHOUT dpi_scale)
                monitor_id = self.config_manager.add_monitor(monitor_data)
                detected_ids.append(monitor_id)

                # Update the connected monitors map
                self.connected_monitors[monitor_id] = monitor

            # Find monitors that are no longer connected
            all_monitors = self.config_manager.get_all_monitors()
            for monitor in all_monitors:
                if monitor["id"] not in detected_ids:
                    if monitor["id"] in self.connected_monitors:
                        del self.connected_monitors[monitor["id"]]

            # Only log at INFO when the set of detected monitors changes.
            detected_key = tuple(sorted(detected_ids))
            if detected_key != self._last_detected_ids:
                self.logger.info(
                    f"Detected {len(detected_ids)} monitors: {list(detected_key)}"
                )
                self._last_detected_ids = detected_key
            else:
                self.logger.debug(
                    f"Detected {len(detected_ids)} monitors: {list(detected_key)}"
                )
            return detected_ids

        except Exception as e:
            self.logger.error(f"Error detecting monitors: {str(e)}")
            return []

    def _detect_monitor_dpi_scale(self, monitor):
        """Detect the DPI scale factor for a monitor using Windows API.

        Args:
            monitor: Monitor object from screeninfo

        Returns:
            float: DPI scale factor (1.0 = 100%, 1.25 = 125%, 1.5 = 150%, etc.)
        """
        try:
            user32 = ctypes.windll.user32
            shcore = ctypes.windll.shcore

            # Create a POINT at the center of the monitor
            center_x = monitor.x + (monitor.width // 2)
            center_y = monitor.y + (monitor.height // 2)

            # Get monitor handle using MonitorFromPoint
            MONITOR_DEFAULTTONEAREST = 2
            hmonitor = user32.MonitorFromPoint(
                ctypes.wintypes.POINT(center_x, center_y), MONITOR_DEFAULTTONEAREST
            )

            # Get scale factor (Windows 8.1+)
            # DEVICE_SCALE_FACTOR enum values: 100, 120, 125, 140, 150, 160, 175, 180, 200, 225, 250, etc.
            scale_factor = ctypes.c_int()
            result = shcore.GetScaleFactorForMonitor(
                hmonitor, ctypes.byref(scale_factor)
            )

            if result == 0:  # S_OK
                # Convert from percentage to decimal (100 -> 1.0, 150 -> 1.5, etc.)
                scale = scale_factor.value / 100.0
                self.logger.debug(
                    f"Monitor at ({monitor.x},{monitor.y}): "
                    f"scale={scale_factor.value}% ({scale:.2f}x)"
                )
                return scale
            else:
                self.logger.debug(
                    f"GetScaleFactorForMonitor returned {result}, using 1.0"
                )
                return 1.0

        except Exception as e:
            self.logger.debug(f"Could not detect DPI scale: {e}, using 1.0")
            return 1.0

    def _generate_monitor_name(self, monitor):
        """Generate a friendly name for a monitor.

        Args:
            monitor: Monitor object from screeninfo

        Returns:
            str: Friendly name for the monitor
        """
        if hasattr(monitor, "name") and monitor.name:
            return f"{monitor.name} ({monitor.width}×{monitor.height})"

        # Generate a name based on position
        if monitor.x == 0 and monitor.y == 0:
            position = "Primary"
        else:
            position = f"at ({monitor.x}, {monitor.y})"

        return f"Monitor {position} ({monitor.width}×{monitor.height})"

    def is_monitor_connected(self, monitor_id):
        """Check if a monitor is currently connected.

        Args:
            monitor_id (str): The ID of the monitor to check

        Returns:
            bool: True if the monitor is connected, False otherwise
        """
        return monitor_id in self.connected_monitors

    def get_connected_monitor_ids(self):
        """Get the IDs of all currently connected monitors.

        Returns:
            list: List of connected monitor IDs
        """
        return list(self.connected_monitors.keys())

    def get_connected_monitor(self, monitor_id):
        """Get a connected monitor by ID.

        Args:
            monitor_id (str): The ID of the monitor to retrieve

        Returns:
            Monitor: The monitor object, or None if not connected
        """
        return self.connected_monitors.get(monitor_id)

    def get_all_connected_monitors(self):
        """Get all currently connected monitors.

        Returns:
            dict: Dictionary of monitor_id -> monitor objects
        """
        return self.connected_monitors

    def get_monitors_with_runtime_info(self):
        """Get all connected monitors with runtime DPI information.

        Returns:
            list: List of monitor dicts with added dpi_scale field
        """
        monitors_with_dpi = []

        for monitor_id, monitor in self.connected_monitors.items():
            # Get base monitor config
            monitor_config = self.config_manager.get_monitor(monitor_id)
            if monitor_config:
                # Add runtime DPI scale
                dpi_scale = self._detect_monitor_dpi_scale(monitor)
                monitor_info = monitor_config.copy()
                monitor_info["dpi_scale"] = dpi_scale
                monitors_with_dpi.append(monitor_info)

        return monitors_with_dpi

    def get_primary_monitor_id(self):
        """Get the ID of the primary monitor.

        Returns:
            str: The ID of the primary monitor, or None if not found
        """
        # First check the connected monitors
        for monitor_id, monitor in self.connected_monitors.items():
            if hasattr(monitor, "is_primary") and monitor.is_primary:
                return monitor_id

        # If no monitor is marked as primary, use the one at (0,0)
        for monitor_id, monitor in self.connected_monitors.items():
            if monitor.x == 0 and monitor.y == 0:
                return monitor_id

        # If still no monitor found, just use the first one
        if self.connected_monitors:
            return list(self.connected_monitors.keys())[0]

        return None

    def get_monitor_by_position(self, x, y):
        """Get the monitor that contains the given position.

        Args:
            x (int): The X coordinate
            y (int): The Y coordinate

        Returns:
            str: The ID of the monitor containing the position, or None if not found
        """
        for monitor_id, monitor in self.connected_monitors.items():
            if (
                monitor.x <= x < monitor.x + monitor.width
                and monitor.y <= y < monitor.y + monitor.height
            ):
                return monitor_id
        return None
