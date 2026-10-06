// AstroBoy4 Systems - Asteroid Shape Registry
// Maintains a registry of available asteroid shapes
// Used by AsteroidManager for random shape selection

package systems

import (
	"astroboy4/gameobjects"
)

// Shape registry - automatically includes all asteroid shapes
// This is used by AsteroidManager.GenerateAsteroid() to select random shapes
var shapeRegistry []gameobjects.AsteroidShape

// init initializes the shape registry with all available shapes
func init() {
	shapeRegistry = []gameobjects.AsteroidShape{
		gameobjects.NewPyramidShape(),
		gameobjects.NewCubeShape(),
		gameobjects.NewOctahedronShape(),
	}
}
