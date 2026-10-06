// AstroBoy4 Systems - Mothership System
// Handles mothership rendering and docking detection
// Adapted from astroBoy3's mothership.go and collision_handler.go

package systems

import (
	"math"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Mothership represents the player's home base/space station
type Mothership struct {
	X, Y   float32 // World position
	Radius float32 // Collision radius
}

// MothershipSystem handles mothership rendering and interaction
type MothershipSystem struct {
	mothership      Mothership
	wasInMothership bool // Prevents immediate re-entry after exiting
}

// NewMothershipSystem creates a new mothership system at the given position
func NewMothershipSystem(x, y, radius float32) *MothershipSystem {
	return &MothershipSystem{
		mothership: Mothership{
			X:      x,
			Y:      y,
			Radius: radius,
		},
		wasInMothership: false,
	}
}

// DrawMothership renders the mothership/space station
func (ms *MothershipSystem) DrawMothership(shipX, shipY, cameraX, cameraY float32, screenWidth, screenHeight int) {
	// Convert world coordinates to screen coordinates
	screenX, screenY := WorldToScreen(ms.mothership.X, ms.mothership.Y, cameraX, cameraY, screenWidth, screenHeight)

	// Only draw if on screen (with buffer for large objects)
	if IsOnScreen(screenX, screenY, screenWidth, screenHeight, 100) {

		// Draw mothership hull (main circle)
		rl.DrawCircle(int32(screenX), int32(screenY), ms.mothership.Radius,
			MothershipHullColor)
		rl.DrawCircleLines(int32(screenX), int32(screenY), ms.mothership.Radius,
			MothershipBorderColor)

		// Draw docking bay (inner circle)
		rl.DrawCircle(int32(screenX), int32(screenY), ms.mothership.Radius*0.7,
			MothershipBayColor)

		// Draw docking bay outline
		rl.DrawCircleLines(int32(screenX), int32(screenY), ms.mothership.Radius*0.7,
			MothershipBayBorder)

		// Draw label
		rl.DrawText("MOTHERSHIP", int32(screenX-35), int32(screenY-5), 10, rl.White)

		// Calculate distance to ship for approach effect
		distance := Distance(shipX, shipY, ms.mothership.X, ms.mothership.Y)

		// Pulsing docking indicator when ship is near
		if distance < ms.mothership.Radius*1.5 {
			pulseRadius := ms.mothership.Radius + float32(MothershipPulseOffset) +
				float32(math.Sin(float64(rl.GetTime())*MothershipPulseFrequency))*float32(MothershipPulseAmplitude)
			rl.DrawCircleLines(int32(screenX), int32(screenY), pulseRadius,
				MothershipIndicator)
		}
	}
}

// CheckDocking checks if ship is within docking range
// Returns true if ship should dock (enter mothership)
func (ms *MothershipSystem) CheckDocking(shipX, shipY float32) bool {
	distance := Distance(shipX, shipY, ms.mothership.X, ms.mothership.Y)

	// Reset wasInMothership flag when far away
	if distance > ms.mothership.Radius*float32(MothershipResetDistanceMultiplier) {
		ms.wasInMothership = false
	}

	// Dock if within radius and not recently docked
	if distance < ms.mothership.Radius && !ms.wasInMothership {
		ms.wasInMothership = true
		return true
	}

	return false
}

// GetPosition returns the mothership's world position
func (ms *MothershipSystem) GetPosition() (float32, float32) {
	return ms.mothership.X, ms.mothership.Y
}

// GetRadius returns the mothership's collision radius
func (ms *MothershipSystem) GetRadius() float32 {
	return ms.mothership.Radius
}

// SetPosition sets the mothership's position (for initialization or relocation)
func (ms *MothershipSystem) SetPosition(x, y float32) {
	ms.mothership.X = x
	ms.mothership.Y = y
}

// ResetDockingFlag resets the docking flag (call when ship leaves mothership)
func (ms *MothershipSystem) ResetDockingFlag() {
	ms.wasInMothership = false
}
