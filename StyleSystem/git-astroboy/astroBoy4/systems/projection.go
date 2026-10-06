// AstroBoy4 Systems - 3D Projection and Collision Utilities
// Provides 3D to 2D projection, convex hull, and polygon collision detection

package systems

import (
	"astroboy4/gameobjects"
	"math"
	"sort"
)

// RotateVector3 applies 3D rotation to a vector using Euler angles (radians)
// Rotation order: X -> Y -> Z (matches Raylib rendering order)
func RotateVector3(v gameobjects.Vector3, rotX, rotY, rotZ float32) gameobjects.Vector3 {
	// Rotation around X axis (inverted to match screen space)
	cosX := float32(math.Cos(float64(-rotX)))
	sinX := float32(math.Sin(float64(-rotX)))
	y1 := v.Y*cosX - v.Z*sinX
	z1 := v.Y*sinX + v.Z*cosX

	// Rotation around Y axis (inverted to match screen space)
	cosY := float32(math.Cos(float64(-rotY)))
	sinY := float32(math.Sin(float64(-rotY)))
	x2 := v.X*cosY + z1*sinY
	z2 := -v.X*sinY + z1*cosY

	// Rotation around Z axis
	cosZ := float32(math.Cos(float64(rotZ)))
	sinZ := float32(math.Sin(float64(rotZ)))
	x3 := x2*cosZ - y1*sinZ
	y3 := x2*sinZ + y1*cosZ

	return gameobjects.Vector3{X: x3, Y: y3, Z: z2}
}

// ProjectToXY projects 3D vertices to 2D by dropping Z coordinate
// Top-down view: looking from +Y down toward origin
// Screen space: X=right, Y=down, so we use X and Z
func ProjectToXY(vertices []gameobjects.Vector3) []Vector2 {
	result := make([]Vector2, len(vertices))
	for i, v := range vertices {
		// Top-down view: X maps to screen X, Z maps to screen Y
		result[i] = Vector2{X: v.X, Y: v.Z}
	}
	return result
}

// ConvexHull2D computes the convex hull of 2D points using Graham scan algorithm
// Returns vertices in counter-clockwise order
func ConvexHull2D(points []Vector2) []Vector2 {
	if len(points) < 3 {
		return points
	}

	// Make a copy to avoid modifying input
	pts := make([]Vector2, len(points))
	copy(pts, points)

	// Find the lowest point (and leftmost if tied)
	lowest := 0
	for i := 1; i < len(pts); i++ {
		if pts[i].Y < pts[lowest].Y || (pts[i].Y == pts[lowest].Y && pts[i].X < pts[lowest].X) {
			lowest = i
		}
	}

	// Swap lowest point to beginning
	pts[0], pts[lowest] = pts[lowest], pts[0]
	pivot := pts[0]

	// Sort remaining points by polar angle with respect to pivot
	sort.Slice(pts[1:], func(i, j int) bool {
		i++ // Adjust indices since we're sorting pts[1:]
		j++

		// Calculate cross product to determine angle
		cross := crossProduct2D(pivot, pts[i], pts[j])
		if cross == 0 {
			// Collinear points - sort by distance
			di := distanceSquared(pivot, pts[i])
			dj := distanceSquared(pivot, pts[j])
			return di < dj
		}
		return cross > 0 // Counter-clockwise
	})

	// Build convex hull using Graham scan
	hull := []Vector2{pts[0], pts[1]}

	for i := 2; i < len(pts); i++ {
		// Remove points that make clockwise turn
		for len(hull) >= 2 {
			a := hull[len(hull)-2]
			b := hull[len(hull)-1]
			c := pts[i]

			if crossProduct2D(a, b, c) <= 0 {
				// Clockwise or collinear - remove middle point
				hull = hull[:len(hull)-1]
			} else {
				break
			}
		}
		hull = append(hull, pts[i])
	}

	return hull
}

// crossProduct2D calculates cross product for three 2D points
// Returns positive if counter-clockwise, negative if clockwise, 0 if collinear
func crossProduct2D(a, b, c Vector2) float32 {
	return (b.X-a.X)*(c.Y-a.Y) - (b.Y-a.Y)*(c.X-a.X)
}

// distanceSquared calculates squared distance between two 2D points
func distanceSquared(a, b Vector2) float32 {
	dx := b.X - a.X
	dy := b.Y - a.Y
	return dx*dx + dy*dy
}

