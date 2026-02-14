"""
Experiment 5: Just maximize (fallback if F11 doesn't work)
"""

import win32gui
import win32con
import time


def get_vivaldi_window():
    """Find Vivaldi window."""

    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if "Vivaldi" in title:
                windows.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows[0] if windows else None


def main():
    result = get_vivaldi_window()
    if not result:
        print("Vivaldi window not found!")
        return

    hwnd, title = result
    print(f"Found: {title} (HWND: {hwnd})")

    # Get current style
    style_before = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style_before < 0:
        style_before = style_before & 0xFFFFFFFF
    print(f"Style before: 0x{style_before:08X}")

    # Just maximize
    print("Maximizing window...")
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

    # Wait and check
    time.sleep(0.5)
    style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style_after < 0:
        style_after = style_after & 0xFFFFFFFF
    print(f"Style after: 0x{style_after:08X}")

    # Check window rect
    rect = win32gui.GetWindowRect(hwnd)
    print(f"Window rect: {rect}")
    print("Note: Maximize is the fallback if F11 doesn't work programmatically")


if __name__ == "__main__":
    main()
