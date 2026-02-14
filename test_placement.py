"""Test script to check window placement values."""

import win32gui
import win32con


def get_foreground_window_info():
    hwnd = win32gui.GetForegroundWindow()
    title = win32gui.GetWindowText(hwnd)
    placement = win32gui.GetWindowPlacement(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

    # Convert to unsigned if negative
    if style < 0:
        style = style & 0xFFFFFFFF

    print(f"\nWindow: {title}")
    print(f"HWND: {hwnd}")
    print(f"Placement tuple: {placement}")
    print(f"  flags: {placement[0]}")
    print(f"  showCmd: {placement[1]} ", end="")

    if placement[1] == win32con.SW_SHOWNORMAL:
        print("(SW_SHOWNORMAL)")
    elif placement[1] == win32con.SW_SHOWMAXIMIZED:
        print("(SW_SHOWMAXIMIZED)")
    elif placement[1] == win32con.SW_SHOWMINIMIZED:
        print("(SW_SHOWMINIMIZED)")
    else:
        print(f"(Unknown: {placement[1]})")

    print(f"  ptMinPosition: {placement[2]}")
    print(f"  ptMaxPosition: {placement[3]}")
    print(f"  rcNormalPosition: {placement[4]}")
    print(f"Rect: {rect}")
    print(f"Style: 0x{style:08X}")
    print(f"Style bits:")
    print(f"  WS_CAPTION: {bool(style & win32con.WS_CAPTION)}")
    print(f"  WS_THICKFRAME: {bool(style & win32con.WS_THICKFRAME)}")
    print(f"  WS_SYSMENU: {bool(style & win32con.WS_SYSMENU)}")
    print(f"  WS_POPUP: {bool(style & win32con.WS_POPUP)}")


if __name__ == "__main__":
    print("Testing window placement...")
    print("\nInstructions:")
    print("1. Run this script")
    print("2. Quickly switch to a MAXIMIZED window")
    print("3. Check the output")
    print("4. Then switch to a FULLSCREEN window")
    print("5. Run again to see the difference")

    import time

    print("\nWaiting 3 seconds for you to switch to a window...")
    time.sleep(3)

    get_foreground_window_info()
