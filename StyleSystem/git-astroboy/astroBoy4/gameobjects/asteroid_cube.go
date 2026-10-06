// AstroBoy4 Game Objects - Cube Asteroid Shape
// Cubic asteroid shape

package gameobjects

import (
	rl "github.com/gen2brain/raylib-go/raylib"
)

// CubeAsteroid renders a cube
type CubeAsteroid struct{}

// NewCubeShape creates a new cube asteroid shape
func NewCubeShape() AsteroidShape {
	return &CubeAsteroid{}
}

// Render draws a cube at the origin
func (c *CubeAsteroid) Render(size float32) {
	// Draw filled cube faces
	asteroidColor := rl.Color{R: 150, G: 150, B: 150, A: 255}
	rl.DrawCube(rl.Vector3{X: 0, Y: 0, Z: 0}, size*2, size*2, size*2, asteroidColor)

	// Draw cube edges in black
	edgeColor := rl.Color{R: 0, G: 0, B: 0, A: 255}
	rl.DrawCubeWires(rl.Vector3{X: 0, Y: 0, Z: 0}, size*2, size*2, size*2, edgeColor)
}

// GetName returns the shape name
func (c *CubeAsteroid) GetName() string {
	return "Cube"
}

// GetBoundingRadius returns the bounding radius for collision detection
// For cube, use diagonal distance (conservative bound)
func (c *CubeAsteroid) GetBoundingRadius(size float32) float32 {
	// Diagonal from center to corner: size * sqrt(3)
	// size*2 is full cube width, so radius = size * sqrt(2) ≈ size * 1.732
	return size * 1.732
}

// GetVertices returns the 8 vertices of the cube in local space
func (c *CubeAsteroid) GetVertices(size float32) []Vector3 {
	return []Vector3{
		{X: size, Y: size, Z: size},    // 0: Front top right
		{X: -size, Y: size, Z: size},   // 1: Front top left
		{X: -size, Y: -size, Z: size},  // 2: Front bottom left
		{X: size, Y: -size, Z: size},   // 3: Front bottom right
		{X: size, Y: size, Z: -size},   // 4: Back top right
		{X: -size, Y: size, Z: -size},  // 5: Back top left
		{X: -size, Y: -size, Z: -size}, // 6: Back bottom left
		{X: size, Y: -size, Z: -size},  // 7: Back bottom right
	}
}

// GetFaces returns the 12 triangular faces of the cube (2 per square face)
func (c *CubeAsteroid) GetFaces() []Face {
	return []Face{
		// Front face (Z+)
		{V0: 0, V1: 1, V2: 2},
		{V0: 0, V1: 2, V2: 3},
		// Back face (Z-)
		{V0: 4, V1: 6, V2: 5},
		{V0: 4, V1: 7, V2: 6},
		// Top face (Y+)
		{V0: 0, V1: 4, V2: 5},
		{V0: 0, V1: 5, V2: 1},
		// Bottom face (Y-)
		{V0: 2, V1: 6, V2: 7},
		{V0: 2, V1: 7, V2: 3},
		// Right face (X+)
		{V0: 0, V1: 3, V2: 7},
		{V0: 0, V1: 7, V2: 4},
		// Left face (X-)
		{V0: 1, V1: 5, V2: 6},
		{V0: 1, V1: 6, V2: 2},
	}
}
