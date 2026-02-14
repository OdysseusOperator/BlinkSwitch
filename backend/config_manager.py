import os
import json
import uuid
from datetime import datetime
import logging
from .monitor_fingerprint import MonitorFingerprint


class ConfigManager:
    """Manages the application configuration stored in JSON format."""

    def __init__(self, config_path=None):
        """Initialize the configuration manager.

        Args:
            config_path (str, optional): Path to the config file. If None, uses default location.
        """
        self.logger = logging.getLogger("ScreenAssign.ConfigManager")
        self.fingerprint_manager = MonitorFingerprint()

        if config_path is None:
            # Default location is in the backend directory
            self.config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "monitors_config.json"
            )
        else:
            self.config_path = config_path

        self.config_dir = os.path.dirname(self.config_path)

        # Ensure the config directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

        # Load or create the config file
        if not os.path.exists(self.config_path):
            self.logger.info(
                f"Config file not found. Creating default at {self.config_path}"
            )
            self.config = self._create_default_config()
            self.save_config()
        else:
            self.load_config()

        # Ensure snapshot exists even if load_config needed to create defaults.
        if not hasattr(self, "_last_saved_json"):
            self._last_saved_json = json.dumps(self.config, sort_keys=True)

    def load_config(self):
        """Load configuration from the JSON file."""
        try:
            with open(self.config_path, "r") as f:
                self.config = json.load(f)

            # Snapshot for change detection in save_config.
            self._last_saved_json = json.dumps(self.config, sort_keys=True)

            # Validate the config structure
            if not self._validate_config():
                self.logger.warning("Invalid config file. Creating new default config.")
                self.config = self._create_default_config()
                self.save_config()

            # Validate that all monitors have fingerprints (fingerprint-based system requirement)
            for monitor in self.config.get("known_monitors", []):
                if "fingerprints" not in monitor:
                    self.logger.error(
                        f"Monitor {monitor.get('id')} is missing required 'fingerprints' field. "
                        "This config is incompatible with the fingerprint-based monitor system. "
                        "Please regenerate your configuration with a clean config file."
                    )

            return True
        except Exception as e:
            self.logger.error(f"Error loading config: {str(e)}")
            self.config = self._create_default_config()
            return False

    def save_config(self):
        """Save configuration to the JSON file, overwriting without backups."""
        try:
            # If nothing changed, skip write
            if hasattr(self, "_last_saved_json"):
                current_json = json.dumps(self.config, sort_keys=True)
                if current_json == self._last_saved_json:
                    return True

            # If the on-disk content is already identical, skip write
            if os.path.exists(self.config_path):
                try:
                    with open(self.config_path, "r") as f:
                        on_disk = json.load(f)
                    if json.dumps(on_disk, sort_keys=True) == json.dumps(
                        self.config, sort_keys=True
                    ):
                        self._last_saved_json = json.dumps(self.config, sort_keys=True)
                        return True
                except Exception:
                    # If we can't read/parse, proceed with writing
                    pass

            # Write directly, overwriting without backup
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)

            self._last_saved_json = json.dumps(self.config, sort_keys=True)
            self.logger.debug(f"Config saved to {self.config_path}")

            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {str(e)}")
            return False

    def _create_default_config(self):
        """Create a default configuration structure."""
        return {
            "known_monitors": [],
            "settings": {"default_layout": None, "center_mouse_on_switch": False},
        }

    def _validate_config(self):
        """Validate that the config has the required structure."""
        if not isinstance(self.config, dict):
            return False
        if "known_monitors" not in self.config or not isinstance(
            self.config["known_monitors"], list
        ):
            return False

        # Ensure settings exist with defaults
        if "settings" not in self.config:
            self.config["settings"] = {
                "default_layout": None,
                "center_mouse_on_switch": False,
            }

        return True

    def add_monitor(self, monitor_data):
        """Add a new monitor to the known_monitors list.

        Uses fingerprint-based matching to identify monitors reliably across:
        - Different Windows detection orders
        - Different machines with different Y offsets

        Args:
            monitor_data (dict): Monitor data to add
        """
        # Generate fingerprints for this monitor
        fingerprints = self.fingerprint_manager.generate_fingerprint(monitor_data)
        monitor_data["fingerprints"] = fingerprints

        # Generate a unique ID if not provided
        if "id" not in monitor_data:
            monitor_data["id"] = f"monitor_{str(uuid.uuid4())[:8]}"

        # Add timestamps if not provided.
        # NOTE: We intentionally avoid updating any "last seen" style fields on every
        # detect cycle to prevent noisy config writes.
        now = datetime.now().isoformat()
        if "first_detected" not in monitor_data:
            monitor_data["first_detected"] = now

        # Check if a monitor with matching fingerprint already exists.
        # Use hierarchical matching: primary first, then secondary, then tertiary
        for existing_monitor in self.config["known_monitors"]:
            existing_fps = existing_monitor.get("fingerprints")

            # All monitors in current config should have fingerprints
            # (this is a fingerprint-based system, requires clean config)
            if existing_fps is None:
                self.logger.warning(
                    f"Monitor {existing_monitor.get('id')} missing fingerprints. "
                    "This config is incompatible with the fingerprint system. "
                    "Please use a clean config file."
                )
                continue

            # Try to match fingerprints
            is_match, reason = self.fingerprint_manager.fingerprints_match(
                fingerprints, existing_fps, strict=False
            )

            if is_match:
                self.logger.debug(
                    f"Monitor match found ({reason}): reusing ID {existing_monitor['id']}"
                )
                # Update position and other dynamic properties
                existing_monitor["x"] = monitor_data.get("x", existing_monitor.get("x"))
                existing_monitor["y"] = monitor_data.get("y", existing_monitor.get("y"))
                existing_monitor["is_primary"] = monitor_data.get(
                    "is_primary", existing_monitor.get("is_primary", False)
                )
                existing_monitor["name"] = monitor_data.get(
                    "name", existing_monitor.get("name")
                )
                existing_monitor["fingerprints"] = fingerprints

                # Mark config as changed (position or name might have updated)
                self.save_config()
                return existing_monitor["id"]

        # If no matching monitor is found, add the new one
        self.config["known_monitors"].append(monitor_data)
        self.save_config()
        self.logger.info(
            f"Added new monitor {monitor_data['id']} with fingerprints: {fingerprints}"
        )
        return monitor_data["id"]

    def update_monitor_connection(self, monitor_id, is_connected=True):
        """Update the connection status of a monitor.

        Args:
            monitor_id (str): The ID of the monitor to update
            is_connected (bool): Whether the monitor is currently connected
        """
        for monitor in self.config["known_monitors"]:
            if monitor["id"] == monitor_id:
                # Deprecated: we no longer persist "last connected" timestamps.
                # Keep method for compatibility, but avoid writing config.
                return True
        return False

    def get_all_monitors(self):
        """Get all known monitors.

        Returns:
            list: All known monitors
        """
        return self.config["known_monitors"]

    def get_monitor(self, monitor_id):
        """Get a monitor by ID.

        Args:
            monitor_id (str): The ID of the monitor to retrieve

        Returns:
            dict: The monitor data, or None if not found
        """
        for monitor in self.config["known_monitors"]:
            if monitor["id"] == monitor_id:
                return monitor
        return None

    def delete_monitor(self, monitor_id):
        """Delete a monitor by ID.

        Args:
            monitor_id (str): The ID of the monitor to delete

        Returns:
            bool: True if deleted, False if not found
        """
        for i, monitor in enumerate(self.config["known_monitors"]):
            if monitor["id"] == monitor_id:
                del self.config["known_monitors"][i]
                self.save_config()
                self.logger.info(f"Deleted monitor {monitor_id}")
                return True
        return False

    # Settings management methods

    def get_settings(self):
        """Get all application settings.

        Returns:
            dict: Application settings
        """
        if "settings" not in self.config:
            self.config["settings"] = {
                "default_layout": None,
                "center_mouse_on_switch": False,
            }
        return self.config["settings"]

    def update_settings(self, settings_dict):
        """Update application settings.

        Args:
            settings_dict (dict): Settings to update (partial or full)

        Returns:
            bool: True if successful
        """
        if "settings" not in self.config:
            self.config["settings"] = {}

        self.config["settings"].update(settings_dict)
        self.save_config()
        self.logger.info(f"Settings updated: {settings_dict}")
        return True

    def get_setting(self, key, default=None):
        """Get a specific setting value.

        Args:
            key (str): Setting key
            default: Default value if key doesn't exist

        Returns:
            The setting value or default
        """
        settings = self.get_settings()
        return settings.get(key, default)

    def set_setting(self, key, value):
        """Set a specific setting value.

        Args:
            key (str): Setting key
            value: Setting value

        Returns:
            bool: True if successful
        """
        return self.update_settings({key: value})
