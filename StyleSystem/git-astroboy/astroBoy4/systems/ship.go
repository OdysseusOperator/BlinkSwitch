// AstroBoy4 Systems - Ship Physics and Weapons
// Enhanced ship movement, rotation, momentum, and weapon systems
// Ported and enhanced from astroBoy3/src/systems/ship_physics_clay.go

package systems

import (
	"math"

	"astroboy4/gameobjects"

	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	shipPrismNoseLength = 24.0
	shipPrismTailOffset = -14.0
	shipPrismHalfWidth  = 10.0
	shipPrismHalfHeight = 5.0
)

var shipMeshFaces = []gameobjects.Face{
	// Top triangle
	{V0: 0, V1: 1, V2: 2},
	// Bottom triangle (reverse winding)
	{V0: 3, V1: 5, V2: 4},
	// Nose-right side
	{V0: 0, V1: 2, V2: 5},
	{V0: 0, V1: 5, V2: 3},
	// Nose-left side
	{V0: 0, V1: 3, V2: 4},
	{V0: 0, V1: 4, V2: 1},
	// Tail face (connect left/right)
	{V0: 1, V1: 4, V2: 5},
	{V0: 1, V1: 5, V2: 2},
}

// ShipPhysics handles ship movement, rotation, momentum, and weapons
type ShipPhysics struct {
	// Position and movement
	X, Y      float32 // World position
	VX, VY    float32 // Velocity (momentum)
	Rotation  float32 // Current rotation in radians
	Thrusting bool    // Is thruster currently active

	modelPitch  float32
	modelRoll   float32
	targetPitch float32
	targetRoll  float32

	// Weapon system
	WeaponCooldown float32 // Current weapon cooldown timer
	MultiShotLevel int     // Multi-shot upgrade level (0 = single shot, 1 = 2 shots, etc.)
	FireRateLevel  int     // Fire rate upgrade level (0 = base rate)

	// Physics constants (from constants.go)
	ThrustForce   float32 // Acceleration when thrusting
	RotationSpeed float32 // How fast ship rotates (radians per second)
	MaxSpeed      float32 // Maximum velocity limit (0 = unlimited)
	DragFactor    float32 // Momentum preservation (0.99 = slight drag)
}

// NewShipPhysics creates a new ship physics system with default values
func NewShipPhysics(startX, startY float32) *ShipPhysics {
	return &ShipPhysics{
		X:              startX,
		Y:              startY,
		VX:             0,
		VY:             0,
		Rotation:       -math.Pi / 2, // Point up initially
		Thrusting:      false,
		modelPitch:     ShipModelIdlePitch,
		modelRoll:      0,
		targetPitch:    ShipModelIdlePitch,
		targetRoll:     0,
		WeaponCooldown: 0,
		MultiShotLevel: 0, // Start with single shot
		FireRateLevel:  0, // Start with base fire rate
		ThrustForce:    ShipAcceleration,
		RotationSpeed:  ShipRotationSpeed * rl.Deg2rad,
		MaxSpeed:       0,    // No speed limit
		DragFactor:     0.99, // Slight drag for realism
	}
}

// HandleInput processes keyboard input for ship controls
func (sp *ShipPhysics) HandleInput(deltaTime float32) {
	// Handle rotation
	turnIntent := float32(0)
	if rl.IsKeyDown(rl.KeyA) || rl.IsKeyDown(rl.KeyLeft) {
		sp.Rotation -= sp.RotationSpeed * deltaTime
		turnIntent -= 1
	}
	if rl.IsKeyDown(rl.KeyD) || rl.IsKeyDown(rl.KeyRight) {
		sp.Rotation += sp.RotationSpeed * deltaTime
		turnIntent += 1
	}
	sp.targetRoll = Clamp(turnIntent*ShipModelTurnRoll, -ShipModelTurnRoll, ShipModelTurnRoll)

	// Handle thrust
	sp.Thrusting = rl.IsKeyDown(rl.KeyW) || rl.IsKeyDown(rl.KeyUp)
	if sp.Thrusting {
		// Apply thrust in the direction the ship is pointing
		cos, sin := RotationVector(sp.Rotation)
		sp.VX += cos * sp.ThrustForce * deltaTime
		sp.VY += sin * sp.ThrustForce * deltaTime
	}

	if sp.Thrusting {
		sp.targetPitch = ShipModelThrustPitch
	} else {
		sp.targetPitch = ShipModelIdlePitch
	}
}

