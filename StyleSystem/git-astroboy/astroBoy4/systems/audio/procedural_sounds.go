// AstroBoy4 Audio System - Procedural Sound Generation
// Generates sound effects procedurally without external audio files

package audio

import (
	"math"
)

// Global sample data arrays to prevent garbage collection
// These are filled once during initialization
var (
	shootData    []int16 // 16-bit PCM samples for shoot sound
	explodeData  []int16 // 16-bit PCM samples for explosion sound
	thrusterData []int16 // 16-bit PCM samples for thruster sound
)

// GenerateShootSound creates a "pew" laser-like sound
// Low-frequency sound that fades smoothly to zero
func GenerateShootSound() []int16 {
	samples := int(ShootDuration * SampleRate)
	shootData = make([]int16, samples)

	// Generate "pew" sound - deep sound that fades to zero
	for i := 0; i < samples; i++ {
		t := float64(i) / SampleRate
		progress := t / ShootDuration // 0.0 to 1.0 progress through the sound

		// Smooth fadeout that reaches zero by the end
		var amplitude float64
		if progress < 0.5 {
			// Exponential decay for first 50%
			amplitude = 0.5 * math.Exp(-t*4)
		} else {
			// Stronger linear fade from current level to zero in last 50%
			fadeProgress := (progress - 0.5) / 0.5               // 0.0 to 1.0 in last 50%
			currentLevel := 0.5 * math.Exp(-0.5*ShootDuration*4) // Level at 50% point
			amplitude = currentLevel * (1.0 - fadeProgress)      // Linear fade to zero
		}

		// Create ONLY low-frequency components - no high-pitched ping!
		// Very low frequency sine waves only
		lowFreq1 := ShootFreqStart1 * math.Exp(-t*8) // Starts at 60Hz, drops lower
		lowFreq2 := ShootFreqStart2 * math.Exp(-t*6) // Starts at 40Hz, drops lower

		// Pure low-frequency content only
		lowTone1 := math.Sin(2 * math.Pi * lowFreq1 * t)
		lowTone2 := math.Sin(2 * math.Pi * lowFreq2 * t)

		// Very controlled noise - only low-frequency noise
		slowNoise := math.Mod(float64(i/100)*0.01, 2.0) - 1.0 // Much slower noise

		// Mix only low-frequency components
		sample := amplitude * (0.4*lowTone1 + 0.3*lowTone2 + 0.3*slowNoise)

		// Convert to 16-bit PCM
		shootData[i] = int16(sample * 32767)
	}

	return shootData
}

// GenerateExplosionSound creates a rumbling explosion sound
// Multiple frequencies with lots of noise for impact
func GenerateExplosionSound() []int16 {
	samples := int(ExplosionDuration * SampleRate)
	explodeData = make([]int16, samples)

	// Generate explosion sound - low frequency rumble with noise
	for i := 0; i < samples; i++ {
		t := float64(i) / SampleRate

		// Create explosion sound:
		// - Mix of higher frequencies for more punch
		// - Lots of noise
		// - Starts very loud, decays over time

		// Higher frequency rumble for more impact
		rumble1 := math.Sin(2 * math.Pi * ExplosionFreq1 * t) // 200Hz
		rumble2 := math.Sin(2 * math.Pi * ExplosionFreq2 * t) // 350Hz
		rumble3 := math.Sin(2 * math.Pi * ExplosionFreq3 * t) // 150Hz
		rumble4 := math.Sin(2 * math.Pi * ExplosionFreq4 * t) // 80Hz

		// Create pseudo-random noise
		noise := math.Mod(float64(i*17+7)*0.00001, 2.0) - 1.0

		// Much louder amplitude with exponential decay
		amplitude := 0.8 * math.Exp(-t*1.5) // Louder and longer decay

		// Mix rumble and noise
		sample := amplitude * (0.25*(rumble1+rumble2+rumble3+rumble4) + 0.5*noise)

		// Clip to prevent distortion
		if sample > 1.0 {
			sample = 1.0
		}
		if sample < -1.0 {
			sample = -1.0
		}

		// Convert to 16-bit PCM
		explodeData[i] = int16(sample * 32767)
	}

	return explodeData
}

// GenerateThrusterSound creates a looping thruster/engine sound
// Deep, continuous engine rumble with subtle variations
func GenerateThrusterSound() []int16 {
	samples := int(ThrusterDuration * SampleRate)
	thrusterData = make([]int16, samples)

	// Generate thruster sound - continuous engine rumble
	for i := 0; i < samples; i++ {
		t := float64(i) / SampleRate

		// Create a continuous engine rumble:
		// - Multiple low frequencies for richness
		// - Slight variations to avoid monotony
		// - Seamless loop (starts and ends at same phase)

		// Much deeper, lower frequency engine rumble
		engine1 := math.Sin(2 * math.Pi * ThrusterFreq1 * t) // 30Hz very deep bass
		engine2 := math.Sin(2 * math.Pi * ThrusterFreq2 * t) // 45Hz low rumble
		engine3 := math.Sin(2 * math.Pi * ThrusterFreq3 * t) // 60Hz subtle harmonic
		engine4 := math.Sin(2 * math.Pi * ThrusterFreq4 * t) // 20Hz ultra-deep bass

		// Add some very subtle variation/modulation
		modulation := 0.05 * math.Sin(2*math.Pi*2*t) // 2Hz slow, subtle variation

		// Create very quiet engine noise
		engineNoise := math.Mod(float64(i*13+5)*0.00002, 2.0) - 1.0 // Much quieter noise

		// Much quieter, more subtle amplitude
		amplitude := 0.15 + modulation // Much quieter than explosion

		// Mix engine components with emphasis on deep frequencies
		engineSound := 0.4*engine1 + 0.3*engine2 + 0.2*engine3 + 0.5*engine4 // More bass
		sample := amplitude * (0.8*engineSound + 0.2*engineNoise)            // Less noise, more tone

		// Clip to prevent distortion
		if sample > 1.0 {
			sample = 1.0
		}
		if sample < -1.0 {
			sample = -1.0
		}

		// Convert to 16-bit PCM
		thrusterData[i] = int16(sample * 32767)
	}

	return thrusterData
}

// GetShootData returns the generated shoot sound samples
func GetShootData() []int16 {
	return shootData
}

// GetExplodeData returns the generated explosion sound samples
func GetExplodeData() []int16 {
	return explodeData
}

// GetThrusterData returns the generated thruster sound samples
func GetThrusterData() []int16 {
	return thrusterData
}
