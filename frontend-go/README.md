# BlinkSwitch Clay Frontend

Opt-in Go/Raylib/Clay frontend. The Python frontend remains the default.

Build from this directory:

```text
build.bat
```

Then start BlinkSwitch with:

```text
start.bat --frontend clay
```

The frontend keeps filtering and selection local for low latency. The backend supplies cached windows/tabs and runtime-only MRU ordering.

On COSMIC/Linux, bind the desktop shortcut to `start_clay.sh --toggle`. The Go frontend listens on `/tmp/blinkswitch-frontend.sock` while running.

For migration testing on Linux, run `./start_blinkswitch_new.sh` from the repository
root. It rebuilds this frontend and starts it with the backend. The testing launcher
sets `BLINKSWITCH_KEEP_OPEN=1`: the window is shown at startup and hiding is disabled,
including after selection, Escape, and hotkey/IPC toggles. Escape still navigates
back from management views. Stop both processes with `Ctrl+C` in the launch terminal.
Normal launchers retain their hidden-start behavior.
An already-running healthy backend is reused and remains running when testing stops.
Testing mode does not register hotkeys or the toggle IPC socket, so the normal
frontend can run alongside it and still open with `Alt+Space` for comparison.
