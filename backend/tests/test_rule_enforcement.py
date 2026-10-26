"""Backend scheduler tests without real windows or platform actions."""

import threading
import unittest
from unittest.mock import Mock, patch

from backend.rule_enforcement import RuleEnforcement


class RuleEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.apply = Mock(return_value={"applied": 1, "failed": 0})
        self.validate = Mock()
        self.scheduler = RuleEnforcement(self.apply, self.validate)

    def test_one_backend_tick_and_deactivation(self):
        self.scheduler.tick(10)
        self.apply.assert_not_called()
        self.scheduler.configure("work", {"1": "monitor-a"})
        self.validate.assert_called_once_with("work", {"1": "monitor-a"})
        self.apply.assert_not_called()
        self.scheduler.tick(10)
        self.scheduler.tick(11)
        self.scheduler.tick(15)
        self.assertEqual(self.apply.call_count, 2)
        self.scheduler.configure(None, {})
        self.scheduler.tick(20)
        self.assertEqual(self.apply.call_count, 2)
        self.assertTrue(self.scheduler.state()["configured"])
        self.assertIsNone(self.scheduler.state()["layout_name"])

    def test_shared_visibility_and_expired_clients(self):
        self.scheduler.configure("work", {"1": "monitor-a"})
        with patch("backend.rule_enforcement.time.monotonic", return_value=10):
            self.scheduler.heartbeat("python", True)
            self.scheduler.heartbeat("go-testing", False)
        self.scheduler.tick(11)
        self.apply.assert_not_called()
        self.scheduler.tick(14)
        self.apply.assert_called_once()

    def test_hidden_client_does_not_override_other_visible_frontend(self):
        self.scheduler.configure("work", {"1": "monitor-a"})
        with patch("backend.rule_enforcement.time.monotonic", return_value=10):
            self.scheduler.heartbeat("python", True)
            self.scheduler.heartbeat("go", False)
        self.scheduler.tick(12)
        self.apply.assert_not_called()
        with patch("backend.rule_enforcement.time.monotonic", return_value=12):
            self.scheduler.heartbeat("python", False)
        self.scheduler.tick(13)
        self.apply.assert_called_once()

    def test_assignment_updates_and_invalid_activation_retains_state(self):
        assignment = {"1": "monitor-a"}
        self.scheduler.configure("work", assignment)
        assignment["1"] = "mutated"
        state = self.scheduler.state()
        state["assignment"]["1"] = "also-mutated"
        self.assertEqual(self.scheduler.state()["assignment"], {"1": "monitor-a"})
        self.scheduler.configure("work", {"1": "monitor-b"})
        self.validate.side_effect = ValueError("unavailable monitor")
        with self.assertRaises(ValueError):
            self.scheduler.configure("invalid", {"1": "missing"})
        self.scheduler.tick(10)
        self.apply.assert_called_once_with("work", {"1": "monitor-b"})

    def test_failure_retries_at_interval(self):
        self.scheduler.configure("work", {"1": "monitor-a"})
        self.apply.side_effect = RuntimeError("monitor disconnected")
        with self.assertLogs("ScreenAssign.RuleEnforcement", level="WARNING"):
            self.scheduler.tick(10)
        self.scheduler.tick(11)
        self.assertEqual(self.apply.call_count, 1)
        self.apply.side_effect = None
        self.scheduler.tick(15)
        self.assertEqual(self.apply.call_count, 2)

    def test_heartbeat_does_not_block_on_window_operation(self):
        entered, release = threading.Event(), threading.Event()
        def apply(*_args):
            entered.set()
            release.wait(2)
        self.scheduler._apply_rules = apply
        self.scheduler.configure("work", {"1": "monitor-a"})
        worker = threading.Thread(target=self.scheduler.tick, args=(10,))
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertEqual(self.scheduler.heartbeat("python", True)["layout_name"], "work")
        finally:
            release.set()
            worker.join(2)

    def test_worker_stops_promptly(self):
        self.scheduler.start()
        worker = self.scheduler._thread
        self.scheduler.stop()
        self.assertFalse(worker.is_alive())


if __name__ == "__main__":
    unittest.main()
