"""Tests for optional rule workspace targeting and platform defaults."""

import unittest

from backend.layout_manager import LayoutManager
from backend.platforms.cosmic.window_manager import CosmicWindowManager
from frontend.commands import WindowDetailsView


class WorkspaceRuleTests(unittest.TestCase):
    def test_layout_schema_accepts_omitted_workspace_and_rejects_invalid_number(self):
        layout = {
            "name": "test",
            "screen_requirements": {
                "total_screens": 1,
                "screens": [{"slot": 1, "orientation": "horizontal"}],
            },
            "rules": [
                {"match_type": "exe", "match_value": "Weztearm", "target_slot": 1}
            ],
        }
        manager = LayoutManager.__new__(LayoutManager)

        self.assertTrue(manager.validate_layout(layout)[0])
        layout["rules"][0]["target_workspace"] = 0
        self.assertFalse(manager.validate_layout(layout)[0])

    def test_rule_editor_omits_default_and_saves_explicit_workspace(self):
        view = WindowDetailsView(
            {"exe_name": "Weztearm", "title": "Weztearm"},
            {
                "data": {
                    "screen_requirements": {
                        "screens": [{"slot": 1, "orientation": "horizontal"}]
                    },
                    "rules": [],
                }
            },
        )

        self.assertNotIn("target_workspace", view.get_rule_config())
        view._cycle_workspace()
        self.assertEqual(view.get_rule_config()["target_workspace"], 2)

    def test_cosmic_workspace_number_is_scoped_to_target_output(self):
        manager = CosmicWindowManager.__new__(CosmicWindowManager)
        manager._monitor_output = lambda monitor_id: "DP-1"
        manager._snapshot = lambda: {
            "outputs": [{"id": 10, "name": "DP-1"}, {"id": 20, "name": "DP-2"}],
            "workspaces": [
                {"id": "a", "output_ids": [10]},
                {"id": "b", "output_ids": [20]},
                {"id": "c", "output_ids": [10]},
            ],
        }

        self.assertEqual(manager._target_workspace("monitor-1", 2), ("DP-1", "c"))


if __name__ == "__main__":
    unittest.main()
