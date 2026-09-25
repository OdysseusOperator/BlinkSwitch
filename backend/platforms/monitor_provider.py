"""Platform-neutral fallback monitor provider using screeninfo."""

from typing import Any

from screeninfo import get_monitors


class ScreenInfoMonitorProvider:
    def enumerate_monitors(self) -> list[Any]:
        return get_monitors()

    def get_scale_factor(self, monitor: Any) -> float:
        return 1.0
