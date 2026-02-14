"""Base class for tab enumerators."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class TabEnumerator(ABC):
    """Abstract base class for tab enumeration."""

    @abstractmethod
    def get_tabs(self) -> List[Dict[str, Any]]:
        """Get list of tabs.

        Returns:
            List of tab dictionaries with keys:
                - type: 'tab'
                - source: 'chrome', 'edge', 'wezterm', etc.
                - id: unique identifier
                - title: tab title
                - url: (optional) tab URL
                - parent_hwnd: (optional) parent window handle
                - extra: any source-specific data
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this tab source is currently available."""
        pass

    @abstractmethod
    def activate_tab(self, tab_id: str) -> bool:
        """Activate a specific tab.

        Args:
            tab_id: The unique identifier of the tab

        Returns:
            True if successful, False otherwise
        """
        pass
