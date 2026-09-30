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
