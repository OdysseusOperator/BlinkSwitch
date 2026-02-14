"""Tab enumeration modules for browser and terminal tabs."""

from .chrome_tabs import ChromeTabManager
from .base import TabEnumerator

__all__ = ["ChromeTabManager", "TabEnumerator"]
