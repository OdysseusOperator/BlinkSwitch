package main

import (
	"fmt"
	"unsafe"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	screenWidth  = 800
	screenHeight = 600
)

var (
	startButtonPressed = false
	customFont         rl.Font
)

// Error handler for Clay
func errorHandler(errorData clay.ErrorData) {
	fmt.Printf("Clay Error: %s\n", errorData.ErrorText)
}

// Text measurement function for Clay with Raylib
func measureTextFunction(text clay.StringSlice, config *clay.TextElementConfig, userData unsafe.Pointer) clay.Dimensions {
	// Use the built-in String() method
	textStr := text.String()
	
	// Get font from userData if available, otherwise use global
	font := customFont
	if userData != nil {
		font = *(*rl.Font)(userData)
	}
	
	// Measure text with Raylib
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
			
			// Use the built-in String() method
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
	rl.InitWindow(screenWidth, screenHeight, "Raylib + Clay Go Hello World")
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

	// Set text measurement function with proper userData
	clay.SetMeasureTextFunction(measureTextFunction, unsafe.Pointer(&customFont))

	// Main loop
	for !rl.WindowShouldClose() {
		mousePosition := rl.GetMousePosition()
		mouseDown := rl.IsMouseButtonDown(rl.MouseLeftButton)
		mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

		// Update Clay pointer state
		clay.SetPointerState(clay.Vector2{X: mousePosition.X, Y: mousePosition.Y}, mouseDown)

		clay.BeginLayout()

		// Main container
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("MainContainer"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingGrow(0),
					Height: clay.SizingGrow(0),
				},
				Padding: clay.PaddingAll(16),
			},
			BackgroundColor: clay.Color{R: 40, G: 40, B: 40, A: 255},
		}, func() {
			// Content container
			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("ContentContainer"),
				Layout: clay.LayoutConfig{
					LayoutDirection: clay.TOP_TO_BOTTOM,
					Sizing: clay.Sizing{
						Width:  clay.SizingGrow(0),
						Height: clay.SizingGrow(0),
					},
					ChildAlignment: clay.ChildAlignment{
						X: clay.ALIGN_X_CENTER,
						Y: clay.ALIGN_Y_CENTER,
					},
					ChildGap: 32,
				},
			}, func() {
				// Title
				clay.Text("Hello World!", clay.TextConfig(clay.TextElementConfig{
					FontSize:  48,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))

				// Button
				buttonColor := clay.Color{R: 70, G: 130, B: 180, A: 255}
				if startButtonPressed {
					buttonColor = clay.Color{R: 100, G: 200, B: 100, A: 255}
				}

				clay.UI()(clay.ElementDeclaration{
					Id: clay.ID("StartButton"),
					Layout: clay.LayoutConfig{
						Sizing: clay.Sizing{
							Width:  clay.SizingFixed(200),
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
					buttonText := "Start"
					if startButtonPressed {
						buttonText = "Started!"
					}
					clay.Text(buttonText, clay.TextConfig(clay.TextElementConfig{
						FontSize:  24,
						TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
					}))
				})

				// Welcome message
				if startButtonPressed {
					clay.Text("Welcome to Raylib + Clay Go!", clay.TextConfig(clay.TextElementConfig{
						FontSize:  20,
						TextColor: clay.Color{R: 200, G: 200, B: 200, A: 255},
					}))
				}
			})
		})

		renderCommands := clay.EndLayout()

		// Handle button interaction
		if clay.PointerOver(clay.ID("StartButton")) && mousePressed {
			startButtonPressed = true
		}

		// Render
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 245, G: 245, B: 245, A: 255}) // Light background

		clayRaylibRender(renderCommands)

		rl.EndDrawing()
	}
}