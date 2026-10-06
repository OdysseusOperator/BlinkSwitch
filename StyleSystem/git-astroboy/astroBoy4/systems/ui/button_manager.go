// AstroBoy4 UI Module - Button Manager
// Handles Clay-based button creation, state management, and interaction
// Ported from astroBoy3/src/ui/ui_buttons_clay.go

package ui

import (
	"github.com/TotallyGamerJet/clay"
	rl "github.com/gen2brain/raylib-go/raylib"
)

// ButtonManager manages all interactive buttons in the UI
type ButtonManager struct {
	buttons       []ClayButton
	mousePosition rl.Vector2
	mousePressed  bool
	mouseDown     bool
	style         ButtonStyle
}

// NewButtonManager creates a new button manager with default styling
func NewButtonManager() *ButtonManager {
	return &ButtonManager{
		buttons: make([]ClayButton, 0),
		style:   DefaultButtonStyle(),
	}
}

// AddButton adds a button to the manager
func (bm *ButtonManager) AddButton(id, label, action string, x, y, width, height float32) {
	button := ClayButton{
		ID:     id,
		Label:  label,
		X:      x,
		Y:      y,
		Width:  width,
		Height: height,
		Action: action,
	}
	bm.buttons = append(bm.buttons, button)
}

// Update handles mouse input and updates button states
// Call this before rendering Clay UI
func (bm *ButtonManager) Update() {
	bm.mousePosition = rl.GetMousePosition()
	bm.mousePressed = rl.IsMouseButtonPressed(rl.MouseLeftButton)
	bm.mouseDown = rl.IsMouseButtonDown(rl.MouseLeftButton)

	// Update Clay pointer state for hover detection
	clay.SetPointerState(clay.Vector2{X: bm.mousePosition.X, Y: bm.mousePosition.Y}, bm.mouseDown)

	// Update button states
	for i := range bm.buttons {
		button := &bm.buttons[i]
		buttonElementId := clay.ID(button.ID)

		// Check if mouse is hovering over this button
		button.Hovered = clay.PointerOver(buttonElementId)

		// Check for button click
		if button.Hovered && bm.mousePressed {
			button.Clicked = true
		} else {
			button.Clicked = false
		}
	}
}

// RenderButton renders a single button using Clay
// Call this inside Clay.BeginLayout()/EndLayout()
func (bm *ButtonManager) RenderButton(button ClayButton) {
	// Determine button color based on state
	bgColor := bm.toClayColor(bm.style.DefaultColor)
	if button.Hovered {
		bgColor = bm.toClayColor(bm.style.HoverColor)
	}
	if button.Clicked {
		bgColor = bm.toClayColor(bm.style.ClickedColor)
	}

	// Create button using Clay UI
	clay.UI()(clay.ElementDeclaration{
		Id: clay.ID(button.ID),
		Layout: clay.LayoutConfig{
			Sizing: clay.Sizing{
				Width:  clay.SizingFixed(button.Width),
				Height: clay.SizingFixed(button.Height),
			},
			Padding: clay.PaddingAll(uint16(bm.style.Padding)),
			ChildAlignment: clay.ChildAlignment{
				X: clay.ALIGN_X_CENTER,
				Y: clay.ALIGN_Y_CENTER,
			},
		},
		BackgroundColor: bgColor,
	}, func() {
		// Button text
		textColor := bm.toClayColor(bm.style.TextColor)
		clay.Text(button.Label, clay.TextConfig(clay.TextElementConfig{
			FontSize:  uint16(bm.style.FontSize),
			TextColor: textColor,
		}))
	})
}

// RenderAllButtons renders all managed buttons
// Call this inside Clay.BeginLayout()/EndLayout()
func (bm *ButtonManager) RenderAllButtons() {
	for _, button := range bm.buttons {
		bm.RenderButton(button)
	}
}

// GetClickedAction returns the action string of any clicked button
// Returns empty string if no button was clicked
func (bm *ButtonManager) GetClickedAction() string {
	for _, button := range bm.buttons {
		if button.Clicked {
			return button.Action
		}
	}
	return ""
}

// Clear removes all buttons from the manager
func (bm *ButtonManager) Clear() {
	bm.buttons = bm.buttons[:0]
}

// GetButtonCount returns the number of managed buttons
func (bm *ButtonManager) GetButtonCount() int {
	return len(bm.buttons)
}

// SetStyle updates the button styling
func (bm *ButtonManager) SetStyle(style ButtonStyle) {
	bm.style = style
}

// toClayColor converts ColorRGBA to clay.Color
func (bm *ButtonManager) toClayColor(c ColorRGBA) clay.Color {
	return clay.Color{
		R: float32(c.R),
		G: float32(c.G),
		B: float32(c.B),
		A: float32(c.A),
	}
}
