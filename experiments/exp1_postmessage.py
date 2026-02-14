"""
Experiment 1: Send F11 using PostMessage
"""

import win32gui
import win32con
import win32api
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

    # Send F11 using PostMessage
    print("Sending F11 via PostMessage...")
    VK_F11 = 0x7A
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_F11, 0)
    time.sleep(0.05)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_F11, 0xC0000001)

    # Wait and check
    time.sleep(1)
    style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style_after < 0:
        style_after = style_after & 0xFFFFFFFF
    print(f"Style after: 0x{style_after:08X}")

    if style_before != style_after:
        print("✓ Style changed!")
    else:
        print("✗ Style unchanged")


if __name__ == "__main__":
    main()
