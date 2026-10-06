// AstroBoy4 Game Objects - Asteroid Base Types
// Base types and interface for asteroid shapes

package gameobjects

// Vector3 represents a 3D vector (used for collision vertices)
type Vector3 struct {
	X, Y, Z float32
}

// Face represents a triangular face with vertex indices
type Face struct {
	V0, V1, V2 int // Indices into the vertex array
}

// AsteroidShape defines the interface for different asteroid shapes
type AsteroidShape interface {
	// Render draws the asteroid shape at the origin with given size and rotations
	// Transformations (translation, rotation) should be applied before calling this
	Render(size float32)

	// GetName returns the name of the shape for debugging
	GetName() string

	// GetBoundingRadius returns the radius for fast circle collision (Tier 1)
	// This should be conservative - large enough to contain the entire shape
	GetBoundingRadius(size float32) float32

	// GetVertices returns 3D vertices for the shape in local space (before rotation)
	// Used for precise collision detection (Tier 2)
	GetVertices(size float32) []Vector3

	// GetFaces returns triangular faces as vertex indices
	// Used for backface culling to determine visible edges
	GetFaces() []Face
}

// Asteroid represents a game asteroid with physics and shape
type Asteroid struct {
	X, Y           float32       // Position
	VX, VY         float32       // Velocity
	RotationX      float32       // Rotation around X axis
	RotationY      float32       // Rotation around Y axis
	RotationZ      float32       // Rotation around Z axis
	RotationSpeedX float32       // Rotation speed around X axis
	RotationSpeedY float32       // Rotation speed around Y axis
	RotationSpeedZ float32       // Rotation speed around Z axis
	Size           float32       // Size of asteroid
	ShapeRenderer  AsteroidShape // Shape renderer
}
