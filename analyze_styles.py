#!/usr/bin/env python3
"""Analyze window style bit changes."""

# Analyze the style bits from the log
before = 0x170B0000
after = 0x17CF0000

WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_POPUP = 0x80000000

print("BEFORE: 0x{:08X}".format(before))
print("  WS_MINIMIZEBOX:", bool(before & WS_MINIMIZEBOX))
print("  WS_MAXIMIZEBOX:", bool(before & WS_MAXIMIZEBOX))
print("  WS_CAPTION:", bool(before & WS_CAPTION))
print("  WS_THICKFRAME:", bool(before & WS_THICKFRAME))
print("  WS_SYSMENU:", bool(before & WS_SYSMENU))
print("  WS_POPUP:", bool(before & WS_POPUP))

print()
print("AFTER: 0x{:08X}".format(after))
print("  WS_MINIMIZEBOX:", bool(after & WS_MINIMIZEBOX))
print("  WS_MAXIMIZEBOX:", bool(after & WS_MAXIMIZEBOX))
print("  WS_CAPTION:", bool(after & WS_CAPTION))
print("  WS_THICKFRAME:", bool(after & WS_THICKFRAME))
print("  WS_SYSMENU:", bool(after & WS_SYSMENU))
print("  WS_POPUP:", bool(after & WS_POPUP))

print()
print("CHANGES:")
print(
    "  MINIMIZEBOX changed:",
    bool(before & WS_MINIMIZEBOX) != bool(after & WS_MINIMIZEBOX),
)
print(
    "  MAXIMIZEBOX changed:",
    bool(before & WS_MAXIMIZEBOX) != bool(after & WS_MAXIMIZEBOX),
)
print("  CAPTION changed:", bool(before & WS_CAPTION) != bool(after & WS_CAPTION))
print(
    "  THICKFRAME changed:", bool(before & WS_THICKFRAME) != bool(after & WS_THICKFRAME)
)

print()
print("INTERPRETATION (OLD - WRONG):")
if not (bool(after & WS_MINIMIZEBOX) or bool(after & WS_MAXIMIZEBOX)):
    print("  Window IS in fullscreen (no min/max boxes)")
else:
    print("  Window is NOT in fullscreen (still has min/max boxes)")

print()
print("INTERPRETATION (CORRECTED LOGIC):")
print("  Check CAPTION and THICKFRAME instead of min/max boxes")
if not (bool(after & WS_CAPTION) or bool(after & WS_THICKFRAME)):
    print("  Window IS in fullscreen (no caption/thickframe)")
else:
    print("  Window is NOT in fullscreen (has caption or thickframe)")

print()
print("CORRECT DETECTION:")
before_fullscreen = not (bool(before & WS_CAPTION) or bool(before & WS_THICKFRAME))
after_fullscreen = not (bool(after & WS_CAPTION) or bool(after & WS_THICKFRAME))
print(f"  BEFORE was fullscreen: {before_fullscreen}")
print(f"  AFTER is fullscreen: {after_fullscreen}")
if before_fullscreen and not after_fullscreen:
    print("  => F11 EXITED fullscreen (window was already fullscreen!)")
elif not before_fullscreen and after_fullscreen:
    print("  => F11 ENTERED fullscreen (success!)")
elif before_fullscreen and after_fullscreen:
    print("  => Still in fullscreen (no change)")
else:
    print("  => Still normal (no change)")
