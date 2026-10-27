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

On Linux, run `./start_go.sh` from the repository root to rebuild this frontend
and start it with the backend. It starts hidden; bind the COSMIC desktop shortcut
to `/absolute/path/to/BlinkSwitch/start_go.sh --toggle`. The Go frontend listens on
`/tmp/blinkswitch-frontend.sock` while running.

Use `./start_go.sh --keep-open` for migration testing: the window appears immediately,
hiding is disabled, and hotkeys/toggle IPC are not registered, allowing comparison
with the normal frontend. Escape still navigates back from management views.
Add `--render-check` for native Wayland scaling diagnostics or `--update` to refresh
Python dependencies. Stop with terminal `Ctrl+C`; a reused backend stays running.
