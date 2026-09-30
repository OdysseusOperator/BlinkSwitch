#!/usr/bin/env python3
"""Start BlinkSwitch backend and frontend under one process supervisor."""

from __future__ import annotations

import argparse
import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[1]
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"
VENV_DIR = ROOT_DIR / ".venv"
REQUIREMENTS_MARKER = VENV_DIR / ".requirements.sha256"
HEALTH_URL = "http://127.0.0.1:5555/screenassign/health"
HEALTH_TIMEOUT_SECONDS = 30


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS_FILE.read_bytes()).hexdigest()


def install_requirements(force: bool) -> None:
    expected_hash = requirements_hash()
    installed_hash = REQUIREMENTS_MARKER.read_text().strip() if REQUIREMENTS_MARKER.exists() else ""
    if not force and installed_hash == expected_hash:
        return

    print("Installing BlinkSwitch requirements...")
    subprocess.run(
        ["uv", "pip", "install", "--python", sys.executable, "-r", str(REQUIREMENTS_FILE)],
        cwd=ROOT_DIR,
        check=True,
    )
    REQUIREMENTS_MARKER.write_text(expected_hash + "\n")


def backend_is_ready() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=1) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def stop_process(process: subprocess.Popen[bytes] | None, name: str) -> None:
    if process is None or process.poll() is not None:
        return
    print(f"Stopping {name}...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print(f"{name} did not stop cleanly; killing it.")
        process.kill()
        process.wait()


def request_shutdown(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def run(update: bool, frontend_name: str) -> int:
    install_requirements(update)
    signal.signal(signal.SIGTERM, request_shutdown)
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"

    backend = subprocess.Popen(
        [sys.executable, "-m", "backend.backend"], cwd=ROOT_DIR, env=environment
    )
    frontend: subprocess.Popen[bytes] | None = None
    try:
        print("Waiting for BlinkSwitch backend...")
        deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if backend.poll() is not None:
                return backend.returncode or 1
            if backend_is_ready():
                break
            time.sleep(1)
        else:
            print("ERROR: BlinkSwitch backend did not become ready within 30 seconds.", file=sys.stderr)
            return 1

        print(f"Starting BlinkSwitch frontend: {frontend_name}...")
        if frontend_name == "python":
            frontend_command = [sys.executable, "-m", "frontend.frontend-switcher"]
        else:
            executable_name = "blinkswitch-frontend.exe" if os.name == "nt" else "blinkswitch-frontend"
            frontend_path = ROOT_DIR / "frontend-go" / executable_name
            if not frontend_path.is_file():
                print(
                    f"ERROR: Clay frontend binary not found: {frontend_path}\n"
                    "Build it with frontend-go\\build.bat on Windows or "
                    "frontend-go/build.sh on Linux.",
                    file=sys.stderr,
                )
                return 1
            frontend_command = [str(frontend_path)]
        frontend = subprocess.Popen(frontend_command, cwd=ROOT_DIR, env=environment)
        while True:
            frontend_code = frontend.poll()
            backend_code = backend.poll()
            if frontend_code is not None:
                return frontend_code
            if backend_code is not None:
                print("ERROR: BlinkSwitch backend exited while frontend was running.", file=sys.stderr)
                return backend_code or 1
            time.sleep(0.25)
    except KeyboardInterrupt:
        return 130
    finally:
        stop_process(frontend, "frontend")
        stop_process(backend, "backend")


def main() -> int:
    parser = argparse.ArgumentParser(description="Start BlinkSwitch backend and frontend together.")
    parser.add_argument("--update", action="store_true", help="reinstall requirements before starting")
    parser.add_argument(
        "--frontend",
        choices=("python", "clay"),
        default=os.environ.get("BLINKSWITCH_FRONTEND", "python"),
        help="frontend implementation to start, default: python",
    )
    args = parser.parse_args()
    return run(args.update, args.frontend)


if __name__ == "__main__":
    raise SystemExit(main())
