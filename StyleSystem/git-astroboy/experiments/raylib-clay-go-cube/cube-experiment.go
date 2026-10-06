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
	rotation   float32
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

		// Update rotation
		if showCube {
			rotation += 0.5
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
					Height: clay.SizingFixed(180),
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

			// Info text
			if showCube {
				clay.Text("Watch the cube spin!", clay.TextConfig(clay.TextElementConfig{
					FontSize:  18,
					TextColor: clay.Color{R: 150, G: 200, B: 150, A: 255},
				}))
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

		// Render
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 20, G: 20, B: 30, A: 255})

		// Draw 3D cube if started
		if showCube {
			rl.BeginMode3D(camera)

			// Draw a wireframe cube
			rl.DrawCubeWires(rl.Vector3{X: 0, Y: 0, Z: 0}, 2.0, 2.0, 2.0, rl.Blue)

			// Draw a solid rotating cube
			rl.PushMatrix()
			rl.Rotatef(rotation, 1.0, 1.0, 0.0)
			rl.DrawCube(rl.Vector3{X: 0, Y: 0, Z: 0}, 2.0, 2.0, 2.0, rl.Color{R: 100, G: 150, B: 255, A: 200})
			rl.PopMatrix()

			// Draw grid
			rl.DrawGrid(10, 1.0)

			rl.EndMode3D()
		}

		// Render Clay UI on top
		clayRaylibRender(renderCommands)

		rl.EndDrawing()
	}
}
