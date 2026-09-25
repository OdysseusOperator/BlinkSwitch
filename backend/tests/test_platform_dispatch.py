"""Platform-neutral tests for dispatch into injected adapters."""

import unittest
from types import SimpleNamespace

from backend.monitor_manager import MonitorManager
from backend.service import ScreenAssignService


class FakeWindowManager:
    def __init__(self):
        self.focused_hwnd = None

    def focus_window(self, hwnd: int) -> bool:
        self.focused_hwnd = hwnd
        return True

    def get_all_windows(self) -> list[dict]:
        return [{"hwnd": self.focused_hwnd}]


class FakeMonitorProvider:
    def __init__(self):
        self.monitor = SimpleNamespace(x=10, y=20, width=1920, height=1080)

    def enumerate_monitors(self) -> list[SimpleNamespace]:
        return [self.monitor]

    def get_scale_factor(self, monitor: SimpleNamespace) -> float:
        return 1.25


class PlatformDispatchTests(unittest.TestCase):
    def test_service_focus_uses_injected_platform_adapter(self):
        manager = FakeWindowManager()
        service = ScreenAssignService.__new__(ScreenAssignService)
        service.window_manager = manager

        self.assertTrue(service.focus_window(1234))
        self.assertEqual(manager.focused_hwnd, 1234)
        self.assertEqual(service.get_running_windows(), [{"hwnd": 1234}])

    def test_monitor_manager_uses_injected_provider(self):
        provider = FakeMonitorProvider()
        manager = MonitorManager.__new__(MonitorManager)
        manager.monitor_provider = provider

        self.assertEqual(manager._enumerate_monitors(), [provider.monitor])
        self.assertEqual(manager._detect_monitor_dpi_scale(provider.monitor), 1.25)


if __name__ == "__main__":
    unittest.main()
