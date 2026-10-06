package main

import (
	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	screenWidth  = 800
	screenHeight = 600
)

var startButtonPressed = false

func main() {
	rl.InitWindow(screenWidth, screenHeight, "Raylib Go Hello World")
	defer rl.CloseWindow()

	rl.SetTargetFPS(60)

	for !rl.WindowShouldClose() {
		// Input handling
		mousePosition := rl.GetMousePosition()
		mousePressed := rl.IsMouseButtonPressed(rl.MouseLeftButton)

		// Button click detection
		buttonRect := rl.Rectangle{X: 300, Y: 200, Width: 200, Height: 60}
		if mousePressed && rl.CheckCollisionPointRec(mousePosition, buttonRect) {
			startButtonPressed = true
		}

		// Drawing
		rl.BeginDrawing()
		rl.ClearBackground(rl.Color{R: 40, G: 40, B: 40, A: 255})

		// Title
		titleText := "Hello World!"
		titleFontSize := int32(48)
		titleWidth := rl.MeasureText(titleText, titleFontSize)
		titleX := (screenWidth - titleWidth) / 2
		rl.DrawText(titleText, titleX, 100, titleFontSize, rl.White)

		// Button
		var buttonColor rl.Color
		if startButtonPressed {
			buttonColor = rl.Color{R: 100, G: 200, B: 100, A: 255}
		} else {
			buttonColor = rl.Color{R: 70, G: 130, B: 180, A: 255}
		}

		rl.DrawRectangleRounded(buttonRect, 0.2, 8, buttonColor)

		// Button text
		var buttonText string
		if startButtonPressed {
			buttonText = "Started!"
		} else {
			buttonText = "Start"
		}

		buttonFontSize := int32(24)
		buttonTextWidth := rl.MeasureText(buttonText, buttonFontSize)
		buttonTextX := buttonRect.X + (buttonRect.Width-float32(buttonTextWidth))/2
		buttonTextY := buttonRect.Y + (buttonRect.Height-float32(buttonFontSize))/2
		rl.DrawText(buttonText, int32(buttonTextX), int32(buttonTextY), buttonFontSize, rl.White)

		// Welcome message
		if startButtonPressed {
			welcomeText := "Welcome to Raylib Go!"
			welcomeFontSize := int32(20)
			welcomeWidth := rl.MeasureText(welcomeText, welcomeFontSize)
			welcomeX := (screenWidth - welcomeWidth) / 2
			rl.DrawText(welcomeText, welcomeX, 300, welcomeFontSize, rl.LightGray)
		}

		rl.EndDrawing()
	}
}