// AstroBoy4 Systems - Advanced Collision Detection
// Provides triangle-circle, polygon-polygon (SAT), and AABB collision detection
// Ported and adapted from astroBoy3/src/systems/collision_system_clay.go

package systems

import (
	"math"

	"astroboy4/gameobjects"
	rl "github.com/gen2brain/raylib-go/raylib"
)

// Type alias for convenience
type Vector3 = gameobjects.Vector3

// CollisionSystem manages all collision detection in the game
type CollisionSystem struct {
	// Debug visualization
	ShowDebugInfo   bool
	debugCollisions []DebugCollision

	// Debug statistics (for performance monitoring)
	tier1Checks   int
	tier2Checks   int
	satChecks     int
	collisionHits int
}

// NewCollisionSystem creates a new collision detection system
func NewCollisionSystem() *CollisionSystem {
	return &CollisionSystem{
		ShowDebugInfo:   false,
		debugCollisions: make([]DebugCollision, 0, 100),
	}
}

// === BOUNDING BOX COLLISION (AABB) ===

// NewBoundingBox creates a bounding box around a position with given dimensions
func NewBoundingBox(centerX, centerY, width, height float32) BoundingBox {
	return BoundingBox{
		X:      centerX,
		Y:      centerY,
		Width:  width,
		Height: height,
	}
}

// BoundingBoxCollision checks if two bounding boxes overlap (AABB collision)
// Fast pre-filtering before more expensive collision checks
func BoundingBoxCollision(bb1, bb2 BoundingBox) bool {
	dx := float32(math.Abs(float64(bb1.X - bb2.X)))
	dy := float32(math.Abs(float64(bb1.Y - bb2.Y)))

	return dx < (bb1.Width+bb2.Width)/2 && dy < (bb1.Height+bb2.Height)/2
}

// === CIRCLE COLLISION ===

// CircleCollision checks collision between two circles with debug visualization
func (cs *CollisionSystem) CircleCollision(x1, y1, r1, x2, y2, r2 float32) bool {
	// Add debug visualization
	if cs.ShowDebugInfo {
		cs.addDebugCircle(x1, y1, r1, rl.Green)
		cs.addDebugCircle(x2, y2, r2, rl.Blue)
	}

	// Use optimized utility function
	return CheckCircleCollision(x1, y1, r1, x2, y2, r2)
}

// === POINT-IN-TRIANGLE COLLISION ===

// PointInTriangle checks if a point is inside a triangle using barycentric coordinates
// Algorithm: Computes barycentric coordinates (u, v, w) and checks if point is inside
func (cs *CollisionSystem) PointInTriangle(p, a, b, c Vector2) bool {
	// Vector from a to c and a to b
	v0x, v0y := c.X-a.X, c.Y-a.Y
	v1x, v1y := b.X-a.X, b.Y-a.Y
	v2x, v2y := p.X-a.X, p.Y-a.Y

	// Dot products
	dot00 := v0x*v0x + v0y*v0y
	dot01 := v0x*v1x + v0y*v1y
	dot02 := v0x*v2x + v0y*v2y
	dot11 := v1x*v1x + v1y*v1y
	dot12 := v1x*v2x + v1y*v2y

	// Compute barycentric coordinates
	denominator := dot00*dot11 - dot01*dot01
	if math.Abs(float64(denominator)) < 0.0001 {
		return false // Degenerate triangle
	}

	invDenom := 1.0 / denominator
	u := (dot11*dot02 - dot01*dot12) * invDenom
	v := (dot00*dot12 - dot01*dot02) * invDenom

	// Check if point is in triangle
	return (u >= 0) && (v >= 0) && (u+v <= 1)
}

// === GEOMETRIC TRANSFORMATIONS ===

// RotatePoint rotates a point around the origin by the given angle (in radians)
func (cs *CollisionSystem) RotatePoint(point Vector2, angle float32) Vector2 {
	cos := float32(math.Cos(float64(angle)))
	sin := float32(math.Sin(float64(angle)))
	return Vector2{
		X: point.X*cos - point.Y*sin,
		Y: point.X*sin + point.Y*cos,
	}
}

// GetWorldVertex transforms a local vertex to world coordinates
// Takes center position, rotation, and local vertex; returns world position
func (cs *CollisionSystem) GetWorldVertex(centerX, centerY, rotation float32, localVertex Vector2) Vector2 {
	rotated := cs.RotatePoint(localVertex, rotation)
	return Vector2{
		X: centerX + rotated.X,
		Y: centerY + rotated.Y,
	}
}

// === TRIANGLE-CIRCLE COLLISION ===

