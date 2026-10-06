# Dependencies

## `libei`

BlinkSwitch's planned Wayland pointer-centering integration uses Linux
Emulated Input (`libei`). It will request a pointer-capable RemoteDesktop
portal session, then send one absolute pointer event to the center of the
monitor containing the selected window. This is required because Wayland
clients cannot directly warp the pointer over another application's surface.

`libei` is a native Linux dependency. It is not installed from Python's
`requirements.txt`. The Nix development shell provides the `libei` package;
non-Nix installations need the distribution packages for `libei` and its
`liboeffis` portal helper, plus an XDG Desktop Portal backend that supports
RemoteDesktop input.

The first use may show a desktop permission dialog. BlinkSwitch requests
pointer input only; it does not request keyboard or screen-capture access.
Until that native integration is enabled, centering remains skipped on
Wayland with a warning. Centering must also be skipped when the portal,
compositor, or native library is unavailable.

## Desktop support

- COSMIC and GNOME Wayland sessions can provide this through their portal and
  compositor support, subject to version and user permission.
- KDE support depends on the installed portal and compositor versions.
- XFCE and Cinnamon commonly run under X11, where `libei` is unnecessary;
  their Wayland sessions require matching RemoteDesktop and `libei` support.
- Windows continues using Win32 `SetCursorPos`; X11-only sessions can use an
  X11-specific implementation without `libei`.
