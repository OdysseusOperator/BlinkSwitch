// AstroBoy4 Collision Test Experiment
// Pure 2D rendering using projected 3D vertices
// No 3D camera - everything in 2D screen space

package main

import (
	"astroboy4/gameobjects"
	"astroboy4/systems"
	"fmt"
	rl "github.com/gen2brain/raylib-go/raylib"
	"math"
	"time"
)

const (
	screenWidth  = 1280
	screenHeight = 720
	worldScale   = 3.0 // Pixels per world unit
)

type GameState struct {
	asteroids      []*gameobjects.Asteroid
	currentIndex   int
	mousePos       rl.Vector2
	tier1Collision bool
	tier2Collision bool
	tier1TimeUs    float64
	tier2TimeUs    float64
	showTier2      bool
	autoRotate     bool
}

func main() {
	rl.InitWindow(screenWidth, screenHeight, "AstroBoy4 - Pure 2D Projection Test")
	rl.SetTargetFPS(60)

	// Create test asteroids
	asteroids := []*gameobjects.Asteroid{
		{X: 0, Y: 0, Size: 50.0, ShapeRenderer: gameobjects.NewSphereShape()},
		{X: 0, Y: 0, Size: 50.0, ShapeRenderer: gameobjects.NewCubeShape()},
		{X: 0, Y: 0, Size: 50.0, ShapeRenderer: gameobjects.NewPyramidShape()},
		{X: 0, Y: 0, Size: 50.0, ShapeRenderer: gameobjects.NewOctahedronShape()},
	}

	state := GameState{
		asteroids:    asteroids,
		currentIndex: 0,
		showTier2:    true,
		autoRotate:   false,
	}

	for !rl.WindowShouldClose() {
		handleInput(&state)
		updateCollision(&state)

		rl.BeginDrawing()
		rl.ClearBackground(rl.NewColor(5, 5, 15, 255))

		drawGrid()
		drawAsteroid2D(&state)
		drawCollisionShapes(&state)
		drawUI(&state)

		rl.EndDrawing()
	}

	rl.CloseWindow()
}

func handleInput(state *GameState) {
	asteroid := state.asteroids[state.currentIndex]

	// SPACE to switch asteroids
	if rl.IsKeyPressed(rl.KeySpace) {
		state.currentIndex++
		if state.currentIndex >= len(state.asteroids) {
			state.currentIndex = 0
		}
	}

	// Arrow keys for rotation
	rotSpeed := float32(2.0 * rl.GetFrameTime())
	if rl.IsKeyDown(rl.KeyLeft) {
		asteroid.RotationY -= rotSpeed
	}
	if rl.IsKeyDown(rl.KeyRight) {
		asteroid.RotationY += rotSpeed
	}
	if rl.IsKeyDown(rl.KeyUp) {
		asteroid.RotationX -= rotSpeed
	}
	if rl.IsKeyDown(rl.KeyDown) {
		asteroid.RotationX += rotSpeed
	}

	// W/S for Z rotation
	if rl.IsKeyDown(rl.KeyW) {
		asteroid.RotationZ -= rotSpeed
	}
	if rl.IsKeyDown(rl.KeyS) {
		asteroid.RotationZ += rotSpeed
	}

	// R to reset
	if rl.IsKeyPressed(rl.KeyR) {
		asteroid.RotationX = 0
		asteroid.RotationY = 0
		asteroid.RotationZ = 0
	}

	// +/- for size
	if rl.IsKeyPressed(rl.KeyEqual) || rl.IsKeyPressed(rl.KeyKpAdd) {
		asteroid.Size += 10.0
		if asteroid.Size > 100.0 {
			asteroid.Size = 100.0
		}
	}
	if rl.IsKeyPressed(rl.KeyMinus) || rl.IsKeyPressed(rl.KeyKpSubtract) {
		asteroid.Size -= 10.0
		if asteroid.Size < 20.0 {
			asteroid.Size = 20.0
		}
	}

	// T to toggle Tier 2
	if rl.IsKeyPressed(rl.KeyT) {
		state.showTier2 = !state.showTier2
	}

	// Q for auto-rotate
	if rl.IsKeyPressed(rl.KeyQ) {
		state.autoRotate = !state.autoRotate
	}

	if state.autoRotate {
		asteroid.RotationZ += 0.5 * rl.GetFrameTime()
		asteroid.RotationX += 0.3 * rl.GetFrameTime()
		asteroid.RotationY += 0.2 * rl.GetFrameTime()
	}

	state.mousePos = rl.GetMousePosition()
}

