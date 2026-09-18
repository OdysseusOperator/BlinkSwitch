# BlinkSwitch COSMIC helper

This helper is the native Wayland boundary for COSMIC. It owns the Wayland
connection because window handles and compositor objects cannot be serialized
or controlled from the Python process.

The helper is a persistent process. It reads one JSON command per line from
stdin and writes one JSON reply per line to stdout. It uses COSMIC's
`cosmic-toplevel-info`, `cosmic-toplevel-management`, and workspace protocols;
it does not use X11, XWayland, or `wmctrl`.

`list` returns windows, outputs, workspaces, capabilities, and observed state.
Window IDs are stable integers for the lifetime of the helper. Commands are
`focus`, `fullscreen`, `unfullscreen`, `maximize`, `unmaximize`, and
`move_workspace`; action replies acknowledge the request, while a subsequent
`list` reports compositor-observed state.
