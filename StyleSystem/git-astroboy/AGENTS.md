# Agent Guidelines for testOpencode Repository

This document provides coding agents with essential information about building, testing, and maintaining code in this repository.

## Repository Overview

This is a game development repository written in Go, using Raylib for graphics and Clay for UI.

**astroBoy3** is a prototype asteroid shooter game that demonstrates various game systems. While it was built as a prototype, its codebase contains well-structured reference implementations for:
- Ship physics and movement
- Collision detection systems
- Game state management
- Shop and upgrade systems
- Clay UI integration patterns
- Audio management

Parts of astroBoy3 can be used as reference when building new systems or games. However, it should be treated as a learning resource rather than production code.

There are also experimental projects in the `experiments/` folder.

## Important Constraints

- **Build Environment**: Running under Windows (not WSL). Never call `go build` directly.
- **Build Scripts**: Always use the build scripts (`.bat` files) to compile.
- **Protected Folders**: NEVER modify the `game-prototype` folder.

## Project Structure

```
testOpencode/
├── astroBoy3/              # Main game project
│   ├── main_game_final.go  # Entry point
│   ├── build.bat           # Build script
│   ├── go.mod              # Go module definition
│   ├── src/
│   │   ├── core/           # Core types and constants
│   │   ├── systems/        # Game systems (physics, collisions, etc.)
│   │   └── ui/             # UI components
│   └── lib/                # External libraries (DLLs)
├── experiments/            # Experimental prototypes
└── GameIdeas/             # Game design documents
```

## Build Commands

### Building astroBoy3
```bash
cd astroBoy3
./build.bat
```

The build script:
- Compiles to `astroboy_main.exe`
- Copies required DLLs (raylib.dll)
- Shows build status

### Running the Game
```bash
cd astroBoy3
./astroboy_main.exe
```

### Running Individual Test Files
For test programs like `test_shop_upgrade_system.go`:
```bash
cd astroBoy3/src/systems
go build -o test_name.exe test_shop_upgrade_system.go shop_upgrade_system_clay.go ui_buttons_clay.go game_state_system.go menu_system_clay.go ship_physics_clay.go asteroid_system_clay.go collision_system_clay.go
```

Note: Include all dependent files in the build command as shown in file headers.

## Code Style Guidelines

### Package Structure
- **Package naming**: Use short, lowercase names (`core`, `systems`, `ui`)
- **Internal packages**: Use `src/` for internal packages
- **Module path**: `raylib-clay-go-example` (from go.mod)

### Imports
```go
import (
    "fmt"
    "math"
    
    "raylib-clay-go-example/src/core"
    "raylib-clay-go-example/src/systems"
    
    "github.com/TotallyGamerJet/clay"
    rl "github.com/gen2brain/raylib-go/raylib"
)
```

**Import order**:
1. Standard library imports
2. Blank line
3. Internal package imports
4. Blank line  
5. External package imports

**Import aliases**:
- Use `rl` for raylib: `rl "github.com/gen2brain/raylib-go/raylib"`
- No alias for clay (unless conflicts occur)

### Naming Conventions

**Exported names** (public API):
```go
type GameStateManager struct { ... }
func NewGame() *Game { ... }
const TargetFPS = 60
```

**Unexported names** (private):
```go
type upgradeInfo struct { ... }
func handleInput(deltaTime float32) { ... }
var screenWidth = 1000
```

**Conventions**:
- Types: PascalCase (`ShipPhysics`, `AsteroidManager`)
- Functions: camelCase (`handleInput`, `updateBullets`) or PascalCase if exported
- Constants: PascalCase (`TargetFPS`, `BulletSpeed`)
- Variables: camelCase (`deltaTime`, `weaponCooldown`)
- Acronyms: Keep uppercase when appropriate (`FPS`, `UI`, `ID`)

### Type Definitions

