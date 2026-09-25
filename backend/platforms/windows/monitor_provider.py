"""Windows monitor enumeration and per-monitor DPI scale detection."""

import ctypes
from ctypes import wintypes
from typing import Any

from screeninfo import get_monitors


class WindowsMonitorProvider:
    def enumerate_monitors(self) -> list[Any]:
        return get_monitors()

    def get_scale_factor(self, monitor: Any) -> float:
        try:
            user32 = ctypes.windll.user32
            shcore = ctypes.windll.shcore
            center_x = monitor.x + monitor.width // 2
            center_y = monitor.y + monitor.height // 2
            hmonitor = user32.MonitorFromPoint(
                wintypes.POINT(center_x, center_y), 2
            )
            scale_factor = ctypes.c_int()
            result = shcore.GetScaleFactorForMonitor(
                hmonitor, ctypes.byref(scale_factor)
            )
            return scale_factor.value / 100.0 if result == 0 else 1.0
        except (AttributeError, OSError, TypeError, ValueError):
            return 1.0
