// AstroBoy4 - Simple Asteroids Game with Clay UI and 3D Rotating Triangle Asteroids
package main

import (
	"fmt"
	"math"
	"unsafe"

	"astroboy4/gameobjects"
	"astroboy4/systems"
	"astroboy4/systems/audio"
	"astroboy4/systems/ui"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

// Game state enum
type GameState int

const (
	StateMenu GameState = iota
	StatePlaying
	StatePaused // Game paused
	StateGameOver
	StateMothership // Docked at mothership
	StateShop       // In upgrade shop
	StateSettings   // Settings menu
)

// Asteroid type alias from gameobjects package
type Asteroid = gameobjects.Asteroid

// Ship type alias - using ShipPhysics from systems package
type Ship = systems.ShipPhysics

// Bullet represents a projectile
type Bullet struct {
	X, Y     float32
	VX, VY   float32
	Lifetime float32
}

// Game holds all game state
type Game struct {
	state            GameState
	ship             *Ship
	asteroidManager  *systems.AsteroidManager
	bullets          []systems.Bullet
	score            int
	credits          int // Currency for buying upgrades
	customFont       rl.Font
	radarSystem      *systems.RadarSystem
	mothershipSystem *systems.MothershipSystem
	audioManager     *audio.AudioManager
	collisionSystem  *systems.CollisionSystem
	shopSystem       *systems.ShopSystem
	settingsManager  *systems.SettingsManager

	// UI systems
	buttonManager *ui.ButtonManager
	menuRenderer  *ui.MenuRenderer

	// Pause system - store ship velocity when pausing/shopping/docking
	pausedShipVX float32
	pausedShipVY float32
}

var (
	game *Game
)

// Clay error handler
func errorHandler(errorData clay.ErrorData) {
	fmt.Printf("Clay Error: %s\n", errorData.ErrorText)
}

// Clay text measurement function
func measureTextFunction(text clay.StringSlice, config *clay.TextElementConfig, userData unsafe.Pointer) clay.Dimensions {
	textStr := text.String()
	font := game.customFont
	if userData != nil {
		font = *(*rl.Font)(userData)
	}
	textSize := rl.MeasureTextEx(font, textStr, float32(config.FontSize), 1.0)
	return clay.Dimensions{Width: textSize.X, Height: textSize.Y}
}

// Clay renderer for Raylib
func clayRaylibRender(renderCommands clay.RenderCommandArray) {
	for i := int32(0); i < renderCommands.Length; i++ {
		renderCommand := clay.RenderCommandArray_Get(&renderCommands, i)

		switch renderCommand.CommandType {
		case clay.RENDER_COMMAND_TYPE_RECTANGLE:
			boundingBox := renderCommand.BoundingBox
			rectData := &renderCommand.RenderData.Rectangle

			rl.DrawRectangle(
				int32(boundingBox.X),
				int32(boundingBox.Y),
				int32(boundingBox.Width),
				int32(boundingBox.Height),
				rl.Color{
					R: uint8(rectData.BackgroundColor.R),
					G: uint8(rectData.BackgroundColor.G),
					B: uint8(rectData.BackgroundColor.B),
					A: uint8(rectData.BackgroundColor.A),
				},
			)

		case clay.RENDER_COMMAND_TYPE_TEXT:
			boundingBox := renderCommand.BoundingBox
			textData := &renderCommand.RenderData.Text
			textStr := textData.StringContents.String()

			rl.DrawTextEx(
				game.customFont,
				textStr,
				rl.Vector2{X: boundingBox.X, Y: boundingBox.Y},
				float32(textData.FontSize),
				1.0,
				rl.Color{
					R: uint8(textData.TextColor.R),
					G: uint8(textData.TextColor.G),
					B: uint8(textData.TextColor.B),
					A: uint8(textData.TextColor.A),
				},
			)
		}
	}
}

// Initialize game
func initGame() {
	collisionSystem := systems.NewCollisionSystem()
	asteroidManager := systems.NewAsteroidManager()

	// Wire up collision system to asteroid manager for debug visualization
	asteroidManager.SetCollisionSystem(collisionSystem)

	// Initialize UI systems
	buttonManager := ui.NewButtonManager()
	menuRenderer := ui.NewMenuRenderer(buttonManager)

	game = &Game{
		state:            StateMenu,
		asteroidManager:  asteroidManager,
		bullets:          make([]systems.Bullet, 0),
		score:            0,
		credits:          0, // Start with no credits
		radarSystem:      systems.NewRadarSystem(),
		mothershipSystem: systems.NewMothershipSystem(200, 200, 45), // Position (200,200), radius 45
		collisionSystem:  collisionSystem,
		shopSystem:       systems.NewShopSystem(),
		settingsManager:  systems.NewSettingsManager(),
		buttonManager:    buttonManager,
		menuRenderer:     menuRenderer,
	}

	// Initialize ship at center
	game.ship = systems.NewShipPhysics(0, 0)
}

// Start new game
func startGame() {
	game.state = StatePlaying
	game.ship.SetPosition(0, 0)
	game.ship.SetVelocity(0, 0)
	game.ship.Rotation = -math.Pi / 2
	game.ship.WeaponCooldown = 0
	game.asteroidManager.ClearAsteroids()
	game.bullets = make([]systems.Bullet, 0)
	game.score = 0
	game.credits = 100 // Start with some credits for testing

	// Spawn initial asteroids just outside the visible window
	shipX, shipY := game.ship.GetPosition()
	game.asteroidManager.SpawnInitialAsteroids(shipX, shipY, 12)
}

// Update game logic
func updateGame(deltaTime float32) {
	// Handle pause/resume with ESC key
	if game.state == StatePlaying && rl.IsKeyPressed(rl.KeyEscape) {
		// Pause the game and store ship velocity
		game.pausedShipVX, game.pausedShipVY = game.ship.GetVelocity()
		game.state = StatePaused
		// Stop thruster sound
		if game.audioManager != nil {
			game.audioManager.StopThruster()
		}
		return
	}

	if game.state == StatePaused && (rl.IsKeyPressed(rl.KeyEscape) || rl.IsKeyPressed(rl.KeyEnter)) {
		// Resume the game and restore velocity
		game.state = StatePlaying
		game.ship.SetVelocity(game.pausedShipVX, game.pausedShipVY)
		return
	}

	// Don't update gameplay when paused
	if game.state == StatePaused {
		return
	}

	// Only update in playing or mothership states
	if game.state != StatePlaying && game.state != StateMothership {
		return
	}

	// Clear collision debug info from previous frame
	game.collisionSystem.ClearDebugInfo()

	// When in mothership state, stop ship drift and only update distance check
	if game.state == StateMothership {
		// Don't update ship physics - keep ship stationary while docked
		// Just check if player has moved far enough to reset docking
		shipX, shipY := game.ship.GetPosition()
		game.mothershipSystem.CheckDocking(shipX, shipY)
		return
	}

	// Ship input and update
	game.ship.HandleInput(deltaTime)
	game.ship.Update(deltaTime)

	// Handle thruster sound
	if game.ship.Thrusting {
		if game.audioManager != nil {
			game.audioManager.StartThruster()
		}
	} else {
		if game.audioManager != nil {
			game.audioManager.StopThruster()
		}
	}

	// Handle shooting (Space key)
	if rl.IsKeyPressed(rl.KeySpace) {
		newBullets := game.ship.Shoot()
		if newBullets != nil {
			game.bullets = append(game.bullets, newBullets...)

			// Play shoot sound
			if game.audioManager != nil {
				game.audioManager.PlayShoot()
			}
		}
	}

	// Toggle collision debug mode with F1
	if rl.IsKeyPressed(rl.KeyF1) {
		game.collisionSystem.ToggleDebugMode()
		if game.collisionSystem.ShowDebugInfo {
			fmt.Println("Collision debug mode: ON")
		} else {
			fmt.Println("Collision debug mode: OFF")
		}
	}

	// Update asteroid manager (handles all asteroid physics and wrapping)
	shipX, shipY := game.ship.GetPosition()
	game.asteroidManager.Update(deltaTime, shipX, shipY)

	// Update audio (for looping thruster sound)
	if game.audioManager != nil {
		game.audioManager.UpdateThruster()
	}

	// Update bullets
	for i := len(game.bullets) - 1; i >= 0; i-- {
		game.bullets[i].X += game.bullets[i].VX * deltaTime
		game.bullets[i].Y += game.bullets[i].VY * deltaTime
		game.bullets[i].Lifetime -= deltaTime

		// Remove expired bullets
		if game.bullets[i].Lifetime <= 0 {
			game.bullets = append(game.bullets[:i], game.bullets[i+1:]...)
		}
	}

	// Check collisions using asteroid manager
	scoreGained := game.asteroidManager.CheckBulletCollisions(&game.bullets)
	if scoreGained > 0 {
		game.score += scoreGained
		game.credits += scoreGained // Credits = score (10 per asteroid)
		// Play explosion sound when asteroid is destroyed
		if game.audioManager != nil {
			game.audioManager.PlayExplosion()
		}
	}

	// Check ship-asteroid collisions using SAT (Separating Axis Theorem)
	shipVertices := game.ship.GetCollisionVertices()
	shipX, shipY = game.ship.GetPosition()

	// Check each asteroid using pixel-perfect SAT polygon-polygon collision
	if len(shipVertices) >= 3 {
		for _, asteroid := range game.asteroidManager.GetAsteroids() {
			boundingRadius := asteroid.ShapeRenderer.GetBoundingRadius(asteroid.Size)
			vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)

			collision := game.collisionSystem.ShipAsteroidCollisionSAT(
				shipX, shipY, shipVertices,
				asteroid.X, asteroid.Y, boundingRadius,
				vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

			if collision {
				// Apply collision impulse (bounce ship away from asteroid)
				dx := shipX - asteroid.X
				dy := shipY - asteroid.Y
				distance := systems.Distance(shipX, shipY, asteroid.X, asteroid.Y)
				if distance > 0 {
					// Normalize direction and apply impulse
					dx /= distance
					dy /= distance
					game.ship.ApplyImpulse(dx*systems.CollisionImpulseForce, dy*systems.CollisionImpulseForce)
				}

				// Game over on collision
				game.state = StateGameOver
				return
			}
		}
	}

	// Check mothership docking
	if game.mothershipSystem.CheckDocking(shipX, shipY) {
		// Docking detected - store velocity and stop ship
		game.pausedShipVX, game.pausedShipVY = game.ship.GetVelocity()
		game.ship.SetVelocity(0, 0) // Stop drifting while docked
		game.state = StateMothership
		// Stop thruster sound
		if game.audioManager != nil {
			game.audioManager.StopThruster()
		}
		return
	}

	// Spawn new asteroids periodically using advanced spawner
	game.asteroidManager.SpawnNewAsteroid(shipX, shipY)
}

// Render game
func renderGame() {
	if game.state != StatePlaying && game.state != StatePaused {
		return
	}

	screenWidth := int(rl.GetScreenWidth())
	screenHeight := int(rl.GetScreenHeight())

	// Camera position follows ship (ship's world position)
	shipX, shipY := game.ship.GetPosition()
	cameraX := shipX
	cameraY := shipY

	// Draw 2D asteroids using projected vertices
	for _, asteroid := range game.asteroidManager.GetAsteroids() {
		// Convert world coordinates to screen coordinates
		asteroidScreenX, asteroidScreenY := systems.WorldToScreen(asteroid.X, asteroid.Y, cameraX, cameraY, screenWidth, screenHeight)

		// Only draw if on screen (with margin)
		if !systems.IsOnScreen(asteroidScreenX, asteroidScreenY, screenWidth, screenHeight, asteroid.Size*2) {
			continue
		}

		vertices := asteroid.ShapeRenderer.GetVertices(asteroid.Size)

		// Get projected polygon (convex hull for silhouette)
		polygon := systems.GetProjectedPolygon(vertices, asteroid.RotationX, asteroid.RotationY, asteroid.RotationZ)

		// Draw filled polygon (grey silhouette)
		if len(polygon) >= 3 {
			// Triangle fan from first vertex
			for i := 1; i < len(polygon)-1; i++ {
				x0 := asteroidScreenX + polygon[0].X
				y0 := asteroidScreenY + polygon[0].Y
				x1 := asteroidScreenX + polygon[i].X
				y1 := asteroidScreenY + polygon[i].Y
				x2 := asteroidScreenX + polygon[i+1].X
				y2 := asteroidScreenY + polygon[i+1].Y

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

				x1 := asteroidScreenX + v0.X
				y1 := asteroidScreenY + v0.Y
				x2 := asteroidScreenX + v1.X
				y2 := asteroidScreenY + v1.Y

				rl.DrawLineEx(rl.Vector2{X: x1, Y: y1}, rl.Vector2{X: x2, Y: y2}, 2.0, rl.Black)
			}
		}
	}

	// Draw ship at center of screen
	shipScreenX := float32(screenWidth) / 2
	shipScreenY := float32(screenHeight) / 2
	game.ship.DrawShip(shipScreenX, shipScreenY)

	// Draw bullets relative to camera
	for _, bullet := range game.bullets {
		// Convert world coordinates to screen coordinates
		bulletScreenX, bulletScreenY := systems.WorldToScreen(bullet.X, bullet.Y, cameraX, cameraY, screenWidth, screenHeight)

		// Only draw if on screen
		if systems.IsOnScreen(bulletScreenX, bulletScreenY, screenWidth, screenHeight, 5) {
			rl.DrawCircle(int32(bulletScreenX), int32(bulletScreenY), systems.BulletRadius, systems.BulletColor)
		}
	}

	// Draw mothership
	game.mothershipSystem.DrawMothership(game.ship.X, game.ship.Y, cameraX, cameraY, screenWidth, screenHeight)

	// Draw radar/minimap (now with mothership)
	mothershipX, mothershipY := game.mothershipSystem.GetPosition()
	game.radarSystem.DrawRadar(
		shipX, shipY,
		game.asteroidManager.GetAsteroids(),
		mothershipX, mothershipY,
		true, // Mothership exists
	)

	// Draw world object counter in top-right corner
	worldObjectCount := len(game.asteroidManager.GetAsteroids()) + len(game.bullets) + 1 // ship
	if game.mothershipSystem != nil {
		worldObjectCount++
	}
	counterText := fmt.Sprintf("World Objects: %d", worldObjectCount)
	textWidth := rl.MeasureText(counterText, 20)
	rl.DrawText(counterText, int32(screenWidth)-textWidth-20, 20, 20, rl.White)

	// Draw collision debug visualization (if enabled with F1)
	game.collisionSystem.DrawDebugInfo(cameraX, cameraY, screenWidth, screenHeight)
}

// Render UI with Clay
func renderUI() {
	// Set pointer state for Clay (needed before BeginLayout)
	mousePosition := rl.GetMousePosition()
	mouseDown := rl.IsMouseButtonDown(rl.MouseLeftButton)
	clay.SetPointerState(clay.Vector2{X: mousePosition.X, Y: mousePosition.Y}, mouseDown)
	clay.SetLayoutDimensions(clay.Dimensions{
		Width:  float32(rl.GetScreenWidth()),
		Height: float32(rl.GetScreenHeight()),
	})

	clay.BeginLayout()

	switch game.state {
	case StateMenu:
		renderMenuUI()
	case StatePlaying:
		renderPlayingUI()
	case StatePaused:
		renderPausedUI()
	case StateGameOver:
		renderGameOverUI()
	case StateMothership:
		renderMothershipUI()
	case StateShop:
		renderShopUI()
	case StateSettings:
		renderSettingsUI()
	}

	renderCommands := clay.EndLayout()
	clayRaylibRender(renderCommands)

	// Render debug overlay (if F1 debug mode is enabled) - drawn after Clay UI
	if game.state == StatePlaying && game.collisionSystem.ShowDebugInfo {
		renderDebugOverlay()
	}
}

// Render debug overlay using Raylib directly (not Clay UI)
func renderDebugOverlay() {
	tier1, tier2, sat, hits := game.collisionSystem.GetDebugStats()
	asteroidCount := len(game.asteroidManager.GetAsteroids())
	bulletCount := len(game.bullets)
	screenWidth := int(rl.GetScreenWidth())

	// Top-right debug panel
	panelX := int32(screenWidth - 330)
	panelY := int32(10)
	panelWidth := int32(320)
	panelHeight := int32(190)

	// Background
	rl.DrawRectangle(panelX, panelY, panelWidth, panelHeight, rl.Color{R: 0, G: 0, B: 0, A: 180})
	rl.DrawRectangleLines(panelX, panelY, panelWidth, panelHeight, rl.Color{R: 100, G: 100, B: 100, A: 255})

	// Title
	y := panelY + 10
	rl.DrawText("DEBUG MODE (F1)", panelX+10, y, 18, rl.Color{R: 255, G: 255, B: 0, A: 255})
	y += 28

	// Stats
	rl.DrawText(fmt.Sprintf("Asteroids: %d", asteroidCount), panelX+10, y, 14, rl.White)
	y += 18
	rl.DrawText(fmt.Sprintf("Bullets: %d", bulletCount), panelX+10, y, 14, rl.White)
	y += 20

	rl.DrawText(fmt.Sprintf("TIER 1 checks: %d", tier1), panelX+10, y, 14, rl.Color{R: 100, G: 150, B: 255, A: 255})
	y += 18
	rl.DrawText(fmt.Sprintf("TIER 2 checks: %d", tier2), panelX+10, y, 14, rl.Color{R: 0, G: 255, B: 100, A: 255})
	y += 18
	rl.DrawText(fmt.Sprintf("SAT checks: %d", sat), panelX+10, y, 14, rl.Color{R: 255, G: 200, B: 0, A: 255})
	y += 18
	rl.DrawText(fmt.Sprintf("Collisions: %d", hits), panelX+10, y, 14, rl.Color{R: 255, G: 50, B: 50, A: 255})
	y += 22

	// Legend
	rl.DrawText("Legend:", panelX+10, y, 12, rl.Color{R: 200, G: 200, B: 200, A: 255})
	y += 16
	rl.DrawText("Blue=AABB Green=No Hit Red=Hit", panelX+10, y, 11, rl.Color{R: 180, G: 180, B: 180, A: 255})
}

// Render menu UI
func renderMenuUI() {
	shouldStartGame, shouldOpenSettings := game.menuRenderer.RenderMainMenu()

	if shouldStartGame {
		startGame()
	}
	if shouldOpenSettings {
		game.settingsManager.StartEditing(int(StateMenu))
		game.state = StateSettings
	}
}

// Render playing UI
func renderPlayingUI() {
	game.menuRenderer.RenderPlayingHUD(
		game.score,
		game.credits,
		game.ship.GetMultiShotCount(),
		game.ship.GetFireRateCooldown(),
	)
}

// Render paused UI
func renderPausedUI() {
	resume, restart, mainMenu := game.menuRenderer.RenderPauseMenu(game.score, game.credits)

	if resume {
		game.ship.SetVelocity(game.pausedShipVX, game.pausedShipVY)
		game.state = StatePlaying
	}
	if restart {
		startGame()
	}
	if mainMenu {
		game.state = StateMenu
	}
}

// Render game over UI
func renderGameOverUI() {
	if game.menuRenderer.RenderGameOverMenu(game.score) {
		startGame()
	}
}

// Render shop UI
func renderShopUI() {
	upgrades := game.shopSystem.GetUpgradeList(game.ship, game.credits)
	selectedIndex := game.shopSystem.GetSelectedIndex()

	// Handle navigation
	if rl.IsKeyPressed(rl.KeyUp) || rl.IsKeyPressed(rl.KeyW) {
		game.shopSystem.SelectPrevious(len(upgrades))
	}
	if rl.IsKeyPressed(rl.KeyDown) || rl.IsKeyPressed(rl.KeyS) {
		game.shopSystem.SelectNext(len(upgrades))
	}

	// Handle purchase
	if (rl.IsKeyPressed(rl.KeyEnter) || rl.IsKeyPressed(rl.KeySpace)) && selectedIndex < len(upgrades) {
		upgrade := upgrades[selectedIndex]
		if game.shopSystem.PurchaseUpgrade(upgrade.Type, game.ship, &game.credits) {
			fmt.Printf("Purchased %s! New level: %d\n", upgrade.Name, upgrade.NextLevel)
		} else {
			fmt.Printf("Not enough credits for %s (need %d, have %d)\n", upgrade.Name, upgrade.Price, game.credits)
		}
	}

	// Handle back (ESC)
	if rl.IsKeyPressed(rl.KeyEscape) {
		game.state = StateMothership
		return
	}

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("ShopContainer"),
		Layout: clay.LayoutConfig{
			Sizing: clay.Sizing{
				Width:  clay.SizingGrow(0),
				Height: clay.SizingGrow(0),
			},
			ChildAlignment: clay.ChildAlignment{
				X: clay.ALIGN_X_CENTER,
				Y: clay.ALIGN_Y_CENTER,
			},
			LayoutDirection: clay.TOP_TO_BOTTOM,
			ChildGap:        24,
		},
	}, func() {
		// Title
		clay.Text("UPGRADE SHOP", clay.TextConfig(clay.TextElementConfig{
			FontSize:  48,
			TextColor: clay.Color{R: 100, G: 255, B: 100, A: 255},
		}))

		// Credits display
		creditsText := fmt.Sprintf("Credits: %d", game.credits)
		clay.Text(creditsText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  24,
			TextColor: clay.Color{R: 255, G: 215, B: 0, A: 255}, // Gold
		}))

		// Upgrades list
		for i, upgrade := range upgrades {
			isSelected := i == selectedIndex
			bgColor := clay.Color{R: 60, G: 60, B: 60, A: 220}
			if isSelected {
				bgColor = clay.Color{R: 100, G: 150, B: 100, A: 255} // Highlight selected
			}

			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID(fmt.Sprintf("Upgrade%d", i)),
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(600),
						Height: clay.SizingFixed(120),
					},
					Padding:         clay.PaddingAll(16),
					ChildGap:        8,
					LayoutDirection: clay.TOP_TO_BOTTOM,
				},
				BackgroundColor: bgColor,
			}, func() {
				// Upgrade name and price
				nameText := fmt.Sprintf("%s - Level %d", upgrade.Name, upgrade.NextLevel)
				clay.Text(nameText, clay.TextConfig(clay.TextElementConfig{
					FontSize:  22,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))

				// Description
				clay.Text(upgrade.Description, clay.TextConfig(clay.TextElementConfig{
					FontSize:  14,
					TextColor: clay.Color{R: 220, G: 220, B: 220, A: 255},
				}))

				// Price and affordability
				priceColor := clay.Color{R: 255, G: 50, B: 50, A: 255} // Red if can't afford
				if upgrade.CanAfford {
					priceColor = clay.Color{R: 100, G: 255, B: 100, A: 255} // Green if can afford
				}
				priceText := fmt.Sprintf("Price: %d credits", upgrade.Price)
				clay.Text(priceText, clay.TextConfig(clay.TextElementConfig{
					FontSize:  16,
					TextColor: priceColor,
				}))
			})
		}

		// Instructions
		clay.Text("Use UP/DOWN to select | ENTER/SPACE to purchase | ESC to go back", clay.TextConfig(clay.TextElementConfig{
			FontSize:  14,
			TextColor: clay.Color{R: 180, G: 180, B: 180, A: 255},
		}))
	})
}

