"""Screen configuration matching for layout system.

This module handles detection of current screen configuration and matching
against layout requirements based on Windows DISPLAY# numbers and orientation.
"""

import logging
import re
from typing import Dict, List, Tuple, Optional


class LayoutMatcher:
    """Matches current screen configuration against layout requirements."""

    def __init__(self, monitor_manager):
        """Initialize the layout matcher.

        Args:
            monitor_manager: MonitorManager instance for accessing monitor data
        """
        self.logger = logging.getLogger("ScreenAssign.LayoutMatcher")
        self.monitor_manager = monitor_manager

    def extract_display_number(self, monitor_name: str) -> Optional[int]:
        """Extract Windows DISPLAY number from monitor name.

        Args:
            monitor_name: Monitor name string (e.g., "\\\\.\\DISPLAY2 (1920×1080)")

        Returns:
            Display number as integer, or None if not found

        Examples:
            >>> extract_display_number("\\\\.\\DISPLAY1 (1080×1920)")
            1
            >>> extract_display_number("\\\\.\\DISPLAY2 (1920×1080)")
            2
        """
        match = re.search(r"DISPLAY(\d+)", monitor_name)
        if match:
            display_num = int(match.group(1))
            self.logger.debug(f"Extracted DISPLAY{display_num} from '{monitor_name}'")
            return display_num

        self.logger.warning(f"Could not extract DISPLAY number from '{monitor_name}'")
        return None

    def get_orientation(self, width: int, height: int) -> str:
        """Calculate screen orientation from dimensions.

        Args:
            width: Screen width in pixels
            height: Screen height in pixels

        Returns:
            "horizontal" if width > height, "vertical" otherwise

        Examples:
            >>> get_orientation(1920, 1080)
            "horizontal"
            >>> get_orientation(1080, 1920)
            "vertical"
        """
        orientation = "horizontal" if width > height else "vertical"
        self.logger.debug(f"Orientation for {width}x{height}: {orientation}")
        return orientation

    def get_screen_configuration(self) -> List[Dict]:
        """Get current screen configuration with DISPLAY# and orientation.

        Returns:
            List of screen configs sorted by DISPLAY number, each containing:
            - display_number: Windows DISPLAY# (1, 2, 3, etc.)
            - orientation: "horizontal" or "vertical"
            - monitor_id: Internal monitor ID
            - width: Screen width
            - height: Screen height
            - name: Monitor name

        Example return:
        [
            {
                "display_number": 1,
                "orientation": "vertical",
                "monitor_id": "monitor_77150378",
                "width": 1080,
                "height": 1920,
                "name": "\\\\.\\DISPLAY1 (1080×1920)"
            },
            {
                "display_number": 2,
                "orientation": "horizontal",
                "monitor_id": "monitor_51e9fcfb",
                "width": 1920,
                "height": 1080,
                "name": "\\\\.\\DISPLAY2 (1920×1080)"
            }
        ]
        """
        configs = []

        # Get all connected monitors
        connected_ids = self.monitor_manager.get_connected_monitor_ids()
        self.logger.debug(f"Processing {len(connected_ids)} connected monitors")

        for monitor_id in connected_ids:
            # Get monitor configuration from config manager
            monitor = self.monitor_manager.config_manager.get_monitor(monitor_id)
            if not monitor:
                self.logger.warning(f"Could not find config for monitor {monitor_id}")
                continue

            # Extract DISPLAY number
            display_num = self.extract_display_number(monitor["name"])
            if display_num is None:
                self.logger.warning(
                    f"Skipping monitor {monitor_id} - no DISPLAY number found"
                )
                continue

            # Calculate orientation
            orientation = self.get_orientation(monitor["width"], monitor["height"])

            config = {
                "display_number": display_num,
                "orientation": orientation,
                "monitor_id": monitor_id,
                "width": monitor["width"],
                "height": monitor["height"],
                "name": monitor["name"],
            }
            configs.append(config)

        # Sort by DISPLAY number
        configs.sort(key=lambda x: x["display_number"])

        self.logger.info(
            f"Screen configuration: {len(configs)} displays - "
            + ", ".join(
                [f"DISPLAY{c['display_number']}:{c['orientation']}" for c in configs]
            )
        )

        return configs

    def matches_requirements(
        self, current_config: List[Dict], layout_requirements: Dict
    ) -> Tuple[bool, str]:
        """Check if current screen setup matches layout requirements.

        Args:
            current_config: Current screen configuration from get_screen_configuration()
            layout_requirements: Layout's screen_requirements section

        Returns:
            Tuple of (matches: bool, reason: str)
            - If matches is True, reason is "All requirements met"
            - If matches is False, reason describes why it doesn't match

        Example:
            >>> current = [{"display_number": 1, "orientation": "vertical"}, ...]
            >>> requirements = {"total_screens": 2, "screens": [...]}
            >>> matches_requirements(current, requirements)
            (True, "All requirements met")
        """
        # Check total screen count
        required_total = layout_requirements.get("total_screens")
        if required_total is not None:
            if len(current_config) != required_total:
                reason = (
                    f"Need exactly {required_total} screen(s), "
                    f"but {len(current_config)} connected"
                )
                self.logger.debug(f"Screen count mismatch: {reason}")
                return False, reason

        # Check each required screen
        required_screens = layout_requirements.get("screens", [])
        for required_screen in required_screens:
            display_num = required_screen["display_number"]
            required_orientation = required_screen["orientation"]

            # Find this display in current config
            current_screen = next(
                (s for s in current_config if s["display_number"] == display_num),
                None,
            )

            if not current_screen:
                reason = f"DISPLAY{display_num} not found (required for layout)"
                self.logger.debug(f"Missing display: {reason}")
                return False, reason

            if current_screen["orientation"] != required_orientation:
                reason = (
                    f"DISPLAY{display_num} is {current_screen['orientation']}, "
                    f"but layout needs {required_orientation}"
                )
                self.logger.debug(f"Orientation mismatch: {reason}")
                return False, reason

        # All requirements met
        self.logger.info("Current screen configuration matches layout requirements")
        return True, "All requirements met"

    def build_display_map(self, current_config: List[Dict]) -> Dict[int, str]:
        """Build mapping from display numbers to monitor IDs.

        Args:
            current_config: Current screen configuration from get_screen_configuration()

        Returns:
            Dictionary mapping display_number -> monitor_id

        Example:
            >>> build_display_map([{"display_number": 1, "monitor_id": "monitor_123"}, ...])
            {1: "monitor_123", 2: "monitor_456"}
        """
        display_map = {
            screen["display_number"]: screen["monitor_id"] for screen in current_config
        }
        self.logger.debug(f"Built display map: {display_map}")
        return display_map

    def get_screen_summary(self, current_config: List[Dict]) -> str:
        """Get human-readable summary of current screen configuration.

        Args:
            current_config: Current screen configuration from get_screen_configuration()

        Returns:
            Formatted string describing the screen setup

        Example:
            "2 screens: DISPLAY1 (vertical, 1080x1920), DISPLAY2 (horizontal, 1920x1080)"
        """
        if not current_config:
            return "No screens detected"

        screen_descriptions = []
        for screen in current_config:
            desc = (
                f"DISPLAY{screen['display_number']} "
                f"({screen['orientation']}, "
                f"{screen['width']}x{screen['height']})"
            )
            screen_descriptions.append(desc)

        summary = f"{len(current_config)} screen(s): {', '.join(screen_descriptions)}"
        return summary
