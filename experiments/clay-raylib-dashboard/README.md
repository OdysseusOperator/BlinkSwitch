# Clay + Raylib Dashboard

Small Windows-first experiment copied from the working `StyleSystem` Go setup.
It demonstrates the complete path:

1. Clay builds a retained layout tree.
2. Clay emits render commands.
3. Raylib renders rectangles and text from those commands.

## Run on Windows

From this directory, with Go 1.24.6 available:

```bat
build.bat
run.bat
```

`raylib.dll` is included beside the source and must remain beside the built executable.

## Linux

Linux needs a shared Raylib library rather than `raylib.dll`. Install Raylib through the system package manager, or build it as `libraylib.so`, then make it discoverable through the normal library path or `LD_LIBRARY_PATH`. The Go binding loads the platform-native Raylib library at runtime.

Build with Nix from this directory:

```bash
./build.sh
```