// TriangleCircleCollision checks collision between a rotated triangle and a circle
// Used for ship (triangle) vs asteroid (circle) collision detection
// Algorithm:
// 1. AABB pre-filtering for performance
// 2. Transform triangle vertices to world coordinates
// 3. Check if circle center is inside triangle
// 4. Check distance from circle center to triangle edges
func (cs *CollisionSystem) TriangleCircleCollision(centerX, centerY, rotation float32, vertices []Vector2, circleX, circleY, radius float32) bool {
	// First check bounding box for performance
	triangleBB := NewBoundingBox(centerX, centerY, 30, 30) // Approximate triangle size
	circleBB := NewBoundingBox(circleX, circleY, radius*2, radius*2)

	if !BoundingBoxCollision(triangleBB, circleBB) {
		return false
	}

	// Transform triangle vertices to world coordinates
	worldVertices := make([]Vector2, len(vertices))
	for i, vertex := range vertices {
		worldVertices[i] = cs.GetWorldVertex(centerX, centerY, rotation, vertex)
	}

	// Add debug visualization
	if cs.ShowDebugInfo {
		cs.addDebugTriangle(worldVertices[0], worldVertices[1], worldVertices[2], rl.Yellow)
		cs.addDebugCircle(circleX, circleY, radius, rl.Red)
	}

	// Check if circle center is inside triangle
	circlePoint := Vector2{X: circleX, Y: circleY}
	if len(worldVertices) >= 3 {
		if cs.PointInTriangle(circlePoint, worldVertices[0], worldVertices[1], worldVertices[2]) {
			return true
		}
	}

	// Check distance from circle center to triangle edges
	for i := 0; i < len(worldVertices); i++ {
		next := (i + 1) % len(worldVertices)
		if cs.DistancePointToLineSegment(circlePoint, worldVertices[i], worldVertices[next]) < radius {
			return true
		}
	}

	return false
}

// === POINT-TO-LINE-SEGMENT DISTANCE ===

// DistancePointToLineSegment calculates the shortest distance from a point to a line segment
// Algorithm: Projects point onto line, clamps to segment, calculates distance
func (cs *CollisionSystem) DistancePointToLineSegment(point, lineStart, lineEnd Vector2) float32 {
	dx := lineEnd.X - lineStart.X
	dy := lineEnd.Y - lineStart.Y

	if dx == 0 && dy == 0 {
		// Line segment is just a point
		dx = point.X - lineStart.X
		dy = point.Y - lineStart.Y
		return float32(math.Sqrt(float64(dx*dx + dy*dy)))
	}

	// Calculate parameter t (projection of point onto line)
	t := ((point.X-lineStart.X)*dx + (point.Y-lineStart.Y)*dy) / (dx*dx + dy*dy)

	var closestX, closestY float32
	if t < 0 {
		// Closest point is lineStart
		closestX, closestY = lineStart.X, lineStart.Y
	} else if t > 1 {
		// Closest point is lineEnd
		closestX, closestY = lineEnd.X, lineEnd.Y
	} else {
		// Closest point is on the line segment
		closestX = lineStart.X + t*dx
		closestY = lineStart.Y + t*dy
	}

	dx = point.X - closestX
	dy = point.Y - closestY
	return float32(math.Sqrt(float64(dx*dx + dy*dy)))
}

// === POLYGON COLLISION (SAT Algorithm) ===

// ConvexPolygonCollision checks collision between two convex polygons using SAT (Separating Axis Theorem)
// Algorithm:
// 1. Generate all potential separating axes (normals to edges)
// 2. Project both polygons onto each axis
// 3. If any axis separates the polygons, no collision
// 4. If no separating axis found, collision exists
func (cs *CollisionSystem) ConvexPolygonCollision(poly1Vertices, poly2Vertices []Vector2) bool {
	// Get all potential separating axes (normals to edges)
	axes := make([]Vector2, 0, len(poly1Vertices)+len(poly2Vertices))

	// Add normals from first polygon
	for i := 0; i < len(poly1Vertices); i++ {
		next := (i + 1) % len(poly1Vertices)
		edge := Vector2{
			X: poly1Vertices[next].X - poly1Vertices[i].X,
			Y: poly1Vertices[next].Y - poly1Vertices[i].Y,
		}
		// Normal is perpendicular to edge
		normal := Vector2{X: -edge.Y, Y: edge.X}
		axes = append(axes, cs.normalizeVector(normal))
	}

	// Add normals from second polygon
	for i := 0; i < len(poly2Vertices); i++ {
		next := (i + 1) % len(poly2Vertices)
		edge := Vector2{
			X: poly2Vertices[next].X - poly2Vertices[i].X,
			Y: poly2Vertices[next].Y - poly2Vertices[i].Y,
		}
		normal := Vector2{X: -edge.Y, Y: edge.X}
		axes = append(axes, cs.normalizeVector(normal))
	}

	// Test each axis
	for _, axis := range axes {
		if cs.separatingAxisExists(poly1Vertices, poly2Vertices, axis) {
			return false // Separating axis found, no collision
		}
	}

	return true // No separating axis found, collision exists
}

