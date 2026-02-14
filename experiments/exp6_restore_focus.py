"""
Experiment 6: SendInput but restore original focus afterward
"""

import win32gui
import win32con
import win32api
import time
import ctypes
from ctypes import wintypes

# Define INPUT structures
PUL = ctypes.POINTER(ctypes.c_ulong)


class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", PUL),
    ]


class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("ii", Input_I)]


def press_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(hexKeyCode, 0, 0, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


def release_key(hexKeyCode):
    extra = ctypes.c_ulong(0)
    ii_ = Input_I()
    ii_.ki = KeyBdInput(hexKeyCode, 0, 0x0002, 0, ctypes.pointer(extra))
    x = Input(ctypes.c_ulong(1), ii_)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))


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

    # Save the current foreground window
    original_foreground = win32gui.GetForegroundWindow()
    original_title = (
        win32gui.GetWindowText(original_foreground) if original_foreground else "None"
    )
    print(f"Original foreground: {original_title} (HWND: {original_foreground})")

    # Get current style
    style_before = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style_before < 0:
        style_before = style_before & 0xFFFFFFFF
    print(f"Style before: 0x{style_before:08X}")

    # Make Vivaldi foreground
    print("Setting Vivaldi as foreground...")
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print(f"Warning: SetForegroundWindow failed: {e}")

    time.sleep(0.2)

    # Send F11 using SendInput
    print("Sending F11 via SendInput...")
    VK_F11 = 0x7A
    press_key(VK_F11)
    time.sleep(0.05)
    release_key(VK_F11)

    # Wait for fullscreen to apply
    time.sleep(0.3)

    # Check style
    style_after = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    if style_after < 0:
        style_after = style_after & 0xFFFFFFFF
    print(f"Style after: 0x{style_after:08X}")

    if style_before != style_after:
        print("✓ Style changed!")
    else:
        print("✗ Style unchanged")

    # Restore original foreground window
    if original_foreground and original_foreground != hwnd:
        print(f"Restoring original foreground: {original_title}")
        try:
            win32gui.SetForegroundWindow(original_foreground)
            print("✓ Focus restored")
        except Exception as e:
            print(f"✗ Could not restore focus: {e}")
    else:
        print("(No need to restore focus)")


if __name__ == "__main__":
    main()
