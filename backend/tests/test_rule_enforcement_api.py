"""HTTP contract for the backend-owned rule scheduler."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask

from backend.layout_manager import LayoutError
from backend.rule_enforcement import RuleEnforcement

# backend.backend also creates an app on import; never start real adapters here.
with patch("backend.service.ScreenAssignService"), patch("backend.tab_enumerators.ChromeTabManager"):
    from backend import backend as api


class RuleEnforcementApiTests(unittest.TestCase):
    def setUp(self):
        self.apply = Mock()
        self.validate = Mock()
        self.scheduler = RuleEnforcement(self.apply, self.validate)
        self.service_patch = patch.object(api, "service", SimpleNamespace(rule_enforcement=self.scheduler))
        self.service_patch.start()
        self.addCleanup(self.service_patch.stop)
        app = Flask(__name__)
        app.register_blueprint(api.screenassign_api, url_prefix="/screenassign")
        self.client = app.test_client()
        self.path = "/screenassign/rule-enforcement"

    def test_shared_activation_heartbeat_and_deactivation(self):
        response = self.client.put(self.path, json={"layout_name": "work", "assignment": {"1": "monitor-a"}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(self.path).json["layout_name"], "work")
        response = self.client.put(self.path + "/clients/python", json={"visible": True})
        self.assertEqual(response.json["assignment"], {"1": "monitor-a"})
        response = self.client.put(self.path, json={"layout_name": None})
        self.assertIsNone(response.json["layout_name"])
        self.apply.assert_not_called()

    def test_invalid_payloads(self):
        for data in ({}, [], {"layout_name": ""}, {"layout_name": 12}, {"layout_name": "work"},
                     {"layout_name": "work", "assignment": {"1": None}}):
            with self.subTest(data=data):
                self.assertEqual(self.client.put(self.path, json=data).status_code, 400)
        self.assertEqual(self.client.put(self.path + "/clients/python", json={"visible": "true"}).status_code, 400)

    def test_layout_conflict_does_not_replace_active_layout(self):
        self.scheduler.configure("work", {"1": "monitor-a"})
        self.validate.side_effect = LayoutError("monitor unavailable")
        response = self.client.put(self.path, json={"layout_name": "invalid", "assignment": {"1": "missing"}})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(self.path).json["layout_name"], "work")


if __name__ == "__main__":
    unittest.main()
