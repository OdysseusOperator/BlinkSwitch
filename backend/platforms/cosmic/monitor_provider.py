"""COSMIC output enumeration and monitor scale metadata."""

import logging
import re
import subprocess
from types import SimpleNamespace
from typing import Any

from screeninfo import get_monitors


class CosmicMonitorProvider:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger("ScreenAssign.CosmicMonitorProvider")

    def enumerate_monitors(self) -> list[Any]:
        try:
            output = subprocess.run(
                ["cosmic-randr", "list", "--kdl"],
                check=True,
                capture_output=True,
                text=True,
                timeout=2,
            ).stdout
            monitors = self.parse_outputs(output)
            if monitors:
                return monitors
        except (OSError, subprocess.SubprocessError) as exc:
            self.logger.warning("COSMIC output enumeration unavailable: %s", exc)
        return get_monitors()

    def get_scale_factor(self, monitor: Any) -> float:
        return float(getattr(monitor, "scale", 1.0))

    @staticmethod
    def parse_outputs(kdl: str) -> list[Any]:
        monitors = []
        block = []
        depth = 0
        for line in kdl.splitlines():
            if not block and line.startswith("output "):
                block = [line]
                depth = line.count("{") - line.count("}")
                continue
            if not block:
                continue
            block.append(line)
            depth += line.count("{") - line.count("}")
            if depth > 0:
                continue

            text = "\n".join(block)
            name = re.search(r'^output "([^"]+)" enabled=#true', text, re.MULTILINE)
            position = re.search(r"^  position (-?\d+) (-?\d+)", text, re.MULTILINE)
            scale = re.search(r"^  scale ([0-9.]+)", text, re.MULTILINE)
            mode = re.search(r"^    mode (\d+) (\d+) \d+ current=#true", text, re.MULTILINE)
            transform = re.search(r'^  transform "([^"]+)"', text, re.MULTILINE)
            if name and position and mode:
                width, height = int(mode.group(1)), int(mode.group(2))
                if transform and transform.group(1) in {"rotate90", "rotate270"}:
                    width, height = height, width
                monitors.append(
                    SimpleNamespace(
                        name=name.group(1),
                        width=width,
                        height=height,
                        x=int(position.group(1)),
                        y=int(position.group(2)),
                        scale=float(scale.group(1)) if scale else 1.0,
                        is_primary=len(monitors) == 0,
                    )
                )
            block = []
        return monitors
