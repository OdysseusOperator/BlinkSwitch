import win32con

maximized = 0x15CF0000
fullscreen = int("0x95000000", 16)  # Convert from signed -6B000000

print("MAXIMIZED: 0x{:08X}".format(maximized))
print("FULLSCREEN: 0x{:08X}".format(fullscreen))
print()

# Check important bits
print("WS_CAPTION (0x00C00000):")
print("  Maximized:", bool(maximized & win32con.WS_CAPTION))
print("  Fullscreen:", bool(fullscreen & win32con.WS_CAPTION))
print()

print("WS_THICKFRAME (0x00040000):")
print("  Maximized:", bool(maximized & win32con.WS_THICKFRAME))
print("  Fullscreen:", bool(fullscreen & win32con.WS_THICKFRAME))
print()

print("WS_SYSMENU (0x00080000):")
print("  Maximized:", bool(maximized & win32con.WS_SYSMENU))
print("  Fullscreen:", bool(fullscreen & win32con.WS_SYSMENU))
print()

print("WS_BORDER (0x00800000):")
print("  Maximized:", bool(maximized & win32con.WS_BORDER))
print("  Fullscreen:", bool(fullscreen & win32con.WS_BORDER))
print()

# XOR to see what changed
diff = maximized ^ fullscreen
print("Bits that changed: 0x{:08X}".format(diff))
print()

# Specific bits in the difference
print("Bits present in maximized but not fullscreen:")
only_maximized = maximized & ~fullscreen
print("  0x{:08X}".format(only_maximized))

print("Bits present in fullscreen but not maximized:")
only_fullscreen = fullscreen & ~maximized
print("  0x{:08X}".format(only_fullscreen))
