// AstroBoy4 Systems - Asteroid Manager
// Advanced asteroid spawning, management, and splitting system
// Adapted from astroBoy3's asteroid_system_clay.go

package systems

import (
	"math"
	"math/rand"

	"astroboy4/gameobjects"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Note: math.Pi is still used for angle calculations
// Other math operations moved to math_utils.go

// AsteroidManager handles asteroid spawning, updating, splitting, and collision
type AsteroidManager struct {
	asteroids       []gameobjects.Asteroid
	nextAsteroidID  int
	minSize         float32          // Minimum size before asteroid is destroyed instead of split
	maxAsteroids    int              // Maximum number of asteroids to maintain
	spawnCooldown   float32          // Time until next asteroid can spawn
	collisionSystem *CollisionSystem // Reference to collision system for debug visualization
}

// NewAsteroidManager creates a new asteroid management system
func NewAsteroidManager() *AsteroidManager {
	return &AsteroidManager{
		asteroids:       make([]gameobjects.Asteroid, 0, 50),
		nextAsteroidID:  1,
		minSize:         AsteroidMinSize,
		maxAsteroids:    int(AsteroidMaxCount),
		spawnCooldown:   0.0,
		collisionSystem: nil, // Will be set later
	}
}

// SetCollisionSystem sets the collision system reference for debug visualization
func (am *AsteroidManager) SetCollisionSystem(cs *CollisionSystem) {
	am.collisionSystem = cs
}

// GenerateAsteroid creates a new asteroid with random shape and properties
func (am *AsteroidManager) GenerateAsteroid(x, y, size float32, id int) gameobjects.Asteroid {
	// Select random shape from registry
	randomShape := shapeRegistry[rand.Intn(len(shapeRegistry))]

	return gameobjects.Asteroid{
		X:              x,
		Y:              y,
		VX:             RandomRange(-50, 50), // Random velocity
		VY:             RandomRange(-50, 50),
		RotationX:      RandomRange(0, 2*math.Pi),
		RotationY:      RandomRange(0, 2*math.Pi),
		RotationZ:      RandomRange(0, 2*math.Pi),
		RotationSpeedX: RandomRotationSpeed(2.0), // -2 to +2 radians per second on X axis
		RotationSpeedY: RandomRotationSpeed(2.0), // -2 to +2 radians per second on Y axis
		RotationSpeedZ: RandomRotationSpeed(2.0), // -2 to +2 radians per second on Z axis
		Size:           size,
		ShapeRenderer:  randomShape,
	}
}

// SpawnInitialAsteroids creates the starting asteroid field with both visible and offscreen asteroids
func (am *AsteroidManager) SpawnInitialAsteroids(shipX, shipY float32, count int) {
	spawnBuffer := float32(AsteroidSpawnScreenBuffer + AsteroidMaxSpawnSize)
	onScreenCount := AsteroidInitialOnScreenCount
	if onScreenCount > count {
		onScreenCount = count
	}

	// Spawn a few asteroids already within the visible area
	for i := 0; i < onScreenCount; i++ {
		var x, y float32
		for attempts := 0; attempts < 8; attempts++ {
			x = shipX + RandomRange(-AsteroidInitialOnScreenRadius, AsteroidInitialOnScreenRadius)
			y = shipY + RandomRange(-AsteroidInitialOnScreenRadius, AsteroidInitialOnScreenRadius)
			if Distance(x, y, shipX, shipY) >= AsteroidSafeSpawnDistance {
				break
			}
		}

		size := RandomRange(AsteroidMinSpawnSize, AsteroidMaxSpawnSize)
		asteroid := am.GenerateAsteroid(x, y, size, am.nextAsteroidID)
		am.nextAsteroidID++
		am.asteroids = append(am.asteroids, asteroid)
	}

	remaining := count - onScreenCount
	for i := 0; i < remaining; i++ {
		x, y := spawnOutsideVisibleWindow(shipX, shipY, spawnBuffer)

		size := RandomRange(AsteroidMinSpawnSize, AsteroidMaxSpawnSize)
		asteroid := am.GenerateAsteroid(x, y, size, am.nextAsteroidID)
		am.nextAsteroidID++
		am.configureInboundVelocity(&asteroid, shipX, shipY)
		am.asteroids = append(am.asteroids, asteroid)
	}
}

// Update updates all asteroids (position, rotation) and spawn cooldown
func (am *AsteroidManager) Update(deltaTime float32, shipX, shipY float32) {
	// Update cooldown
	if am.spawnCooldown > 0 {
		am.spawnCooldown -= deltaTime
	}

	visibleRadius := spawnVisibleRadius()
	maxDistance := visibleRadius * 2

	// Update asteroid physics
	for i := len(am.asteroids) - 1; i >= 0; i-- {
		asteroid := &am.asteroids[i]
		asteroid.X += asteroid.VX * deltaTime
		asteroid.Y += asteroid.VY * deltaTime

		// Update rotation on each axis independently
		asteroid.RotationX += asteroid.RotationSpeedX * deltaTime
		asteroid.RotationY += asteroid.RotationSpeedY * deltaTime
		asteroid.RotationZ += asteroid.RotationSpeedZ * deltaTime

		if Distance(asteroid.X, asteroid.Y, shipX, shipY) > maxDistance {
			am.asteroids = append(am.asteroids[:i], am.asteroids[i+1:]...)
		}
	}
}

// SplitAsteroid splits an asteroid into two smaller pieces
func (am *AsteroidManager) SplitAsteroid(originalAsteroid gameobjects.Asteroid) {
	if originalAsteroid.Size <= am.minSize {
		return // Don't split if too small
	}

	// Create two smaller asteroids
	newSize := originalAsteroid.Size * AsteroidSplitSizeMultiplier

	// Create first fragment
	id1 := am.nextAsteroidID
	am.nextAsteroidID++
	asteroid1 := am.GenerateAsteroid(originalAsteroid.X, originalAsteroid.Y, newSize, id1)
	// Give it some velocity away from the original position
	angle1 := RandomRange(0, 2*math.Pi)
	speed := RandomRange(AsteroidFragmentMinSpeed, AsteroidFragmentMaxSpeed)
	cos1, sin1 := RotationVector(angle1)
	asteroid1.VX = originalAsteroid.VX + cos1*speed
	asteroid1.VY = originalAsteroid.VY + sin1*speed
	// Inherit parent rotation with small variation
	asteroid1.RotationX = originalAsteroid.RotationX + RandomRange(-0.3, 0.3)
	asteroid1.RotationY = originalAsteroid.RotationY + RandomRange(-0.3, 0.3)
	asteroid1.RotationZ = originalAsteroid.RotationZ + RandomRange(-0.3, 0.3)
	// Inherit rotation speeds with variation
	asteroid1.RotationSpeedX = originalAsteroid.RotationSpeedX + RandomRotationSpeed(0.5)
	asteroid1.RotationSpeedY = originalAsteroid.RotationSpeedY + RandomRotationSpeed(0.5)
	asteroid1.RotationSpeedZ = originalAsteroid.RotationSpeedZ + RandomRotationSpeed(0.5)

	// Create second fragment
	id2 := am.nextAsteroidID
	am.nextAsteroidID++
	asteroid2 := am.GenerateAsteroid(originalAsteroid.X, originalAsteroid.Y, newSize, id2)
	// Give it velocity in roughly opposite direction
	angle2 := angle1 + math.Pi + RandomRange(-0.4, 0.4) // Opposite direction with variance
	cos2, sin2 := RotationVector(angle2)
	asteroid2.VX = originalAsteroid.VX + cos2*speed
	asteroid2.VY = originalAsteroid.VY + sin2*speed
	// Inherit parent rotation with small variation
	asteroid2.RotationX = originalAsteroid.RotationX + RandomRange(-0.3, 0.3)
	asteroid2.RotationY = originalAsteroid.RotationY + RandomRange(-0.3, 0.3)
	asteroid2.RotationZ = originalAsteroid.RotationZ + RandomRange(-0.3, 0.3)
	// Inherit rotation speeds with variation
	asteroid2.RotationSpeedX = originalAsteroid.RotationSpeedX + RandomRotationSpeed(0.5)
	asteroid2.RotationSpeedY = originalAsteroid.RotationSpeedY + RandomRotationSpeed(0.5)
	asteroid2.RotationSpeedZ = originalAsteroid.RotationSpeedZ + RandomRotationSpeed(0.5)

	// Add the new asteroids
	am.asteroids = append(am.asteroids, asteroid1, asteroid2)
}

// CheckBulletCollisions checks collisions between bullets and asteroids using 2-tier detection
// Tier 1: Fast bounding circle check
// Tier 2: Precise projected polygon check
// Returns score gained from destroyed asteroids
func (am *AsteroidManager) CheckBulletCollisions(bullets *[]Bullet) int {
	score := 0

	// Check bullet-asteroid collisions
	for i := len(*bullets) - 1; i >= 0; i-- {
		bullet := (*bullets)[i]

		for j := len(am.asteroids) - 1; j >= 0; j-- {
			asteroid := am.asteroids[j]

			// Use CollisionSystem for 2-tier bullet-asteroid collision detection
			boundingRadius := asteroid.ShapeRenderer.GetBoundingRadius(asteroid.Size)
			vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)

			var collision bool
			if am.collisionSystem != nil {
				// Use collision system (includes debug visualization)
				collision = am.collisionSystem.BulletAsteroidCollision(
					bullet.X, bullet.Y,
					asteroid.X, asteroid.Y, boundingRadius,
					vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)
			} else {
				// Fallback to direct collision check (if collision system not set)
				// TIER 1: Fast bounding circle check
				if !CheckCircleCollision(bullet.X, bullet.Y, BulletRadius,
					asteroid.X, asteroid.Y, boundingRadius) {
					continue
				}

				// TIER 2: Precise projected polygon check (if shape has vertices)
				if len(vertices) > 0 {
					polygon := GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)
					bulletPoint := Vector2{X: bullet.X, Y: bullet.Y}
					if !PointInPolygon(bulletPoint, polygon, asteroid.X, asteroid.Y) {
						continue
					}
				}
				collision = true
			}

			if !collision {
				continue
			}

			// Collision confirmed!
			score += 10

			// Remove bullet
			*bullets = append((*bullets)[:i], (*bullets)[i+1:]...)

			// Split asteroid if large enough, otherwise just destroy it
			if asteroid.Size > am.minSize {
				am.SplitAsteroid(asteroid)
			}

			// Remove original asteroid
			am.asteroids = append(am.asteroids[:j], am.asteroids[j+1:]...)
			break
		}
	}

	return score
}