// Update updates ship physics (position, momentum, weapon cooldown)
func (sp *ShipPhysics) Update(deltaTime float32) {
	// Apply drag to maintain momentum but prevent infinite acceleration
	sp.VX *= sp.DragFactor
	sp.VY *= sp.DragFactor

	// Apply speed limit if set
	if sp.MaxSpeed > 0 {
		speed := float32(math.Sqrt(float64(sp.VX*sp.VX + sp.VY*sp.VY)))
		if speed > sp.MaxSpeed {
			sp.VX = (sp.VX / speed) * sp.MaxSpeed
			sp.VY = (sp.VY / speed) * sp.MaxSpeed
		}
	}

	// Update position based on velocity
	sp.X += sp.VX * deltaTime
	sp.Y += sp.VY * deltaTime

	// Update weapon cooldown
	if sp.WeaponCooldown > 0 {
		sp.WeaponCooldown -= deltaTime
	}

	sp.updateModelOrientation(deltaTime)
}

// GetSpeed returns the current speed of the ship
func (sp *ShipPhysics) GetSpeed() float32 {
	return float32(math.Sqrt(float64(sp.VX*sp.VX + sp.VY*sp.VY)))
}

// GetFrontPosition returns the position at the front of the ship (for bullet spawning)
func (sp *ShipPhysics) GetFrontPosition() (float32, float32) {
	cos, sin := RotationVector(sp.Rotation)
	frontDistance := float32(15) // Distance to front of ship
	return sp.X + cos*frontDistance, sp.Y + sin*frontDistance
}

// GetBackPosition returns the position at the back of the ship (for thruster effects)
func (sp *ShipPhysics) GetBackPosition() (float32, float32) {
	cos, sin := RotationVector(sp.Rotation)
	backDistance := float32(10) // Distance to back of ship
	return sp.X - cos*backDistance, sp.Y - sin*backDistance
}

// CanShoot returns true if the weapon is ready to fire
func (sp *ShipPhysics) CanShoot() bool {
	return sp.WeaponCooldown <= 0
}

// GetFireRateCooldown returns the current fire rate cooldown based on upgrade level
// Base cooldown: 0.5s
// Reduction: 5% per level (multiply by 0.95 each level)
// Min cooldown: 0.05s (20 shots/sec max)
func (sp *ShipPhysics) GetFireRateCooldown() float32 {
	baseCooldown := float32(0.5)
	minCooldown := float32(0.05)

	cooldown := baseCooldown * float32(math.Pow(0.95, float64(sp.FireRateLevel)))
	if cooldown < minCooldown {
		cooldown = minCooldown
	}

	return cooldown
}

// Shoot creates bullets based on multi-shot upgrade level
// Returns slice of bullets with proper spread
func (sp *ShipPhysics) Shoot() []Bullet {
	if !sp.CanShoot() {
		return nil
	}

	// Set cooldown
	sp.WeaponCooldown = sp.GetFireRateCooldown()

	// Calculate number of bullets based on upgrade level
	bulletCount := 1 + sp.MultiShotLevel
	bullets := make([]Bullet, bulletCount)

	// Calculate spread angle (±15 degrees per bullet)
	spreadAngle := float32(15 * rl.Deg2rad)

	for i := 0; i < bulletCount; i++ {
		// Calculate angle offset for this bullet
		angleOffset := float32(0)
		if bulletCount > 1 {
			// Spread bullets evenly across the angle
			// For 2 bullets: -15°, +15°
			// For 3 bullets: -15°, 0°, +15°
			// For 4 bullets: -22.5°, -7.5°, +7.5°, +22.5°
			ratio := float32(i) / float32(bulletCount-1) // 0 to 1
			angleOffset = (ratio - 0.5) * 2 * spreadAngle
		}

		// Calculate bullet direction with spread
		bulletAngle := sp.Rotation + angleOffset
		bulletCos, bulletSin := RotationVector(bulletAngle)

		// Spawn bullet at front of ship
		frontX, frontY := sp.GetFrontPosition()

		bullets[i] = Bullet{
			X:        frontX,
			Y:        frontY,
			VX:       sp.VX + bulletCos*BulletSpeed, // Inherit ship momentum
			VY:       sp.VY + bulletSin*BulletSpeed,
			Lifetime: BulletLifeTime,
		}
	}

	return bullets
}

