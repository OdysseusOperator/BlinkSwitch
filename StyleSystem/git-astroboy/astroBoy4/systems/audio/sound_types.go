// AstroBoy4 Audio System - Sound Types
// Defines sound types, constants, and enums for the audio system

package audio

// SoundType represents different sound effects in the game
type SoundType int

const (
	SoundShoot     SoundType = iota // Weapon firing sound
	SoundExplosion                  // Asteroid destruction sound
	SoundThruster                   // Ship thruster/engine sound
)

// Audio system constants
const (
	SampleRate = 44100 // 44.1kHz sample rate
)

// Sound duration constants (in seconds)
const (
	ShootDuration     = 0.3 // Shoot sound duration
	ExplosionDuration = 1.0 // Explosion sound duration
	ThrusterDuration  = 2.0 // Thruster sound duration (looping)
)

// Volume constants (0.0 to 1.0)
const (
	MasterVolume    = 0.8 // Master volume for all sounds
	ShootVolume     = 0.7 // Shoot sound volume
	ExplosionVolume = 0.8 // Explosion sound volume
	ThrusterVolume  = 0.6 // Thruster sound volume (quieter for looping)
)

// Frequency ranges for procedural sounds (in Hz)
const (
	// Shoot sound - low frequency "pew"
	ShootFreqStart1 = 60.0 // Starting frequency for first tone
	ShootFreqStart2 = 40.0 // Starting frequency for second tone

	// Explosion sound - rumbling impact
	ExplosionFreq1 = 200.0 // High-frequency rumble
	ExplosionFreq2 = 350.0 // High-frequency punch
	ExplosionFreq3 = 150.0 // Mid-frequency rumble
	ExplosionFreq4 = 80.0  // Low-frequency bass

	// Thruster sound - deep engine rumble
	ThrusterFreq1 = 30.0 // Very deep bass
	ThrusterFreq2 = 45.0 // Low rumble
	ThrusterFreq3 = 60.0 // Subtle harmonic
	ThrusterFreq4 = 20.0 // Ultra-deep bass
)
