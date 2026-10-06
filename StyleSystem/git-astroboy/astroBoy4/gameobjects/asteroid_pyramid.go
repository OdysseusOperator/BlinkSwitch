// AstroBoy4 Game Objects - Pyramid Asteroid Shape
// Triangular pyramid (tetrahedron) asteroid shape

package gameobjects

import (
	rl "github.com/gen2brain/raylib-go/raylib"
)

// PyramidAsteroid renders a triangular pyramid (tetrahedron)
type PyramidAsteroid struct{}

// NewPyramidShape creates a new pyramid asteroid shape
func NewPyramidShape() AsteroidShape {
	return &PyramidAsteroid{}
}

// Render draws a tetrahedron at the origin
func (p *PyramidAsteroid) Render(size float32) {
	// Define vertices for tetrahedron
	v1 := rl.Vector3{X: 0, Y: size, Z: 0}
	v2 := rl.Vector3{X: -size, Y: -size, Z: size}
	v3 := rl.Vector3{X: size, Y: -size, Z: size}
	v4 := rl.Vector3{X: 0, Y: -size, Z: -size}

	// Draw faces
	asteroidColor := rl.Color{R: 150, G: 150, B: 150, A: 255}
	rl.DrawTriangle3D(v1, v2, v3, asteroidColor)
	rl.DrawTriangle3D(v1, v3, v4, asteroidColor)
	rl.DrawTriangle3D(v1, v4, v2, asteroidColor)
	rl.DrawTriangle3D(v2, v4, v3, asteroidColor)

	// Draw edges
	edgeColor := rl.Color{R: 0, G: 0, B: 0, A: 255}
	rl.DrawLine3D(v1, v2, edgeColor)
	rl.DrawLine3D(v1, v3, edgeColor)
	rl.DrawLine3D(v1, v4, edgeColor)
	rl.DrawLine3D(v2, v3, edgeColor)
	rl.DrawLine3D(v3, v4, edgeColor)
	rl.DrawLine3D(v4, v2, edgeColor)
}

// GetName returns the shape name
func (p *PyramidAsteroid) GetName() string {
	return "Pyramid"
}

// GetBoundingRadius returns the bounding radius for collision detection
// Conservative radius that contains all vertices
func (p *PyramidAsteroid) GetBoundingRadius(size float32) float32 {
	// Distance from center to farthest base corner: sqrt(size^2 + size^2 + size^2) = sqrt(3) * size
	return size * 1.732 // sqrt(3) ≈ 1.732
}

// GetVertices returns the 4 vertices of the tetrahedron in local space
func (p *PyramidAsteroid) GetVertices(size float32) []Vector3 {
	return []Vector3{
		{X: 0, Y: size, Z: 0},         // 0: Apex
		{X: -size, Y: -size, Z: size}, // 1: Base corner 1
		{X: size, Y: -size, Z: size},  // 2: Base corner 2
		{X: 0, Y: -size, Z: -size},    // 3: Base corner 3
	}
}

// GetFaces returns the 4 triangular faces of the tetrahedron
func (p *PyramidAsteroid) GetFaces() []Face {
	return []Face{
		{V0: 0, V1: 1, V2: 2}, // Front face
		{V0: 0, V1: 2, V2: 3}, // Right face
		{V0: 0, V1: 3, V2: 1}, // Left face
		{V0: 1, V1: 3, V2: 2}, // Bottom face
	}
}
