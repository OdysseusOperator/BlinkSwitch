"""
assignment.py — persistence helpers for slot→monitor assignments.

Format of assignment.json:
{
    "dual-screen-home": {
        "1": "-1920_0_1080_1920",
        "2": "0_0_1920_1080"
    }
}

The file lives next to this module at frontend/assignment.json.
"""

import json
import logging
import os
from typing import Dict

logger = logging.getLogger("WindowSwitcher.Assignment")

_ASSIGNMENT_FILE = os.path.join(os.path.dirname(__file__), "assignment.json")


def load_assignments() -> Dict[str, Dict[str, str]]:
    """Load all layout assignments from disk.

    Returns:
        Dict mapping layout_name → {slot_str → identity_key}.
        Returns an empty dict if the file does not exist or cannot be parsed.
    """
    if not os.path.exists(_ASSIGNMENT_FILE):
        logger.info(f"assignment.json not found at {_ASSIGNMENT_FILE}, starting empty")
        return {}
    try:
        with open(_ASSIGNMENT_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            logger.warning("assignment.json root is not a dict — ignoring")
            return {}
        logger.info(f"Loaded assignments for {len(data)} layouts from {_ASSIGNMENT_FILE}")
        return data
    except Exception as exc:
        logger.warning(f"Failed to load assignment.json: {exc}")
        return {}


def save_assignments(assignments: Dict[str, Dict[str, str]]) -> None:
    """Persist all layout assignments to disk.

    Args:
        assignments: Dict mapping layout_name → {slot_str → identity_key}.

    Raises:
        OSError: if the file cannot be written (caller should handle).
    """
    try:
        with open(_ASSIGNMENT_FILE, "w", encoding="utf-8") as fh:
            json.dump(assignments, fh, indent=2)
        logger.info(f"Saved assignments for {len(assignments)} layouts to {_ASSIGNMENT_FILE}")
    except Exception as exc:
        logger.error(f"Failed to save assignment.json: {exc}")
        raise
