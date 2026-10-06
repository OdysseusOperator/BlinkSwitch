// AstroBoy4 Systems - Game Constants
// Central configuration and constants for the entire game
// Ported from astroBoy3/src/core/constants.go

package systems

import rl "github.com/gen2brain/raylib-go/raylib"

// Game configuration constants
const (
	// Frame rate and timing
	TargetFPS = 60

	// Weapon system
	WeaponCooldownTime = 0.15  // Base cooldown between shots
	BulletLifeTime     = 3.0   // Bullet lifetime in seconds
	BulletSpeed        = 600.0 // Bullet velocity

	// Ship physics
	ShipAcceleration     = 300.0 // Thrust force
	ShipMaxSpeed         = 250.0 // Maximum ship speed
	ShipDrag             = 0.95  // Drag coefficient (0.0 = no drag, 1.0 = instant stop)
	ShipRotationSpeed    = 200.0 // Rotation speed in degrees per second
	ShipModelIdlePitch   = 0.25  // Base pitch to reveal hull thickness
	ShipModelThrustPitch = 0.45  // Pitch when thrusters are firing
	ShipModelTurnRoll    = 0.30  // Roll applied when turning
	ShipModelTiltSpeed   = 8.0   // Interpolation speed for pitch/roll changes

	// Collision
	CollisionImpulse    = 120.0 // Impulse strength when ship hits asteroid
	ShipCollisionRadius = 10.0  // Ship collision radius

	// Radar/Minimap configuration
	RadarSize  = 150    // Radar display size in pixels
	RadarRange = 1000.0 // Radar world range

	// UI layout
	UIMargin           = 10  // Standard UI margin
	PanelWidth         = 300 // Standard panel width
	PanelHeight        = 120 // Standard panel height
	MissionPanelHeight = 80  // Mission HUD panel height

	// Asteroid system
	AsteroidMinSize               = 25.0   // Minimum size before asteroid is destroyed
	AsteroidMaxCount              = 40     // Maximum concurrent asteroids
	AsteroidSpawnCooldownMin      = 0.2    // Minimum spawn cooldown in seconds
	AsteroidSpawnCooldownMax      = 0.2    // Maximum spawn cooldown in seconds
	AsteroidSpawnAreaSize         = 2000.0 // Spawn area size around ship
	AsteroidSafeSpawnDistance     = 200.0  // Minimum safe distance from ship
	AsteroidMinSpawnSize          = 40.0   // Minimum spawn size
	AsteroidMaxSpawnSize          = 70.0   // Maximum spawn size
	AsteroidSpawnScreenBuffer     = 300.0  // Pixels beyond visible window for spawning
	AsteroidInitialOnScreenCount  = 4      // Number of asteroids spawned in view on start
	AsteroidInitialOnScreenRadius = 500.0  // Radius for in-view initial spawn placement
	AsteroidSplitSizeMultiplier   = 0.6    // Size multiplier when splitting
	AsteroidFragmentMinSpeed      = 40.0   // Minimum fragment speed
	AsteroidFragmentMaxSpeed      = 70.0   // Maximum fragment speed
	AsteroidCollisionMultiplier   = 0.8    // Collision radius multiplier

	// Ship rendering
	ShipBackOffset = 10.0 // Back of ship offset for thruster

	// Thruster flame
	FlameMinLength = 10.0 // Minimum flame length
	FlameMaxLength = 18.0 // Maximum flame length (min + 8)
	FlameWidth     = 4.0  // Flame width

	// Mothership
	MothershipPulseOffset             = 5.0 // Pulse ring base offset
	MothershipPulseFrequency          = 4.0 // Pulse animation frequency
	MothershipPulseAmplitude          = 3.0 // Pulse animation amplitude
	MothershipResetDistanceMultiplier = 2.0 // Distance multiplier for docking reset

	// 3D rendering
	World3DScaleFactor  = 50.0 // World to 3D coordinate scale
	Asteroid3DSizeScale = 30.0 // Asteroid size to 3D scale

	// Collision detection
	BulletRadius          = 3.0   // Bullet collision radius
	CollisionImpulseForce = 120.0 // Force applied when ship hits asteroid
)

