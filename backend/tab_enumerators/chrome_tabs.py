"""Chrome tab storage and management."""

import time
import threading
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from .base import TabEnumerator


class ChromeTabManager(TabEnumerator):
    """Manages Chrome tab data received from the extension."""

    def __init__(self, ttl_seconds: int = 10):
        """Initialize tab manager.

        Args:
            ttl_seconds: How long to keep tab data before considering it stale
        """
        self.ttl_seconds = ttl_seconds
        self._tabs_data: Dict[str, Any] = {}  # keyed by chrome_pid (extension ID)
        self._lock = threading.Lock()

    def update_tabs(
        self,
        chrome_pid: str,
        tabs: List[Dict[str, Any]],
        timestamp: int,
        browser_name: str = "Chrome",
    ) -> None:
        """Update tabs for a Chrome instance.

        Args:
            chrome_pid: Unique identifier for Chrome instance (extension ID)
            tabs: List of tab dictionaries from extension
            timestamp: Unix timestamp in milliseconds
            browser_name: Name of the browser (Chrome, Edge, Vivaldi, etc.)
        """
        with self._lock:
            self._tabs_data[chrome_pid] = {
                "tabs": tabs,
                "timestamp": timestamp,
                "last_update": time.time(),
                "browser_name": browser_name,
            }

    def get_tabs(self) -> List[Dict[str, Any]]:
        """Get all current Chrome tabs across all instances.

        Returns:
            List of tab dictionaries compatible with window switcher
        """
        with self._lock:
            now = time.time()
            all_tabs = []

            # Clean up stale data
            stale_pids = []
            for pid, data in self._tabs_data.items():
                if now - data["last_update"] > self.ttl_seconds:
                    stale_pids.append(pid)

            for pid in stale_pids:
                del self._tabs_data[pid]

            # Collect all tabs
            for pid, data in self._tabs_data.items():
                browser_name = data.get("browser_name", "Chrome")
                exe_name = self._get_exe_name(browser_name)

                for tab in data["tabs"]:
                    # Extract domain from URL
                    domain = ""
                    url = tab.get("url", "")
                    if url:
                        try:
                            parsed = urlparse(url)
                            domain = parsed.netloc or ""
                        except:
                            pass

                    # Format title with domain
                    title = tab.get("title", "Untitled")
                    if domain and not domain.startswith("chrome://"):
                        display_title = f"{title} ({domain})"
                    else:
                        display_title = title

                    all_tabs.append(
                        {
                            "type": "tab",
                            "source": browser_name.lower(),
                            "id": f"{browser_name.lower()}_{tab['id']}",
                            "chrome_tab_id": tab["id"],
                            "chrome_window_id": tab["windowId"],
                            "chrome_pid": pid,
                            "title": display_title,
                            "raw_title": title,  # Original title without domain
                            "url": url,
                            "domain": domain,
                            "active": tab.get("active", False),
                            "pinned": tab.get("pinned", False),
                            "audible": tab.get("audible", False),
                            "app_name": browser_name,
                            "app_display_name": browser_name,
                            "exe_name": exe_name,
                        }
                    )

            return all_tabs

    def _get_exe_name(self, browser_name: str) -> str:
        """Get the executable name for a browser.

        Args:
            browser_name: Name of the browser

        Returns:
            Executable filename
        """
        browser_exes = {
            "Chrome": "chrome.exe",
            "Edge": "msedge.exe",
            "Vivaldi": "vivaldi.exe",
            "Brave": "brave.exe",
            "Opera": "opera.exe",
            "Chromium": "chromium.exe",
        }
        return browser_exes.get(browser_name, "chrome.exe")

    def is_available(self) -> bool:
        """Check if Chrome tabs are available."""
        with self._lock:
            if not self._tabs_data:
                return False
            now = time.time()
            # Check if any data is fresh
            for data in self._tabs_data.values():
                if now - data["last_update"] <= self.ttl_seconds:
                    return True
            return False

    def activate_tab(self, tab_id: str) -> bool:
        """Activate a Chrome tab via extension.

        Note: This doesn't directly activate - it's handled by the
        /activate-tab endpoint which sends a message to the extension.

        Args:
            tab_id: Tab ID in format "chrome_{numeric_id}" or "edge_{numeric_id}"

        Returns:
            True if tab exists, False otherwise
        """
        # Just verify the tab exists
        tabs = self.get_tabs()
        return any(tab["id"] == tab_id for tab in tabs)

    def get_tab_by_id(self, tab_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific tab by ID.

        Args:
            tab_id: Tab ID in format "browser_{numeric_id}"

        Returns:
            Tab dictionary or None if not found
        """
        tabs = self.get_tabs()
        for tab in tabs:
            if tab["id"] == tab_id:
                return tab
        return None
