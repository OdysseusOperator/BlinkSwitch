// AstroBoy4 Systems - Radar/Minimap System
// Displays a minimap in the bottom-right corner showing ship, asteroids, and mothership
// Adapted from astroBoy3's game_renderer.go

package systems

import (
	"astroboy4/gameobjects"

	rl "github.com/gen2brain/raylib-go/raylib"
)

const (
	// Local radar constants (use RadarSize and RadarRange from constants.go)
	RadarDisplaySize = RadarSize // Radar size in pixels (from constants.go)
	RadarMargin      = 10        // Distance from screen edge
	// RadarRange defined in constants.go
)

// RadarSystem handles minimap rendering
type RadarSystem struct {
	enabled bool
}

// NewRadarSystem creates a new radar system
func NewRadarSystem() *RadarSystem {
	return &RadarSystem{
		enabled: true,
	}
}

// DrawRadar renders the minimap/radar in the bottom-right corner
// mothershipX, mothershipY: position of mothership (pass nil/0 if no mothership exists yet)
// hasMothership: whether to draw mothership on radar
func (rs *RadarSystem) DrawRadar(
	shipX, shipY float32,
	asteroids []gameobjects.Asteroid,
	mothershipX, mothershipY float32,
	hasMothership bool,
) {
	if !rs.enabled {
		return
	}

	radarSize := int32(RadarDisplaySize)
	radarX := int32(rl.GetScreenWidth()) - radarSize - RadarMargin
	radarY := int32(rl.GetScreenHeight()) - radarSize - RadarMargin

	// Draw radar background
	rl.DrawRectangle(radarX, radarY, radarSize, radarSize, RadarBackgroundColor)
	rl.DrawRectangleLines(radarX, radarY, radarSize, radarSize, RadarBorderColor)

	// Ship at center of radar
	shipRadarX := radarX + radarSize/2
	shipRadarY := radarY + radarSize/2
	rl.DrawCircle(shipRadarX, shipRadarY, 3, RadarShipColor)

	// Radar scale (world units per radar pixel)
	radarScale := float32(RadarRange / float64(radarSize))

	// Draw asteroids on radar
	for _, asteroid := range asteroids {
		// Convert world coordinates to radar coordinates
		radarRelX, radarRelY := WorldToRadar(asteroid.X, asteroid.Y, shipX, shipY, radarScale)

		// Check if within radar bounds
		if radarRelX >= -radarSize/2 && radarRelX <= radarSize/2 &&
			radarRelY >= -radarSize/2 && radarRelY <= radarSize/2 {
			pixelX := shipRadarX + radarRelX
			pixelY := shipRadarY + radarRelY

			// Double-check pixel is within radar rectangle
			if pixelX >= radarX && pixelX < radarX+radarSize &&
				pixelY >= radarY && pixelY < radarY+radarSize {
				rl.DrawCircle(pixelX, pixelY, 2, RadarAsteroidColor)
			}
		}
	}

	// Draw mothership on radar (if it exists)
	if hasMothership {
		// Convert world coordinates to radar coordinates
		radarRelX, radarRelY := WorldToRadar(mothershipX, mothershipY, shipX, shipY, radarScale)

		if radarRelX >= -radarSize/2 && radarRelX <= radarSize/2 &&
			radarRelY >= -radarSize/2 && radarRelY <= radarSize/2 {
			pixelX := shipRadarX + radarRelX
			pixelY := shipRadarY + radarRelY

			if pixelX >= radarX && pixelX < radarX+radarSize &&
				pixelY >= radarY && pixelY < radarY+radarSize {
				// Mothership shown as green dot
				rl.DrawCircle(pixelX, pixelY, 3, RadarMothershipColor)
			}
		}
	}

	// Draw radar label
	rl.DrawText("RADAR", radarX, radarY-15, 10, rl.Gray)
}

// SetEnabled enables or disables the radar
func (rs *RadarSystem) SetEnabled(enabled bool) {
	rs.enabled = enabled
}

// IsEnabled returns whether the radar is enabled
func (rs *RadarSystem) IsEnabled() bool {
	return rs.enabled
}