// DrawShip renders the ship at screen center with proper rotation
func (sp *ShipPhysics) DrawShip(screenCenterX, screenCenterY float32) {
	// Calculate ship orientation
	cos, sin := RotationVector(sp.Rotation)

	// Draw thruster flame if thrusting (draw before ship so it's behind)
	if sp.Thrusting {
		sp.drawThrusterFlame(screenCenterX, screenCenterY, cos, sin)
	}

	projected := sp.projectShipVertices()
	if len(projected) < 3 {
		return
	}

	screenVerts := make([]rl.Vector2, len(projected))
	for i, vertex := range projected {
		screenVerts[i] = rl.Vector2{X: screenCenterX + vertex.X, Y: screenCenterY + vertex.Y}
	}

	// Draw each triangular face like the asteroid cube renderer
	for _, face := range shipMeshFaces {
		v0 := screenVerts[face.V0]
		v1 := screenVerts[face.V1]
		v2 := screenVerts[face.V2]
		rl.DrawTriangle(v0, v1, v2, AsteroidFillColor)
	}

	// Draw visible mesh edges for better readability (same as asteroid cubes)
	edges := GetVisibleEdges(getShipVertices(), shipMeshFaces, sp.modelPitch, sp.Rotation, sp.modelRoll)
	for _, edge := range edges {
		v0 := projected[edge.V0]
		v1 := projected[edge.V1]
		start := rl.Vector2{X: screenCenterX + v0.X, Y: screenCenterY + v0.Y}
		end := rl.Vector2{X: screenCenterX + v1.X, Y: screenCenterY + v1.Y}
		rl.DrawLineEx(start, end, 2.0, AsteroidEdgeColor)
	}

	// Outline hull using convex hull of projected vertices
	hull := ConvexHull2D(projected)
	if len(hull) >= 3 {
		for i := 0; i < len(hull); i++ {
			j := (i + 1) % len(hull)
			start := rl.Vector2{X: screenCenterX + hull[i].X, Y: screenCenterY + hull[i].Y}
			end := rl.Vector2{X: screenCenterX + hull[j].X, Y: screenCenterY + hull[j].Y}
			rl.DrawLineEx(start, end, 2.5, AsteroidEdgeColor)
		}
	}
}

// drawThrusterFlame renders the thruster flame effect with randomization
func (sp *ShipPhysics) drawThrusterFlame(shipScreenX, shipScreenY, cos, sin float32) {
	// Flame extends from back of ship with random length
	flameLength := float32(FlameMinLength) + float32(rl.GetRandomValue(0, int32(FlameMaxLength-FlameMinLength)))
	flameWidth := float32(FlameWidth)

	// Back of ship position
	backX := shipScreenX - cos*float32(ShipBackOffset)
	backY := shipScreenY - sin*float32(ShipBackOffset)

	// Flame tip position
	tipX := backX - cos*flameLength
	tipY := backY - sin*flameLength

	// Flame sides (perpendicular to ship direction)
	perpX := -sin * flameWidth
	perpY := cos * flameWidth

	// Draw flame as triangle with random color variation
	flameColor := rl.Color{
		R: 255,
		G: uint8(100 + rl.GetRandomValue(0, 155)), // Variable orange/red
		B: 0,
		A: 200, // Semi-transparent
	}

	flame1 := rl.Vector2{X: backX + perpX, Y: backY + perpY}
	flame2 := rl.Vector2{X: tipX, Y: tipY}
	flame3 := rl.Vector2{X: backX - perpX, Y: backY - perpY}

	rl.DrawTriangle(flame1, flame2, flame3, flameColor)

	// Draw flame outline for better visibility
	outlineColor := rl.Color{R: 255, G: 150, B: 0, A: 255} // Orange outline
	rl.DrawLineEx(flame1, flame2, 1.5, outlineColor)
	rl.DrawLineEx(flame2, flame3, 1.5, outlineColor)
	rl.DrawLineEx(flame3, flame1, 1.5, outlineColor)
}

// ApplyImpulse applies an external force to the ship (for collisions)
func (sp *ShipPhysics) ApplyImpulse(impulseX, impulseY float32) {
	sp.VX += impulseX
	sp.VY += impulseY
}