// Common colors used throughout the game
var (
	// Background colors
	SpaceBackgroundColor = rl.Color{R: 5, G: 5, B: 15, A: 255}
	DarkSpaceColor       = rl.Color{R: 10, G: 10, B: 30, A: 255}
	MenuBackgroundColor  = rl.Color{R: 10, G: 10, B: 40, A: 255}

	// UI colors
	PanelBackgroundColor = rl.Color{R: 0, G: 0, B: 30, A: 180}
	PanelBorderColor     = rl.Color{R: 100, G: 150, B: 200, A: 255}

	// Text colors
	TitleColor     = rl.Color{R: 255, G: 200, B: 100, A: 255} // Golden
	HighlightColor = rl.Color{R: 255, G: 255, B: 0, A: 255}   // Yellow
	SuccessColor   = rl.Color{R: 100, G: 255, B: 100, A: 255} // Light green
	WarningColor   = rl.Color{R: 255, G: 255, B: 0, A: 255}   // Yellow
	DangerColor    = rl.Color{R: 255, G: 100, B: 100, A: 255} // Red
	InfoColor      = rl.Color{R: 100, G: 200, B: 255, A: 255} // Blue
	WhiteColor     = rl.Color{R: 255, G: 255, B: 255, A: 255} // White
	LightGrayColor = rl.Color{R: 200, G: 200, B: 200, A: 255} // Light gray

	// Mothership colors
	MothershipHullColor   = rl.Color{R: 80, G: 80, B: 120, A: 255}
	MothershipBorderColor = rl.Color{R: 150, G: 150, B: 200, A: 255}
	MothershipBayColor    = rl.Color{R: 40, G: 40, B: 80, A: 255}
	MothershipBayBorder   = rl.Color{R: 100, G: 100, B: 150, A: 255}
	MothershipIndicator   = rl.Color{R: 0, G: 255, B: 255, A: 150}

	// Mission colors (for future use)
	MissionActiveColor   = rl.Color{R: 100, G: 255, B: 100, A: 180} // Light green
	MissionCompleteColor = rl.Color{R: 0, G: 255, B: 0, A: 180}     // Green
	MissionPendingColor  = rl.Color{R: 255, G: 255, B: 0, A: 180}   // Yellow

	// Radar colors
	RadarBackgroundColor = rl.Color{R: 0, G: 0, B: 50, A: 150}
	RadarBorderColor     = rl.Color{R: 100, G: 100, B: 100, A: 255}
	RadarShipColor       = rl.Color{R: 255, G: 50, B: 50, A: 255}
	RadarAsteroidColor   = rl.Color{R: 200, G: 200, B: 200, A: 255}
	RadarMothershipColor = rl.Color{R: 0, G: 255, B: 100, A: 255}
	RadarMissionColor    = rl.Color{R: 255, G: 100, B: 100, A: 255}

	// Bullet colors
	BulletColor = rl.Color{R: 255, G: 255, B: 0, A: 255} // Yellow

	// Asteroid colors
	AsteroidFillColor = rl.Color{R: 150, G: 150, B: 150, A: 255} // Gray
	AsteroidEdgeColor = rl.Color{R: 0, G: 0, B: 0, A: 255}       // Black

	// Debug visualization colors
	DebugBoundingBoxColor = rl.Color{R: 100, G: 100, B: 255, A: 128} // Blue - AABB boxes
	DebugTier1MissColor   = rl.Color{R: 100, G: 100, B: 255, A: 255} // Blue - TIER 1 bounds (no collision)
	DebugTier1HitColor    = rl.Color{R: 255, G: 255, B: 0, A: 255}   // Yellow - TIER 1 hit, TIER 2 miss
	DebugTier2MissColor   = rl.Color{R: 0, G: 255, B: 100, A: 255}   // Green - No collision
	DebugTier2HitColor    = rl.Color{R: 255, G: 50, B: 50, A: 255}   // Red - Collision detected
	DebugShipColor        = rl.Color{R: 100, G: 150, B: 255, A: 255} // Light blue - Ship shape
	DebugPointColor       = rl.Color{R: 255, G: 255, B: 0, A: 255}   // Yellow - Bullet point
	DebugTextColor        = rl.Color{R: 255, G: 255, B: 255, A: 255} // White - Debug text
	DebugBackgroundColor  = rl.Color{R: 0, G: 0, B: 0, A: 180}       // Semi-transparent black
)

// Available resolution options
var AvailableResolutions = []Resolution{
	{Width: 640, Height: 480, Label: "640x480"},
	{Width: 800, Height: 600, Label: "800x600"},
	{Width: 1024, Height: 768, Label: "1024x768"},
	{Width: 1280, Height: 720, Label: "1280x720"},
	{Width: 1600, Height: 900, Label: "1600x900"},
	{Width: 1920, Height: 1080, Label: "1920x1080"},
}