// Render mothership docking UI
func renderMothershipUI() {
	upgrades, undock := game.menuRenderer.RenderMothershipMenu(game.score, game.credits)

	if upgrades {
		game.state = StateShop
	}
	if undock {
		game.ship.SetVelocity(game.pausedShipVX, game.pausedShipVY)
		game.state = StatePlaying
	}
}

// Render settings UI
func renderSettingsUI() {
	pending := game.settingsManager.GetPendingSettings()

	// Handle navigation with keyboard
	if rl.IsKeyPressed(rl.KeyLeft) || rl.IsKeyPressed(rl.KeyA) {
		game.settingsManager.CycleResolution(false) // Previous resolution
	}
	if rl.IsKeyPressed(rl.KeyRight) || rl.IsKeyPressed(rl.KeyD) {
		game.settingsManager.CycleResolution(true) // Next resolution
	}
	if rl.IsKeyPressed(rl.KeyF) {
		game.settingsManager.ToggleFullscreen()
	}

	// Handle Apply
	if rl.IsKeyPressed(rl.KeyEnter) {
		err := game.settingsManager.ApplyPendingSettings()
		if err != nil {
			fmt.Printf("Error applying settings: %v\n", err)
		}
		game.state = GameState(game.settingsManager.GetPreviousState())
		return
	}

	// Handle Back (ESC)
	if rl.IsKeyPressed(rl.KeyEscape) {
		game.settingsManager.DiscardPendingSettings()
		game.state = GameState(game.settingsManager.GetPreviousState())
		return
	}

	resInfo := game.settingsManager.GetPendingResolution()
	mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("SettingsContainer"),
		Layout: clay.LayoutConfig{
			Sizing: clay.Sizing{
				Width:  clay.SizingGrow(0),
				Height: clay.SizingGrow(0),
			},
			ChildAlignment: clay.ChildAlignment{
				X: clay.ALIGN_X_CENTER,
				Y: clay.ALIGN_Y_CENTER,
			},
			LayoutDirection: clay.TOP_TO_BOTTOM,
			ChildGap:        32,
		},
	}, func() {
		// Title
		clay.Text("SETTINGS", clay.TextConfig(clay.TextElementConfig{
			FontSize:  56,
			TextColor: clay.Color{R: 100, G: 200, B: 255, A: 255},
		}))

		// Resolution setting
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("ResolutionContainer"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(600),
					Height: clay.SizingFixed(80),
				},
				Padding:         clay.PaddingAll(16),
				ChildGap:        16,
				LayoutDirection: clay.LEFT_TO_RIGHT,
				ChildAlignment: clay.ChildAlignment{
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: clay.Color{R: 60, G: 60, B: 80, A: 220},
		}, func() {
			clay.Text("Resolution:", clay.TextConfig(clay.TextElementConfig{
				FontSize:  24,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))

			// Previous button
			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("ResolutionPrevButton"),
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(50),
						Height: clay.SizingFixed(50),
					},
					Padding: clay.PaddingAll(8),
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
				},
				BackgroundColor: clay.Color{R: 80, G: 130, B: 180, A: 255},
			}, func() {
				clay.Text("<", clay.TextConfig(clay.TextElementConfig{
					FontSize:  28,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))
			})

			if clay.PointerOver(clay.ID("ResolutionPrevButton")) && mousePressed {
				game.settingsManager.CycleResolution(false)
			}

			// Current resolution display
			clay.UI()(clay.ElementDeclaration{
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width: clay.SizingFixed(200),
					},
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
				},
			}, func() {
				clay.Text(resInfo.Label, clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 100, A: 255},
				}))
			})

			// Next button
			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("ResolutionNextButton"),
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(50),
						Height: clay.SizingFixed(50),
					},
					Padding: clay.PaddingAll(8),
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
				},
				BackgroundColor: clay.Color{R: 80, G: 130, B: 180, A: 255},
			}, func() {
				clay.Text(">", clay.TextConfig(clay.TextElementConfig{
					FontSize:  28,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))
			})

			if clay.PointerOver(clay.ID("ResolutionNextButton")) && mousePressed {
				game.settingsManager.CycleResolution(true)
			}
		})

		// Fullscreen toggle
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("FullscreenContainer"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(600),
					Height: clay.SizingFixed(80),
				},
				Padding:         clay.PaddingAll(16),
				ChildGap:        16,
				LayoutDirection: clay.LEFT_TO_RIGHT,
				ChildAlignment: clay.ChildAlignment{
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: clay.Color{R: 60, G: 60, B: 80, A: 220},
		}, func() {
			clay.Text("Fullscreen:", clay.TextConfig(clay.TextElementConfig{
				FontSize:  24,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))

			// Toggle button
			fullscreenText := "OFF"
			btnColor := clay.Color{R: 150, G: 60, B: 60, A: 255} // Red for OFF
			if pending.Fullscreen {
				fullscreenText = "ON"
				btnColor = clay.Color{R: 60, G: 150, B: 60, A: 255} // Green for ON
			}

			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("FullscreenToggleButton"),
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(120),
						Height: clay.SizingFixed(50),
					},
					Padding: clay.PaddingAll(8),
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
				},
				BackgroundColor: btnColor,
			}, func() {
				clay.Text(fullscreenText, clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))
			})

			if clay.PointerOver(clay.ID("FullscreenToggleButton")) && mousePressed {
				game.settingsManager.ToggleFullscreen()
			}
		})

		// Apply button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("ApplyButton"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(250),
					Height: clay.SizingFixed(70),
				},
				Padding: clay.PaddingAll(16),
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_CENTER,
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: clay.Color{R: 60, G: 150, B: 60, A: 255},
		}, func() {
			clay.Text("APPLY", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("ApplyButton")) && mousePressed {
			err := game.settingsManager.ApplyPendingSettings()
			if err != nil {
				fmt.Printf("Error applying settings: %v\n", err)
			}
			game.state = GameState(game.settingsManager.GetPreviousState())
			return
		}

		// Back button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("BackButton"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(250),
					Height: clay.SizingFixed(70),
				},
				Padding: clay.PaddingAll(16),
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_CENTER,
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: clay.Color{R: 150, G: 60, B: 60, A: 255},
		}, func() {
			clay.Text("BACK", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("BackButton")) && mousePressed {
			game.settingsManager.DiscardPendingSettings()
			game.state = GameState(game.settingsManager.GetPreviousState())
			return
		}

		// Instructions
		clay.Text("LEFT/RIGHT: Change resolution | F: Toggle fullscreen | ENTER: Apply | ESC: Cancel", clay.TextConfig(clay.TextElementConfig{
			FontSize:  14,
			TextColor: clay.Color{R: 180, G: 180, B: 180, A: 255},
		}))
	})
}

