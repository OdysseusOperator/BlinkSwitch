// AstroBoy4 Systems - Math Utilities
// Common mathematical operations used throughout the game
// Eliminates code duplication and provides performance optimizations

package systems

import (
	"math"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Distance calculates the Euclidean distance between two points
// Used for collision detection, proximity checks, etc.
func Distance(x1, y1, x2, y2 float32) float32 {
	dx := x1 - x2
	dy := y1 - y2
	return float32(math.Sqrt(float64(dx*dx + dy*dy)))
}

// DistanceSquared calculates the squared distance between two points
// Faster than Distance() as it avoids the sqrt() call
// Use for collision detection when you only need to compare distances
func DistanceSquared(x1, y1, x2, y2 float32) float32 {
	dx := x1 - x2
	dy := y1 - y2
	return dx*dx + dy*dy
}

// CheckCircleCollision checks if two circles collide
// Returns true if circles overlap
// Optimized: uses squared distance to avoid sqrt()
func CheckCircleCollision(x1, y1, r1, x2, y2, r2 float32) bool {
	totalRadius := r1 + r2
	return DistanceSquared(x1, y1, x2, y2) < totalRadius*totalRadius
}

// CheckCircleCollisionWithDistance returns both collision status and actual distance
// Useful when you need the distance for other purposes (e.g., impulse calculation)
func CheckCircleCollisionWithDistance(x1, y1, r1, x2, y2, r2 float32) (bool, float32) {
	dist := Distance(x1, y1, x2, y2)
	return dist < (r1 + r2), dist
}

// WorldToScreen converts world coordinates to screen coordinates
// Accounts for camera position and centers on screen
func WorldToScreen(worldX, worldY, cameraX, cameraY float32, screenWidth, screenHeight int) (float32, float32) {
	screenX := worldX - cameraX + float32(screenWidth)/2
	screenY := worldY - cameraY + float32(screenHeight)/2
	return screenX, screenY
}

// WorldToRadar converts world coordinates to radar pixel coordinates
// Returns relative position from ship center, scaled to radar
func WorldToRadar(worldX, worldY, shipX, shipY, radarScale float32) (int32, int32) {
	relX := worldX - shipX
	relY := worldY - shipY
	return int32(relX / radarScale), int32(relY / radarScale)
}

// WorldTo3D converts 2D world coordinates to 3D space coordinates
// Used for rendering 3D asteroids from 2D game positions
func WorldTo3D(worldX, worldY, cameraX, cameraY, scale float32) (float32, float32) {
	relativeX := worldX - cameraX
	relativeY := worldY - cameraY
	return relativeX / scale, -relativeY / scale
}

// RotationVector returns the direction vector (cos, sin) for a given rotation angle
// Useful for movement and rendering calculations
func RotationVector(rotation float32) (float32, float32) {
	return float32(math.Cos(float64(rotation))), float32(math.Sin(float64(rotation)))
}

// IsOnScreen checks if a position is visible on screen with buffer
// Buffer allows for checking slightly off-screen objects
func IsOnScreen(screenX, screenY float32, screenWidth, screenHeight int, buffer float32) bool {
	return screenX >= -buffer && screenX <= float32(screenWidth)+buffer &&
		screenY >= -buffer && screenY <= float32(screenHeight)+buffer
}

// RandomRotationSpeed generates a random rotation speed centered at 0
// Returns a value in the range [-maxAbsolute, +maxAbsolute]
func RandomRotationSpeed(maxAbsolute float32) float32 {
	return float32(rl.GetRandomValue(-100, 100)) / 100.0 * maxAbsolute
}

// RandomRange generates a random float32 in the given range [min, max]
func RandomRange(min, max float32) float32 {
	return min + float32(rl.GetRandomValue(0, 100))/100.0*(max-min)
}

// Clamp restricts a value to a given range
func Clamp(value, min, max float32) float32 {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
