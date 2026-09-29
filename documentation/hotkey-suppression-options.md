# Hotkey Suppression Options

## Problem

The app uses `pynput.GlobalHotKeys` to listen for **Alt+Space**. By default, `GlobalHotKeys` does not suppress the key event — it fires a callback when it detects the combo, but the keypress is also passed through to whatever app is in the foreground. This causes the Alt key state (and the Space key) to leak into other applications, which can trigger unintended behavior such as activating system menus or interacting with the Windows Alt+Tab switcher.

---

## Option 1: pynput `suppress=True` (Implemented)

Switch from `pynput.GlobalHotKeys` to a lower-level `pynput.keyboard.Listener` with `suppress=True`, and manually detect the Alt+Space combo by tracking which keys are currently held down.

**How it works:**
- `pynput.keyboard.Listener(suppress=True)` installs a low-level keyboard hook that consumes every key event before it reaches any other application.
- On each key press/release, check whether both `<alt>` and `<space>` are currently held. If so, fire the toggle callback.

**Pros:**
- No new dependencies — stays within the existing `pynput` stack.
- Key events are fully consumed; nothing leaks to other apps.

**Cons:**
- All keyboard events are intercepted by our listener thread, so the combo must be detected manually.
- If the listener thread crashes, keyboard input could be lost until the process is restarted.

---

## Option 2: `keyboard` Library

Add the [`keyboard`](https://pypi.org/project/keyboard/) pip package, which has a built-in hotkey suppression flag:

```python
import keyboard
keyboard.add_hotkey('alt+space', callback, suppress=True)
```

**Pros:**
- Clean, ergonomic API — suppression is a single parameter.
- Handles combo detection internally.

**Cons:**
- Adds a new dependency.
- Requires running as administrator on some Windows configurations.
- Less control over low-level behavior compared to pynput or Win32 directly.

---

## Option 3: Win32 `RegisterHotKey`

Use Windows' native `RegisterHotKey` function via `ctypes`. Windows delivers the registered hotkey as a `WM_HOTKEY` message to the owning window's message queue and does **not** pass it to any other application — suppression is inherent.

```python
import ctypes
user32 = ctypes.windll.user32
# MOD_ALT = 0x0001, VK_SPACE = 0x20
user32.RegisterHotKey(hwnd, id, 0x0001, 0x20)
# Poll WM_HOTKEY messages with PeekMessage in a loop
```

**Pros:**
- Most Windows-native and reliable approach.
- No third-party dependency beyond `ctypes` (stdlib).
- Suppression guaranteed by the OS.

**Cons:**
- Requires a Win32 message pump (`PeekMessage` / `GetMessage` loop).
- `RegisterHotKey` works most reliably when tied to a real window handle.
- More boilerplate code compared to the other options.
