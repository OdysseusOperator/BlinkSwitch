import hashlib
import logging
from typing import Dict, Optional, Tuple


class MonitorFingerprint:
    """Generate stable hardware fingerprints for monitors.

    The fingerprint allows reliable monitor identification across:
    - Different Windows detection orders
    - Different machines with different Y offsets
    - System restarts and reconfiguration

    Strategy: Use resolution (stable) combined with Windows connector info.
    - Primary: Windows DISPLAY connector name + resolution (most stable)
    - Secondary: Resolution only (works across Y offset changes on different machines)

    Two levels are sufficient because:
    - Each physical monitor gets a unique DISPLAY# connector from Windows
    - Multiple identical-resolution monitors get different DISPLAY# numbers
    - If PRIMARY connector is unavailable, fall back to SECONDARY (resolution)
    """

    def __init__(self):
        self.logger = logging.getLogger("ScreenAssign.MonitorFingerprint")

    def generate_fingerprint(self, monitor_data: Dict) -> Dict[str, str]:
        """Generate a fingerprint for a monitor.

        Args:
            monitor_data: Dict with keys: name, width, height, x, y, is_primary

        Returns:
            Dict with fingerprint components:
            - primary: Windows connector + resolution (most stable across machines)
            - secondary: Resolution only (fallback, works across Y offset changes)
        """
        # Primary: Windows DISPLAY connector + resolution
        # Each physical monitor gets a unique DISPLAY# number from Windows
        # Combined with resolution, this uniquely identifies the monitor
        primary_fp = self._generate_connector_resolution_fp(monitor_data)

        # Secondary: Resolution only (fallback for cross-machine configs)
        # When a config moves to another machine, DISPLAY# might differ
        # but resolution stays the same, allowing matching by resolution
        secondary_fp = self._generate_resolution_fp(monitor_data)

        return {
            "primary": primary_fp,  # Most reliable across machines
            "secondary": secondary_fp,  # Fallback for Y offset/layout changes
        }

    def _generate_connector_resolution_fp(self, monitor_data: Dict) -> str:
        """Generate fingerprint from Windows connector name + resolution.

        Windows DISPLAY connector names are stable across reboots on same hardware.
        Combined with resolution provides strong identification across machines.

        Example: "DISPLAY1_1920x1080"
        """
        name = monitor_data.get("name", "")
        width = monitor_data.get("width", 0)
        height = monitor_data.get("height", 0)

        import re

        # Try to extract DISPLAY# from name
        match = re.search(r"DISPLAY(\d+)", name)
        if match:
            connector = f"DISPLAY{match.group(1)}"
            fp = f"{connector}_{width}x{height}"
            self.logger.debug(f"Generated connector+resolution FP: {fp}")
            return fp

        # Fallback: just use resolution
        return self._generate_resolution_fp(monitor_data)

    def _generate_resolution_fp(self, monitor_data: Dict) -> str:
        """Generate fingerprint from resolution only.

        This is stable across:
        - Different Windows detection orders
        - Different machine Y offsets (position changes)
        - Position/layout changes

        Works well when exporting config to different machines with same monitors.
        """
        width = monitor_data.get("width", 0)
        height = monitor_data.get("height", 0)

        if width == 0 or height == 0:
            raise ValueError("Invalid monitor dimensions")

        fp = f"{width}x{height}"
        self.logger.debug(f"Generated resolution FP: {fp}")
        return fp

    def fingerprints_match(
        self, fp1: Dict[str, str], fp2: Dict[str, str], strict: bool = False
    ) -> Tuple[bool, str]:
        """Compare two fingerprints for matching.

        Args:
            fp1, fp2: Fingerprints from generate_fingerprint()
            strict: If True, primary fingerprint must match exactly.
                   If False, allows fallback to secondary.

        Returns:
            (is_match, reason_string) - reason indicates why they matched
        """
        # Primary match: Windows connector + resolution
        # Most reliable for matching across machines with same hardware setup
        if fp1["primary"] == fp2["primary"]:
            return True, "connector_and_resolution_match"

        if strict:
            return False, "primary_mismatch_strict"

        # Secondary match: Resolution only
        # Works when exporting config to different machine with different Y offsets
        # Falls back here when DISPLAY# connector differs between machines
        if fp1["secondary"] == fp2["secondary"]:
            return True, "resolution_match"

        return False, "no_match"

    def update_monitor_from_detected(
        self, known_monitor: Dict, detected_monitor_data: Dict
    ) -> Dict:
        """Update a known monitor with new detected data.

        Preserves stable fingerprints while updating other properties.

        Args:
            known_monitor: Monitor from config (with id and fingerprints)
            detected_monitor_data: Fresh detection data

        Returns:
            Updated monitor data to save to config
        """
        # Keep the original ID
        updated = {**known_monitor}

        # Update dynamic properties
        updated["x"] = detected_monitor_data.get("x", known_monitor.get("x"))
        updated["y"] = detected_monitor_data.get("y", known_monitor.get("y"))
        updated["is_primary"] = detected_monitor_data.get(
            "is_primary", known_monitor.get("is_primary", False)
        )

        # Update name for display (use latest name)
        updated["name"] = detected_monitor_data.get("name", known_monitor.get("name"))

        # Regenerate fingerprints for updated position data
        updated["fingerprints"] = self.generate_fingerprint(updated)

        return updated