// CheckShipCollision checks if ship collides with any asteroid using 2-tier detection
func (am *AsteroidManager) CheckShipCollision(shipX, shipY, shipRadius float32) bool {
	for _, asteroid := range am.asteroids {
		// TIER 1: Fast bounding circle check
		boundingRadius := asteroid.ShapeRenderer.GetBoundingRadius(asteroid.Size)
		if !CheckCircleCollision(shipX, shipY, shipRadius,
			asteroid.X, asteroid.Y, boundingRadius) {
			continue
		}

		// TIER 2: Precise projected polygon check (if shape has vertices)
		vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)
		if len(vertices) > 0 {
			// Project 3D shape to 2D polygon
			polygon := GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

			// Check if ship center is inside projected polygon
			shipPoint := Vector2{X: shipX, Y: shipY}
			if !PointInPolygon(shipPoint, polygon, asteroid.X, asteroid.Y) {
				continue
			}
		}

		return true
	}
	return false
}

// SpawnNewAsteroid spawns a new asteroid periodically at screen edges
func (am *AsteroidManager) SpawnNewAsteroid(shipX, shipY float32) {
	if am.spawnCooldown <= 0 && len(am.asteroids) < am.maxAsteroids {
		spawnBuffer := float32(AsteroidSpawnScreenBuffer + AsteroidMaxSpawnSize)
		x, y := spawnOutsideVisibleWindow(shipX, shipY, spawnBuffer)

		size := RandomRange(AsteroidMinSpawnSize, AsteroidMaxSpawnSize)
		asteroid := am.GenerateAsteroid(x, y, size, am.nextAsteroidID)

		am.configureInboundVelocity(&asteroid, shipX, shipY)

		am.nextAsteroidID++
		am.asteroids = append(am.asteroids, asteroid)
		am.spawnCooldown = AsteroidSpawnCooldownMin + float32(rand.Float64()*(AsteroidSpawnCooldownMax-AsteroidSpawnCooldownMin))
	}
}