func updateCollision(state *GameState) {
	asteroid := state.asteroids[state.currentIndex]

	// Convert mouse screen position to world coordinates
	centerX := float32(screenWidth) / 2
	centerY := float32(screenHeight) / 2
	mouseWorldX := (state.mousePos.X - centerX) / worldScale
	mouseWorldY := (state.mousePos.Y - centerY) / worldScale

	// TIER 1: Bounding circle
	start := time.Now()
	boundingRadius := asteroid.ShapeRenderer.GetBoundingRadius(asteroid.Size)
	state.tier1Collision = systems.CheckCircleCollision(
		mouseWorldX, mouseWorldY, 0.5,
		asteroid.X, asteroid.Y, boundingRadius)
	state.tier1TimeUs = float64(time.Since(start).Microseconds())

	// TIER 2: Projected polygon
	state.tier2Collision = false
	if state.tier1Collision && state.showTier2 {
		start = time.Now()
		vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)
		if len(vertices) > 0 {
			polygon := systems.GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)
			mousePoint := systems.Vector2{X: mouseWorldX, Y: mouseWorldY}
			state.tier2Collision = systems.PointInPolygon(mousePoint, polygon, asteroid.X, asteroid.Y)
		} else {
			state.tier2Collision = state.tier1Collision
		}
		state.tier2TimeUs = float64(time.Since(start).Microseconds())
	}
}

func worldToScreen(worldX, worldY float32) (float32, float32) {
	centerX := float32(screenWidth) / 2
	centerY := float32(screenHeight) / 2
	return centerX + worldX*worldScale, centerY + worldY*worldScale
}

func drawGrid() {
	centerX := float32(screenWidth) / 2
	centerY := float32(screenHeight) / 2

	// Grid lines every 50 world units
	gridSpacing := 50.0 * worldScale
	gridColor := rl.NewColor(30, 30, 50, 255)

	// Vertical lines
	for x := centerX; x < float32(screenWidth); x += float32(gridSpacing) {
		rl.DrawLine(int32(x), 0, int32(x), screenHeight, gridColor)
	}
	for x := centerX; x > 0; x -= float32(gridSpacing) {
		rl.DrawLine(int32(x), 0, int32(x), screenHeight, gridColor)
	}

	// Horizontal lines
	for y := centerY; y < float32(screenHeight); y += float32(gridSpacing) {
		rl.DrawLine(0, int32(y), screenWidth, int32(y), gridColor)
	}
	for y := centerY; y > 0; y -= float32(gridSpacing) {
		rl.DrawLine(0, int32(y), screenWidth, int32(y), gridColor)
	}

	// Axes
	rl.DrawLine(int32(centerX), 0, int32(centerX), screenHeight, rl.NewColor(50, 50, 100, 255))
	rl.DrawLine(0, int32(centerY), screenWidth, int32(centerY), rl.NewColor(50, 50, 100, 255))

	// Origin
	rl.DrawCircle(int32(centerX), int32(centerY), 4, rl.White)
}

