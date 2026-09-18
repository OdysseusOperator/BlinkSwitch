"""COSMIC Wayland window manager backed by the native helper process."""

import json
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from .window_manager import MaximizeState


class CosmicWindowManager:
    """WindowManager-compatible adapter for COSMIC's Wayland protocols."""

    def __init__(self, config_manager=None, monitor_manager=None, layout_manager=None, helper_path=None):
        self.logger = logging.getLogger("ScreenAssign.CosmicWindowManager")
        self.config_manager = config_manager
        self.monitor_manager = monitor_manager
        self.layout_manager = layout_manager
        self._lock = threading.Lock()
        self._process = None

        if os.name != "posix" or not os.environ.get("WAYLAND_DISPLAY"):
            raise RuntimeError("COSMIC window management requires a Linux COSMIC Wayland session")
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        session = os.environ.get("XDG_SESSION_DESKTOP", "").lower()
        if "cosmic" not in desktop and "cosmic" not in session:
            raise RuntimeError("COSMIC window management requires XDG_CURRENT_DESKTOP or XDG_SESSION_DESKTOP=cosmic")

        executable = self._find_helper(helper_path)
        try:
            self._process = subprocess.Popen(
                [executable], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, bufsize=1,
            )
        except OSError as exc:
            raise RuntimeError(f"Unable to launch COSMIC helper '{executable}': {exc}") from exc

    def _find_helper(self, helper_path):
        candidates = []
        if helper_path:
            candidates.append(Path(helper_path).expanduser())
        env_path = os.environ.get("COSMIC_HELPER")
        if env_path:
            candidates.append(Path(env_path).expanduser())
        root = Path(__file__).resolve().parent.parent / "cosmic-helper"
        candidates.extend((root / "target" / "release" / "blinkswitch-cosmic-helper",
                           root / "target" / "debug" / "blinkswitch-cosmic-helper"))
        found = shutil.which("blinkswitch-cosmic-helper")
        if found:
            candidates.append(Path(found))
        for candidate in candidates:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        searched = ", ".join(str(path) for path in candidates)
        raise RuntimeError(f"COSMIC helper unavailable; set COSMIC_HELPER or build blinkswitch-cosmic-helper (searched: {searched})")

    def _request(self, command, **fields):
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None or process.stdin is None or process.stdout is None:
                raise RuntimeError("COSMIC helper is not running")
            payload = {"command": command, **fields}
            try:
                process.stdin.write(json.dumps(payload) + "\n")
                process.stdin.flush()
                line = process.stdout.readline()
            except OSError as exc:
                raise RuntimeError(f"COSMIC helper communication failed: {exc}") from exc
            if not line:
                raise RuntimeError("COSMIC helper exited without a response")
            try:
                reply = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"COSMIC helper returned invalid JSON: {exc}") from exc
            if not reply.get("ok"):
                raise RuntimeError(reply.get("error") or "COSMIC helper rejected request")
            return reply.get("result") or {}

    def _snapshot(self):
        return self._request("list")

    @staticmethod
    def _state(window, state):
        return any(state in value for value in window.get("states", []))

    def get_all_windows(self):
        result = self._snapshot()
        windows = []
        for window in result.get("windows", []):
            geometry = (window.get("geometry") or [{}])[0]
            app_id = window.get("app_id") or ""
            windows.append({
                "hwnd": window["id"], "title": window.get("title") or "",
                "app_name": app_id, "app_display_name": app_id,
                "class_name": app_id, "pid": None, "process_path": None,
                "exe_name": app_id, "is_system": False, "is_uwp": False,
                "is_minimized": self._state(window, "minimized"),
                "position": (geometry.get("x", 0), geometry.get("y", 0),
                             geometry.get("width", 0), geometry.get("height", 0)),
                "is_maximized": self._state(window, "maximized"),
                "is_fullscreen": self._state(window, "fullscreen"),
                "monitor_id": self._monitor_id(geometry, window),
            })
        return windows

    def _monitor_id(self, geometry, window=None):
        if window and self.monitor_manager:
            output_ids = {
                item.get("id") for item in window.get("outputs", [])
            }
            snapshot_outputs = self._snapshot().get("outputs", [])
            for output in snapshot_outputs:
                if output.get("id") not in output_ids:
                    continue
                output_name = output.get("name") or output.get("description")
                for monitor in self.monitor_manager.get_all_connected_monitors().values():
                    if output_name in {getattr(monitor, "name", None), monitor.get("name") if isinstance(monitor, dict) else None}:
                        return monitor.get("id") if isinstance(monitor, dict) else None
                return self._monitor_at_output(output)
        if self.monitor_manager:
            x = geometry.get("x", 0) + geometry.get("width", 0) // 2
            y = geometry.get("y", 0) + geometry.get("height", 0) // 2
            monitor_id = self.monitor_manager.get_monitor_by_position(x, y)
            if monitor_id:
                return monitor_id
        outputs = (self._snapshot().get("outputs", []) if window is None else [])
        return next((item.get("name") or item.get("description") for item in outputs), None)

    def _monitor_at_output(self, output):
        if not self.monitor_manager:
            return None
        for monitor_id, monitor in self.monitor_manager.get_all_connected_monitors().items():
            if output.get("x") == monitor.x and output.get("y") == monitor.y:
                return monitor_id
        return None

    def _monitor_output(self, monitor_id):
        result = self._snapshot()
        monitor = self.monitor_manager.get_connected_monitor(monitor_id) if self.monitor_manager else None
        for output in result.get("outputs", []):
            if monitor_id in {output.get("name"), output.get("description")}:
                return output.get("name") or output.get("description")
            if monitor and output.get("x") == monitor.x and output.get("y") == monitor.y:
                return output.get("name") or output.get("description")
        return None

    def focus_window(self, hwnd):
        self._request("focus", id=int(hwnd))
        return True

    def fullscreen_window(self, hwnd, monitor_id=None):
        fields: dict[str, Any] = {"id": int(hwnd)}
        if monitor_id:
            output = self._monitor_output(monitor_id)
            if output:
                fields["target_output"] = output
        self._request("fullscreen", **fields)
        return True

    def unfullscreen_window(self, hwnd):
        self._request("unfullscreen", id=int(hwnd))
        return True

    def maximize_window(self, hwnd, monitor=None):
        self._request("maximize", id=int(hwnd))
        return True

    def move_window(self, hwnd, monitor):
        monitor_id = getattr(monitor, "id", None) or (monitor.get("id") if isinstance(monitor, dict) else None)
        if not monitor_id:
            raise RuntimeError("COSMIC move requires a monitor with an id")
        return self.move_window_to_monitor(hwnd, monitor_id, maximize=False)

    def is_window_maximized(self, hwnd):
        window = next((item for item in self.get_all_windows() if item["hwnd"] == int(hwnd)), None)
        return bool(window and window["is_maximized"])

    def get_window_monitor_id(self, hwnd):
        window = next((item for item in self.get_all_windows() if item["hwnd"] == int(hwnd)), None)
        return window.get("monitor_id") if window else None

    def restore_window(self, hwnd):
        self._request("unmaximize", id=int(hwnd))
        return True

    def move_window_to_monitor(self, hwnd, monitor_id, maximize=True):
        """Move through the helper's workspace API when target workspace is known."""
        output = self._monitor_output(monitor_id)
        if not output:
            raise RuntimeError(f"Target monitor {monitor_id} has no COSMIC output")
        result = self._snapshot()
        workspaces = result.get("workspaces", [])
        output_ids = {
            item.get("id") for item in result.get("outputs", [])
            if item.get("name") == output or item.get("description") == output
        }
        target = next((item for item in workspaces if output_ids.intersection(item.get("output_ids", []))), None)
        if target is None and workspaces:
            target = workspaces[0]
        if target is None or not target.get("id") and not target.get("name"):
            raise RuntimeError("COSMIC helper exposed no target workspace for monitor move")
        self._request("move_workspace", id=int(hwnd), workspace=target.get("id") or target.get("name"), target_output=output)
        if maximize:
            self.maximize_window(hwnd)
        return True

    def apply_window_rule(self, hwnd, monitor_id, maximize=MaximizeState.UNSET, skip_popups=False, fullscreen=None):
        current = next((item for item in self.get_all_windows() if item["hwnd"] == int(hwnd)), None)
        if current is None:
            return {"changed": False, "operations": []}
        operations = []
        if current.get("monitor_id") != monitor_id:
            self.move_window_to_monitor(hwnd, monitor_id, maximize=False)
            operations.append("move")
        if maximize is MaximizeState.MAXIMIZED and not current["is_maximized"]:
            self.maximize_window(hwnd)
            operations.append("maximize")
        elif maximize is MaximizeState.NOT_MAXIMIZED and current["is_maximized"]:
            self.restore_window(hwnd)
            operations.append("restore")
        if fullscreen is True and not current.get("is_fullscreen"):
            self.fullscreen_window(hwnd, monitor_id)
            operations.append("fullscreen")
        elif fullscreen is False and current.get("is_fullscreen"):
            self.unfullscreen_window(hwnd)
            operations.append("unfullscreen")
        return {"changed": bool(operations), "operations": operations}

    def apply_rules_for_window(self, hwnd, layout_name, assignment):
        if not self.layout_manager:
            return {"matched": False, "changed": False, "operations": [], "rule_id": None, "message": "No layout_manager configured"}
        rules = self.layout_manager.get_rules_for_layout(layout_name, assignment)
        window = next((item for item in self.get_all_windows() if item["hwnd"] == int(hwnd)), None)
        if not window:
            return {"matched": False, "changed": False, "operations": [], "rule_id": None, "message": "Window not found"}
        for rule in rules:
            value = (rule.get("match_value") or "").lower()
            match_type = rule.get("match_type")
            candidate = window.get("exe_name") if match_type == "exe" else window.get("title")
            if match_type == "process_path":
                candidate = window.get("process_path")
            matches = value and (candidate or "").lower() == value if match_type == "exe" else value and value in (candidate or "").lower()
            if matches:
                result = self.apply_window_rule(int(hwnd), rule.get("target_monitor_id"), MaximizeState.from_rule(rule.get("maximize")), rule.get("skip_popups", False), rule.get("fullscreen"))
                return {**result, "matched": True, "rule_id": rule.get("rule_id"), "message": ", ".join(result["operations"]) or "Window already in correct state"}
        return {"matched": False, "changed": False, "operations": [], "rule_id": None, "message": "No rule matched window"}

    def apply_rules(self, layout_name, assignment):
        results = {"applied": 0, "skipped_no_monitor": 0, "skipped_no_window": 0, "failed": 0, "details": []}
        if not self.layout_manager:
            return results
        for window in self.get_all_windows():
            try:
                result = self.apply_rules_for_window(window["hwnd"], layout_name, assignment)
                if result["changed"]:
                    results["applied"] += 1
            except Exception as exc:
                self.logger.error("Error applying COSMIC rule to window %s: %s", window["hwnd"], exc)
                results["failed"] += 1
        return results

    def close(self):
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
