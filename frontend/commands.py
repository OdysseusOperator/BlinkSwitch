"""
Command system for Screeny window switcher.

Provides a registry of fuzzy-findable commands (like /monitors)
and their corresponding UI views.
"""

from typing import Any, Callable, Optional, Dict, List
import logging

logger = logging.getLogger("WindowSwitcher.Commands")


# ============================================================================
# Helper functions (copied from backend to avoid import dependency)
# ============================================================================


def _normalize_exe_name(exe_name: str) -> str:
    """Normalize exe name for comparison (lowercase, ensure .exe suffix)."""
    s = (exe_name or "").strip().lower()
    if s.endswith(".exe"):
        return s
    return s + ".exe" if s else s


def _find_matching_rule_for_window(
    window_data: Dict, rules: List[Dict]
) -> Optional[Dict]:
    """Find if any rule matches the given window.

    Checks ALL match types: exe, window_title, process_path.
    Uses the same matching logic as backend for consistency.

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
            if _normalize_exe_name(exe_name) == _normalize_exe_name(match_value_lower):
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


class Command:
    """Represents a single command that can be executed."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        category: str = "General",
    ):
        """
        Initialize a command.

        Args:
            name: Command name (e.g., "monitors")
            description: Human-readable description
            handler: Function to call when command is selected
            category: Optional category for grouping
        """
        self.name = name
        self.description = description
        self.handler = handler
        self.category = category

    def get_label(self) -> str:
        """Get the display label for this command."""
        return f"/{self.name} - {self.description}"

    def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the command with the given context."""
        return self.handler(context)


class CommandRegistry:
    """Registry for all fuzzy-findable commands."""

    def __init__(self):
        self.commands: Dict[str, Command] = {}
        logger.info("CommandRegistry initialized")

    def register(
        self,
        name: str,
        description: str,
        handler: Callable,
        category: str = "General",
    ) -> None:
        """Register a new command."""
        cmd = Command(name, description, handler, category)
        self.commands[name] = cmd
        logger.info(f"Registered command: /{name}")

    def get_command(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self.commands.get(name)

    def search_commands(self, query: str) -> List[Command]:
        """
        Search commands by query string.

        Args:
            query: Search query (case-insensitive)

        Returns:
            List of matching commands
        """
        query_lower = query.lower().strip()

        # Remove leading slash if present
        if query_lower.startswith("/"):
            query_lower = query_lower[1:]

        if not query_lower:
            # Return all commands if no query
            return list(self.commands.values())

        # Simple substring matching
        matches = []
        for cmd in self.commands.values():
            searchable = f"{cmd.name} {cmd.description}".lower()
            if query_lower in searchable:
                matches.append(cmd)

        # Sort by relevance (exact name match first, then by name)
        matches.sort(key=lambda c: (c.name.lower() != query_lower, c.name.lower()))

        return matches

    def is_command_query(self, query: str) -> bool:
        """Check if a query string is a command (starts with /)."""
        return query.strip().startswith("/")


class MonitorManagementView:
    """
    UI View for managing monitors.

    Displays list of monitors and allows deletion with 'd' key.
    """

    def __init__(self, monitors_data: List[Dict[str, Any]]):
        """
        Initialize the monitor management view.

        Args:
            monitors_data: List of monitor dictionaries from API
        """
        self.monitors = monitors_data
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible_rows = 12
        logger.info(
            f"MonitorManagementView initialized with {len(monitors_data)} monitors"
        )

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        Args:
            ch: Character code (0 if none)
            key_down: True if down arrow pressed
            key_up: True if up arrow pressed
            key_escape: True if escape pressed
            key_backspace: True if backspace pressed
            key_d: True if 'd' key pressed

        Returns:
            Action to take: 'close', 'delete:<monitor_id>', or None
        """
        # Handle escape (close)
        if key_escape:
            return "close"

        # Handle navigation
        if key_down and self.monitors:
            self.selected = min(self.selected + 1, len(self.monitors) - 1)
            if self.selected >= self.scroll_offset + self.max_visible_rows:
                self.scroll_offset = self.selected - self.max_visible_rows + 1

        if key_up and self.monitors:
            self.selected = max(self.selected - 1, 0)
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected

        # Handle delete
        if key_d and self.monitors:
            monitor = self.monitors[self.selected]
            return f"delete:{monitor['id']}"

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns:
            Dict with:
                - title: View title
                - items: List of visible monitor items
                - selected: Index of selected item
                - scroll_offset: Current scroll position
                - total_count: Total number of monitors
                - help_text: Help text to display
        """
        visible = self.monitors[
            self.scroll_offset : self.scroll_offset + self.max_visible_rows
        ]

        items = []
        for monitor in visible:
            # Format: "DISPLAY1 (3840×2160) at (-3840, 0)"
            name = monitor.get("name", "Unknown")
            width = monitor.get("width", 0)
            height = monitor.get("height", 0)
            x = monitor.get("x", 0)
            y = monitor.get("y", 0)
            is_primary = monitor.get("is_primary", False)
            connected = monitor.get("connected", True)

            # Build label
            primary_tag = " [PRIMARY]" if is_primary else ""
            connected_tag = "" if connected else " [DISCONNECTED]"
            label = (
                f"{name} ({width}×{height}) at ({x}, {y}){primary_tag}{connected_tag}"
            )

            items.append(
                {
                    "label": label,
                    "id": monitor.get("id", ""),
                    "connected": connected,
                }
            )

        return {
            "title": "Monitor Management",
            "items": items,
            "selected": self.selected - self.scroll_offset,
            "scroll_offset": self.scroll_offset,
            "total_count": len(self.monitors),
            "help_text": "Press 'd' to delete | Esc to close",
        }


class LayoutManagementView:
    """
    UI View for managing layouts.

    Displays list of available layouts and allows activation/deactivation.
    """

    def __init__(
        self,
        layouts_data: List[Dict[str, Any]],
        active_layout: Optional[str],
        activate_fn: Optional[Callable],
        deactivate_fn: Optional[Callable],
        fetch_screen_config_fn: Optional[Callable],
    ):
        """
        Initialize the layout management view.

        Args:
            layouts_data: List of layout dictionaries from API
            active_layout: Currently active layout name (stem only, e.g. "coding") or None
            activate_fn: Function to activate a layout
            deactivate_fn: Function to deactivate current layout
            fetch_screen_config_fn: Function to fetch current screen config
        """
        self.layouts = layouts_data
        self.active_layout = active_layout
        self.activate_fn = activate_fn
        self.deactivate_fn = deactivate_fn
        self.fetch_screen_config_fn = fetch_screen_config_fn
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible_rows = 12
        self.error_message = None
        logger.info(
            f"LayoutManagementView initialized with {len(layouts_data)} layouts"
        )

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
        key_a: bool = False,
        key_enter: bool = False,
        key_n: bool = False,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        Args:
            ch: Character code (0 if none)
            key_down: True if down arrow pressed
            key_up: True if up arrow pressed
            key_escape: True if escape pressed
            key_backspace: True if backspace pressed
            key_d: True if 'd' key pressed (delete layout)
            key_a: True if 'a' key pressed (toggle activate/deactivate)
            key_enter: True if enter pressed (toggle activate/deactivate)
            key_n: True if 'n' key pressed (new layout)

        Returns:
            Action to take: 'close', 'refresh', 'new_layout', or None
        """
        # Handle escape (close)
        if key_escape:
            return "close"

        # Handle navigation
        if key_down and self.layouts:
            self.selected = min(self.selected + 1, len(self.layouts) - 1)
            if self.selected >= self.scroll_offset + self.max_visible_rows:
                self.scroll_offset = self.selected - self.max_visible_rows + 1

        if key_up and self.layouts:
            self.selected = max(self.selected - 1, 0)
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected

        # Handle new layout ('n' key)
        if key_n:
            return "new_layout"

        # Handle toggle activate/deactivate (Enter or 'a' key)
        if (key_enter or key_a) and self.layouts:
            layout = self.layouts[self.selected]
            layout_name = layout["file_name"].replace(".json", "")

            # Check if this layout is currently active
            active_file_name = (
                f"{self.active_layout}.json" if self.active_layout else ""
            )
            is_active = layout["file_name"] == active_file_name

            try:
                if is_active:
                    # Deactivate if currently active
                    if self.deactivate_fn:
                        result = self.deactivate_fn()
                        if result.get("success"):
                            self.error_message = (
                                f"✓ Deactivated: {result.get('deactivated', 'layout')}"
                            )
                            return "refresh"
                        else:
                            self.error_message = (
                                f"✗ {result.get('message', 'Failed to deactivate')}"
                            )
                    else:
                        self.error_message = "✗ Deactivate function not available"
                else:
                    # Activate if not active
                    if self.activate_fn:
                        result = self.activate_fn(layout_name)
                        if result.get("success"):
                            self.error_message = f"✓ Activated: {layout['name']}"
                            return "refresh"
                        else:
                            self.error_message = (
                                f"✗ Failed: {result.get('error', 'Unknown error')}"
                            )
                    else:
                        self.error_message = "✗ Activate function not available"
            except Exception as e:
                self.error_message = f"✗ Error: {str(e)}"
            return None

        # Handle delete ('d' key)
        if key_d and self.layouts:
            return "delete_layout"

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns:
            Dict with:
                - title: View title
                - items: List of visible layout items
                - selected: Index of selected item
                - scroll_offset: Current scroll position
                - total_count: Total number of layouts
                - help_text: Help text to display
                - error_message: Error/success message to show
        """
        visible = self.layouts[
            self.scroll_offset : self.scroll_offset + self.max_visible_rows
        ]

        # Get current active layout name
        active_name = (
            f"{self.active_layout}.json" if self.active_layout else ""
        )

        items = []
        for layout in visible:
            # Format: "Dual Horizontal (2 screens) - browser on left, code on right"
            name = layout.get("name", "Unknown")
            screens = layout.get("total_screens", 0)
            description = layout.get("description", "")
            file_name = layout.get("file_name", "")

            is_active = file_name == active_name
            active_tag = " [ACTIVE]" if is_active else ""

            label = (
                f"{name} ({screens} screen{'s' if screens != 1 else ''}){active_tag}"
            )
            if description:
                label += f" - {description}"

            items.append(
                {
                    "label": label,
                    "name": name,
                    "file_name": file_name,
                    "is_active": is_active,
                    "connected": True,  # Layouts are always "connected" (available)
                }
            )

        # Build help text
        help_parts = ["Enter/A to toggle", "D to delete", "N for new", "Esc to close"]
        if self.error_message:
            help_parts.insert(0, self.error_message)

        return {
            "title": "Layout Management",
            "items": items,
            "selected": self.selected - self.scroll_offset,
            "scroll_offset": self.scroll_offset,
            "total_count": len(self.layouts),
            "help_text": " | ".join(help_parts),
        }


class AssignView:
    """
    UI View for assigning layout slots to physical monitors.

    Shows one row per slot from screen_requirements.screens.
    Monitor legend is shown below the slot list, numbered 1-N.
    Digit keys 1-9 assign the Nth connected monitor to the current slot.
    Up/Down moves between slots, S saves, Esc closes without saving.
    """

    def __init__(
        self,
        active_layout: Dict[str, Any],
        monitors: List[Dict[str, Any]],
        current_assignment: Dict[str, str],
        layout_name: str = "",
    ):
        """
        Initialize the assign view.

        Args:
            active_layout: Layout info dict (must have 'data' with screen_requirements)
            monitors: List of monitor dicts from /screen-config (identity_key, orientation, etc.)
            current_assignment: Current slot→identity_key mapping for this layout
                                e.g. {"1": "-1920_0_1080_1920", "2": "0_0_1920_1080"}
            layout_name: Stem name of the layout being assigned (e.g. "dual-screen-home").
                         Used by the save handler; does NOT need to be the active layout.
        """
        self.monitors = monitors  # connected monitors, each with identity_key
        self.layout_name = layout_name  # which layout this assignment is for

        # Extract slots from layout screen_requirements
        self.slots: List[Dict[str, Any]] = []
        if active_layout and "data" in active_layout:
            sr = active_layout["data"].get("screen_requirements", {})
            self.slots = sr.get("screens", [])

        # Working copy of the assignment (slot str → identity_key str)
        self.assignment: Dict[str, str] = dict(current_assignment)

        self.selected = 0  # index into self.slots
        self.error_message: Optional[str] = None

        logger.info(
            f"AssignView initialized: layout='{layout_name}', {len(self.slots)} slots, {len(monitors)} monitors"
        )

    def set_error(self, msg: str) -> None:
        """Set an error message to display."""
        self.error_message = msg

    def get_assignment(self) -> Dict[str, str]:
        """Return the current (possibly edited) slot→identity_key mapping."""
        return dict(self.assignment)

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
        key_a: bool = False,
        key_enter: bool = False,
        key_n: bool = False,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        - Up/Down: move between slots
        - Digit 1-9: assign Nth connected monitor to current slot
        - S: save and return "save"
        - Esc: close without saving, return "close"

        Returns:
            "save", "close", or None
        """
        if key_escape:
            return "close"

        if self.slots:
            if key_down:
                self.selected = min(self.selected + 1, len(self.slots) - 1)
            if key_up:
                self.selected = max(self.selected - 1, 0)

        # Digit keys 1-9
        if ch and ord("1") <= ch <= ord("9"):
            digit = ch - ord("0")  # 1-based index
            monitor_idx = digit - 1
            if monitor_idx < len(self.monitors):
                monitor = self.monitors[monitor_idx]
                identity_key = monitor.get("identity_key", "")
                if self.slots:
                    slot_num = str(self.slots[self.selected]["slot"])
                    self.assignment[slot_num] = identity_key
                    logger.info(
                        f"AssignView: slot {slot_num} → {identity_key} (monitor {digit})"
                    )
            else:
                self.error_message = f"No monitor #{digit}"

        # S to save
        if ch == ord("s") or ch == ord("S"):
            return "save"

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns items list with:
          - Slot rows: "[*] Slot 1 (vertical) → -1920_0_1080_1920"
          - Blank separator row
          - Monitor legend rows: "1: -1920_0_1080_1920 (vertical, 1080×1920)"

        Help text: "1-9 assign monitor | Up/Down navigate | S save | Esc cancel"
        Plus error_message prepended if set.
        """
        items: List[Dict[str, Any]] = []

        for idx, screen in enumerate(self.slots):
            slot_num = screen.get("slot", idx + 1)
            orientation = screen.get("orientation", "?")
            assigned_key = self.assignment.get(str(slot_num), "(unassigned)")
            marker = "[*]" if idx == self.selected else "[ ]"
            label = f"{marker} Slot {slot_num} ({orientation}) → {assigned_key}"
            items.append({"label": label, "connected": idx == self.selected})

        # Blank separator
        items.append({"label": "", "connected": False})

        # Monitor legend
        for i, monitor in enumerate(self.monitors):
            identity_key = monitor.get("identity_key", "?")
            orientation = monitor.get("orientation", "?")
            width = monitor.get("width", 0)
            height = monitor.get("height", 0)
            label = f"{i + 1}: {identity_key} ({orientation}, {width}×{height})"
            items.append({"label": label, "connected": False})

        help_parts = ["1-9 assign monitor", "Up/Down navigate", "S save", "Esc cancel"]
        if self.error_message:
            help_parts.insert(0, self.error_message)

        return {
            "title": "Assign Monitors to Slots",
            "items": items,
            "selected": self.selected,
            "scroll_offset": 0,
            "total_count": len(self.slots),
            "help_text": " | ".join(help_parts),
        }


class WindowsView:
    """
    UI View for displaying all windows.

    Allows browsing windows and selecting one to configure.
    """

    def __init__(
        self,
        windows_data: List[Dict[str, Any]],
        active_layout: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the windows view.

        Args:
            windows_data: List of window dictionaries from API
            active_layout: Currently active layout info or None
        """
        self.windows = windows_data
        self.active_layout = active_layout
        self.selected = 0
        self.scroll_offset = 0
        self.max_visible_rows = 12
        self.error_message = None

        # Identify which windows have rules (for visual feedback)
        self.windows_with_rules = self._identify_windows_with_rules()

        logger.info(
            f"WindowsView initialized with {len(windows_data)} windows, active_layout: {active_layout.get('name') if active_layout else 'None'}"
        )

    def _identify_windows_with_rules(self) -> set:
        """Return set of HWNDs for windows that have matching rules.

        Returns:
            Set of window HWNDs that have rules in the active layout
        """
        windows_with_rules = set()

        if not self.active_layout or "data" not in self.active_layout:
            return windows_with_rules

        rules = self.active_layout["data"].get("rules", [])

        for window in self.windows:
            if _find_matching_rule_for_window(window, rules):
                hwnd = window.get("hwnd")
                if hwnd is not None:
                    windows_with_rules.add(hwnd)

        logger.debug(f"Found {len(windows_with_rules)} windows with rules")
        return windows_with_rules

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
        key_a: bool = False,
        key_enter: bool = False,
        key_n: bool = False,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        Args:
            ch: Character code (0 if none)
            key_down: True if down arrow pressed
            key_up: True if up arrow pressed
            key_escape: True if escape pressed
            key_backspace: True if backspace pressed
            key_d: True if 'd' key pressed (delete rule for selected window)
            key_a: True if 'a' key pressed (not used)
            key_enter: True if enter pressed (open window details)
            key_n: True if 'n' key pressed (not used)

        Returns:
            Action to take: 'close', 'window_details', 'delete_window_rule', or None
        """
        # Handle escape (close)
        if key_escape:
            return "close"

        # Handle navigation
        if key_down and self.windows:
            self.selected = min(self.selected + 1, len(self.windows) - 1)
            if self.selected >= self.scroll_offset + self.max_visible_rows:
                self.scroll_offset = self.selected - self.max_visible_rows + 1

        if key_up and self.windows:
            self.selected = max(self.selected - 1, 0)
            if self.selected < self.scroll_offset:
                self.scroll_offset = self.selected

        # Handle enter (open window details)
        if key_enter and self.windows and self.active_layout:
            return "window_details"

        # Handle D key - delete rule for the selected window (only if it has one)
        if key_d and self.windows and self.active_layout:
            selected_window = self.windows[self.selected] if self.selected < len(self.windows) else None
            if selected_window:
                hwnd = selected_window.get("hwnd")
                if hwnd is not None and hwnd in self.windows_with_rules:
                    return "delete_window_rule"

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns:
            Dict with:
                - title: View title
                - items: List of visible window items
                - selected: Index of selected item
                - scroll_offset: Current scroll position
                - total_count: Total number of windows
                - help_text: Help text to display
        """
        # Check if a layout is active
        if not self.active_layout:
            return {
                "title": "Windows Management",
                "items": [
                    {
                        "label": "⚠ Please select a layout first",
                        "connected": False,
                    },
                    {
                        "label": "Use /layouts to activate a layout before managing windows",
                        "connected": False,
                    },
                ],
                "selected": -1,
                "scroll_offset": 0,
                "total_count": 0,
                "help_text": "Esc to close | /layouts to select a layout",
            }

        visible = self.windows[
            self.scroll_offset : self.scroll_offset + self.max_visible_rows
        ]

        items = []
        for window in visible:
            # Format: "Chrome - GitHub (chrome.exe)"
            title = window.get("title", "Untitled")
            exe_name = window.get("exe_name", "unknown.exe")
            app_name = window.get("app_name", exe_name)

            # Truncate long titles
            if len(title) > 50:
                title = title[:47] + "..."

            label = f"{title} ({exe_name})"

            # Check if this window has a rule (for color coding)
            hwnd = window.get("hwnd")
            has_rule = hwnd is not None and hwnd in self.windows_with_rules

            items.append(
                {
                    "label": label,
                    "hwnd": hwnd,
                    "connected": has_rule,  # True = yellow (has rule), False = white (no rule)
                }
            )

        # Build help text
        layout_name = (
            self.active_layout.get("name", "Unknown") if self.active_layout else "None"
        )
        help_parts = [f"Layout: {layout_name}", "Enter to configure"]

        # Show D=delete hint if the selected window has a rule
        if self.windows and self.active_layout:
            selected_window = self.windows[self.selected] if self.selected < len(self.windows) else None
            if selected_window:
                hwnd = selected_window.get("hwnd")
                if hwnd is not None and hwnd in self.windows_with_rules:
                    help_parts.append("D=delete rule")

        help_parts.append("Esc to close")
        if self.error_message:
            help_parts.insert(0, self.error_message)

        return {
            "title": "Windows Management",
            "items": items,
            "selected": self.selected - self.scroll_offset,
            "scroll_offset": self.scroll_offset,
            "total_count": len(self.windows),
            "help_text": " | ".join(help_parts),
        }


