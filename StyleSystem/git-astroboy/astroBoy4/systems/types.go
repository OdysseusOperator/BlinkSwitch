// AstroBoy4 Systems - Shared Types
// Common types used across systems
// Ported and expanded from astroBoy3/src/core/types.go

package systems

import rl "github.com/gen2brain/raylib-go/raylib"

// Vector2 represents a 2D vector for collision calculations and physics
type Vector2 struct {
	X, Y float32
}

// Resolution represents a screen resolution option
type Resolution struct {
	Width, Height int
	Label         string
}

// BoundingBox represents an axis-aligned bounding box for fast collision pre-filtering
type BoundingBox struct {
	X, Y          float32 // Center position
	Width, Height float32 // Full width and height
}

// Bullet represents a projectile
type Bullet struct {
	X, Y     float32
	VX, VY   float32
	Lifetime float32 // Remaining lifetime in seconds (renamed from Life for consistency)
}

// DebugCollision stores information for visualizing collision tests
type DebugCollision struct {
	Type     string       // "box", "circle", "triangle", "polygon"
	Position rl.Vector2   // Position for rendering
	Size     float32      // Size/radius for rendering
	Vertices []rl.Vector2 // For polygon shapes
	Color    rl.Color     // Debug color
	Active   bool         // Whether this debug info is currently active
}
