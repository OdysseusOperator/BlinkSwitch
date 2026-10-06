package main

import (
	"fmt"
	"unsafe"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	screenWidth  = 1024
	screenHeight = 768
)

var (
	showCube   = false
	customFont rl.Font
	camera     rl.Camera3D

	// Rotation speeds for each axis (range: -2.0 to 2.0)
	rotationSpeedX float32 = 0.5
	rotationSpeedY float32 = 0.5
	rotationSpeedZ float32 = 0.5

	// Current rotation angles (continuously accumulate)
	rotationX float32
	rotationY float32
	rotationZ float32
)

// Error handler for Clay
func errorHandler(errorData clay.ErrorData) {
	fmt.Printf("Clay Error: %s\n", errorData.ErrorText)
}

// Text measurement function for Clay with Raylib
func measureTextFunction(text clay.StringSlice, config *clay.TextElementConfig, userData unsafe.Pointer) clay.Dimensions {
	textStr := text.String()

	font := customFont
	if userData != nil {
		font = *(*rl.Font)(userData)
	}

	textSize := rl.MeasureTextEx(font, textStr, float32(config.FontSize), 1.0)

	return clay.Dimensions{
		Width:  textSize.X,
		Height: textSize.Y,
	}
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
				customFont,
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

// renderSliderControl creates a slider control with increment/decrement buttons
// axis: "X", "Y", or "Z" - the axis name
// value: pointer to the current rotation speed value
// min, max: value range limits
// step: amount to change per button click
func renderSliderControl(axis string, value *float32, min, max, step float32) {
	// Container for entire slider row
	clay.UI()(clay.ElementDeclaration{
		Layout: clay.LayoutConfig{
			LayoutDirection: clay.LEFT_TO_RIGHT,
			Sizing: clay.Sizing{
				Width:  clay.SizingFixed(500),
				Height: clay.SizingFixed(50),
			},
			ChildAlignment: clay.ChildAlignment{
				Y: clay.ALIGN_Y_CENTER,
			},
			ChildGap: 12,
		},
	}, func() {
		// Label
		clay.Text(axis+" Rotation:", clay.TextConfig(clay.TextElementConfig{
			FontSize:  18,
			TextColor: clay.Color{R: 220, G: 220, B: 220, A: 255},
		}))

		// Decrement button [-]
		decrementBtnColor := clay.Color{R: 180, G: 70, B: 70, A: 255}
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("Btn" + axis + "Dec"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(40),
					Height: clay.SizingFixed(40),
				},
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_CENTER,
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: decrementBtnColor,
		}, func() {
			clay.Text("-", clay.TextConfig(clay.TextElementConfig{
				FontSize:  24,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		// Visual bar representation
		clay.UI()(clay.ElementDeclaration{
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(200),
					Height: clay.SizingFixed(32),
				},
			},
			BackgroundColor: clay.Color{R: 50, G: 50, B: 70, A: 255},
		}, func() {
			// Calculate fill percentage based on value
			// Map from [-2.0, 2.0] to [0.0, 1.0]
			normalizedValue := (*value - min) / (max - min)
			fillWidth := normalizedValue * 200

			// Filled portion
			clay.UI()(clay.ElementDeclaration{
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(fillWidth),
						Height: clay.SizingFixed(32),
					},
				},
				BackgroundColor: clay.Color{R: 80, G: 150, B: 220, A: 255},
			}, func() {})
		})

		// Increment button [+]
		incrementBtnColor := clay.Color{R: 70, G: 180, B: 70, A: 255}
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("Btn" + axis + "Inc"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingFixed(40),
					Height: clay.SizingFixed(40),
				},
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_CENTER,
					Y: clay.ALIGN_Y_CENTER,
				},
			},
			BackgroundColor: incrementBtnColor,
		}, func() {
			clay.Text("+", clay.TextConfig(clay.TextElementConfig{
				FontSize:  24,
				TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
			}))
		})

		// Value display
		valueText := fmt.Sprintf("%.2f", *value)
		clay.Text(valueText, clay.TextConfig(clay.TextElementConfig{
			FontSize:  18,
			TextColor: clay.Color{R: 150, G: 220, B: 150, A: 255},
		}))
	})
}