// normalizeVector normalizes a vector to unit length
func (cs *CollisionSystem) normalizeVector(v Vector2) Vector2 {
	length := float32(math.Sqrt(float64(v.X*v.X + v.Y*v.Y)))
	if length == 0 {
		return Vector2{X: 0, Y: 0}
	}
	return Vector2{X: v.X / length, Y: v.Y / length}
}

// separatingAxisExists checks if an axis separates two polygons
func (cs *CollisionSystem) separatingAxisExists(poly1, poly2 []Vector2, axis Vector2) bool {
	min1, max1 := cs.projectPolygon(poly1, axis)
	min2, max2 := cs.projectPolygon(poly2, axis)

	// Check if projections overlap
	return max1 < min2 || max2 < min1
}

// projectPolygon projects a polygon onto an axis and returns min/max values
func (cs *CollisionSystem) projectPolygon(vertices []Vector2, axis Vector2) (float32, float32) {
	if len(vertices) == 0 {
		return 0, 0
	}

	// Project first vertex
	dot := vertices[0].X*axis.X + vertices[0].Y*axis.Y
	min, max := dot, dot

	// Project remaining vertices
	for i := 1; i < len(vertices); i++ {
		dot = vertices[i].X*axis.X + vertices[i].Y*axis.Y
		if dot < min {
			min = dot
		}
		if dot > max {
			max = dot
		}
	}

	return min, max
}

// === POINT-IN-PROJECTED-POLYGON COLLISION ===

// PointInProjectedPolygon checks if a 2D point collides with a projected 3D asteroid
// This is the TIER 2 collision check for bullets
// Returns true if the point is inside the projected polygon
func (cs *CollisionSystem) PointInProjectedPolygon(pointX, pointY float32, vertices []Vector3, rotX, rotY, rotZ float32, asteroidX, asteroidY float32) bool {
	// Project 3D shape to 2D polygon
	polygon := GetProjectedPolygon(vertices, rotX, rotY, rotZ)

	if len(polygon) == 0 {
		return false
	}

	// Check if point is inside projected polygon
	point := Vector2{X: pointX, Y: pointY}
	return PointInPolygon(point, polygon, asteroidX, asteroidY)
}

// BulletAsteroidCollision checks collision between a bullet (point) and an asteroid using 2-tier detection
// TIER 1: Fast bounding circle check
// TIER 2: Precise projected polygon check
// Returns true if collision detected
func (cs *CollisionSystem) BulletAsteroidCollision(bulletX, bulletY float32, asteroidX, asteroidY, boundingRadius float32, vertices []Vector3, rotX, rotY, rotZ float32) bool {
	// Track statistics
	cs.tier1Checks++

	// TIER 1: Fast bounding circle check
	// Bullet is treated as a point (radius = 0 for simplicity, or use BulletRadius constant)
	if !CheckCircleCollision(bulletX, bulletY, BulletRadius, asteroidX, asteroidY, boundingRadius) {
		// Add debug visualization for TIER 1 miss
		if cs.ShowDebugInfo {
			cs.addDebugCircle(asteroidX, asteroidY, boundingRadius, DebugTier1MissColor)
		}
		return false
	}

	// TIER 2: Precise projected polygon check (if shape has vertices)
	if len(vertices) > 0 {
		cs.tier2Checks++

		// Project 3D shape to 2D polygon
		polygon := GetProjectedPolygon(vertices, rotX, rotY, rotZ)

		// Check if bullet point is inside projected polygon
		bulletPoint := Vector2{X: bulletX, Y: bulletY}
		hit := PointInPolygon(bulletPoint, polygon, asteroidX, asteroidY)

		// Add debug visualization for TIER 2
		if cs.ShowDebugInfo {
			if hit {
				cs.addDebugPolygon(polygon, asteroidX, asteroidY, DebugTier2HitColor) // Red = HIT
				cs.addDebugPoint(bulletX, bulletY, DebugPointColor)                   // Yellow = bullet point
			} else {
				cs.addDebugPolygon(polygon, asteroidX, asteroidY, DebugTier2MissColor)      // Green = TIER 2 miss
				cs.addDebugCircle(asteroidX, asteroidY, boundingRadius, DebugTier1HitColor) // Yellow = TIER 1 hit
			}
		}

		if hit {
			cs.collisionHits++
		}
		return hit
	}

	// If no vertices (sphere), TIER 1 is sufficient
	if cs.ShowDebugInfo {
		cs.addDebugCircle(asteroidX, asteroidY, boundingRadius, DebugTier2HitColor) // Red = sphere hit
	}
	cs.collisionHits++
	return true
}

