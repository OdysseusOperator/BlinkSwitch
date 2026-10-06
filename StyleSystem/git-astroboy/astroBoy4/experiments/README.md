# AstroBoy4 Experiments

This folder contains experimental tools and tests for developing and testing AstroBoy4 features.

## Structure

```
experiments/
├── collision-test/     # Collision detection visualization and testing
└── (future experiments)
```

## Available Experiments

### collision-test
Interactive tool for testing and visualizing asteroid collision detection with mouse cursor.

**Purpose**: Develop and test collision detection algorithms for different asteroid shapes before integrating into the main game.

**Features**:
- Select between 4 asteroid types (Sphere, Cube, Pyramid, Octahedron)
- Full 3D rotation control
- Real-time collision detection visualization
- Uses actual gameobjects from astroBoy4

**Build & Run**:
```bash
cd experiments/collision-test
./build.bat
./collision-test.exe
```

See `collision-test/README.md` for detailed documentation.

---

## Creating New Experiments

When creating new experiments:

1. Create a new folder under `experiments/`
2. Include a `build.bat` for easy building
3. Add a `README.md` explaining the experiment's purpose
4. Import and use actual astroBoy4 packages where relevant:
   - `astroboy4/gameobjects` - Asteroid shapes
   - `astroboy4/systems` - Game systems
5. Document your findings and how to integrate into main game

## Why Experiments?

Experiments allow you to:
- Test new features in isolation
- Rapidly iterate on algorithms
- Visualize and debug complex systems
- Develop without breaking the main game
- Create reusable testing tools

Any successful code from experiments can be ported to the main game in `astroBoy4/systems/`.
