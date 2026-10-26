"""One-shot window actions must not modify layouts or combine operations."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from backend.platforms.cosmic.window_manager import CosmicWindowManager

with patch("backend.service.ScreenAssignService"), patch("backend.tab_enumerators.ChromeTabManager"):
    from backend import backend as api


class WindowActionsTests(unittest.TestCase):
    def setUp(self):
        self.manager = Mock()
        self.manager.get_all_windows.return_value = [{"hwnd": 42}]
        self.monitors = Mock()
        svc = SimpleNamespace(window_manager=self.manager, monitor_manager=self.monitors)
        service_patch = patch.object(api, "service", svc)
        service_patch.start()
        self.addCleanup(service_patch.stop)
        app = Flask(__name__)
        app.register_blueprint(api.screenassign_api, url_prefix="/screenassign")
        self.client = app.test_client()

    def post(self, **payload):
        return self.client.post("/screenassign/test-window-action", json={"hwnd": 42, **payload})

    def test_screen_move_does_not_maximize(self):
        self.assertEqual(self.post(action="screen", monitor_id="screen-b").status_code, 200)
        self.manager.move_window_to_monitor.assert_called_once_with(42, "screen-b", maximize=False)
        self.manager.maximize_window.assert_not_called()

    def test_workspace_and_maximize_are_independent(self):
        self.manager.move_window_to_workspace.return_value = False
        self.assertEqual(self.post(action="workspace", workspace=3).status_code, 200)
        self.manager.move_window_to_workspace.assert_called_once_with(42, 3)
        self.manager.move_window_to_monitor.assert_not_called()
        self.assertEqual(self.post(action="maximize").status_code, 200)
        self.manager.maximize_window.assert_called_once_with(42, None)
        self.manager.apply_rules.assert_not_called()

    def test_validation_and_stale_targets(self):
        for payload in ({"action": "invalid"}, {"action": "workspace", "workspace": True},
                        {"action": "workspace", "workspace": 0}, {"action": "maximize", "hwnd": True}):
            self.assertEqual(self.post(**payload).status_code, 400)
        self.manager.get_all_windows.return_value = []
        self.assertEqual(self.post(action="maximize").status_code, 404)
        self.manager.get_all_windows.return_value = [{"hwnd": 42}]
        self.monitors.get_connected_monitor.return_value = None
        self.assertEqual(self.post(action="screen", monitor_id="gone").status_code, 400)

    def test_native_error_is_reported(self):
        self.manager.move_window_to_workspace.side_effect = RuntimeError("Workspace unavailable")
        response = self.post(action="workspace", workspace=99)
        self.assertEqual(response.status_code, 409)
        self.assertIn("Workspace unavailable", response.json["error"])

    def test_cosmic_workspace_resolves_runtime_monitor_registry_key(self):
        manager = CosmicWindowManager.__new__(CosmicWindowManager)
        monitor = SimpleNamespace(name="DP-1", x=0, y=0)
        manager.monitor_manager = Mock()
        manager.monitor_manager.get_all_connected_monitors.return_value = {"registry-id": monitor}
        manager.monitor_manager.get_connected_monitor.return_value = monitor
        manager._snapshot = Mock(return_value={
            "windows": [{"id": 3, "outputs": [{"id": 10}]}],
            "outputs": [{"id": 10, "name": "DP-1", "x": 0, "y": 0}],
            "workspaces": [
                {"id": "workspace-a", "output_ids": [10]},
                {"id": "workspace-b", "output_ids": [10]},
            ],
        })
        manager._request = Mock(return_value={})

        self.assertEqual(manager.get_window_monitor_id(3), "registry-id")
        self.assertTrue(manager.move_window_to_workspace(3, 2))
        manager._request.assert_called_once_with(
            "move_workspace", id=3, workspace="workspace-b", target_output="DP-1"
        )
        # Persisted monitor dictionaries must also use the registry's key.
        manager.monitor_manager.get_all_connected_monitors.return_value = {
            "registry-id": {"name": "DP-1", "id": "not-the-registry-key"}
        }
        self.assertEqual(manager.get_window_monitor_id(3), "registry-id")

    def test_cosmic_workspace_preserves_output_and_does_not_maximize(self):
        manager = CosmicWindowManager.__new__(CosmicWindowManager)
        manager.get_window_monitor_id = Mock(return_value="current-monitor")
        manager.move_window_to_monitor = Mock(return_value=True)
        self.assertTrue(manager.move_window_to_workspace(42, 3))
        manager.move_window_to_monitor.assert_called_once_with(
            42, "current-monitor", maximize=False, workspace_number=3
        )