class WindowDetailsView:
    """
    UI View for configuring a specific window to be added to a layout.

    Allows selecting target display and maximize options, then saves rule.
    """

    def __init__(
        self,
        window_data: Dict[str, Any],
        active_layout: Dict[str, Any],
    ):
        """
        Initialize the window details view.

        Args:
            window_data: Window data from the selected window
            active_layout: Current active layout info
        """
        self.window = window_data
        self.active_layout = active_layout

        # Extract screens from active layout's screen_requirements
        self.screens = []
        if active_layout and "data" in active_layout:
            screen_requirements = active_layout["data"].get("screen_requirements", {})
            self.screens = screen_requirements.get("screens", [])

        self.selected = 0
        self.scroll_offset = 0
        self.max_visible_rows = 12

        # Configuration options
        self.selected_display = 1  # Default to slot 1
        self.maximize = False

        # match_type: "exe" or "window_title" (substring)
        # MATCH_TYPES order determines cycling with T key
        self.MATCH_TYPES = ["exe", "window_title"]
        self.match_type = "exe"
        # match_value_title: the substring to match when match_type == "window_title"
        # Pre-populated from the current window title as a sensible default
        self.match_value_title = window_data.get("title", "")

        # skip_popups: when True, maximize is skipped for WS_POPUP windows
        self.skip_popups = False

        # Check for existing rule (for edit mode)
        self.existing_rule = None
        self.is_edit_mode = False
        self.error_message = None

        if active_layout and "data" in active_layout:
            rules = active_layout["data"].get("rules", [])
            self.existing_rule = _find_matching_rule_for_window(window_data, rules)

            if self.existing_rule:
                self.is_edit_mode = True
                # Pre-populate values from existing rule (v2 uses target_slot)
                self.selected_display = self.existing_rule.get(
                    "target_slot",
                    self.existing_rule.get("target_display", 1),  # v1 fallback
                )
                self.maximize = self.existing_rule.get("maximize", False)
                self.match_type = self.existing_rule.get("match_type", "exe")
                if self.match_type == "window_title":
                    self.match_value_title = self.existing_rule.get("match_value", self.match_value_title)
                self.skip_popups = self.existing_rule.get("skip_popups", False)
                logger.info(
                    f"Edit mode: Loading existing rule {self.existing_rule.get('rule_id')} for {window_data.get('title', 'Unknown')}"
                )

        logger.info(
            f"WindowDetailsView initialized for window: {window_data.get('title', 'Unknown')}"
        )

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
        key_a: bool = False,
        key_enter: bool = False,
        key_n: bool = False,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        Navigation:
        - Up/Down: Select option
        - Enter: Toggle option or save
        - m: Toggle maximize
        - s: Save rule and close
        - Esc/Backspace: Go back

        Args:
            ch: Character code (0 if none)
            key_down: True if down arrow pressed
            key_up: True if up arrow pressed
            key_escape: True if escape pressed
            key_backspace: True if backspace pressed
            key_d: True if 'd' key pressed
            key_a: True if 'a' key pressed
            key_enter: True if enter pressed
            key_n: True if 'n' key pressed

        Returns:
            Action to take: 'close', 'save', or None
        """
        if key_escape or key_backspace:
            return "close"

        # Get total items count (screens + match-type row + maximize row + skip-popups row + save button)
        total_items = len(self.screens) + 4

        # Navigation
        if key_down:
            self.selected = (self.selected + 1) % total_items
            logger.debug(f"Selected: {self.selected}")
        elif key_up:
            self.selected = (self.selected - 1) % total_items
            logger.debug(f"Selected: {self.selected}")

        # Index offsets for the option rows that follow the slot list
        idx_match_type = len(self.screens)
        idx_maximize   = len(self.screens) + 1
        idx_skip_popups = len(self.screens) + 2
        idx_save       = len(self.screens) + 3

        # Enter key - toggle or save
        if key_enter:
            if self.selected < len(self.screens):
                # Selecting a slot
                self.selected_display = self.screens[self.selected]["slot"]
                logger.info(f"Selected slot: {self.selected_display}")
            elif self.selected == idx_match_type:
                # If already window_title, Enter opens the text editor for the substring
                if self.match_type == "window_title":
                    return "edit_title_match"
                # Otherwise cycle to window_title
                current_idx = self.MATCH_TYPES.index(self.match_type)
                self.match_type = self.MATCH_TYPES[(current_idx + 1) % len(self.MATCH_TYPES)]
                logger.info(f"Match type cycled to: {self.match_type}")
            elif self.selected == idx_maximize:
                # Toggle maximize
                self.maximize = not self.maximize
                logger.info(f"Maximize toggled to: {self.maximize}")
            elif self.selected == idx_skip_popups:
                # Toggle skip_popups
                self.skip_popups = not self.skip_popups
                logger.info(f"Skip popups toggled to: {self.skip_popups}")
            elif self.selected == idx_save:
                # Save button
                return "save"

        # Keyboard shortcuts
        if ch == ord("m") or ch == ord("M"):
            self.maximize = not self.maximize
            logger.info(f"Maximize toggled to: {self.maximize}")
        elif ch == ord("t") or ch == ord("T"):
            # If already window_title, T opens the substring text editor
            if self.match_type == "window_title":
                return "edit_title_match"
            # Otherwise cycle to window_title
            current_idx = self.MATCH_TYPES.index(self.match_type)
            self.match_type = self.MATCH_TYPES[(current_idx + 1) % len(self.MATCH_TYPES)]
            logger.info(f"Match type cycled to: {self.match_type}")
        elif ch == ord("p") or ch == ord("P"):
            self.skip_popups = not self.skip_popups
            logger.info(f"Skip popups toggled to: {self.skip_popups}")
        elif ch == ord("s") or ch == ord("S"):
            return "save"
        elif (ch == ord("d") or ch == ord("D")) and self.is_edit_mode:
            # Delete rule (only available in edit mode)
            return "delete"

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns:
            Dict with:
                - title: View title
                - items: List of items (monitors + options + save button)
                - selected: Currently selected item index
                - scroll_offset: 0
                - total_count: Total items
                - help_text: Help text to display
        """
        title = self.window.get("title", "Unknown Window")
        exe_name = self.window.get("exe_name", "unknown.exe")

        items = []

        # Add display selection items
        for screen in self.screens:
            slot = screen["slot"]
            orientation = screen["orientation"]
            description = screen.get("description", f"Slot {slot}")
            selected_marker = "[*]" if slot == self.selected_display else "[ ]"
            items.append(
                {
                    "label": f"{selected_marker} Slot {slot}: {description} [{orientation}]",
                    "connected": True,
                }
            )

        # Add match-type row
        if self.match_type == "exe":
            match_label = f"[T] Match: exe = {exe_name}"
        else:
            # Show the title substring value (truncated for display)
            display_val = self.match_value_title[:38] + "…" if len(self.match_value_title) > 38 else self.match_value_title
            match_label = f"[T] Match: title contains \"{display_val}\""
        items.append({"label": match_label, "connected": True})

        # Add maximize option
        maximize_marker = "[X]" if self.maximize else "[ ]"
        items.append({"label": f"{maximize_marker} Maximize", "connected": True})

        # Add skip-popups option
        skip_marker = "[X]" if self.skip_popups else "[ ]"
        items.append({"label": f"{skip_marker} Skip popups (don't maximize WS_POPUP windows)", "connected": True})

        # Add save button
        save_label = ">> UPDATE RULE <<" if self.is_edit_mode else ">> SAVE RULE <<"
        items.append({"label": save_label, "connected": True})

        # Build help text
        help_parts = [f"Window: {exe_name}"]
        if self.match_type == "window_title":
            help_parts.append("T=edit substring  M=maximize  P=skip popups  S=save")
        else:
            help_parts.append("T=match type  M=maximize  P=skip popups  S=save")
        if self.is_edit_mode:
            help_parts.append("D=delete")
        help_parts.append("Esc=cancel")

        help_text = " | ".join(help_parts)

        # Prepend error message if present
        if self.error_message:
            help_text = f"{self.error_message} | {help_text}"

        # Build title
        title_prefix = "Edit Rule" if self.is_edit_mode else "Create Rule"

        return {
            "title": f"{title_prefix} - {title[:40]}",
            "items": items,
            "selected": self.selected - self.scroll_offset,
            "scroll_offset": self.scroll_offset,
            "total_count": len(items),
            "help_text": help_text,
        }

    def get_rule_config(self) -> Dict[str, Any]:
        """
        Get the current rule configuration.

        Returns:
            Dict with rule configuration ready to be sent to API
        """
        exe_name = self.window.get("exe_name", "unknown.exe")

        if self.match_type == "window_title":
            match_value = self.match_value_title
        else:
            match_value = exe_name

        return {
            "match_type": self.match_type,
            "match_value": match_value,
            "target_slot": self.selected_display,  # Slot number (1, 2, 3...)
            "maximize": self.maximize,
            "skip_popups": self.skip_popups,
        }