// spawnOutsideVisibleWindow picks a random position outside the visible screen area with buffer
func spawnOutsideVisibleWindow(shipX, shipY float32, buffer float32) (float32, float32) {
	visibleRadius := spawnVisibleRadius()
	spawnDistance := visibleRadius + buffer

	var x, y float32
	switch rand.Intn(4) {
	case 0: // Top edge - spawn above screen
		x = shipX + RandomRange(-spawnDistance, spawnDistance)
		y = shipY - spawnDistance
	case 1: // Right edge - spawn to the right
		x = shipX + spawnDistance
		y = shipY + RandomRange(-spawnDistance, spawnDistance)
	case 2: // Bottom edge - spawn below screen
		x = shipX + RandomRange(-spawnDistance, spawnDistance)
		y = shipY + spawnDistance
	default: // Left edge - spawn to the left
		x = shipX - spawnDistance
		y = shipY + RandomRange(-spawnDistance, spawnDistance)
	}

	return x, y
}

// configureInboundVelocity aims a spawned asteroid roughly toward the ship with variation
func (am *AsteroidManager) configureInboundVelocity(asteroid *gameobjects.Asteroid, shipX, shipY float32) {
	distance := Distance(shipX, shipY, asteroid.X, asteroid.Y)
	if distance <= 0 {
		return
	}

	dx := (shipX - asteroid.X) / distance
	dy := (shipY - asteroid.Y) / distance
	speed := RandomRange(60, 140)
	randomAngleOffset := RandomRange(-0.4, 0.4)
	cosOffset := float32(math.Cos(float64(randomAngleOffset)))
	sinOffset := float32(math.Sin(float64(randomAngleOffset)))

	newDx := dx*cosOffset - dy*sinOffset
	newDy := dx*sinOffset + dy*cosOffset

	asteroid.VX = newDx*speed + RandomRange(-15, 15)
	asteroid.VY = newDy*speed + RandomRange(-15, 15)
}

// GetAsteroids returns all current asteroids (for rendering)
func (am *AsteroidManager) GetAsteroids() []gameobjects.Asteroid {
	return am.asteroids
}

// GetAsteroidCount returns the current number of asteroids
func (am *AsteroidManager) GetAsteroidCount() int {
	return len(am.asteroids)
}

// ClearAsteroids removes all asteroids (for game restart)
func (am *AsteroidManager) ClearAsteroids() {
	am.asteroids = make([]gameobjects.Asteroid, 0, 50)
	am.spawnCooldown = 0.0
}

func spawnVisibleRadius() float32 {
	width := float64(rl.GetScreenWidth())
	height := float64(rl.GetScreenHeight())
	return float32(math.Hypot(width/2, height/2))
}
