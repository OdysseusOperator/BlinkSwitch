// AstroBoy4 Audio System - Audio Manager
// Main audio system for managing all game sounds

package audio

import (
	"fmt"
	"unsafe"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// AudioManager handles all game audio using Raylib
type AudioManager struct {
	shootSound     rl.Sound
	explodeSound   rl.Sound
	thrusterSound  rl.Sound
	thrusterActive bool
	initialized    bool
}

// NewAudioManager creates and initializes the audio system
// Note: Raylib audio device must be initialized before calling this
func NewAudioManager() (*AudioManager, error) {
	am := &AudioManager{
		initialized: true,
	}

	fmt.Println("Audio: Creating procedural sound effects...")

	// Generate and load shoot sound
	shootSamples := GenerateShootSound()
	shootWave := rl.Wave{
		FrameCount: uint32(len(shootSamples)),
		SampleRate: uint32(SampleRate),
		SampleSize: 16, // 16-bit samples
		Channels:   1,  // Mono
		Data:       unsafe.Pointer(&shootSamples[0]),
	}
	am.shootSound = rl.LoadSoundFromWave(shootWave)
	fmt.Printf("Audio: Shoot sound generated - %d samples\n", len(shootSamples))

	// Generate and load explosion sound
	explodeSamples := GenerateExplosionSound()
	explodeWave := rl.Wave{
		FrameCount: uint32(len(explodeSamples)),
		SampleRate: uint32(SampleRate),
		SampleSize: 16,
		Channels:   1,
		Data:       unsafe.Pointer(&explodeSamples[0]),
	}
	am.explodeSound = rl.LoadSoundFromWave(explodeWave)
	fmt.Printf("Audio: Explosion sound generated - %d samples\n", len(explodeSamples))

	// Generate and load thruster sound
	thrusterSamples := GenerateThrusterSound()
	thrusterWave := rl.Wave{
		FrameCount: uint32(len(thrusterSamples)),
		SampleRate: uint32(SampleRate),
		SampleSize: 16,
		Channels:   1,
		Data:       unsafe.Pointer(&thrusterSamples[0]),
	}
	am.thrusterSound = rl.LoadSoundFromWave(thrusterWave)
	fmt.Printf("Audio: Thruster sound generated - %d samples\n", len(thrusterSamples))

	// Set volume levels
	rl.SetMasterVolume(MasterVolume)
	rl.SetSoundVolume(am.shootSound, ShootVolume)
	rl.SetSoundVolume(am.explodeSound, ExplosionVolume)
	rl.SetSoundVolume(am.thrusterSound, ThrusterVolume)

	fmt.Printf("Audio: System initialized - device ready: %v\n", rl.IsAudioDeviceReady())
	return am, nil
}

// Cleanup unloads all sounds
// Note: Audio device is managed by main Raylib, don't close it here
func (am *AudioManager) Cleanup() {
	if am.initialized {
		rl.UnloadSound(am.shootSound)
		rl.UnloadSound(am.explodeSound)
		rl.UnloadSound(am.thrusterSound)
		am.initialized = false
		fmt.Println("Audio: System cleaned up")
	}
}

// PlayShoot plays the shooting sound effect
// Won't play if already playing to prevent sound spam
func (am *AudioManager) PlayShoot() {
	if am.initialized && !rl.IsSoundPlaying(am.shootSound) {
		rl.PlaySound(am.shootSound)
	}
}

// PlayExplosion plays the explosion sound effect
// Won't play if already playing to prevent sound spam
func (am *AudioManager) PlayExplosion() {
	if am.initialized && !rl.IsSoundPlaying(am.explodeSound) {
		rl.PlaySound(am.explodeSound)
	}
}

// StartThruster starts playing the thruster sound (loops)
func (am *AudioManager) StartThruster() {
	am.thrusterActive = true
	if am.initialized && !rl.IsSoundPlaying(am.thrusterSound) {
		rl.PlaySound(am.thrusterSound)
	}
}

// UpdateThruster keeps the thruster sound looping while active
// Call this in the game update loop
func (am *AudioManager) UpdateThruster() {
	// Only restart if we want the thruster to be active and it's not playing
	if am.thrusterActive && am.initialized && !rl.IsSoundPlaying(am.thrusterSound) {
		// Restart the sound to create a seamless loop
		rl.PlaySound(am.thrusterSound)
	}
}

// StopThruster stops the thruster sound
func (am *AudioManager) StopThruster() {
	am.thrusterActive = false
	if am.initialized && rl.IsSoundPlaying(am.thrusterSound) {
		rl.StopSound(am.thrusterSound)
	}
}

// IsThrusterActive returns whether the thruster sound should be playing
func (am *AudioManager) IsThrusterActive() bool {
	return am.thrusterActive
}

// SetMasterVolume sets the master volume (0.0 to 1.0)
func (am *AudioManager) SetMasterVolume(volume float32) {
	if am.initialized {
		rl.SetMasterVolume(volume)
	}
}

// SetSoundVolume sets the volume for a specific sound type (0.0 to 1.0)
func (am *AudioManager) SetSoundVolume(soundType SoundType, volume float32) {
	if !am.initialized {
		return
	}

	switch soundType {
	case SoundShoot:
		rl.SetSoundVolume(am.shootSound, volume)
	case SoundExplosion:
		rl.SetSoundVolume(am.explodeSound, volume)
	case SoundThruster:
		rl.SetSoundVolume(am.thrusterSound, volume)
	}
}

// IsInitialized returns whether the audio system is initialized
func (am *AudioManager) IsInitialized() bool {
	return am.initialized
}
