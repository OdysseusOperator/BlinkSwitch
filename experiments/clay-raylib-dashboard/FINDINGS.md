# Clay + Raylib Findings

## Reference Project

The working reference came from `StyleSystem/git-astroboy/experiments/raylib-clay-go-text`.
Its relevant stack is:

- Go 1.24+
- `github.com/TotallyGamerJet/clay` v0.0.7
- `github.com/gen2brain/raylib-go/raylib` v0.55.1
- Raylib render commands drawn manually through Raylib Go

The cube and font-test assets were not required for the basic Clay integration.

## Integration Pattern

Clay does layout; Raylib draws the resulting render commands.

1. Create Clay memory with `clay.MinMemorySize()`.
2. Initialize Clay with the window dimensions and an error handler.
3. Register a text measurement callback using `clay.SetMeasureTextFunction`.
4. Call `clay.BeginLayout()` each frame.
5. Build the UI with `clay.UI` and `clay.Text`.
6. Call `clay.EndLayout()` to receive render commands.
7. Draw rectangle and text commands between Raylib drawing calls.

Text measurement and rendering must use the same Raylib font. Clay asks the callback for text dimensions while building the layout, so the measurement callback must call `rl.MeasureTextEx` with the active font.

## Important Clay Callback Detail

Passing `nil` as the callback user data caused this panic:

```text
panic: interface conversion: interface {} is nil, not unsafe.Pointer
```

Clay v0.0.7 casts the user data to `unsafe.Pointer`. The working setup passes a non-nil pointer:

```go
clay.SetMeasureTextFunction(measureText, unsafe.Pointer(&currentFont))
```

The callback currently reads the global `currentFont`; the pointer keeps Clay's expected callback data non-nil.

## Text Wrapping

Clay wraps long text when its parent has a constrained width. The dashboard includes a deliberately long description inside a `SizingGrow(0)` container with padding. This demonstrates automatic line breaking without manually splitting the string.

The Clay layout dimensions are initialized to `960x620`. The prototype does not currently update Clay dimensions when the native window is resized.

## BlinkSwitch Font

The prototype loads:

```text
../../frontend/fonts/MonaspaceNeonFrozen-Medium.ttf
```

The path is relative to the process working directory, which should be `experiments/clay-raylib-dashboard`. If loading fails, the app falls back to `rl.GetFontDefault()`.

## Native Runtime Libraries

Windows needs `raylib.dll` beside the executable. The DLL copied into this experiment matches the working StyleSystem reference DLL.

Linux needs a native shared Raylib library, normally `libraylib.so` or a versioned equivalent. It must be installed through the system package manager or made visible through `LD_LIBRARY_PATH`. This checkout did not contain a Linux Raylib shared library.

## Nix Build

Run from any directory:

```bash
./experiments/clay-raylib-dashboard/build.sh
```

`build.sh` uses `nix shell` with Go, Wayland, X11, OpenGL, and X11 protocol development packages. Raylib Go's embedded GLFW C code does not automatically receive all required Nix include and library paths, so the script derives Nix store paths and supplies `C_INCLUDE_PATH` and `CGO_LDFLAGS` explicitly.

The build was verified successfully in this environment. The generated executable is intentionally not checked into the experiment directory.

## Window Border Flicker

The prototype does not draw a native window border. Raylib creates a normally decorated window, and the BlinkSwitch COSMIC frontend runs through XWayland because it needs positionable windows.

Border-only flicker is therefore most likely native decoration handling in COSMIC/XWayland rather than Clay rendering. The prototype now sets this before `rl.InitWindow`:

```go
rl.SetConfigFlags(rl.FlagWindowUndecorated)
```

This removes compositor-provided decoration. If the flicker remains in the client content area, it is a separate Raylib/XWayland rendering issue.

## Prototype Files

- `main.go`, Clay dashboard and Raylib renderer
- `go.mod`, pinned direct dependencies
- `go.sum`, dependency checksums
- `build.sh`, Nix Linux build
- `build.bat`, Windows build
- `run.bat`, Windows run command
- `raylib.dll`, Windows runtime library
- `README.md`, short usage guide
