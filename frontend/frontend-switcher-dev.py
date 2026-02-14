"""
Development wrapper for window_switcher.py with auto-reload.

This script watches window_switcher.py for changes and automatically
restarts it when modifications are detected.

Usage:
    python window_switcher_dev.py
"""

import os
import sys
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class WindowSwitcherReloader(FileSystemEventHandler):
    """Handles file system events and restarts the window switcher."""

    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.last_restart = 0
        self.restart_delay = 1  # Minimum seconds between restarts
        self.start_process()

    def start_process(self):
        """Start the window switcher process."""
        if self.process:
            self.stop_process()

        print(f"\n{'=' * 60}")
        print(f"[DEV] Starting window_switcher.py...")
        print(f"{'=' * 60}\n")

        # Start the process
        self.process = subprocess.Popen(
            [sys.executable, self.script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        # Print output in real-time
        import threading

        def print_output():
            if self.process and self.process.stdout:
                for line in iter(self.process.stdout.readline, ""):
                    if line:
                        print(line.rstrip())

        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()

    def stop_process(self):
        """Stop the window switcher process."""
        if self.process:
            print(f"\n[DEV] Stopping window_switcher.py...")
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"[DEV] Force killing window_switcher.py...")
                self.process.kill()
            self.process = None

    def on_modified(self, event):
        """Handle file modification events."""
        if event.src_path.endswith("window_switcher.py"):
            # Debounce rapid file changes
            current_time = time.time()
            if current_time - self.last_restart < self.restart_delay:
                return

            self.last_restart = current_time
            print(f"\n[DEV] Detected change in {event.src_path}")
            print(f"[DEV] Reloading in {self.restart_delay}s...")
            time.sleep(self.restart_delay)
            self.start_process()


def main():
    """Main entry point for the dev wrapper."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "window_switcher.py")

    if not os.path.exists(script_path):
        print(f"Error: Could not find window_switcher.py at {script_path}")
        sys.exit(1)

    print("=" * 60)
    print("Window Switcher - Development Mode with Auto-Reload")
    print("=" * 60)
    print(f"Watching: {script_path}")
    print("Press CTRL+C to exit")
    print("=" * 60)

    # Set up file watcher
    event_handler = WindowSwitcherReloader(script_path)
    observer = Observer()
    observer.schedule(event_handler, path=script_dir, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[DEV] Shutting down...")
        event_handler.stop_process()
        observer.stop()
        observer.join()
        print("[DEV] Stopped.")


if __name__ == "__main__":
    main()
