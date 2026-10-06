// AstroBoy4 UI Module - Menu Layouts
// All Clay UI layout rendering for different game states
// Extracted from main.go for better organization

package ui

import (
	"fmt"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

// MenuRenderer handles rendering of all menu screens
type MenuRenderer struct {
	buttonManager *ButtonManager
}

// NewMenuRenderer creates a new menu renderer
func NewMenuRenderer(buttonManager *ButtonManager) *MenuRenderer {
	return &MenuRenderer{
		buttonManager: buttonManager,
	}
}

// RenderMainMenu renders the main menu UI
func (mr *MenuRenderer) RenderMainMenu() (startGame bool, openSettings bool) {
	mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("MainContainer"),
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
		clay.Text("ASTEROIDS", clay.TextConfig(clay.TextElementConfig{
			FontSize:  64,
			TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
		}))

		// Start Game button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("StartButton"),
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
			BackgroundColor: clay.Color{R: 70, G: 130, B: 180, A: 255},
		}, func() {
			clay.Text("START GAME", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if (clay.PointerOver(clay.ID("StartButton")) && mousePressed) || rl.IsKeyPressed(rl.KeyEnter) {
			startGame = true
		}

		// Settings button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("SettingsButton"),
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
			BackgroundColor: clay.Color{R: 100, G: 100, B: 120, A: 255},
		}, func() {
			clay.Text("SETTINGS", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("SettingsButton")) && mousePressed {
			openSettings = true
		}

		clay.Text("Controls: WASD or Arrows to move, Space to shoot", clay.TextConfig(clay.TextElementConfig{
			FontSize:  18,
			TextColor: clay.Color{R: 200, G: 200, B: 200, A: 255},
		}))

		clay.Text("Press ENTER to start", clay.TextConfig(clay.TextElementConfig{
			FontSize:  16,
			TextColor: clay.Color{R: 150, G: 150, B: 150, A: 255},
		}))
	})

	return
}

// RenderPauseMenu renders the pause menu UI
func (mr *MenuRenderer) RenderPauseMenu(score, credits int) (resume, restart, mainMenu bool) {
	mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("PauseContainer"),
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
		clay.Text("PAUSED", clay.TextConfig(clay.TextElementConfig{
			FontSize:  64,
			TextColor: clay.Color{R: 100, G: 200, B: 255, A: 255},
		}))

		scoreText := fmt.Sprintf("Score: %d | Credits: %d", score, credits)
		clay.Text(scoreText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  20,
			TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
		}))

		// Resume button (green)
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("ResumeButton"),
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
			BackgroundColor: clay.Color{R: 70, G: 180, B: 70, A: 255},
		}, func() {
			clay.Text("RESUME", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("ResumeButton")) && mousePressed {
			resume = true
		}

		// Restart button (orange)
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("RestartButton"),
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
			BackgroundColor: clay.Color{R: 255, G: 165, B: 0, A: 255},
		}, func() {
			clay.Text("RESTART", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("RestartButton")) && mousePressed {
			restart = true
		}

		// Main Menu button (red)
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("MainMenuButton"),
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
			BackgroundColor: clay.Color{R: 180, G: 70, B: 70, A: 255},
		}, func() {
			clay.Text("MAIN MENU", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("MainMenuButton")) && mousePressed {
			mainMenu = true
		}

		clay.Text("Press ESC or ENTER to resume", clay.TextConfig(clay.TextElementConfig{
			FontSize:  16,
			TextColor: clay.Color{R: 150, G: 150, B: 150, A: 255},
		}))
	})

	return
}

// RenderGameOverMenu renders the game over screen
func (mr *MenuRenderer) RenderGameOverMenu(finalScore int) bool {
	mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)
	playAgain := false

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("GameOverContainer"),
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
		clay.Text("GAME OVER", clay.TextConfig(clay.TextElementConfig{
			FontSize:  64,
			TextColor: clay.Color{R: 255, G: 100, B: 100, A: 255},
		}))

		scoreText := fmt.Sprintf("Final Score: %d", finalScore)
		clay.Text(scoreText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  32,
			TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
		}))

		// Play Again button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("RestartButton"),
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
			BackgroundColor: clay.Color{R: 70, G: 130, B: 180, A: 255},
		}, func() {
			clay.Text("PLAY AGAIN", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("RestartButton")) && mousePressed {
			playAgain = true
		}
	})

	return playAgain
}

// RenderMothershipMenu renders the mothership docking screen
func (mr *MenuRenderer) RenderMothershipMenu(score, credits int) (upgrades, undock bool) {
	mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("MothershipContainer"),
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
		clay.Text("MOTHERSHIP", clay.TextConfig(clay.TextElementConfig{
			FontSize:  64,
			TextColor: clay.Color{R: 100, G: 200, B: 255, A: 255},
		}))

		clay.Text("Docked at Station", clay.TextConfig(clay.TextElementConfig{
			FontSize:  24,
			TextColor: clay.Color{R: 200, G: 200, B: 200, A: 255},
		}))

		scoreText := fmt.Sprintf("Score: %d | Credits: %d", score, credits)
		clay.Text(scoreText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  20,
			TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
		}))

		// Upgrades button (green)
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("UpgradesButton"),
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
			BackgroundColor: clay.Color{R: 100, G: 180, B: 70, A: 255},
		}, func() {
			clay.Text("UPGRADES", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("UpgradesButton")) && mousePressed {
			upgrades = true
		}

		// Undock button
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("UndockButton"),
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
			BackgroundColor: clay.Color{R: 70, G: 130, B: 180, A: 255},
		}, func() {
			clay.Text("UNDOCK", clay.TextConfig(clay.TextElementConfig{
				FontSize:  28,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		if clay.PointerOver(clay.ID("UndockButton")) && mousePressed {
			undock = true
		}
	})

	return
}

// RenderPlayingHUD renders the in-game HUD (score, weapons, etc.)
func (mr *MenuRenderer) RenderPlayingHUD(score, credits int, multiShot int, fireRate float32) {
	// Top-left HUD panel
	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("HUD"),
		Layout: clay.LayoutConfig{
			Sizing: clay.Sizing{
				Width:  clay.SizingFixed(250),
				Height: clay.SizingFixed(100),
			},
			Padding:         clay.PaddingAll(12),
			ChildGap:        4,
			LayoutDirection: clay.TOP_TO_BOTTOM,
		},
		BackgroundColor: clay.Color{R: 40, G: 40, B: 40, A: 200},
	}, func() {
		scoreText := fmt.Sprintf("Score: %d", score)
		clay.Text(scoreText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  24,
			TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
		}))

		// Weapon info
		multiShotText := fmt.Sprintf("Multi-shot: %dx", multiShot)
		clay.Text(multiShotText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  14,
			TextColor: clay.Color{R: 200, G: 200, B: 255, A: 255},
		}))

		fireRateText := fmt.Sprintf("Fire rate: %.2f/s", 1.0/fireRate)
		clay.Text(fireRateText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  14,
			TextColor: clay.Color{R: 200, G: 255, B: 200, A: 255},
		}))

		// Credits
		creditsText := fmt.Sprintf("Credits: %d", credits)
		clay.Text(creditsText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  14,
			TextColor: clay.Color{R: 255, G: 215, B: 0, A: 255}, // Gold color
		}))
	})
}