func drawAsteroid2D(state *GameState) {
	asteroid := state.asteroids[state.currentIndex]

	// Get projected polygon (same as used for collision)
	vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)
	if len(vertices) == 0 {
		// Sphere - draw as circle
		centerX, centerY := worldToScreen(asteroid.X, asteroid.Y)
		radius := asteroid.Size * worldScale
		rl.DrawCircle(int32(centerX), int32(centerY), radius, rl.NewColor(150, 150, 150, 255))
		rl.DrawCircleLines(int32(centerX), int32(centerY), radius, rl.Black)
		return
	}

	polygon := systems.GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

	// Draw filled polygon (grey silhouette)
	if len(polygon) >= 3 {
		// Triangle fan from first vertex
		for i := 1; i < len(polygon)-1; i++ {
			x0, y0 := worldToScreen(polygon[0].X+asteroid.X, polygon[0].Y+asteroid.Y)
			x1, y1 := worldToScreen(polygon[i].X+asteroid.X, polygon[i].Y+asteroid.Y)
			x2, y2 := worldToScreen(polygon[i+1].X+asteroid.X, polygon[i+1].Y+asteroid.Y)

			// Draw both winding orders to ensure visibility
			rl.DrawTriangle(
				rl.Vector2{X: x0, Y: y0},
				rl.Vector2{X: x1, Y: y1},
				rl.Vector2{X: x2, Y: y2},
				rl.NewColor(150, 150, 150, 255))
			rl.DrawTriangle(
				rl.Vector2{X: x0, Y: y0},
				rl.Vector2{X: x2, Y: y2},
				rl.Vector2{X: x1, Y: y1},
				rl.NewColor(150, 150, 150, 255))
		}
	}

	// Draw visible edges (shows 3D structure)
	faces := asteroid.ShapeRenderer.GetFaces()
	if len(faces) > 0 {
		edges := systems.GetVisibleEdges(vertices, faces, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

		// Rotate and project vertices for edge drawing
		rotatedVerts := make([]systems.Vector2, len(vertices))
		for i, v := range vertices {
			rotated := systems.RotateVector3(v, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)
			rotatedVerts[i] = systems.Vector2{X: rotated.X, Y: rotated.Z}
		}

		// Draw each visible edge
		for _, edge := range edges {
			v0 := rotatedVerts[edge.V0]
			v1 := rotatedVerts[edge.V1]

			x1, y1 := worldToScreen(v0.X+asteroid.X, v0.Y+asteroid.Y)
			x2, y2 := worldToScreen(v1.X+asteroid.X, v1.Y+asteroid.Y)

			rl.DrawLineEx(rl.Vector2{X: x1, Y: y1}, rl.Vector2{X: x2, Y: y2}, 2.0, rl.Black)
		}
	}
}

func drawCollisionShapes(state *GameState) {
	asteroid := state.asteroids[state.currentIndex]
	centerX, centerY := worldToScreen(asteroid.X, asteroid.Y)

	// TIER 1: Bounding circle
	boundingRadius := asteroid.ShapeRenderer.GetBoundingRadius(asteroid.Size)
	screenRadius := boundingRadius * worldScale

	tier1Color := rl.Blue
	if state.tier1Collision {
		tier1Color = rl.Yellow
	}
	rl.DrawCircleLines(int32(centerX), int32(centerY), screenRadius, tier1Color)

	// TIER 2: Projected polygon overlay
	if state.showTier2 {
		vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)
		if len(vertices) > 0 {
			polygon := systems.GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

			// Draw vertices
			for _, v := range polygon {
				vx, vy := worldToScreen(v.X+asteroid.X, v.Y+asteroid.Y)
				rl.DrawCircle(int32(vx), int32(vy), 4, rl.Yellow)
			}

			// Draw polygon edges
			tier2Color := rl.Green
			if state.tier2Collision {
				tier2Color = rl.Red
			}

			for i := 0; i < len(polygon); i++ {
				j := (i + 1) % len(polygon)
				x1, y1 := worldToScreen(polygon[i].X+asteroid.X, polygon[i].Y+asteroid.Y)
				x2, y2 := worldToScreen(polygon[j].X+asteroid.X, polygon[j].Y+asteroid.Y)
				rl.DrawLineEx(rl.Vector2{X: x1, Y: y1}, rl.Vector2{X: x2, Y: y2}, 3.0, tier2Color)
			}
		}
	}

	// Draw mouse cursor
	rl.DrawCircle(int32(state.mousePos.X), int32(state.mousePos.Y), 6, rl.White)
	rl.DrawCircleLines(int32(state.mousePos.X), int32(state.mousePos.Y), 7, rl.Black)

	// Draw asteroid center
	rl.DrawCircle(int32(centerX), int32(centerY), 5, rl.Red)
}

