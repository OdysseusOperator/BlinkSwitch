"""Platform-specific window-management adapters."""

import os
import sys


def create_window_manager(config_manager, monitor_manager, layout_manager):
    """Construct the native adapter for the current supported platform."""
    if os.name == "nt":
        from .windows.window_manager import WindowsWindowManager

        return WindowsWindowManager(config_manager, monitor_manager, layout_manager)

    if sys.platform.startswith("linux"):
        from .cosmic.window_manager import CosmicWindowManager

        return CosmicWindowManager(config_manager, monitor_manager, layout_manager)

    raise RuntimeError(f"Window management is unsupported on platform: {os.name}")


def create_monitor_provider():
    """Construct a native monitor provider, with screeninfo as fallback."""
    if os.name == "nt":
        from .windows.monitor_provider import WindowsMonitorProvider

        return WindowsMonitorProvider()

    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
        from .cosmic.monitor_provider import CosmicMonitorProvider

        return CosmicMonitorProvider()

    from .monitor_provider import ScreenInfoMonitorProvider

    return ScreenInfoMonitorProvider()