**Struct definitions**:
```go
// GameStateManager handles game state transitions
type GameStateManager struct {
    currentState    GameState
    previousState   GameState
    buttonManager   *ui.ButtonManager
}
```

**Constructor pattern**:
```go
// NewGameStateManager creates a new game state manager
func NewGameStateManager(buttonManager *ui.ButtonManager) *GameStateManager {
    return &GameStateManager{
        currentState:  StateMenu,
        buttonManager: buttonManager,
    }
}
```

### Comments

**File headers**:
```go
// AstroBoy Game Core - Core game structures and initialization
// Extracted from main_game_final.go for better code organization

package systems
```

**Function comments** (for exported functions):
```go
// NewCollisionSystem creates a new collision detection system
func NewCollisionSystem() *CollisionSystem {
    // ...
}
```

**Inline comments** (when logic is complex):
```go
// Only draw if on screen
if screenX >= -100 && screenX <= float32(screenWidth)+100 {
    // ...
}
```

### Error Handling

**Standard pattern**:
```go
audioManager, err := NewRaylibSoundManager()
if err != nil {
    fmt.Printf("Warning: Failed to initialize audio system: %v\n", err)
    // Continue without audio or return error
}
```

**Deferred cleanup**:
```go
rl.InitWindow(width, height, title)
defer rl.CloseWindow()

rl.InitAudioDevice()
defer rl.CloseAudioDevice()
```

### Constants and Configuration

Define constants in `src/core/constants.go`:
```go
const (
    TargetFPS = 60
    BulletLifeTime = 3.0
    ShipMaxSpeed = 250.0
)
```

Define colors as variables:
```go
var (
    SpaceBackgroundColor = rl.Color{R: 5, G: 5, B: 15, A: 255}
    ShipColor = rl.Color{R: 255, G: 255, B: 0, A: 255}
)
```

### Clay UI Integration

**Initialize Clay**:
```go
systems.InitializeClay()
defer systems.CleanupClay()
```

**UI rendering pattern**:
```go
clay.BeginLayout()  // No parameters
// Build UI elements
clay.EndLayout()    // No parameters

// Render Clay UI
systems.ClayRaylibRender()
```

### Raylib Patterns

**Game loop structure**:
```go
for !rl.WindowShouldClose() {
    deltaTime := rl.GetFrameTime()
    
    handleInput(deltaTime)
    update(deltaTime)
    
    rl.BeginDrawing()
    rl.ClearBackground(SpaceBackgroundColor)
    render()
    rl.EndDrawing()
}
```

**Resource management**:
```go
texture := rl.LoadTexture("path/to/texture.png")
defer rl.UnloadTexture(texture)
```

## Testing

Currently, no automated test framework is set up. Testing is done through:
1. Building and running individual test programs
2. Manual gameplay testing
3. Debug mode (F1 in-game for debug info)

## Common Patterns

### Game State Management
```go
currentState := gameState.GetCurrentState()
switch currentState {
case StatePlaying:
    // Handle gameplay
case StateMenu:
    // Handle menu
case StateShop:
    // Handle shop
}
```

### Physics Updates
```go
func Update(deltaTime float32) {
    // Update position
    x += vx * deltaTime
    y += vy * deltaTime
    
    // Apply drag
    vx *= drag
    vy *= drag
}
```

### Collision Detection
```go
// Circle collision
dx := x1 - x2
dy := y1 - y2
distance := float32(math.Sqrt(float64(dx*dx + dy*dy)))
if distance < r1 + r2 {
    // Collision detected
}
```

## Debug Features

- **F1**: Toggle debug mode
- **F2**: Toggle FPS display
- **C**: Add credits (cheat)

## Additional Notes

- Use `float32` for game coordinates and physics (Raylib uses float32)
- Use `int32` for Raylib drawing functions (they require int32)
- Always check if resources loaded successfully before using them
- Performance: Target 60 FPS, optimize rendering in game loop