func drawUI(state *GameState) {
	asteroid := state.asteroids[state.currentIndex]

	// Top panel
	rl.DrawRectangle(0, 0, screenWidth, 200, rl.NewColor(0, 0, 0, 200))

	rl.DrawText("PURE 2D PROJECTION - NO 3D CAMERA", 20, 20, 24, rl.White)

	// Asteroid info
	rl.DrawText(fmt.Sprintf("Asteroid: %s (SPACE)", asteroid.ShapeRenderer.GetName()), 20, 50, 18, rl.White)
	rl.DrawText(fmt.Sprintf("Size: %.1f world units", asteroid.Size), 20, 72, 16, rl.Gray)

	// Collision status
	y := int32(100)
	if state.tier1Collision {
		rl.DrawText("TIER 1: HIT", 20, y, 22, rl.Yellow)
	} else {
		rl.DrawText("TIER 1: MISS", 20, y, 22, rl.Blue)
	}

	vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)
	if state.showTier2 && len(vertices) > 0 {
		y += 28
		if state.tier2Collision {
			rl.DrawText("TIER 2: HIT", 20, y, 22, rl.Red)
		} else if state.tier1Collision {
			rl.DrawText("TIER 2: MISS", 20, y, 22, rl.Green)
		} else {
			rl.DrawText("TIER 2: (skipped)", 20, y, 18, rl.Gray)
		}
	} else if len(vertices) == 0 {
		y += 28
		rl.DrawText("TIER 2: N/A (sphere)", 20, y, 16, rl.Gray)
	}

	// Performance
	rl.DrawText(fmt.Sprintf("T1: %.2fµs | T2: %.2fµs", state.tier1TimeUs, state.tier2TimeUs),
		20, 160, 16, rl.Gray)

	// Rotation
	rl.DrawText(fmt.Sprintf("Rot: X=%.1f° Y=%.1f° Z=%.1f°",
		asteroid.RotationX*180/math.Pi, asteroid.RotationY*180/math.Pi, asteroid.RotationZ*180/math.Pi),
		20, 180, 14, rl.Gray)

	// Bottom panel
	y = int32(screenHeight - 140)
	rl.DrawRectangle(0, y, screenWidth, 140, rl.NewColor(0, 0, 0, 200))

	rl.DrawText("CONTROLS:", 20, y+10, 18, rl.White)
	rl.DrawText("SPACE: Switch | ← → ↑ ↓: Rotate X/Y | W S: Rotate Z", 20, y+32, 14, rl.Gray)
	rl.DrawText("+/-: Size | R: Reset | T: Toggle Tier 2 | Q: Auto-rotate", 20, y+50, 14, rl.Gray)

	rl.DrawText("LEGEND:", 20, y+75, 16, rl.White)
	rl.DrawRectangle(20, y+95, 15, 15, rl.NewColor(150, 150, 150, 255))
	rl.DrawText("Grey: Projected Shape", 40, y+95, 12, rl.Gray)
	rl.DrawCircle(200, y+102, 4, rl.Blue)
	rl.DrawText("Blue: T1 Circle", 210, y+95, 12, rl.Blue)
	rl.DrawCircle(320, y+102, 4, rl.Green)
	rl.DrawText("Green: T2 Polygon", 330, y+95, 12, rl.Green)
	rl.DrawCircle(470, y+102, 4, rl.Yellow)
	rl.DrawText("Yellow: Vertices", 480, y+95, 12, rl.Yellow)

	rl.DrawText("Grey shape = what you see in game | Collision overlays should match exactly", 20, y+115, 12, rl.White)
}
