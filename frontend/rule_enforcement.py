"""Report overlay visibility and mirror backend rule state; never schedule rules."""

import logging
import threading
import uuid
from typing import Any

import requests

logger = logging.getLogger("WindowSwitcher.RuleEnforcement")


class RuleEnforcementClient:
    def __init__(self, api_url: str) -> None:
        self._url = f"{api_url}/rule-enforcement/clients/{uuid.uuid4().hex}"
        self._lock = threading.Lock()
        self._visible = False
        self._state: dict[str, Any] | None = None
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="RuleStateSync", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def update(self, visible: bool) -> dict[str, Any] | None:
        with self._lock:
            self._visible = visible
            state, self._state = self._state, None
            return state

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        with requests.Session() as session:
            while not self._stop.is_set():
                with self._lock:
                    visible = self._visible
                try:
                    response = session.put(self._url, json={"visible": visible}, timeout=0.9)
                    response.raise_for_status()
                    state = response.json()
                    with self._lock:
                        self._state = state
                except (requests.RequestException, ValueError) as exc:
                    logger.debug("Rule state sync unavailable: %s", exc)
                self._stop.wait(1)
