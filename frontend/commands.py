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
        self.max_visible_rows = 8
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
        active_layout: Optional[Dict[str, Any]],
        activate_fn: Optional[Callable],
        deactivate_fn: Optional[Callable],
        fetch_screen_config_fn: Optional[Callable],
    ):
        """
        Initialize the layout management view.

        Args:
            layouts_data: List of layout dictionaries from API
            active_layout: Currently active layout info or None
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
        self.max_visible_rows = 8
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
                self.active_layout.get("file_name", "") if self.active_layout else ""
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
            self.active_layout.get("file_name", "") if self.active_layout else ""
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


class ScreenConfigView:
    """
    UI View for displaying current screen configuration.
    """

    def __init__(self, screen_config_data: Dict[str, Any]):
        """
        Initialize the screen config view.

        Args:
            screen_config_data: Screen config data from API
        """
        self.screens = screen_config_data.get("screens", [])
        self.summary = screen_config_data.get("summary", "")
        logger.info(f"ScreenConfigView initialized with {len(self.screens)} screens")

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
            key_d: True if 'd' key pressed (not used in this view)
            key_a: True if 'a' key pressed (not used in this view)
            key_enter: True if enter pressed (not used in this view)
            key_n: True if 'n' key pressed (not used in this view)

        Returns:
            Action to take: 'close' or None
        """
        if key_escape:
            return "close"
        return None

    def get_render_data(self) -> Dict[str, Any]:
        """
        Get data needed for rendering.

        Returns:
            Dict with:
                - title: View title
                - items: List of screen items
                - selected: Always 0 (no selection)
                - scroll_offset: Always 0
                - total_count: Number of screens
                - help_text: Help text to display
                - show_screen_overlays: Flag to trigger physical screen overlays
                - screens: Screen configuration data for overlay rendering
        """
        items = []
        for screen in self.screens:
            display_num = screen.get("display_number", 0)
            orientation = screen.get("orientation", "unknown")
            width = screen.get("width", 0)
            height = screen.get("height", 0)
            name = screen.get("name", "Unknown")

            label = f"DISPLAY{display_num}: {orientation} ({width}×{height}) - {name}"
            items.append({"label": label, "connected": True})

        return {
            "title": f"Screen Configuration - {self.summary}",
            "items": items,
            "selected": -1,  # No selection
            "scroll_offset": 0,
            "total_count": len(items),
            "help_text": "Esc to close",
            "show_screen_overlays": True,  # Enable physical screen numbering
            "screens": self.screens,  # Pass screen data for overlay rendering
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
        self.max_visible_rows = 8
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
            key_d: True if 'd' key pressed (not used)
            key_a: True if 'a' key pressed (not used)
            key_enter: True if enter pressed (open window details)
            key_n: True if 'n' key pressed (not used)

        Returns:
            Action to take: 'close', 'window_details', or None
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
        help_parts = [f"Layout: {layout_name}", "Enter to configure", "Esc to close"]
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

    Allows selecting target display, fullscreen/maximize options, then saves rule.
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

        # Configuration options
        self.selected_display = 1  # Default to Display 1 (logical display number)
        self.fullscreen = False
        self.maximize = False

        # Check for existing rule (for edit mode)
        self.existing_rule = None
        self.is_edit_mode = False
        self.error_message = None

        if active_layout and "data" in active_layout:
            rules = active_layout["data"].get("rules", [])
            self.existing_rule = _find_matching_rule_for_window(window_data, rules)

            if self.existing_rule:
                self.is_edit_mode = True
                # Pre-populate values from existing rule
                self.selected_display = self.existing_rule.get("target_display", 1)
                self.fullscreen = self.existing_rule.get("fullscreen", False)
                self.maximize = self.existing_rule.get("maximize", False)
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
        - f: Toggle fullscreen
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

        # Get total items count (screens + 2 options + 1 save button)
        total_items = len(self.screens) + 3

        # Navigation
        if key_down:
            self.selected = (self.selected + 1) % total_items
            logger.debug(f"Selected: {self.selected}")
        elif key_up:
            self.selected = (self.selected - 1) % total_items
            logger.debug(f"Selected: {self.selected}")

        # Enter key - toggle or save
        if key_enter:
            if self.selected < len(self.screens):
                # Selecting a display
                self.selected_display = self.screens[self.selected]["display_number"]
                logger.info(f"Selected display: {self.selected_display}")
            elif self.selected == len(self.screens):
                # Toggle fullscreen
                self.fullscreen = not self.fullscreen
                logger.info(f"Fullscreen toggled to: {self.fullscreen}")
            elif self.selected == len(self.screens) + 1:
                # Toggle maximize
                self.maximize = not self.maximize
                logger.info(f"Maximize toggled to: {self.maximize}")
            elif self.selected == len(self.screens) + 2:
                # Save button
                return "save"

        # Keyboard shortcuts
        if ch == ord("f") or ch == ord("F"):
            self.fullscreen = not self.fullscreen
            logger.info(f"Fullscreen toggled to: {self.fullscreen}")
        elif ch == ord("m") or ch == ord("M"):
            self.maximize = not self.maximize
            logger.info(f"Maximize toggled to: {self.maximize}")
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
            display_num = screen["display_number"]
            orientation = screen["orientation"]
            description = screen.get("description", f"Display {display_num}")
            selected_marker = "[*]" if display_num == self.selected_display else "[ ]"
            items.append(
                {
                    "label": f"{selected_marker} Display {display_num}: {description} [{orientation}]",
                    "connected": True,
                }
            )

        # Add fullscreen option
        fullscreen_marker = "[X]" if self.fullscreen else "[ ]"
        items.append({"label": f"{fullscreen_marker} Fullscreen", "connected": True})

        # Add maximize option
        maximize_marker = "[X]" if self.maximize else "[ ]"
        items.append({"label": f"{maximize_marker} Maximize", "connected": True})

        # Add save button
        save_label = ">> UPDATE RULE <<" if self.is_edit_mode else ">> SAVE RULE <<"
        items.append({"label": save_label, "connected": True})

        # Build help text
        help_parts = [f"Window: {exe_name}"]
        help_parts.append("F=fullscreen M=maximize S=save")
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

        return {
            "match_type": "exe",
            "match_value": exe_name,
            "target_display": self.selected_display,  # Logical display number (1, 2, 3...)
            "fullscreen": self.fullscreen,
            "maximize": self.maximize,
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
    fetch_screen_config_fn: Optional[Callable] = None,
    activate_layout_fn: Optional[Callable] = None,
    deactivate_layout_fn: Optional[Callable] = None,
    get_active_layout_fn: Optional[Callable] = None,
    fetch_windows_fn: Optional[Callable] = None,
    fetch_settings_fn: Optional[Callable] = None,
    update_settings_fn: Optional[Callable] = None,
) -> None:
    """
    Register built-in commands.

    Args:
        fetch_monitors_fn: Function to fetch monitors from API
        fetch_layouts_fn: Function to fetch available layouts
        fetch_screen_config_fn: Function to fetch current screen configuration
        activate_layout_fn: Function to activate a layout
        deactivate_layout_fn: Function to deactivate current layout
        get_active_layout_fn: Function to get active layout info
        fetch_windows_fn: Function to fetch all windows
        fetch_settings_fn: Function to fetch application settings
        update_settings_fn: Function to update application settings
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
            active_layout = get_active_layout_fn() if get_active_layout_fn else None
            return LayoutManagementView(
                layouts,
                active_layout,
                activate_layout_fn,
                deactivate_layout_fn,
                fetch_screen_config_fn,
            )

        registry.register(
            "layouts",
            "Manage layouts (select to activate, 'a' to activate, 'd' to deactivate)",
            handle_layouts_command,
            category="Layouts",
        )

    if fetch_screen_config_fn:

        def handle_screen_config_command(context: Dict[str, Any]) -> Any:
            """Handle /screen-config command - show current screen configuration."""
            logger.info("Executing /screen-config command")
            screen_config = fetch_screen_config_fn()
            return ScreenConfigView(screen_config)

        registry.register(
            "screen-config",
            "Show current screen configuration",
            handle_screen_config_command,
            category="System",
        )

    if fetch_windows_fn:

        def handle_windows_command(context: Dict[str, Any]) -> Any:
            """Handle /windows command - show all windows."""
            logger.info("Executing /windows command")
            windows = fetch_windows_fn()
            active_layout = get_active_layout_fn() if get_active_layout_fn else None
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