// === SHIP-ASTEROID POLYGON COLLISION (SAT) ===

// ShipAsteroidCollisionSAT checks collision between ship (projected mesh) and an asteroid polygon
// Ship vertices are expected to already be in world coordinates (centered on ship position)
func (cs *CollisionSystem) ShipAsteroidCollisionSAT(shipX, shipY float32, shipVertices []Vector2, asteroidX, asteroidY, boundingRadius float32, asteroidVertices []Vector3, rotX, rotY, rotZ float32) bool {
	if len(shipVertices) < 3 {
		return false
	}
	// Track statistics
	cs.tier1Checks++

	// Pre-filter with AABB bounding boxes for performance
	shipBB := NewBoundingBox(shipX, shipY, 30, 30) // Approximate ship size (15 units front, 10 units back)
	asteroidBB := NewBoundingBox(asteroidX, asteroidY, boundingRadius*2, boundingRadius*2)

	if !BoundingBoxCollision(shipBB, asteroidBB) {
		if cs.ShowDebugInfo {
			cs.addDebugCircle(asteroidX, asteroidY, boundingRadius, DebugTier1MissColor)
		}
		return false
	}

	if len(shipVertices) < 3 {
		return false
	}
	shipWorldVertices := shipVertices

	// Get asteroid projected polygon in world coordinates
	asteroidPolygon := GetProjectedPolygon(asteroidVertices, rotX, rotY, rotZ)
	if len(asteroidPolygon) == 0 {
		// Fallback to circle collision for spheres
		return cs.CircleCollision(shipX, shipY, 8, asteroidX, asteroidY, boundingRadius)
	}

	// Transform asteroid polygon to world coordinates
	asteroidWorldVertices := make([]Vector2, len(asteroidPolygon))
	for i, vertex := range asteroidPolygon {
		asteroidWorldVertices[i] = Vector2{
			X: vertex.X + asteroidX,
			Y: vertex.Y + asteroidY,
		}
	}

	// Track SAT check
	cs.satChecks++

	// Use SAT for convex polygon collision
	collision := cs.ConvexPolygonCollision(shipWorldVertices, asteroidWorldVertices)

	// Add debug visualization with collision result
	if cs.ShowDebugInfo {
		if len(shipWorldVertices) >= 3 {
			relative := make([]Vector2, len(shipWorldVertices))
			for i, v := range shipWorldVertices {
				relative[i] = Vector2{X: v.X - shipX, Y: v.Y - shipY}
			}
			cs.addDebugPolygon(relative, shipX, shipY, DebugShipColor)
		}

		// Asteroid polygon colored by result
		if collision {
			cs.addDebugPolygon(asteroidPolygon, asteroidX, asteroidY, DebugTier2HitColor) // Red = collision
		} else {
			cs.addDebugPolygon(asteroidPolygon, asteroidX, asteroidY, DebugTier2MissColor) // Green = no collision
		}
	}

	if collision {
		cs.collisionHits++
	}

	return collision
}

// === DEBUG VISUALIZATION ===

// ToggleDebugMode toggles debug visualization on/off
func (cs *CollisionSystem) ToggleDebugMode() {
	cs.ShowDebugInfo = !cs.ShowDebugInfo
}

// addDebugCircle adds a circle to debug visualization
func (cs *CollisionSystem) addDebugCircle(x, y, radius float32, color rl.Color) {
	cs.debugCollisions = append(cs.debugCollisions, DebugCollision{
		Type:     "circle",
		Position: rl.Vector2{X: x, Y: y},
		Size:     radius,
		Color:    color,
		Active:   true,
	})
}

// addDebugTriangle adds a triangle to debug visualization
func (cs *CollisionSystem) addDebugTriangle(a, b, c Vector2, color rl.Color) {
	// Store triangle vertices for debug rendering
	cs.debugCollisions = append(cs.debugCollisions, DebugCollision{
		Type: "triangle",
		Vertices: []rl.Vector2{
			{X: a.X, Y: a.Y},
			{X: b.X, Y: b.Y},
			{X: c.X, Y: c.Y},
		},
		Color:  color,
		Active: true,
	})
}

