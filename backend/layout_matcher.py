"""Screen configuration matching for layout system.

Slot-based monitor resolution for layout rules.

A "slot" is a 1-based integer defined in the layout JSON (e.g. slot 1, slot 2).
The frontend maps each slot to a physical monitor using an identity key of the
form  x_y_W_H  (e.g. "-1920_0_1080_1920"), which is returned by
GET /monitors?connected_only=true  as  identity_key.

The backend is stateless: the assignment dict is passed in on every call and
never persisted here.
"""

import logging
from typing import Dict


class LayoutError(Exception):
    """Raised for layout-related errors (unmatched assignment, bad schema, etc.)."""

    pass


class LayoutMatcher:
    """Resolves layout slot numbers to physical monitor IDs."""

    def __init__(self, monitor_manager):
        """Initialise the layout matcher.

        Args:
            monitor_manager: MonitorManager instance for accessing monitor data
        """
        self.logger = logging.getLogger("ScreenAssign.LayoutMatcher")
        self.monitor_manager = monitor_manager

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_orientation(self, width: int, height: int) -> str:
        """Return 'horizontal' if width > height, else 'vertical'."""
        return "horizontal" if width > height else "vertical"

    def build_slot_map(self, assignment: Dict[str, str]) -> Dict[int, str]:
        """Resolve slot numbers to monitor IDs using the caller-supplied assignment.

        The assignment dict maps slot numbers (as strings, e.g. "1", "2") to
        monitor identity keys of the form  x_y_W_H
        (e.g. {"-1920_0_1080_1920", "0_0_1920_1080"}).

        Steps:
          1. Refresh connected monitors via detect_monitors().
          2. Build an identity_key -> monitor_id lookup from the live topology.
          3. For each slot in the assignment, look up the monitor_id.
          4. Raise LayoutError with a clear message if any key is unmatched.

        Args:
            assignment: {"1": "x_y_W_H", "2": "x_y_W_H", ...}

        Returns:
            {1: "monitor_id", 2: "monitor_id", ...}

        Raises:
            LayoutError: if assignment is empty/None, or if any identity key
                         does not match a currently connected monitor.
        """
        if not assignment:
            raise LayoutError(
                "assignment is required: pass a dict mapping slot numbers to "
                "monitor identity keys (x_y_W_H)"
            )

        # Fresh topology
        self.monitor_manager.detect_monitors()

        # Build identity_key -> monitor_id from connected monitors
        identity_map: Dict[str, str] = {}
        for (
            monitor_id,
            monitor,
        ) in self.monitor_manager.get_all_connected_monitors().items():
            cfg = self.monitor_manager.config_manager.get_monitor(monitor_id)
            if not cfg:
                continue
            key = f"{monitor.x}_{monitor.y}_{cfg['width']}_{cfg['height']}"
            identity_map[key] = monitor_id

        self.logger.debug(f"Connected identity map: {identity_map}")

        # Resolve each slot
        slot_map: Dict[int, str] = {}
        for slot_str, identity_key in assignment.items():
            try:
                slot = int(slot_str)
            except ValueError:
                raise LayoutError(
                    f"Assignment slot key '{slot_str}' is not a valid integer"
                )

            if identity_key not in identity_map:
                connected_keys = list(identity_map.keys())
                raise LayoutError(
                    f"Slot {slot} assignment '{identity_key}' does not match any "
                    f"connected monitor. Connected monitors: {connected_keys}"
                )

            slot_map[slot] = identity_map[identity_key]

        self.logger.debug(f"Resolved slot map: {slot_map}")
        return slot_map
