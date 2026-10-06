# Raylib Go Hello World Example

## Overview

This project demonstrates how to create a simple GUI application in Go using Raylib Go bindings. It recreates the same functionality as the C + Clay example but uses pure Raylib Go without any UI layout library.

## Dependencies

### Primary Dependency
- `github.com/gen2brain/raylib-go/raylib` - Official Raylib Go bindings

### Transitive Dependencies
- `github.com/ebitengine/purego` - Pure Go CGO-free bindings library
- `golang.org/x/exp` - Experimental Go packages
- `golang.org/x/sys` - System call packages

## Why Ebitengine/Purego?

The presence of `ebitengine/purego` might be confusing since this is supposed to be a Raylib project. Here's the explanation:

**What is Purego?**
- Purego is a library that allows Go programs to call C libraries without using CGO
- It enables "pure Go" bindings to native C libraries
- Developed by the Ebitengine (formerly Ebiten) team for game development

**Why does Raylib-Go use it?**
- `gen2brain/raylib-go` uses purego internally to interface with the native Raylib C library
- This allows the Go bindings to work without requiring CGO compilation
- Results in easier cross-compilation and deployment
- Still provides full access to Raylib's native performance and features

**Is this still "real" Raylib?**
- Yes! The underlying rendering, physics, and audio are all handled by the native Raylib C library
- Purego is just the bridge layer between Go and C
- All Raylib functionality is available and performs identically to direct C usage

## Project Structure

```
raylib-clay-go-example/
├── main.go              # Main application code
├── go.mod              # Go module definition
├── go.sum              # Dependency checksums
└── Documentation.md    # This file
```

## Features Implemented

- **Window Management**: 800x600 window with dark background
- **Text Rendering**: "Hello World!" title with proper centering
- **Interactive Button**: Clickable start button with hover detection
- **State Management**: Button changes color and text when clicked
- **Welcome Message**: Appears after button interaction
- **Mouse Input**: Left-click detection with collision testing

## Key Differences from C + Clay Version

| Aspect | C + Clay | Go + Raylib |
|--------|----------|-------------|
| Layout System | Clay UI library with automatic centering | Manual positioning and centering calculations |
| Text Measurement | Clay's text measurement API | Raylib's `MeasureText()` function |
| Button Detection | Clay's `PointerOver()` function | Manual collision detection with `CheckCollisionPointRec()` |
| Memory Management | Manual arena allocation | Go garbage collector |
| Error Handling | Clay error handlers | Go error handling patterns |

## Running the Application

### Prerequisites
- Go 1.19 or later
- Windows (tested), Linux, or macOS
- No additional system dependencies (thanks to purego!)

### Build and Run
```bash
go build
./raylib-clay-go-example.exe  # Windows
./raylib-clay-go-example      # Linux/macOS
```

### Expected Behavior
1. Window opens with dark gray background
2. "Hello World!" appears centered at the top in white text
3. Blue "Start" button is centered below the title
4. Clicking the button turns it green and changes text to "Started!"
5. "Welcome to Raylib Go!" message appears below the button

## Code Architecture

### Main Components
- **Window Initialization**: Sets up 800x600 window with 60 FPS target
- **Input Handling**: Mouse position tracking and click detection
- **Rendering Loop**: Clears background, draws UI elements, presents frame
- **State Management**: Boolean flag for button press state

### Rendering Pipeline
1. Clear background with dark gray color
2. Calculate and draw centered title text
3. Draw button rectangle with current state color
4. Calculate and draw centered button text
5. Conditionally draw welcome message
6. Present frame

## Alternative Raylib Go Bindings

If you prefer different approaches:

- **`github.com/lachee/raylib-goplus`** - Alternative binding with different API design
- **Direct CGO bindings** - Custom bindings using traditional CGO
- **`github.com/arl/raylib-go`** - Another community binding

However, `gen2brain/raylib-go` is the most mature and widely adopted solution.