func main() {
	// Initialize game state first (before window, so we can load settings)
	initGame()

	// Load settings from disk
	settings := game.settingsManager.LoadSettings()

	// Get resolution from settings
	res := systems.AvailableResolutions[settings.ResolutionIndex]

	// Initialize window with settings resolution
	rl.InitWindow(int32(res.Width), int32(res.Height), "AstroBoy4 - Asteroids")
	defer rl.CloseWindow()

	rl.SetTargetFPS(systems.TargetFPS)

	// Apply settings (fullscreen, etc.)
	game.settingsManager.ApplySettings(settings)

	// Disable ESC closing window - we'll handle ESC manually for navigation
	rl.SetExitKey(0)

	// Initialize audio device
	rl.InitAudioDevice()
	defer rl.CloseAudioDevice()

	// Load font
	customFont := rl.LoadFontEx("C:/Windows/Fonts/arial.ttf", 96, nil, 0)
	if customFont.Texture.ID == 0 {
		customFont = rl.GetFontDefault()
	}
	defer func() {
		if customFont.Texture.ID != rl.GetFontDefault().Texture.ID {
			rl.UnloadFont(customFont)
		}
	}()

	// Initialize Clay with the actual window resolution
	totalMemorySize := clay.MinMemorySize()
	memory := make([]byte, totalMemorySize)
	arena := clay.CreateArenaWithCapacityAndMemory(memory)

	clay.Initialize(
		arena,
		clay.Dimensions{Width: float32(res.Width), Height: float32(res.Height)},
		clay.ErrorHandler{ErrorHandlerFunction: errorHandler},
	)

	clay.SetMeasureTextFunction(measureTextFunction, unsafe.Pointer(&customFont))

	// Store font in game
	game.customFont = customFont

	// Save settings on exit
	defer func() {
		err := game.settingsManager.SaveSettings(game.settingsManager.GetCurrentSettings())
		if err != nil {
			fmt.Printf("Error saving settings on exit: %v\n", err)
		}
	}()

	// Initialize audio system
	audioMgr, err := audio.NewAudioManager()
	if err != nil {
		fmt.Printf("Warning: Failed to initialize audio: %v\n", err)
	} else {
		game.audioManager = audioMgr
		defer game.audioManager.Cleanup()
	}

	// Main game loop
	running := true
	for running {
		deltaTime := rl.GetFrameTime()

		updateGame(deltaTime)

		rl.BeginDrawing()
		rl.ClearBackground(systems.SpaceBackgroundColor)

		renderGame()
		renderUI()

		rl.EndDrawing()

		// Check for quit (ESC only works in main menu, or Alt+F4 always works)
		if game.state == StateMenu && rl.IsKeyPressed(rl.KeyEscape) {
			running = false
		}
		if rl.WindowShouldClose() { // Alt+F4 or window close button
			running = false
		}
	}
}