// addDebugPolygon adds a polygon to debug visualization
func (cs *CollisionSystem) addDebugPolygon(polygon []Vector2, offsetX, offsetY float32, color rl.Color) {
	if len(polygon) == 0 {
		return
	}

	// Convert to world coordinates and store
	vertices := make([]rl.Vector2, len(polygon))
	for i, v := range polygon {
		vertices[i] = rl.Vector2{X: v.X + offsetX, Y: v.Y + offsetY}
	}

	cs.debugCollisions = append(cs.debugCollisions, DebugCollision{
		Type:     "polygon",
		Vertices: vertices,
		Color:    color,
		Active:   true,
	})
}

// addDebugPoint adds a point to debug visualization
func (cs *CollisionSystem) addDebugPoint(x, y float32, color rl.Color) {
	cs.debugCollisions = append(cs.debugCollisions, DebugCollision{
		Type:     "point",
		Position: rl.Vector2{X: x, Y: y},
		Size:     3, // Point radius
		Color:    color,
		Active:   true,
	})
}

// ClearDebugInfo clears all debug visualization data
// Call this each frame before collision checks
func (cs *CollisionSystem) ClearDebugInfo() {
	cs.debugCollisions = cs.debugCollisions[:0]
	cs.tier1Checks = 0
	cs.tier2Checks = 0
	cs.satChecks = 0
	cs.collisionHits = 0
}

// GetDebugStats returns debug statistics for display
func (cs *CollisionSystem) GetDebugStats() (tier1, tier2, sat, hits int) {
	return cs.tier1Checks, cs.tier2Checks, cs.satChecks, cs.collisionHits
}

// DrawDebugInfo renders collision debug visualization
// Call this during rendering phase
func (cs *CollisionSystem) DrawDebugInfo(cameraX, cameraY float32, screenWidth, screenHeight int) {
	if !cs.ShowDebugInfo {
		return
	}

	for _, debug := range cs.debugCollisions {
		if !debug.Active {
			continue
		}

		switch debug.Type {
		case "circle":
			// Convert world coordinates to screen coordinates
			screenX, screenY := WorldToScreen(debug.Position.X, debug.Position.Y, cameraX, cameraY, screenWidth, screenHeight)

			// Only draw if on screen
			if IsOnScreen(screenX, screenY, screenWidth, screenHeight, 50) {
				rl.DrawCircleLines(int32(screenX), int32(screenY), debug.Size, debug.Color)
			}

		case "triangle":
			if len(debug.Vertices) >= 3 {
				// Convert all vertices to screen coordinates
				v0x, v0y := WorldToScreen(debug.Vertices[0].X, debug.Vertices[0].Y, cameraX, cameraY, screenWidth, screenHeight)
				v1x, v1y := WorldToScreen(debug.Vertices[1].X, debug.Vertices[1].Y, cameraX, cameraY, screenWidth, screenHeight)
				v2x, v2y := WorldToScreen(debug.Vertices[2].X, debug.Vertices[2].Y, cameraX, cameraY, screenWidth, screenHeight)

				// Draw triangle outline
				rl.DrawTriangleLines(
					rl.Vector2{X: v0x, Y: v0y},
					rl.Vector2{X: v1x, Y: v1y},
					rl.Vector2{X: v2x, Y: v2y},
					debug.Color,
				)
			}

		case "polygon":
			if len(debug.Vertices) >= 3 {
				// Convert all vertices to screen coordinates and draw edges
				screenVerts := make([]rl.Vector2, len(debug.Vertices))
				for i, v := range debug.Vertices {
					screenVerts[i].X, screenVerts[i].Y = WorldToScreen(v.X, v.Y, cameraX, cameraY, screenWidth, screenHeight)
				}

				// Draw polygon edges
				for i := 0; i < len(screenVerts); i++ {
					j := (i + 1) % len(screenVerts)
					rl.DrawLineEx(screenVerts[i], screenVerts[j], 2.0, debug.Color)
				}

				// Draw vertices as small circles
				for _, v := range screenVerts {
					rl.DrawCircle(int32(v.X), int32(v.Y), 2, debug.Color)
				}
			}

		case "point":
			// Convert world coordinates to screen coordinates
			screenX, screenY := WorldToScreen(debug.Position.X, debug.Position.Y, cameraX, cameraY, screenWidth, screenHeight)

			// Only draw if on screen
			if IsOnScreen(screenX, screenY, screenWidth, screenHeight, 10) {
				rl.DrawCircle(int32(screenX), int32(screenY), debug.Size, debug.Color)
				rl.DrawCircleLines(int32(screenX), int32(screenY), debug.Size+1, rl.White)
			}
		}
	}
}
