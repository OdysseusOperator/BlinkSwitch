package main

import (
	"fmt"
	"unsafe"

	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	screenWidth  = 960
	screenHeight = 620
)

var currentFont rl.Font

func clayError(errorData clay.ErrorData) {
	fmt.Printf("Clay error: %s\n", errorData.ErrorText)
}

func measureText(text clay.StringSlice, config *clay.TextElementConfig, _ unsafe.Pointer) clay.Dimensions {
	size := rl.MeasureTextEx(currentFont, text.String(), float32(config.FontSize), 1)
	return clay.Dimensions{Width: size.X, Height: size.Y}
}

func toRaylibColor(color clay.Color) rl.Color {
	return rl.Color{R: uint8(color.R), G: uint8(color.G), B: uint8(color.B), A: uint8(color.A)}
}

func renderClay(commands clay.RenderCommandArray) {
	for i := int32(0); i < commands.Length; i++ {
		command := clay.RenderCommandArray_Get(&commands, i)
		box := command.BoundingBox

		switch command.CommandType {
		case clay.RENDER_COMMAND_TYPE_RECTANGLE:
			rl.DrawRectangle(
				int32(box.X), int32(box.Y), int32(box.Width), int32(box.Height),
				toRaylibColor(command.RenderData.Rectangle.BackgroundColor),
			)
		case clay.RENDER_COMMAND_TYPE_TEXT:
			text := command.RenderData.Text
			rl.DrawTextEx(
				currentFont,
				text.StringContents.String(),
				rl.Vector2{X: box.X, Y: box.Y},
				float32(text.FontSize),
				1,
				toRaylibColor(text.TextColor),
			)
		}
	}
}

func text(value string, size uint16, color clay.Color) {
	clay.Text(value, clay.TextConfig(clay.TextElementConfig{
		FontSize:  size,
		TextColor: color,
	}))
}

func card(id string, label string, value string, accent clay.Color) {
	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID(id),
		Layout: clay.LayoutConfig{
			LayoutDirection: clay.TOP_TO_BOTTOM,
			Padding:         clay.PaddingAll(20),
			ChildGap:        8,
		},
		BackgroundColor: clay.Color{R: 29, G: 35, B: 48, A: 255},
	}, func() {
		text(label, 14, clay.Color{R: 142, G: 157, B: 181, A: 255})
		text(value, 28, accent)
	})
}

func buildUI() {
	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID("App"),
		Layout: clay.LayoutConfig{
			LayoutDirection: clay.TOP_TO_BOTTOM,
			Sizing: clay.Sizing{
				Width:  clay.SizingGrow(0),
				Height: clay.SizingGrow(0),
			},
			Padding:  clay.PaddingAll(32),
			ChildGap: 24,
		},
		BackgroundColor: clay.Color{R: 15, G: 19, B: 28, A: 255},
	}, func() {
		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("Header"),
			Layout: clay.LayoutConfig{
				Sizing: clay.Sizing{Width: clay.SizingGrow(0)},
				ChildAlignment: clay.ChildAlignment{
					X: clay.ALIGN_X_LEFT,
					Y: clay.ALIGN_Y_CENTER,
				},
			},
		}, func() {
			text("BLINKSWITCH", 26, clay.Color{R: 232, G: 239, B: 255, A: 255})
			text("  /  layout preview", 16, clay.Color{R: 112, G: 131, B: 164, A: 255})
		})

		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("Summary"),
			Layout: clay.LayoutConfig{
				LayoutDirection: clay.LEFT_TO_RIGHT,
				Sizing:          clay.Sizing{Width: clay.SizingGrow(0)},
				ChildGap:        16,
			},
		}, func() {
			card("Monitors", "MONITORS", "3 connected", clay.Color{R: 116, G: 218, B: 174, A: 255})
			card("Layouts", "SAVED LAYOUTS", "8 ready", clay.Color{R: 143, G: 177, B: 255, A: 255})
			card("Windows", "ACTIVE WINDOWS", "12 tracked", clay.Color{R: 255, G: 193, B: 112, A: 255})
		})

		clay.UI()(clay.ElementDeclaration{
			Id: clay.ID("Panel"),
			Layout: clay.LayoutConfig{
				LayoutDirection: clay.TOP_TO_BOTTOM,
				Sizing:          clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)},
				Padding:         clay.PaddingAll(24),
				ChildGap:        16,
			},
			BackgroundColor: clay.Color{R: 22, G: 27, B: 38, A: 255},
		}, func() {
			text("Current arrangement", 20, clay.Color{R: 232, G: 239, B: 255, A: 255})
			text("A small Clay layout rendered directly through Raylib.", 15, clay.Color{R: 142, G: 157, B: 181, A: 255})
			clay.UI()(clay.ElementDeclaration{
				Id: clay.ID("Arrangement"),
				Layout: clay.LayoutConfig{
					LayoutDirection: clay.LEFT_TO_RIGHT,
					Sizing:          clay.Sizing{Width: clay.SizingGrow(0), Height: clay.SizingGrow(0)},
					ChildGap:        12,
				},
			}, func() {
				card("Primary", "PRIMARY", "Editor", clay.Color{R: 232, G: 239, B: 255, A: 255})
				card("Secondary", "SECONDARY", "Browser", clay.Color{R: 232, G: 239, B: 255, A: 255})
				card("Utility", "UTILITY", "Terminal", clay.Color{R: 232, G: 239, B: 255, A: 255})
			})
		})

		text("Clay computes the layout; Raylib draws its render commands.", 14, clay.Color{R: 91, G: 108, B: 137, A: 255})
	})
}

func main() {
	rl.InitWindow(screenWidth, screenHeight, "Clay + Raylib Dashboard")
	defer rl.CloseWindow()
	rl.SetTargetFPS(60)

	currentFont = rl.GetFontDefault()

	arena := clay.CreateArenaWithCapacityAndMemory(make([]byte, clay.MinMemorySize()))
	clay.Initialize(
		arena,
		clay.Dimensions{Width: screenWidth, Height: screenHeight},
		clay.ErrorHandler{ErrorHandlerFunction: clayError},
	)
	clay.SetMeasureTextFunction(measureText, unsafe.Pointer(&currentFont))

	for !rl.WindowShouldClose() {
		clay.BeginLayout()
		buildUI()
		commands := clay.EndLayout()

		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 15, G: 19, B: 28, A: 255})
		renderClay(commands)
		rl.EndDrawing()
	}
}