class SettingsView:
    """
    UI View for application settings.

    Allows configuring:
    - Default layout (auto-activated on startup)
    - Center mouse on window switch toggle
    """

    def __init__(
        self,
        settings: Dict[str, Any],
        layouts_data: List[Dict[str, Any]],
        update_settings_fn: Callable,
    ):
        """
        Initialize the settings view.

        Args:
            settings: Current settings dict from API
            layouts_data: List of available layouts
            update_settings_fn: Function to update settings via API
        """
        self.settings = settings
        self.layouts = layouts_data
        self.update_settings_fn = update_settings_fn

        # Menu items
        self.menu_items = [
            "default_layout",
            "center_mouse_on_switch",
        ]
        self.selected = 0
        self.max_visible_rows = 12
        self.error_message = None

        logger.info("SettingsView initialized")

    def handle_input(
        self,
        ch: int,
        key_down: bool,
        key_up: bool,
        key_escape: bool,
        key_backspace: bool,
        key_d: bool,
        key_a: bool = False,
        key_enter: bool = False,
        key_n: bool = False,
    ) -> Optional[str]:
        """
        Handle keyboard input.

        Navigation:
        - Up/Down: Select setting
        - Enter: Toggle setting (mouse centering)
        - Left/Right: Cycle through layouts (when default layout selected)
        - Esc/Backspace: Close

        Args:
            ch: Character code (0 if none)
            key_down: True if down arrow pressed
            key_up: True if up arrow pressed
            key_escape: True if escape pressed
            key_backspace: True if backspace pressed
            key_d: True if 'd' key pressed
            key_a: True if 'a' key pressed
            key_enter: True if enter pressed
            key_n: True if 'n' key pressed

        Returns:
            Action to take: 'close', or None
        """
        # Handle escape (close)
        if key_escape or key_backspace:
            return "close"

        # Handle navigation
        if key_down:
            self.selected = min(self.selected + 1, len(self.menu_items) - 1)

        if key_up:
            self.selected = max(self.selected - 1, 0)

        item = self.menu_items[self.selected]

        # Handle Left/Right for cycling layouts
        if item == "default_layout":
            from raylib import rl

            if rl.IsKeyPressed(rl.KEY_LEFT) or rl.IsKeyPressed(rl.KEY_RIGHT):
                # Cycle through layouts
                if not self.layouts:
                    self.error_message = "✗ No layouts available"
                    return None

                current_layout = self.settings.get("default_layout")

                # Build layout name list (None first, then all layouts)
                layout_names = [None] + [
                    l["file_name"].replace(".json", "") for l in self.layouts
                ]

                try:
                    current_idx = (
                        layout_names.index(current_layout)
                        if current_layout in layout_names
                        else 0
                    )
                except ValueError:
                    current_idx = 0

                # Move left or right
                if rl.IsKeyPressed(rl.KEY_LEFT):
                    new_idx = (current_idx - 1) % len(layout_names)
                else:
                    new_idx = (current_idx + 1) % len(layout_names)

                new_layout = layout_names[new_idx]
                result = self.update_settings_fn({"default_layout": new_layout})
                if result.get("success"):
                    self.settings["default_layout"] = new_layout
                    display_name = new_layout if new_layout else "(None)"
                    self.error_message = f"✓ Default layout: {display_name}"
                else:
                    self.error_message = (
                        f"✗ Failed to update: {result.get('error', 'Unknown')}"
                    )

        # Handle Enter - toggle setting
        if key_enter:
            if item == "center_mouse_on_switch":
                # Toggle the setting
                current = self.settings.get("center_mouse_on_switch", False)
                new_value = not current
                result = self.update_settings_fn({"center_mouse_on_switch": new_value})
                if result.get("success"):
                    self.settings["center_mouse_on_switch"] = new_value
                    self.error_message = (
                        f"✓ Mouse centering: {'ON' if new_value else 'OFF'}"
                    )
                else:
                    self.error_message = (
                        f"✗ Failed to update: {result.get('error', 'Unknown')}"
                    )

        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get render data for the settings view.

        Returns:
            Dict with:
                - title: View title
                - items: List of setting items
                - selected: Index of selected item
                - scroll_offset: Always 0 (no scrolling)
                - total_count: Number of settings
                - help_text: Help text to display
        """
        items = []

        # Default Layout setting
        default_layout = self.settings.get("default_layout")
        layout_display = default_layout if default_layout else "(None)"
        items.append(
            {
                "label": f"Default Layout: {layout_display}",
                "connected": True,
            }
        )

        # Center Mouse on Switch setting
        center_mouse = self.settings.get("center_mouse_on_switch", False)
        toggle_display = "ON" if center_mouse else "OFF"
        items.append(
            {
                "label": f"Center Mouse on Switch: {toggle_display}",
                "connected": True,
            }
        )

        # Build help text
        help_text = (
            "Up/Down: Navigate | Left/Right: Cycle layout | Enter: Toggle | Esc: Close"
        )
        if self.error_message:
            help_text = f"{self.error_message} | {help_text}"

        return {
            "title": "Settings",
            "items": items,
            "selected": self.selected,
            "scroll_offset": 0,
            "total_count": len(items),
            "help_text": help_text,
        }


# Global command registry instance
_registry: Optional[CommandRegistry] = None


def get_registry() -> CommandRegistry:
    """Get the global command registry (singleton)."""
    global _registry
    if _registry is None:
        _registry = CommandRegistry()
    return _registry


def register_builtin_commands(
    fetch_monitors_fn: Callable,
    fetch_layouts_fn: Optional[Callable] = None,
    activate_layout_fn: Optional[Callable] = None,
    deactivate_layout_fn: Optional[Callable] = None,
    get_active_layout_name_fn: Optional[Callable] = None,
    fetch_windows_fn: Optional[Callable] = None,
    fetch_settings_fn: Optional[Callable] = None,
    update_settings_fn: Optional[Callable] = None,
    fetch_layout_data_fn: Optional[Callable] = None,
    fetch_screen_config_fn: Optional[Callable] = None,
    get_assignment_fn: Optional[Callable] = None,
) -> None:
    """
    Register built-in commands.

    Args:
        fetch_monitors_fn: Function to fetch monitors from API (legacy /monitors command)
        fetch_layouts_fn: Function to fetch available layouts
        activate_layout_fn: Function to activate a layout
        deactivate_layout_fn: Function to deactivate current layout
        get_active_layout_name_fn: Function to get active layout name (str | None)
        fetch_windows_fn: Function to fetch all windows
        fetch_settings_fn: Function to fetch application settings
        update_settings_fn: Function to update application settings
        fetch_layout_data_fn: Function to fetch full layout data dict by name
        fetch_screen_config_fn: Function to fetch /screen-config → {"monitors": [...]}
                                Required for the /assign command.
        get_assignment_fn: Function(layout_name) → dict[str, str] returning the
                           current slot→identity_key assignment for that layout.
                           Required for the /assign command.
    """
    registry = get_registry()

    def handle_monitors_command(context: Dict[str, Any]) -> Any:
        """Handle /monitors command - show monitor management view."""
        logger.info("Executing /monitors command")
        monitors = fetch_monitors_fn()
        return MonitorManagementView(monitors)

    registry.register(
        "monitors",
        "Manage monitors (press 'd' to delete)",
        handle_monitors_command,
        category="System",
    )

    # Layout commands (if handlers provided)
    if fetch_layouts_fn:

        def handle_layouts_command(context: Dict[str, Any]) -> Any:
            """Handle /layouts command - show available layouts."""
            logger.info("Executing /layouts command")
            layouts = fetch_layouts_fn()
            active_layout = get_active_layout_name_fn() if get_active_layout_name_fn else None
            return LayoutManagementView(
                layouts,
                active_layout,
                activate_layout_fn,
                deactivate_layout_fn,
                None,  # fetch_screen_config_fn no longer used by LayoutManagementView
            )

        registry.register(
            "layouts",
            "Manage layouts (select to activate, 'a' to activate, 'd' to deactivate)",
            handle_layouts_command,
            category="Layouts",
        )

    # /assign command — map layout slots to physical monitors
    if fetch_screen_config_fn and get_assignment_fn and fetch_layout_data_fn and get_active_layout_name_fn:

        def handle_assign_command(context: Dict[str, Any]) -> Any:
            """Handle /assign command - assign monitors to layout slots.

            Uses the active layout if one is set; otherwise falls back to the
            first available layout so the user can set up an assignment before
            activating anything.
            """
            logger.info("Executing /assign command")
            target_layout_name = get_active_layout_name_fn()

            # If no layout is active, fall back to any available layout
            if not target_layout_name:
                if fetch_layouts_fn:
                    layouts = fetch_layouts_fn()
                    if layouts:
                        first = layouts[0]
                        target_layout_name = first.get("file_name", "").replace(".json", "")
                        logger.info(f"/assign: no active layout, falling back to '{target_layout_name}'")

            if not target_layout_name:
                error_view = AssignView({}, [], {}, layout_name="")
                error_view.set_error("No layouts found. Create a layout first.")
                return error_view

            layout_data = fetch_layout_data_fn(target_layout_name)
            if not layout_data:
                error_view = AssignView({}, [], {}, layout_name=target_layout_name)
                error_view.set_error(f"Could not load layout '{target_layout_name}'")
                return error_view

            screen_config = fetch_screen_config_fn()
            monitors = screen_config.get("monitors", [])
            current_assignment = get_assignment_fn(target_layout_name)
            return AssignView(layout_data, monitors, current_assignment, layout_name=target_layout_name)

        registry.register(
            "assign",
            "Assign physical monitors to layout slots (digit keys 1-9, S to save)",
            handle_assign_command,
            category="System",
        )

    if fetch_windows_fn:

        def handle_windows_command(context: Dict[str, Any]) -> Any:
            """Handle /windows command - show all windows."""
            logger.info("Executing /windows command")
            windows = fetch_windows_fn()
            active_layout_name = get_active_layout_name_fn() if get_active_layout_name_fn else None
            active_layout = (
                fetch_layout_data_fn(active_layout_name)
                if fetch_layout_data_fn and active_layout_name
                else None
            )
            return WindowsView(windows, active_layout)

        registry.register(
            "windows",
            "Manage windows (select to configure)",
            handle_windows_command,
            category="Windows",
        )

    # Settings command
    if fetch_settings_fn and update_settings_fn and fetch_layouts_fn:

        def handle_settings_command(context: Dict[str, Any]) -> Any:
            """Handle /settings command - show application settings."""
            logger.info("Executing /settings command")
            settings = fetch_settings_fn()
            layouts = fetch_layouts_fn()
            return SettingsView(settings, layouts, update_settings_fn)

        registry.register(
            "settings",
            "Application settings (default layout, mouse centering)",
            handle_settings_command,
            category="System",
        )

    logger.info("Built-in commands registered")
