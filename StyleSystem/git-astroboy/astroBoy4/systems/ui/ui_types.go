// AstroBoy4 UI Module - Type Definitions
// Common UI types for Clay-based interface elements

package ui

// ClayButton represents an interactive button in the Clay UI system
type ClayButton struct {
	ID      string  // Unique identifier for Clay element
	Label   string  // Display text
	X, Y    float32 // Position (for absolute positioning)
	Width   float32 // Button width
	Height  float32 // Button height
	Action  string  // Action identifier when clicked
	Hovered bool    // Current hover state
	Clicked bool    // Current click state
}

// ColorRGBA represents an RGBA color (simple wrapper for Clay compatibility)
type ColorRGBA struct {
	R, G, B, A uint8
}

// ButtonStyle defines visual styling for buttons
type ButtonStyle struct {
	DefaultColor ColorRGBA
	HoverColor   ColorRGBA
	ClickedColor ColorRGBA
	TextColor    ColorRGBA
	FontSize     int
	Padding      float32
}

// DefaultButtonStyle returns the standard button styling
func DefaultButtonStyle() ButtonStyle {
	return ButtonStyle{
		DefaultColor: ColorRGBA{R: 100, G: 100, B: 100, A: 255}, // Medium gray
		HoverColor:   ColorRGBA{R: 150, G: 150, B: 150, A: 255}, // Light gray
		ClickedColor: ColorRGBA{R: 80, G: 80, B: 80, A: 255},    // Dark gray
		TextColor:    ColorRGBA{R: 255, G: 255, B: 255, A: 255}, // White
		FontSize:     16,
		Padding:      8,
	}
}
