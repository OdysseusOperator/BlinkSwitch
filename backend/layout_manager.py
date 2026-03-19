"""Layout management system for BlinkSwitch.

Handles loading, validating, and applying named layout presets.

Schema versions
---------------
v1 (legacy)  uses  display_number / target_display  (DISPLAY# connector IDs)
v2 (current) uses  slot / target_slot               (user-assigned 1-based integers)

When a v1 layout is loaded it is migrated in-memory to v2 automatically.
The on-disk file is NOT rewritten by this module; use the migrate_layouts script
for a permanent migration.
"""

import json
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .layout_matcher import LayoutMatcher, LayoutError  # noqa: F401  (re-export)


def normalize_exe_name(exe_name: str) -> str:
    """Normalize exe name for comparison (lowercase, ensure .exe suffix)."""
    s = (exe_name or "").strip().lower()
    if s.endswith(".exe"):
        return s
    return s + ".exe" if s else s


def find_matching_rule_for_window(
    window_data: Dict, rules: List[Dict]
) -> Optional[Dict]:
    """Find the first rule that matches the given window.

    Checks ALL match types: exe, window_title, process_path.

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
            exe_name = (
                window_data.get("exe_name") or window_data.get("app_name") or ""
            ).strip()
            if normalize_exe_name(exe_name) == normalize_exe_name(match_value_lower):
                return rule

        elif match_type == "window_title":
            title = (window_data.get("title") or "").lower()
            if match_value_lower and match_value_lower in title:
                return rule

        elif match_type == "process_path":
            process_path = (window_data.get("process_path") or "").lower()
            if match_value_lower and match_value_lower == process_path:
                return rule

    return None


def _migrate_v1_to_v2(layout_data: Dict) -> Dict:
    """Return an in-memory v2 copy of a v1 layout dict.

    Renames:
      screen_requirements.screens[*].display_number  →  slot
      rules[*].target_display                        →  target_slot
    Adds schema_version: 2.

    The original dict is NOT modified; a shallow-copied version is returned.
    """
    import copy
    data = copy.deepcopy(layout_data)

    # Migrate screen requirements
    for screen in data.get("screen_requirements", {}).get("screens", []):
        if "display_number" in screen and "slot" not in screen:
            screen["slot"] = screen.pop("display_number")

    # Migrate rules
    for rule in data.get("rules", []):
        if "target_display" in rule and "target_slot" not in rule:
            rule["target_slot"] = rule.pop("target_display")

    data["schema_version"] = 2
    return data


class LayoutManager:
    """Manages layout lifecycle: loading and validation of named layout presets.

    The backend is stateless:
    - The frontend tracks which layout is active.
    - The frontend owns the slot→monitor assignment and passes it on every call.
    - This class never persists assignment data.
    """

    def __init__(self, config_manager, monitor_manager, layouts_dir="layouts"):
        self.logger = logging.getLogger("ScreenAssign.LayoutManager")
        self.config_manager = config_manager
        self.monitor_manager = monitor_manager
        self.layouts_dir = Path(layouts_dir)
        self.matcher = LayoutMatcher(monitor_manager)

        if not self.layouts_dir.exists():
            self.layouts_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created layouts directory: {self.layouts_dir}")

    # ------------------------------------------------------------------
    # Layout file I/O
    # ------------------------------------------------------------------

    def list_layouts(self) -> List[Dict]:
        """List all available layout files.

        Returns:
            List of layout info dicts with: name, file_path, description,
            total_screens, schema_version.
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
                    "schema_version": layout_data.get("schema_version", 1),
                }
                layouts.append(layout_info)

            except Exception as e:
                self.logger.error(f"Error reading layout file {layout_file}: {e}")

        self.logger.debug(f"Found {len(layouts)} layout(s)")
        return layouts

    def load_layout(self, layout_name: str) -> Dict:
        """Load a layout file by name, migrating v1 → v2 in-memory if needed.

        Args:
            layout_name: Name of the layout file (with or without .json extension)

        Returns:
            Layout data dictionary (always schema_version 2)

        Raises:
            LayoutError: If layout file not found or invalid
        """
        if not layout_name.endswith(".json"):
            layout_name = f"{layout_name}.json"

        layout_path = self.layouts_dir / layout_name

        if not layout_path.exists():
            raise LayoutError(f"Layout file not found: {layout_path}")

        try:
            with open(layout_path, "r") as f:
                layout_data = json.load(f)

            # Migrate v1 → v2 in memory
            if layout_data.get("schema_version", 1) < 2:
                self.logger.info(
                    f"Migrating layout '{layout_data.get('name', layout_name)}' "
                    "from schema v1 to v2 in-memory"
                )
                layout_data = _migrate_v1_to_v2(layout_data)

            # Validate
            is_valid, error_msg = self.validate_layout(layout_data)
            if not is_valid:
                raise LayoutError(f"Invalid layout file: {error_msg}")

            self.logger.info(
                f"Loaded layout '{layout_data.get('name')}' from {layout_path}"
            )
            return layout_data

        except json.JSONDecodeError as e:
            raise LayoutError(f"Invalid JSON in layout file: {e}")
        except LayoutError:
            raise
        except Exception as e:
            raise LayoutError(f"Error loading layout: {e}")

    def validate_layout(self, layout_data: Dict) -> Tuple[bool, str]:
        """Validate a v2 layout structure.

        Args:
            layout_data: Layout dictionary (must already be schema_version 2)

        Returns:
            (is_valid, error_message)
        """
        if "name" not in layout_data:
            return False, "Missing required field: name"

        if "screen_requirements" not in layout_data:
            return False, "Missing required field: screen_requirements"

        if "rules" not in layout_data:
            return False, "Missing required field: rules"

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
            if "slot" not in screen:
                return False, f"Screen {i} missing: slot"

            if "orientation" not in screen:
                return False, f"Screen {i} missing: orientation"

            if screen["orientation"] not in ["horizontal", "vertical"]:
                return (
                    False,
                    f"Screen {i} has invalid orientation: {screen['orientation']} "
                    "(must be 'horizontal' or 'vertical')",
                )

        if not isinstance(layout_data["rules"], list):
            return False, "rules must be a list"

        # Collect valid slots from screen requirements
        valid_slots = {s["slot"] for s in screen_req["screens"]}

        for i, rule in enumerate(layout_data["rules"]):
            if "match_type" not in rule:
                return False, f"Rule {i} missing: match_type"

            if "match_value" not in rule:
                return False, f"Rule {i} missing: match_value"

            if "target_slot" not in rule:
                return False, f"Rule {i} missing: target_slot"

            if rule["target_slot"] not in valid_slots:
                return (
                    False,
                    f"Rule {i} targets slot {rule['target_slot']} which is not "
                    f"in screen_requirements (valid slots: {sorted(valid_slots)})",
                )

        return True, "Layout is valid"

    # ------------------------------------------------------------------
    # Slot-based rule resolution
    # ------------------------------------------------------------------

    def can_apply_layout(
        self, layout_data: Dict, assignment: Dict[str, str]
    ) -> Tuple[bool, str]:
        """Check if the assignment satisfies the layout's screen requirements.

        Verifies:
        1. The number of slots in the assignment matches total_screens.
        2. Each required slot is present in the assignment.
        3. The orientation of the assigned monitor matches the requirement.

        Args:
            layout_data: v2 layout dict (from load_layout)
            assignment:  {"1": "x_y_W_H", "2": "x_y_W_H", ...}

        Returns:
            (can_apply: bool, reason: str)
        """
        screen_req = layout_data["screen_requirements"]
        required_total = screen_req.get("total_screens")

        if required_total is not None and len(assignment) != required_total:
            return (
                False,
                f"Layout needs {required_total} screen(s) but assignment "
                f"provides {len(assignment)}",
            )

        # Build slot map (raises LayoutError if an identity key is unmatched)
        try:
            slot_map = self.matcher.build_slot_map(assignment)
        except LayoutError as e:
            return False, str(e)

        # Check orientation requirements
        for screen in screen_req.get("screens", []):
            slot = screen["slot"]
            required_orientation = screen["orientation"]

            if slot not in slot_map:
                return False, f"Slot {slot} is required but not in assignment"

            monitor_id = slot_map[slot]
            cfg = self.config_manager.get_monitor(monitor_id)
            if not cfg:
                return False, f"Monitor for slot {slot} not found in config"

            actual_orientation = self.matcher.get_orientation(
                cfg["width"], cfg["height"]
            )
            if actual_orientation != required_orientation:
                return (
                    False,
                    f"Slot {slot}: monitor is {actual_orientation} but layout "
                    f"requires {required_orientation}",
                )

        return True, "All requirements met"

    def ensure_layout_can_apply(
        self, layout_name: str, assignment: Dict[str, str]
    ) -> Dict:
        """Load layout and verify it can be applied with the given assignment.

        Args:
            layout_name: Layout file name (with or without .json)
            assignment:  {"1": "x_y_W_H", "2": "x_y_W_H", ...}

        Returns:
            Loaded layout data if compatible

        Raises:
            LayoutError: If layout cannot be loaded or requirements are not met
        """
        layout_data = self.load_layout(layout_name)
        can_apply, reason = self.can_apply_layout(layout_data, assignment)
        if not can_apply:
            layout_title = layout_data.get("name", layout_name)
            raise LayoutError(f"Layout '{layout_title}' cannot be applied: {reason}")
        return layout_data

    def get_rules_for_layout(
        self, layout_name: str, assignment: Dict[str, str]
    ) -> List[Dict]:
        """Load a layout and return its rules with target_monitor_id resolved.

        Args:
            layout_name: Layout file name (with or without .json)
            assignment:  {"1": "x_y_W_H", "2": "x_y_W_H", ...}

        Returns:
            List of runtime rules with target_monitor_id populated.

        Raises:
            LayoutError: If layout_name is empty, file not found, invalid,
                         or assignment does not match connected monitors.
        """
        if not layout_name or not layout_name.strip():
            raise LayoutError("layout_name must be a non-empty string")

        layout_data = self.load_layout(layout_name)
        slot_map = self.matcher.build_slot_map(assignment)

        self.logger.debug(
            f"Resolving rules for layout '{layout_data['name']}' "
            f"with slot_map={slot_map}"
        )

        rules = []
        for layout_rule in layout_data.get("rules", []):
            target_slot = layout_rule.get("target_slot")

            if target_slot is None:
                self.logger.warning(
                    f"Rule {layout_rule.get('rule_id', '(no id)')} missing "
                    "target_slot, skipping"
                )
                continue

            if target_slot not in slot_map:
                self.logger.warning(
                    f"Rule targets slot {target_slot} which is not in "
                    f"slot_map: {slot_map}"
                )
                continue

            rule = {
                "rule_id": layout_rule.get("rule_id", f"rule_{uuid.uuid4().hex[:8]}"),
                "match_type": layout_rule["match_type"],
                "match_value": layout_rule["match_value"],
                "target_monitor_id": slot_map[target_slot],
                "fullscreen": layout_rule.get("fullscreen", False),
                "maximize": layout_rule.get("maximize", False),
            }
            rules.append(rule)

        self.logger.debug(
            f"Resolved {len(rules)} rule(s) from layout '{layout_data['name']}'"
        )
        return rules

    # ------------------------------------------------------------------
    # Layout preview & creation
    # ------------------------------------------------------------------

    def get_layout_preview(self, layout_name: str) -> Dict:
        """Get a preview of what a layout would do (without activating it).

        Note: can_apply is not checked here because it requires an assignment
        dict that is owned by the frontend. The preview returns layout metadata
        only.

        Args:
            layout_name: Name of the layout to preview

        Returns:
            Dictionary with layout preview info

        Raises:
            LayoutError: If layout cannot be loaded
        """
        layout_data = self.load_layout(layout_name)

        return {
            "name": layout_data.get("name", layout_name),
            "description": layout_data.get("description", ""),
            "file_name": f"{layout_name}.json",
            "schema_version": layout_data.get("schema_version", 2),
            "screen_requirements": layout_data.get("screen_requirements", {}),
            "rules_count": len(layout_data.get("rules", [])),
            "data": layout_data,
        }

    def create_layout_from_current_config(
        self, layout_name: str, description: str = ""
    ) -> Dict:
        """Create a new layout file (schema v2) from connected monitors.

        The new layout has empty rules — the user adds them afterwards.
        Slot numbers are assigned 1..N (no positional ordering assumed;
        the user assigns monitors to slots via the frontend).

        Args:
            layout_name: Name for the new layout
            description: Optional description

        Returns:
            {"success": bool, "message": str, "file_name": str, "file_path": str}
        """
        self.monitor_manager.detect_monitors()
        connected_ids = self.monitor_manager.get_connected_monitor_ids()

        if not connected_ids:
            return {
                "success": False,
                "message": "No screens detected. Cannot create layout.",
            }

        screens = []
        for i, monitor_id in enumerate(connected_ids, start=1):
            cfg = self.config_manager.get_monitor(monitor_id)
            if not cfg:
                continue
            orientation = self.matcher.get_orientation(cfg["width"], cfg["height"])
            screens.append(
                {
                    "slot": i,
                    "orientation": orientation,
                    "description": f"Slot {i} — {cfg['width']}×{cfg['height']} ({orientation})",
                }
            )

        layout_data = {
            "schema_version": 2,
            "name": layout_name,
            "description": description
            or f"Layout with {len(screens)} screen{'s' if len(screens) != 1 else ''}",
            "version": "1.0",
            "screen_requirements": {
                "total_screens": len(screens),
                "screens": screens,
            },
            "rules": [],
            "metadata": {
                "created": datetime.now().isoformat(),
                "author": "screeny",
                "tags": [s["orientation"] for s in screens],
            },
        }

        file_name = f"{layout_name.lower().replace(' ', '-')}.json"
        file_path = self.layouts_dir / file_name

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
