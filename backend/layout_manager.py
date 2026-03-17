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
    """Manages layout lifecycle: loading and validation of named layout presets.

    The backend is stateless with respect to layout activation — the frontend
    tracks which layout is active and passes the layout name explicitly on every
    /apply-rules and /apply-rule-for-window call.
    """

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

    def get_rules_for_layout(self, layout_name: str) -> List[Dict]:
        """Load a layout by name and return its rules resolved to current monitors.

        Resolves logical display numbers to physical monitor IDs fresh on every
        call — the backend is stateless; no active-layout state is stored.

        Args:
            layout_name: Name of the layout file (with or without .json extension).
                         Must be non-empty.

        Returns:
            List of runtime rules with target_monitor_id resolved.

        Raises:
            LayoutError: If layout_name is empty, file not found, or invalid.

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
        if not layout_name or not layout_name.strip():
            raise LayoutError("layout_name must be a non-empty string")

        # Load and validate the layout file (raises LayoutError on failure)
        layout_data = self.load_layout(layout_name)

        # Build display map fresh from current screen configuration
        screen_config = self.matcher.get_screen_configuration()
        display_map = self.matcher.build_display_map(screen_config)

        self.logger.debug(
            f"Resolving rules for layout '{layout_data['name']}' with display_map={display_map}"
        )

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

            rule = {
                "rule_id": layout_rule.get("rule_id", f"rule_{uuid.uuid4().hex[:8]}"),
                "match_type": layout_rule["match_type"],
                "match_value": layout_rule["match_value"],
                "target_monitor_id": target_monitor_id,
                "fullscreen": layout_rule.get("fullscreen", False),
                "maximize": layout_rule.get("maximize", False),
            }
            rules.append(rule)

        self.logger.debug(
            f"Resolved {len(rules)} rule(s) from layout '{layout_data['name']}'"
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
            "data": layout_data,
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
