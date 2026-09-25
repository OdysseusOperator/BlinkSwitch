"""Shared, platform-neutral window-management types."""

from enum import Enum


class MaximizeState(str, Enum):
    MAXIMIZED = "maximized"
    NOT_MAXIMIZED = "not_maximized"
    UNSET = "unset"

    @classmethod
    def from_rule(cls, value: object) -> "MaximizeState":
        """Deserialize legacy and current maximize rule values."""
        if value is True:
            return cls.MAXIMIZED
        if isinstance(value, str):
            try:
                return cls(value)
            except ValueError:
                pass
        return cls.UNSET
