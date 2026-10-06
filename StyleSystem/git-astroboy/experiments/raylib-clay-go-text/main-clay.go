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
	fontRegular    rl.Font
	fontBold       rl.Font
	fontItalic     rl.Font
	fontBoldItalic rl.Font
	currentFont    *rl.Font
)

// Error handler for Clay
func errorHandler(errorData clay.ErrorData) {
	fmt.Printf("Clay Error: %s\n", errorData.ErrorText)
}

// Text measurement function for Clay with Raylib
func measureTextFunction(text clay.StringSlice, config *clay.TextElementConfig, userData unsafe.Pointer) clay.Dimensions {
	// Use the built-in String() method
	textStr := text.String()

	// Use currentFont which we'll set before each text element
	font := *currentFont

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
				*currentFont,
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
	rl.InitWindow(screenWidth, screenHeight, "Monaspace Krypton Font Test")
	defer rl.CloseWindow()

	rl.SetTargetFPS(60)

	// Load all four font variants
	fontRegular = rl.LoadFontEx("MonaspaceKryptonNF-Regular.otf", 64, nil, 0)
	fontBold = rl.LoadFontEx("MonaspaceKryptonNF-Bold.otf", 64, nil, 0)
	fontItalic = rl.LoadFontEx("MonaspaceKryptonNF-Italic.otf", 64, nil, 0)
	fontBoldItalic = rl.LoadFontEx("MonaspaceKryptonNF-BoldItalic.otf", 64, nil, 0)

	// Initialize currentFont to fontRegular
	currentFont = &fontRegular

	// Defer cleanup
	defer rl.UnloadFont(fontRegular)
	defer rl.UnloadFont(fontBold)
	defer rl.UnloadFont(fontItalic)
	defer rl.UnloadFont(fontBoldItalic)

	// Initialize Clay
	totalMemorySize := clay.MinMemorySize()
	memory := make([]byte, totalMemorySize)
	arena := clay.CreateArenaWithCapacityAndMemory(memory)

	clay.Initialize(
		arena,
		clay.Dimensions{Width: screenWidth, Height: screenHeight},
		clay.ErrorHandler{ErrorHandlerFunction: errorHandler},
	)

	// Set text measurement function
	clay.SetMeasureTextFunction(measureTextFunction, unsafe.Pointer(currentFont))

	// Main loop
	for !rl.WindowShouldClose() {
		clay.BeginLayout()

		// Main container
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("MainContainer"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{
					Width:  clay.SizingGrow(0),
					Height: clay.SizingGrow(0),
				},
				Padding: clay.PaddingAll(40),
			},
			BackgroundColor: clay.Color{R: 30, G: 30, B: 35, A: 255},
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
						X: clay.ALIGN_X_LEFT,
						Y: clay.ALIGN_Y_TOP,
					},
					ChildGap: 40,
				},
			}, func() {
				// Title
				currentFont = &fontBold
				clay.Text("Monaspace Krypton Font Test", clay.TextConfig(clay.TextElementConfig{
					FontSize:  32,
					TextColor: clay.Color{R: 200, G: 220, B: 255, A: 255},
				}))

				// Regular
				currentFont = &fontRegular
				clay.Text("Regular: The quick brown fox jumps over the lazy dog", clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))

				// Bold
				currentFont = &fontBold
				clay.Text("Bold: The quick brown fox jumps over the lazy dog", clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))

				// Italic
				currentFont = &fontItalic
				clay.Text("Italic: The quick brown fox jumps over the lazy dog", clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))

				// Bold Italic
				currentFont = &fontBoldItalic
				clay.Text("Bold Italic: The quick brown fox jumps over the lazy dog", clay.TextConfig(clay.TextElementConfig{
					FontSize:  24,
					TextColor: clay.Color{R: 255, G: 255, B: 255, A: 255},
				}))
			})
		})

		renderCommands := clay.EndLayout()

		// Render
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 30, G: 30, B: 35, A: 255})

		clayRaylibRender(renderCommands)

		rl.EndDrawing()
	}
}