// PointInPolygon checks if a point is inside a polygon using ray casting algorithm
// offsetX, offsetY translate the polygon to world coordinates
func PointInPolygon(point Vector2, polygon []Vector2, offsetX, offsetY float32) bool {
	if len(polygon) < 3 {
		return false
	}

	// Ray casting algorithm: count intersections with polygon edges
	intersections := 0

	for i := 0; i < len(polygon); i++ {
		j := (i + 1) % len(polygon)

		// Get polygon edge vertices (in world coordinates)
		v1 := Vector2{X: polygon[i].X + offsetX, Y: polygon[i].Y + offsetY}
		v2 := Vector2{X: polygon[j].X + offsetX, Y: polygon[j].Y + offsetY}

		// Check if ray from point crosses this edge
		if ((v1.Y > point.Y) != (v2.Y > point.Y)) &&
			(point.X < (v2.X-v1.X)*(point.Y-v1.Y)/(v2.Y-v1.Y)+v1.X) {
			intersections++
		}
	}

	// Odd number of intersections means point is inside
	return intersections%2 == 1
}

// GetProjectedPolygon projects 3D shape vertices to 2D polygon for collision detection
// Returns convex hull of projected vertices
func GetProjectedPolygon(vertices []gameobjects.Vector3, rotX, rotY, rotZ float32) []Vector2 {
	if len(vertices) == 0 {
		return []Vector2{}
	}

	// Step 1: Rotate vertices in 3D space
	rotated := make([]gameobjects.Vector3, len(vertices))
	for i, v := range vertices {
		rotated[i] = RotateVector3(v, rotX, rotY, rotZ)
	}

	// Step 2: Project to 2D (drop Z coordinate)
	projected := ProjectToXY(rotated)

	// Step 3: Calculate convex hull to get outer boundary
	hull := ConvexHull2D(projected)

	return hull
}

// Edge represents a line segment between two vertex indices
type Edge struct {
	V0, V1 int
}

// GetVisibleEdges returns the edges of visible faces after rotation
// Uses backface culling: only faces with normals pointing toward camera (+Y) are visible
func GetVisibleEdges(vertices []gameobjects.Vector3, faces []gameobjects.Face, rotX, rotY, rotZ float32) []Edge {
	if len(vertices) == 0 || len(faces) == 0 {
		return []Edge{}
	}

	// Step 1: Rotate vertices in 3D space
	rotated := make([]gameobjects.Vector3, len(vertices))
	for i, v := range vertices {
		rotated[i] = RotateVector3(v, rotX, rotY, rotZ)
	}

	// Step 2: Collect edges from visible faces using backface culling
	edgeMap := make(map[Edge]bool) // Use map to deduplicate edges

	for _, face := range faces {
		// Get face vertices
		v0 := rotated[face.V0]
		v1 := rotated[face.V1]
		v2 := rotated[face.V2]

		// Calculate face normal using cross product
		// edge1 = v1 - v0
		edge1X := v1.X - v0.X
		edge1Z := v1.Z - v0.Z

		// edge2 = v2 - v0
		edge2X := v2.X - v0.X
		edge2Z := v2.Z - v0.Z

		// normal = edge1 × edge2
		// We only need normalY component for backface culling
		// normalY = edge1Z * edge2X - edge1X * edge2Z
		normalY := edge1Z*edge2X - edge1X*edge2Z

		// Backface culling: face is visible if normal.Y > 0 (pointing toward camera)
		// Camera is at +Y looking down toward origin
		if normalY > 0 {
			// Add edges from this face (with deduplication)
			addEdge(edgeMap, face.V0, face.V1)
			addEdge(edgeMap, face.V1, face.V2)
			addEdge(edgeMap, face.V2, face.V0)
		}
	}

	// Convert map to slice
	edges := make([]Edge, 0, len(edgeMap))
	for edge := range edgeMap {
		edges = append(edges, edge)
	}

	return edges
}

// addEdge adds an edge to the map with normalized order (smaller index first)
func addEdge(edgeMap map[Edge]bool, v0, v1 int) {
	// Normalize edge order to avoid duplicates
	if v0 > v1 {
		v0, v1 = v1, v0
	}
	edgeMap[Edge{V0: v0, V1: v1}] = true
}
