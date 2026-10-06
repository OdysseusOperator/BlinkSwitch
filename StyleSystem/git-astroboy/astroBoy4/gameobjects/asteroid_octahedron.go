// AstroBoy4 Game Objects - Octahedron Asteroid Shape
// Octahedron (8-sided) asteroid shape

package gameobjects

import (
	rl "github.com/gen2brain/raylib-go/raylib"
)

// OctahedronAsteroid renders an octahedron (two pyramids joined at base)
type OctahedronAsteroid struct{}

// NewOctahedronShape creates a new octahedron asteroid shape
func NewOctahedronShape() AsteroidShape {
	return &OctahedronAsteroid{}
}

// Render draws an octahedron at the origin
func (o *OctahedronAsteroid) Render(size float32) {
	// Define vertices for octahedron (6 vertices)
	top := rl.Vector3{X: 0, Y: size, Z: 0}
	bottom := rl.Vector3{X: 0, Y: -size, Z: 0}
	front := rl.Vector3{X: 0, Y: 0, Z: size}
	back := rl.Vector3{X: 0, Y: 0, Z: -size}
	right := rl.Vector3{X: size, Y: 0, Z: 0}
	left := rl.Vector3{X: -size, Y: 0, Z: 0}

	// Draw 8 triangular faces
	asteroidColor := rl.Color{R: 150, G: 150, B: 150, A: 255}

	// Top 4 faces
	rl.DrawTriangle3D(top, front, right, asteroidColor)
	rl.DrawTriangle3D(top, right, back, asteroidColor)
	rl.DrawTriangle3D(top, back, left, asteroidColor)
	rl.DrawTriangle3D(top, left, front, asteroidColor)

	// Bottom 4 faces
	rl.DrawTriangle3D(bottom, right, front, asteroidColor)
	rl.DrawTriangle3D(bottom, back, right, asteroidColor)
	rl.DrawTriangle3D(bottom, left, back, asteroidColor)
	rl.DrawTriangle3D(bottom, front, left, asteroidColor)

	// Draw edges in black
	edgeColor := rl.Color{R: 0, G: 0, B: 0, A: 255}

	// Edges from top
	rl.DrawLine3D(top, front, edgeColor)
	rl.DrawLine3D(top, right, edgeColor)
	rl.DrawLine3D(top, back, edgeColor)
	rl.DrawLine3D(top, left, edgeColor)

	// Middle square edges
	rl.DrawLine3D(front, right, edgeColor)
	rl.DrawLine3D(right, back, edgeColor)
	rl.DrawLine3D(back, left, edgeColor)
	rl.DrawLine3D(left, front, edgeColor)

	// Edges from bottom
	rl.DrawLine3D(bottom, front, edgeColor)
	rl.DrawLine3D(bottom, right, edgeColor)
	rl.DrawLine3D(bottom, back, edgeColor)
	rl.DrawLine3D(bottom, left, edgeColor)
}

// GetName returns the shape name
func (o *OctahedronAsteroid) GetName() string {
	return "Octahedron"
}

// GetBoundingRadius returns the bounding radius for collision detection
func (o *OctahedronAsteroid) GetBoundingRadius(size float32) float32 {
	// Octahedron vertices are at distance 'size' from center
	return size
}

// GetVertices returns the 6 vertices of the octahedron in local space
func (o *OctahedronAsteroid) GetVertices(size float32) []Vector3 {
	return []Vector3{
		{X: 0, Y: size, Z: 0},  // 0: Top
		{X: 0, Y: -size, Z: 0}, // 1: Bottom
		{X: 0, Y: 0, Z: size},  // 2: Front
		{X: 0, Y: 0, Z: -size}, // 3: Back
		{X: size, Y: 0, Z: 0},  // 4: Right
		{X: -size, Y: 0, Z: 0}, // 5: Left
	}
}

// GetFaces returns the 8 triangular faces of the octahedron
func (o *OctahedronAsteroid) GetFaces() []Face {
	return []Face{
		// Top 4 faces
		{V0: 0, V1: 2, V2: 4}, // Top-front-right
		{V0: 0, V1: 4, V2: 3}, // Top-right-back
		{V0: 0, V1: 3, V2: 5}, // Top-back-left
		{V0: 0, V1: 5, V2: 2}, // Top-left-front
		// Bottom 4 faces
		{V0: 1, V1: 4, V2: 2}, // Bottom-right-front
		{V0: 1, V1: 3, V2: 4}, // Bottom-back-right
		{V0: 1, V1: 5, V2: 3}, // Bottom-left-back
		{V0: 1, V1: 2, V2: 5}, // Bottom-front-left
	}
}
