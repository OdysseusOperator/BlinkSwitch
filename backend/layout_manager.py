"""Layout management system for Screeny.

Handles loading, validating, activating, and deactivating named layout presets
based on screen configuration (DISPLAY# and orientation).
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .layout_matcher import LayoutMatcher


def normalize_exe_name(exe_name: str) -> str:
    """Normalize exe name for comparison (lowercase, ensure .exe suffix).

    Args:
        exe_name: The executable name to normalize

    Returns:
        Normalized exe name (lowercase with .exe suffix)
    """
    s = (exe_name or "").strip().lower()
    if s.endswith(".exe"):
        return s
    return s + ".exe" if s else s


def find_matching_rule_for_window(
    window_data: Dict, rules: List[Dict]
) -> Optional[Dict]:
    """Find if any rule matches the given window.

    Checks ALL match types: exe, window_title, process_path.
    Uses the same matching logic as window_manager.py for consistency.

    Args:
        window_data: Window dict with exe_name, title, process_path
        rules: List of rule dicts from layout

    Returns:
        First matching rule dict, or None if no match
    """
    for rule in rules:
        match_type = rule.get("match_type")
        match_value = (rule.get("match_value") or "").strip()
        match_value_lower = match_value.lower()

        if match_type == "exe":
            # Normalize and compare exe names
            exe_name = (
                window_data.get("exe_name") or window_data.get("app_name") or ""
            ).strip()
            if normalize_exe_name(exe_name) == normalize_exe_name(match_value_lower):
                return rule

        elif match_type == "window_title":
            # Substring match (case-insensitive)
            title = (window_data.get("title") or "").lower()
            if match_value_lower and match_value_lower in title:
                return rule

        elif match_type == "process_path":
            # Exact path match (case-insensitive)
            process_path = (window_data.get("process_path") or "").lower()
            if match_value_lower and match_value_lower == process_path:
                return rule

    return None


class LayoutError(Exception):
    """Exception raised for layout-related errors."""

    pass


class LayoutManager:
    """Manages layout lifecycle: loading, validation, activation, deactivation."""

    def __init__(self, config_manager, monitor_manager, layouts_dir="layouts"):
        """Initialize the layout manager.

        Args:
            config_manager: ConfigManager instance for rule management
            monitor_manager: MonitorManager instance for screen detection
            layouts_dir: Directory containing layout JSON files
        """
        self.logger = logging.getLogger("ScreenAssign.LayoutManager")
        self.config_manager = config_manager
        self.monitor_manager = monitor_manager
        self.layouts_dir = Path(layouts_dir)
        self.matcher = LayoutMatcher(monitor_manager)

        # Active layout state
        self.active_layout = None  # Dict with name, data, display_map, activated_at

        # Ensure layouts directory exists
        if not self.layouts_dir.exists():
            self.layouts_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created layouts directory: {self.layouts_dir}")

    def list_layouts(self) -> List[Dict]:
        """List all available layout files.

        Returns:
            List of layout info dicts with: name, file_path, description, screen_requirements

        Example:
            [
                {
                    "name": "Coding Setup",
                    "file_name": "coding.json",
                    "file_path": "/path/to/layouts/coding.json",
                    "description": "VS Code on vertical, Vivaldi on horizontal",
                    "total_screens": 2
                }
            ]
        """
        layouts = []

        if not self.layouts_dir.exists():
            self.logger.warning(f"Layouts directory does not exist: {self.layouts_dir}")
            return layouts

        for layout_file in self.layouts_dir.glob("*.json"):
            try:
                with open(layout_file, "r") as f:
                    layout_data = json.load(f)

                layout_info = {
                    "name": layout_data.get("name", layout_file.stem),
                    "file_name": layout_file.name,
                    "file_path": str(layout_file),
                    "description": layout_data.get("description", ""),
                    "total_screens": layout_data.get("screen_requirements", {}).get(
                        "total_screens", 0
                    ),
                }
                layouts.append(layout_info)

            except Exception as e:
                self.logger.error(f"Error reading layout file {layout_file}: {e}")

        self.logger.debug(f"Found {len(layouts)} layout(s)")
        return layouts

    def load_layout(self, layout_name: str) -> Dict:
        """Load a layout file by name.

        Args:
            layout_name: Name of the layout file (with or without .json extension)

        Returns:
            Layout data dictionary

        Raises:
            LayoutError: If layout file not found or invalid
        """
        # Handle both "coding" and "coding.json"
        if not layout_name.endswith(".json"):
            layout_name = f"{layout_name}.json"

        layout_path = self.layouts_dir / layout_name

        if not layout_path.exists():
            raise LayoutError(f"Layout file not found: {layout_path}")

        try:
            with open(layout_path, "r") as f:
                layout_data = json.load(f)

            # Validate layout structure
            is_valid, error_msg = self.validate_layout(layout_data)
            if not is_valid:
                raise LayoutError(f"Invalid layout file: {error_msg}")

            self.logger.info(
                f"Loaded layout '{layout_data.get('name')}' from {layout_path}"
            )
            return layout_data

        except json.JSONDecodeError as e:
            raise LayoutError(f"Invalid JSON in layout file: {e}")
        except Exception as e:
            raise LayoutError(f"Error loading layout: {e}")

    def validate_layout(self, layout_data: Dict) -> Tuple[bool, str]:
        """Validate layout structure and requirements.

        Args:
            layout_data: Layout dictionary to validate

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        # Check required top-level fields
        if "name" not in layout_data:
            return False, "Missing required field: name"

        if "screen_requirements" not in layout_data:
            return False, "Missing required field: screen_requirements"

        if "rules" not in layout_data:
            return False, "Missing required field: rules"

        # Validate screen_requirements
        screen_req = layout_data["screen_requirements"]

        if not isinstance(screen_req, dict):
            return False, "screen_requirements must be a dictionary"

        if "total_screens" not in screen_req:
            return False, "screen_requirements missing: total_screens"

        if "screens" not in screen_req:
            return False, "screen_requirements missing: screens"

        if not isinstance(screen_req["screens"], list):
            return False, "screen_requirements.screens must be a list"

        # Validate each screen requirement
        for i, screen in enumerate(screen_req["screens"]):
            if "display_number" not in screen:
                return False, f"Screen {i} missing: display_number"

            if "orientation" not in screen:
                return False, f"Screen {i} missing: orientation"

            if screen["orientation"] not in ["horizontal", "vertical"]:
                return (
                    False,
                    f"Screen {i} has invalid orientation: {screen['orientation']} "
                    "(must be 'horizontal' or 'vertical')",
                )

        # Validate rules
        if not isinstance(layout_data["rules"], list):
            return False, "rules must be a list"

        for i, rule in enumerate(layout_data["rules"]):
            if "match_type" not in rule:
                return False, f"Rule {i} missing: match_type"

            if "match_value" not in rule:
                return False, f"Rule {i} missing: match_value"

            if "target_display" not in rule:
                return False, f"Rule {i} missing: target_display"

            # Check that target_display references a valid display from requirements
            target_display = rule["target_display"]
            required_displays = [s["display_number"] for s in screen_req["screens"]]

            if target_display not in required_displays:
                return (
                    False,
                    f"Rule {i} targets DISPLAY{target_display} which is not in screen_requirements",
                )

        return True, "Layout is valid"

    def can_apply_layout(self, layout_data: Dict) -> Tuple[bool, str]:
        """Check if current screen configuration matches layout requirements.

        Args:
            layout_data: Layout dictionary

        Returns:
            Tuple of (can_apply: bool, reason: str)
        """
        # Get current screen configuration
        current_config = self.matcher.get_screen_configuration()

        # Match against layout requirements
        matches, reason = self.matcher.matches_requirements(
            current_config, layout_data["screen_requirements"]
        )

        return matches, reason

    def activate_layout(self, layout_name: str) -> Dict:
        """Activate a layout if screen configuration matches.

        Process:
        1. Load layout file
        2. Validate screen requirements match current setup
        3. Build display map
        4. Mark layout as active

        Args:
            layout_name: Name of the layout to activate

        Returns:
            Dictionary with activation result:
            {
                "success": bool,
                "layout": str,
                "rules_applied": int,
                "message": str
            }

        Raises:
            LayoutError: If layout cannot be activated
        """
        # Check if a layout is already active
        if self.active_layout:
            return {
                "success": False,
                "message": f"Layout '{self.active_layout['name']}' is already active. "
                "Deactivate it first before activating another.",
            }

        # Load layout
        try:
            layout_data = self.load_layout(layout_name)
        except LayoutError as e:
            raise LayoutError(f"Cannot load layout: {e}")

        # Check if screen configuration matches
        can_apply, reason = self.can_apply_layout(layout_data)
        if not can_apply:
            raise LayoutError(
                f"Screen configuration doesn't match layout requirements: {reason}"
            )

        # Get current screen configuration and build display map
        screen_config = self.matcher.get_screen_configuration()
        display_map = self.matcher.build_display_map(screen_config)

        self.logger.info(
            f"Activating layout '{layout_data['name']}' with display mapping: {display_map}"
        )

        # Mark layout as active (rules will be read from layout via get_active_rules())
        self.active_layout = {
            "name": layout_data["name"],
            "file_name": layout_name
            if layout_name.endswith(".json")
            else f"{layout_name}.json",
            "data": layout_data,
            "display_map": display_map,
            "activated_at": datetime.now().isoformat(),
        }

        rules_count = len(layout_data.get("rules", []))
        self.logger.info(
            f"Successfully activated layout '{layout_data['name']}' with {rules_count} rule(s)"
        )

        return {
            "success": True,
            "layout": layout_data["name"],
            "rules_applied": rules_count,
            "message": f"Layout '{layout_data['name']}' activated successfully",
        }

    def deactivate_layout(self) -> Dict:
        """Deactivate the currently active layout.

        Process:
        1. Clear active layout state (rules stop being applied)

        Returns:
            Dictionary with deactivation result:
            {
                "success": bool,
                "deactivated": str,
                "message": str
            }
        """
        if not self.active_layout:
            return {
                "success": False,
                "message": "No active layout to deactivate",
            }

        layout_name = self.active_layout["name"]
        self.logger.info(f"Deactivating layout '{layout_name}'")

        # Clear state (rules will no longer be applied)
        self.active_layout = None

        self.logger.info(f"Layout '{layout_name}' deactivated")

        return {
            "success": True,
            "deactivated": layout_name,
            "message": f"Layout '{layout_name}' deactivated successfully",
        }

    def check_active_layout_validity(self) -> bool:
        """Check if active layout still matches screen configuration.

        Auto-deactivates if screens have changed (wrong count, orientation, etc.)
        Should be called periodically by service loop.

        Returns:
            True if no active layout or layout is still valid
            False if layout was auto-deactivated due to screen changes
        """
        if not self.active_layout:
            return True  # No active layout, nothing to check

        layout_name = self.active_layout["name"]
        layout_data = self.active_layout["data"]

        # Check if current screen config still matches
        can_apply, reason = self.can_apply_layout(layout_data)

        if not can_apply:
            self.logger.warning(
                f"Active layout '{layout_name}' no longer valid: {reason}. Auto-deactivating."
            )
            self.deactivate_layout()
            return False

        self.logger.debug(f"Active layout '{layout_name}' still valid")
        return True

    def get_active_layout(self) -> Optional[Dict]:
        """Get information about the currently active layout.

        Returns:
            Dictionary with active layout info, or None if no layout active
            {
                "name": str,
                "file_name": str,
                "activated_at": str,
                "rules_created": int,
                "display_map": dict,
                "screen_summary": str
            }
        """
        if not self.active_layout:
            return None

        # Get current screen config for summary
        screen_config = self.matcher.get_screen_configuration()
        screen_summary = self.matcher.get_screen_summary(screen_config)

        return {
            "name": self.active_layout["name"],
            "file_name": self.active_layout["file_name"],
            "activated_at": self.active_layout["activated_at"],
            "rules_count": len(self.active_layout["data"].get("rules", [])),
            "display_map": self.active_layout["display_map"],
            "screen_summary": screen_summary,
            "data": self.active_layout["data"],  # Include full data for UI
        }

    def get_active_rules(self) -> List[Dict]:
        """Get rules from the active layout, resolved to current monitors.

        Reads rules directly from the active layout file and maps logical
        display numbers to physical monitor IDs using the display_map.

        Returns:
            List of runtime rules with target_monitor_id resolved.
            Empty list if no layout is active.

        Example return:
            [
                {
                    "rule_id": "rule_abc123",
                    "match_type": "exe",
                    "match_value": "chrome.exe",
                    "target_monitor_id": "monitor_xyz123",  # Resolved!
                    "fullscreen": true,
                    "maximize": false
                }
            ]
        """
        if not self.active_layout:
            self.logger.debug("No active layout - returning empty rules list")
            return []

        layout_data = self.active_layout["data"]
        display_map = self.active_layout["display_map"]
        rules = []

        for layout_rule in layout_data.get("rules", []):
            target_display = layout_rule.get("target_display")

            if not target_display:
                self.logger.warning(
                    f"Rule {layout_rule.get('rule_id', '(no id)')} missing target_display, skipping"
                )
                continue

            # Map display number to monitor ID
            if target_display not in display_map:
                self.logger.warning(
                    f"Rule targets DISPLAY{target_display} which isn't in display_map: {display_map}"
                )
                continue

            target_monitor_id = display_map[target_display]

            # Create runtime rule
            rule = {
                "rule_id": layout_rule.get("rule_id", f"rule_{uuid.uuid4().hex[:8]}"),
                "match_type": layout_rule["match_type"],
                "match_value": layout_rule["match_value"],
                "target_monitor_id": target_monitor_id,  # Resolved at runtime
                "fullscreen": layout_rule.get("fullscreen", False),
                "maximize": layout_rule.get("maximize", False),
            }
            rules.append(rule)

        self.logger.debug(
            f"Resolved {len(rules)} rule(s) from active layout '{self.active_layout['name']}'"
        )
        return rules

    def get_layout_preview(self, layout_name: str) -> Dict:
        """Get a preview of what a layout would do (without activating it).

        Args:
            layout_name: Name of the layout to preview

        Returns:
            Dictionary with layout preview info:
            {
                "name": str,
                "description": str,
                "can_apply": bool,
                "reason": str,
                "screen_requirements": dict,
                "current_screen_config": list,
                "rules_count": int
            }

        Raises:
            LayoutError: If layout cannot be loaded
        """
        layout_data = self.load_layout(layout_name)
        current_config = self.matcher.get_screen_configuration()
        can_apply, reason = self.can_apply_layout(layout_data)

        return {
            "name": layout_data.get("name", layout_name),
            "description": layout_data.get("description", ""),
            "file_name": f"{layout_name}.json",
            "can_apply": can_apply,
            "reason": reason,
            "screen_requirements": layout_data.get("screen_requirements", {}),
            "current_screen_config": current_config,
            "rules_count": len(layout_data.get("rules", [])),
        }

    def create_layout_from_current_config(
        self, layout_name: str, description: str = ""
    ) -> Dict:
        """Create a new layout file from the current screen configuration.

        Args:
            layout_name: Name for the new layout
            description: Optional description

        Returns:
            Dictionary with creation result:
            {
                "success": bool,
                "message": str,
                "file_name": str,
                "file_path": str
            }
        """
        # Get current screen configuration
        screen_config = self.matcher.get_screen_configuration()

        if not screen_config:
            return {
                "success": False,
                "message": "No screens detected. Cannot create layout.",
            }

        # Build screen requirements from current config
        screens = []
        for screen in screen_config:
            screens.append(
                {
                    "display_number": screen["display_number"],
                    "orientation": screen["orientation"],
                    "description": f"{screen['orientation'].capitalize()} screen - {screen['name']}",
                }
            )

        # Create layout structure (with empty rules - user will add later)
        layout_data = {
            "name": layout_name,
            "description": description
            or f"Layout with {len(screens)} screen{'s' if len(screens) != 1 else ''}",
            "version": "1.0",
            "screen_requirements": {"total_screens": len(screens), "screens": screens},
            "rules": [],  # Empty - user will add window rules later
            "metadata": {
                "created": datetime.now().isoformat(),
                "author": "screeny",
                "tags": [s["orientation"] for s in screens],
            },
        }

        # Save to file
        file_name = f"{layout_name.lower().replace(' ', '-')}.json"
        file_path = self.layouts_dir / file_name

        # Check if file already exists
        if file_path.exists():
            return {
                "success": False,
                "message": f"Layout '{layout_name}' already exists. Please choose a different name.",
            }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, indent=2)

            self.logger.info(f"Created new layout: {file_path}")

            return {
                "success": True,
                "message": f"Layout '{layout_name}' created successfully",
                "file_name": file_name,
                "file_path": str(file_path),
            }
        except Exception as e:
            self.logger.error(f"Failed to create layout file: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to create layout: {str(e)}",
            }