// SetPosition sets the ship's world position (for respawning, teleporting, etc.)
func (sp *ShipPhysics) SetPosition(x, y float32) {
	sp.X = x
	sp.Y = y
}

// GetPosition returns the ship's current world position
func (sp *ShipPhysics) GetPosition() (float32, float32) {
	return sp.X, sp.Y
}

// GetVelocity returns the ship's current velocity
func (sp *ShipPhysics) GetVelocity() (float32, float32) {
	return sp.VX, sp.VY
}

// SetVelocity sets the ship's velocity (for special effects, stopping, etc.)
func (sp *ShipPhysics) SetVelocity(vx, vy float32) {
	sp.VX = vx
	sp.VY = vy
}

// GetCollisionVertices returns ship vertices in world coordinates for collision detection
func (sp *ShipPhysics) GetCollisionVertices() []Vector2 {
	localHull := sp.getLocalShipHull()
	if len(localHull) < 3 {
		return nil
	}

	worldHull := make([]Vector2, len(localHull))
	for i, vertex := range localHull {
		worldHull[i] = Vector2{X: sp.X + vertex.X, Y: sp.Y + vertex.Y}
	}
	return worldHull
}

// UpgradeMultiShot increases the multi-shot level
func (sp *ShipPhysics) UpgradeMultiShot() {
	sp.MultiShotLevel++
}

// UpgradeFireRate increases the fire rate level
func (sp *ShipPhysics) UpgradeFireRate() {
	sp.FireRateLevel++
}

// GetMultiShotCount returns the current number of bullets fired per shot
func (sp *ShipPhysics) GetMultiShotCount() int {
	return 1 + sp.MultiShotLevel
}

// GetMultiShotLevel returns the current multi-shot upgrade level
func (sp *ShipPhysics) GetMultiShotLevel() int {
	return sp.MultiShotLevel
}

// GetFireRateLevel returns the current fire rate upgrade level
func (sp *ShipPhysics) GetFireRateLevel() int {
	return sp.FireRateLevel
}

// getLocalShipHull projects the 3D ship mesh into 2D using the shared projection utilities
func (sp *ShipPhysics) getLocalShipHull() []Vector2 {
	projected := sp.projectShipVertices()
	if len(projected) < 3 {
		return nil
	}
	polygon := ConvexHull2D(projected)
	if len(polygon) < 3 {
		return nil
	}
	return polygon
}

func (sp *ShipPhysics) projectShipVertices() []Vector2 {
	mesh := getShipVertices()
	projected := make([]Vector2, len(mesh))
	for i, vertex := range mesh {
		rotated := RotateVector3(vertex, sp.modelPitch, sp.Rotation, sp.modelRoll)
		projected[i] = Vector2{X: rotated.X, Y: rotated.Z}
	}
	return projected
}

func getShipVertices() []gameobjects.Vector3 {
	return []gameobjects.Vector3{
		// Top triangle (Y + height)
		{X: shipPrismNoseLength, Y: shipPrismHalfHeight, Z: 0},                   // Nose
		{X: shipPrismTailOffset, Y: shipPrismHalfHeight, Z: -shipPrismHalfWidth}, // Left tail
		{X: shipPrismTailOffset, Y: shipPrismHalfHeight, Z: shipPrismHalfWidth},  // Right tail
		// Bottom triangle (Y - height)
		{X: shipPrismNoseLength, Y: -shipPrismHalfHeight, Z: 0},                   // Nose bottom
		{X: shipPrismTailOffset, Y: -shipPrismHalfHeight, Z: -shipPrismHalfWidth}, // Left tail bottom
		{X: shipPrismTailOffset, Y: -shipPrismHalfHeight, Z: shipPrismHalfWidth},  // Right tail bottom
	}
}

func (sp *ShipPhysics) updateModelOrientation(deltaTime float32) {
	maxDelta := ShipModelTiltSpeed * deltaTime
	sp.modelPitch = approachValue(sp.modelPitch, sp.targetPitch, maxDelta)
	sp.modelRoll = approachValue(sp.modelRoll, sp.targetRoll, maxDelta)
}

func approachValue(current, target, maxDelta float32) float32 {
	delta := target - current
	if delta > maxDelta {
		delta = maxDelta
	} else if delta < -maxDelta {
		delta = -maxDelta
	}
	return current + delta
}
