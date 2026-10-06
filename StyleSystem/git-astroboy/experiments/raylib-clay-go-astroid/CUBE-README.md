# 3D Cube Experiment with Clay UI and Raylib

This experiment demonstrates the integration of Clay UI (for 2D UI elements) with Raylib's 3D rendering capabilities.

## Features

- **Clay UI**: Modern UI framework for creating responsive interfaces
- **3D Rendering**: Real-time 3D cube that spins smoothly
- **Interactive Button**: Toggle the cube on/off with a button
- **Clean Design**: Dark theme with smooth animations

## What It Does

1. When you start the application, you'll see a UI panel with a "Start Cube" button
2. Click the button to make a 3D cube appear and start spinning
3. The cube rotates slowly around its diagonal axis
4. Click the button again to stop/hide the cube

## Building

### Windows (PowerShell)
```powershell
.\build-cube.ps1
```

### WSL
```bash
chmod +x build-cube.sh
./build-cube.sh
```

## Running

After building, simply run:
```
cube-experiment.exe
```

## Code Structure

- **Clay UI Layer**: Top panel with button and text (2D overlay)
- **3D Rendering**: Spinning cube with wireframe outline and grid
- **Camera**: Positioned at (10, 10, 10) looking at the origin
- **Rotation**: Cube rotates at 0.5 degrees per frame around (1, 1, 0) axis

## Dependencies

- `github.com/TotallyGamerJet/clay` - Clay UI library for Go
- `github.com/gen2brain/raylib-go/raylib` - Raylib bindings for Go

These are already defined in `go.mod`.