func main() {
	rl.InitWindow(screenWidth, screenHeight, "Clay + Raylib 3D Cube Experiment")
	defer rl.CloseWindow()

	rl.SetTargetFPS(60)

	// Load font
	customFont = rl.LoadFontEx("C:/Windows/Fonts/arial.ttf", 96, nil, 0)
	if customFont.Texture.ID == 0 {
		customFont = rl.GetFontDefault()
	}
	defer func() {
		if customFont.Texture.ID != rl.GetFontDefault().Texture.ID {
			rl.UnloadFont(customFont)
		}
	}()

	// Initialize Clay
	totalMemorySize := clay.MinMemorySize()
	memory := make([]byte, totalMemorySize)
	arena := clay.CreateArenaWithCapacityAndMemory(memory)

	clay.Initialize(
		arena,
		clay.Dimensions{Width: screenWidth, Height: screenHeight},
		clay.ErrorHandler{ErrorHandlerFunction: errorHandler},
	)

	clay.SetMeasureTextFunction(measureTextFunction, unsafe.Pointer(&customFont))

	// Setup 3D camera
	camera = rl.Camera3D{
		Position:   rl.Vector3{X: 10.0, Y: 10.0, Z: 10.0},
		Target:     rl.Vector3{X: 0.0, Y: 0.0, Z: 0.0},
		Up:         rl.Vector3{X: 0.0, Y: 1.0, Z: 0.0},
		Fovy:       45.0,
		Projection: rl.CameraPerspective,
	}

	// Main loop
	for !rl.WindowShouldClose() {
		mousePosition := rl.GetMousePosition()
		mouseDown := rl.IsMouseButtonDown(rl.MouseLeftButton)
		mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

		// Update rotations for each axis
		if showCube {
			rotationX += rotationSpeedX
			rotationY += rotationSpeedY
			rotationZ += rotationSpeedZ
		}

		// Update Clay pointer state
		clay.SetPointerState(clay.Vector2{X: mousePosition.X, Y: mousePosition.Y}, mouseDown)

		clay.BeginLayout()

		// Top UI Panel (fixed at top, doesn't fill screen)
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("TopPanel"),
			Layout: clay.LayoutConfig{
				LayoutDirection: clay.TOP_TO_BOTTOM,
				Sizing: clay.Sizing{
					Width:  clay.SizingGrow(0),
					Height: clay.SizingFixed(420),
				},
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_CENTER,
					Y: clay.ALIGN_Y_CENTER,
				},
				ChildGap: 20,
				Padding:  clay.PaddingAll(16),
			},
			BackgroundColor: clay.Color{R: 30, G: 30, B: 45, A: 220},
		}, func() {
			// Title
			clay.Text("3D Cube Experiment", clay.TextConfig(clay.TextElementConfig{
				FontSize:  42,
				TextColor: clay.Color{R: 100, G: 200, B: 255, A: 255},
			}))

			// Button
			buttonColor := clay.Color{R: 70, G: 130, B: 180, A: 255}
			if showCube {
				buttonColor = clay.Color{R: 180, G: 70, B: 70, A: 255}
			}

			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("StartButton"),
				Layout: clay.LayoutConfig{
					Sizing: clay.Sizing{
						Width:  clay.SizingFixed(220),
						Height: clay.SizingFixed(60),
					},
					Padding: clay.PaddingAll(16),
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
				},
				BackgroundColor: buttonColor,
			}, func() {
				buttonText := "Start Cube"
				if showCube {
					buttonText = "Stop Cube"
				}
				clay.Text(buttonText, clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))
			})

			// Info text and sliders
			if showCube {
				clay.Text("Adjust rotation speeds:", clay.TextConfig(clay.TextElementConfig{
					FontSize:  18,
					TextColor: clay.Color{R: 150, G: 200, B: 150, A: 255},
				}))

				// X Axis Slider
				renderSliderControl("X", &rotationSpeedX, -2.0, 2.0, 0.1)

				// Y Axis Slider
				renderSliderControl("Y", &rotationSpeedY, -2.0, 2.0, 0.1)

				// Z Axis Slider
				renderSliderControl("Z", &rotationSpeedZ, -2.0, 2.0, 0.1)

			} else {
				clay.Text("Click the button to start", clay.TextConfig(clay.TextElementConfig{
					FontSize:  18,
					TextColor: clay.Color{R: 180, G: 180, B: 180, A: 255},
				}))
			}
		})

		renderCommands := clay.EndLayout()

		// Handle button interaction
		if clay.PointerOver(clay.ID("StartButton")) && mousePressed {
			showCube = !showCube
		}

		// Handle slider button interactions
		if showCube && mousePressed {
			// X Axis buttons
			if clay.PointerOver(clay.ID("BtnXDec")) {
				rotationSpeedX -= 0.1
				if rotationSpeedX < -2.0 {
					rotationSpeedX = -2.0
				}
			}
			if clay.PointerOver(clay.ID("BtnXInc")) {
				rotationSpeedX += 0.1
				if rotationSpeedX > 2.0 {
					rotationSpeedX = 2.0
				}
			}

			// Y Axis buttons
			if clay.PointerOver(clay.ID("BtnYDec")) {
				rotationSpeedY -= 0.1
				if rotationSpeedY < -2.0 {
					rotationSpeedY = -2.0
				}
			}
			if clay.PointerOver(clay.ID("BtnYInc")) {
				rotationSpeedY += 0.1
				if rotationSpeedY > 2.0 {
					rotationSpeedY = 2.0
				}
			}

			// Z Axis buttons
			if clay.PointerOver(clay.ID("BtnZDec")) {
				rotationSpeedZ -= 0.1
				if rotationSpeedZ < -2.0 {
					rotationSpeedZ = -2.0
				}
			}
			if clay.PointerOver(clay.ID("BtnZInc")) {
				rotationSpeedZ += 0.1
				if rotationSpeedZ > 2.0 {
					rotationSpeedZ = 2.0
				}
			}
		}

		// Render
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 20, G: 20, B: 30, A: 255})

		// Draw 3D cube if started
		if showCube {
			rl.BeginMode3D(camera)

			// Draw rotating cube with separate axis rotations
			rl.PushMatrix()
			rl.Rotatef(rotationX, 1.0, 0.0, 0.0) // Rotate around X axis
			rl.Rotatef(rotationY, 0.0, 1.0, 0.0) // Rotate around Y axis
			rl.Rotatef(rotationZ, 0.0, 0.0, 1.0) // Rotate around Z axis

			// Draw solid cube with mid-grey infill
			rl.DrawCube(rl.Vector3{X: 0, Y: 0, Z: 0}, 2.0, 2.0, 2.0, rl.Color{R: 128, G: 128, B: 128, A: 255})

			// Draw black wireframe edges
			rl.DrawCubeWires(rl.Vector3{X: 0, Y: 0, Z: 0}, 2.0, 2.0, 2.0, rl.Black)

			rl.PopMatrix()

			rl.EndMode3D()
		}

		// Render Clay UI on top
		clayRaylibRender(renderCommands)

		rl.EndDrawing()
	}
}
