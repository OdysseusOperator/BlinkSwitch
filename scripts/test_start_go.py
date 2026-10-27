"""Exercise Linux launcher routing without starting services or building binaries."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == "posix", "Linux shell launcher")
class StartGoTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="blinkswitch launchers ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / "calls"
        shutil.copy2(ROOT / "start_go.sh", self.root / "start_go.sh")
        self.stub("start.sh", "start")
        self.stub("frontend-go/build.sh", "build")
        self.stub("frontend-go/blinkswitch-frontend", "toggle")
        self.environment = {
            key: value for key, value in os.environ.items()
            if key not in {"BLINKSWITCH_KEEP_OPEN", "BLINKSWITCH_RENDER_CHECK", "WAYLAND_DISPLAY"}
        }
        self.environment["LAUNCH_TEST_LOG"] = str(self.log)

    def stub(self, path: str, label: str, code: int = 0) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            '#!/usr/bin/env bash\n'
            f'printf "%s\\n" "{label}:$*|keep=${{BLINKSWITCH_KEEP_OPEN:-0}}|render=${{BLINKSWITCH_RENDER_CHECK:-0}}" '
            '>> "$LAUNCH_TEST_LOG"\n'
            f'exit {code}\n'
        )
        target.chmod(0o755)

    def launch(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.root / "start_go.sh"), *arguments],
            cwd="/", env=self.environment, capture_output=True, text=True, check=False,
        )

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_normal_start_builds_then_delegates_to_shared_launcher(self):
        self.assertEqual(self.launch().returncode, 0)
        self.assertEqual(self.calls(), [
            "build:|keep=0|render=0", "start:--frontend clay|keep=0|render=0",
        ])

    def test_testing_options_and_update_are_forwarded(self):
        self.environment["WAYLAND_DISPLAY"] = "wayland-1"
        self.assertEqual(self.launch("--keep-open", "--render-check", "--update").returncode, 0)
        self.assertEqual(self.calls(), [
            "build:|keep=1|render=1", "start:--frontend clay --update|keep=1|render=1",
        ])

    def test_toggle_skips_build_and_supervisor(self):
        self.assertEqual(self.launch("--toggle").returncode, 0)
        self.assertEqual(self.calls(), ["toggle:--toggle|keep=0|render=0"])

    def test_help_and_invalid_options_do_not_start_anything(self):
        self.assertIn("Usage:", self.launch("--help").stdout)
        self.assertEqual(self.launch("--invalid").returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_render_check_requires_wayland(self):
        self.assertEqual(self.launch("--render-check").returncode, 1)
        self.assertEqual(self.calls(), [])

    def test_build_failure_does_not_start_services(self):
        self.stub("frontend-go/build.sh", "build", code=17)
        self.assertEqual(self.launch().returncode, 17)
        self.assertEqual(self.calls(), ["build:|keep=0|render=0"])


if __name__ == "__main__":
    unittest.main()
