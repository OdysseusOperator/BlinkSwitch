import win32con

normal = 0x14CF0000
fullscreen = 0x94000000  # -6C000000 unsigned

print("NORMAL (whole screen): 0x{:08X}".format(normal))
print("FULLSCREEN: 0x{:08X}".format(fullscreen))
print()

print("WS_CAPTION (0x00C00000):")
print("  Normal:", bool(normal & win32con.WS_CAPTION))
print("  Fullscreen:", bool(fullscreen & win32con.WS_CAPTION))
print()

print("WS_THICKFRAME (0x00040000):")
print("  Normal:", bool(normal & win32con.WS_THICKFRAME))
print("  Fullscreen:", bool(fullscreen & win32con.WS_THICKFRAME))
print()

print("WS_SYSMENU (0x00080000):")
print("  Normal:", bool(normal & win32con.WS_SYSMENU))
print("  Fullscreen:", bool(fullscreen & win32con.WS_SYSMENU))
print()

print("WS_POPUP (0x80000000):")
print("  Normal:", bool(normal & win32con.WS_POPUP))
print("  Fullscreen:", bool(fullscreen & win32con.WS_POPUP))
