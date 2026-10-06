# Monaspace Krypton Font Test with Clay UI

This experiment demonstrates how to properly use multiple fonts with the Clay UI library in Go.

## What This Does

Displays all four Monaspace Krypton font variants in a clean Clay UI layout:
- Regular
- Bold
- Italic
- Bold Italic

Each style is shown with sample text for easy comparison.

## Key Technical Insight: Dynamic Font Switching with Clay

### The Problem
Clay UI requires a text measurement function that's set once during initialization. When you need to render text with different fonts, you can't just change which font you pass to the measurement function on a per-text basis.

### The Solution
Use a **global font pointer** that both the measurement function and renderer reference:

```go
var currentFont *rl.Font  // Pointer, not value!

// Measurement function uses the pointer
func measureTextFunction(text clay.StringSlice, config *clay.TextElementConfig, userData unsafe.Pointer) clay.Dimensions {
    font := *currentFont  // Dereference to get the actual font
    textSize := rl.MeasureTextEx(font, textStr, float32(config.FontSize), 1.0)
    return clay.Dimensions{Width: textSize.X, Height: textSize.Y}
}

// Renderer also uses the pointer
func clayRaylibRender(renderCommands clay.RenderCommandArray) {
    // ...
    rl.DrawTextEx(*currentFont, textStr, position, fontSize, spacing, color)
}
```

### Usage Pattern

Before each `clay.Text()` call, set the `currentFont` pointer to the desired font:

```go
currentFont = &fontBold
clay.Text("Bold text here", clay.TextConfig(...))

currentFont = &fontItalic
clay.Text("Italic text here", clay.TextConfig(...))
```

### Why This Works

1. **Measurement Phase**: When Clay calls the measurement function during layout, it dereferences `currentFont` to measure with the correct font
2. **Rendering Phase**: When rendering, the same pointer is dereferenced to draw with the matching font
3. **Synchronization**: Because both phases use the same pointer, they always stay in sync

### Critical Details

- Use a **pointer** (`*rl.Font`), not a value - this allows you to change which font it points to
- Set `currentFont` **before** calling `clay.Text()` - Clay needs it during the layout phase
- Both measurement and rendering must use the **same** `currentFont` pointer

## Building and Running

```bash
go build -o font-test.exe main-clay.go
./font-test.exe
```

Or use the provided scripts:
```bash
./build-font-test.bat
./run-font-test.bat
```

## Files

- `main-clay.go` - Main font test program
- `MonaspaceKryptonNF-*.otf` - Font files (Regular, Bold, Italic, BoldItalic)
- `build-font-test.bat` - Build script
- `run-font-test.bat` - Run script
