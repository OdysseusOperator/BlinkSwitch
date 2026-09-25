"""Structural interfaces shared by the platform adapters and service."""

from typing import Any, Protocol


class WindowManagerProtocol(Protocol):
    """Operations the shared service requires from a native window manager."""

    def get_all_windows(self) -> list[dict[str, Any]]: ...

    def focus_window(self, hwnd: int) -> bool: ...

    def apply_rules(self, layout_name: str, assignment: dict[str, str]) -> dict[str, Any]: ...

    def apply_rules_for_window(
        self, hwnd: int, layout_name: str, assignment: dict[str, str]
    ) -> dict[str, Any]: ...


class MonitorProviderProtocol(Protocol):
    """Platform-specific monitor enumeration and scale detection."""

    def enumerate_monitors(self) -> list[Any]: ...

    def get_scale_factor(self, monitor: Any) -> float: ...
