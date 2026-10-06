# AstroBoy4 2-Tier Collision Detection Test

Interactive tool for testing and visualizing the 2-tier collision detection system.

**Uses actual gameobjects and collision system from astroBoy4!**

## Features

- **4 Asteroid Types**: Sphere, Cube, Pyramid, Octahedron (cycle with arrow keys)
- **2-Tier Collision Visualization**: 
  - Tier 1: Bounding circle (fast pre-filter)
  - Tier 2: Projected polygon (precise collision)
- **Full 3D Rotation Control**: Test all rotation combinations
- **Real-time Performance Metrics**: Microsecond timing for each tier
- **Interactive Testing**: Move mouse to test collision at any point
- **Visual Feedback**: See both collision tiers simultaneously

## Controls

### Asteroid Selection
- **← →**: Cycle through asteroid types (Sphere, Cube, Pyramid, Octahedron)

### Rotation Controls
- **↑ ↓**: Rotate around X axis
- **A D**: Rotate around Y axis
- **Q E**: Rotate around Z axis
- **Mouse Drag**: Click and drag to rotate freely
- **R**: Reset all rotations to zero

### Other Controls
- **+/-**: Adjust asteroid size
- **T**: Toggle Tier 2 visualization on/off

## Building

```bash
cd astroBoy4/experiments/collision-test
./build.bat
```

## Running

```bash
./collision-test.exe
```

## Understanding the Visualization

### Color Legend

- **Blue Circle**: Tier 1 bounding radius (conservative)
- **Yellow Circle**: Tier 1 hit detected
- **Green Polygon**: Tier 2 projected shape (no collision)
- **Red Polygon**: Tier 2 collision detected
- **Yellow Dots**: Individual projected vertices (before convex hull)
- **White Dot**: Mouse cursor position

### Collision Detection Flow

1. **Tier 1 (Fast)**: Check if mouse is within bounding circle
   - If MISS: Skip Tier 2 (optimization)
   - If HIT: Proceed to Tier 2

2. **Tier 2 (Precise)**: Check if mouse is inside projected polygon
   - Project 3D vertices with current rotation
   - Calculate convex hull
   - Point-in-polygon test

### Performance Metrics

Top-right corner shows:
- **Tier 1 time**: Microseconds for bounding circle check
- **Tier 2 time**: Microseconds for polygon projection + collision

Typical values:
- Tier 1: 0.1-0.5 µs (very fast)
- Tier 2: 1-5 µs (still very fast, only runs if Tier 1 passes)

## Testing Scenarios

### Test Case 1: Sphere
- **Expected**: Tier 2 not needed (bounding circle is exact)
- **Vertices**: 0 (displays "N/A")
- **Result**: Tier 1 and Tier 2 always match

### Test Case 2: Cube (No Rotation)
- **Expected**: Square projection
- **Vertices**: 4 (convex hull of 8 corners)
- **Test**: Corners should be precise

### Test Case 3: Cube (45° Z Rotation)
- **Expected**: Diamond projection
- **Vertices**: 4
- **Test**: Edges should match visual appearance

### Test Case 4: Cube (45° X or Y Rotation)
- **Expected**: Hexagon or octagon projection
- **Vertices**: 6-8
- **Test**: 3D tumbling should show accurate shape

### Test Case 5: Pyramid (Various Rotations)
- **Expected**: Triangle or quad projection
- **Vertices**: 3-4
- **Test**: Tip should be visible when pointing up

### Test Case 6: Octahedron (Tumbling)
- **Expected**: Diamond/hexagon projection
- **Vertices**: 4-6
- **Test**: Should change shape as it rotates

## Comparing to Main Game

The collision detection in this experiment is **identical** to the main game:

- Same `GetBoundingRadius()` implementations
- Same `GetVertices()` implementations
- Same `GetProjectedPolygon()` function
- Same `PointInPolygon()` algorithm

**What you see here is exactly what happens in the game!**

## Performance Notes

From `astroBoy4/PERFORMANCE_IMPROVEMENTS.md`:

Current implementation is **calculate on-demand** (no caching). This is sufficient for typical gameplay:
- 10 asteroids × 5 bullets = 50 checks/frame
- ~95% filtered by Tier 1
- ~2-3 Tier 2 checks per frame
- Total collision time: < 0.05ms per frame

**Future optimizations available if needed** (see PERFORMANCE_IMPROVEMENTS.md):
- Backface culling for projection
- Per-frame polygon caching
- Spatial partitioning

## Integration with Main Game

Located in:
- **Collision system**: `astroBoy4/systems/projection.go`
- **Shape definitions**: `astroBoy4/gameobjects/asteroid_*.go`
- **Bullet collision**: `astroBoy4/systems/asteroid_manager.go` (CheckBulletCollisions)
- **Ship collision**: `astroBoy4/systems/asteroid_manager.go` (CheckShipCollision)

## Technical Details

- **Resolution**: 1280x720
- **Frame Rate**: 60 FPS target
- **Camera**: Perspective projection, 45° FOV
- **Collision Method**: Ray casting (2D point projected to 3D)
- **Projection**: Orthographic (full 3D rotation applied before dropping Z)
- **Polygon Algorithm**: Convex hull (Graham scan)
- **Point-in-Polygon**: Ray casting algorithm
