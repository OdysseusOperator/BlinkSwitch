"""Runtime-only rule scheduler shared by all frontends."""

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

RULES_APPLY_INTERVAL = 5.0
FRONTEND_VISIBILITY_TTL = 4.0


class RuleEnforcement:
    def __init__(self, apply_rules: Callable[..., dict[str, Any]], validate: Callable[..., None]) -> None:
        self.logger = logging.getLogger("ScreenAssign.RuleEnforcement")
        self.lock = threading.RLock()
        self._state_lock = threading.RLock()
        self._apply_rules = apply_rules
        self._validate = validate
        self._configured = False
        self._layout: str | None = None
        self._assignment: dict[str, str] = {}
        self._clients: dict[str, tuple[bool, float]] = {}
        self._last_apply = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def state(self) -> dict[str, Any]:
        with self._state_lock:
            return {"layout_name": self._layout, "assignment": self._assignment.copy(), "configured": self._configured}

    def configure(self, layout: str | None, assignment: dict[str, str]) -> dict[str, Any]:
        with self.lock:
            # Validate before replacing the working configuration. Only the worker
            # applies automatically, outside HTTP requests and frontend draw loops.
            if layout is not None:
                self._validate(layout, assignment)
            with self._state_lock:
                self._configured = True
                self._layout = layout
                self._assignment = assignment.copy() if layout else {}
                self._last_apply = 0.0
                return self.state()

    def heartbeat(self, client_id: str, visible: bool) -> dict[str, Any]:
        with self._state_lock:
            self._clients[client_id] = (visible, time.monotonic())
            return self.state()

    def tick(self, now: float | None = None) -> None:
        with self.lock:
            now = time.monotonic() if now is None else now
            with self._state_lock:
                self._clients = {
                    key: value for key, value in self._clients.items()
                    if now - value[1] < FRONTEND_VISIBILITY_TTL
                }
                if not self._layout or any(visible for visible, _ in self._clients.values()):
                    return
                if now - self._last_apply < RULES_APPLY_INTERVAL:
                    return
                self._last_apply = now
                layout, assignment = self._layout, self._assignment.copy()
            try:
                self._apply_rules(layout, assignment)
            except Exception:
                self.logger.warning("Periodic rule application failed for layout %s", layout, exc_info=True)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="RuleEnforcer", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(1):
            self.tick()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            # Do not close platform adapters underneath an in-flight application.
            self._thread.join()
