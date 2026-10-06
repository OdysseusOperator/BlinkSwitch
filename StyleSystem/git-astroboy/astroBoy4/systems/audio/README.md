# AstroBoy4 Audio System

## Overview
The audio system provides procedurally-generated sound effects without requiring external audio files. All sounds are generated at runtime using 16-bit PCM audio at 44.1kHz.

## Structure

```
systems/audio/
├── sound_types.go       # Constants, enums, and type definitions
├── procedural_sounds.go # Procedural sound generation algorithms
├── audio_manager.go     # Main audio management system
└── README.md           # This file
```

## Features

### Procedural Sound Generation
- **No external files needed** - All sounds generated at runtime
- **16-bit PCM audio** at 44.1kHz sample rate
- **Memory-efficient** - Global sample arrays prevent garbage collection

### Sound Effects

#### 1. Shoot Sound (0.3 seconds)
- **Type:** Weapon firing effect
- **Characteristics:** 
  - Low-frequency "pew" (30-60Hz)
  - Smooth exponential decay
  - No high-pitched ping
- **Trigger:** When player fires bullet (Space key)
- **Volume:** 0.7

#### 2. Explosion Sound (1.0 seconds)
- **Type:** Asteroid destruction
- **Characteristics:**
  - Multi-frequency rumble (80-350Hz)
  - Heavy noise component for impact
  - Loud initial hit with exponential decay
- **Trigger:** When asteroid is destroyed
- **Volume:** 0.8

#### 3. Thruster Sound (2.0 seconds, looping)
- **Type:** Ship engine/thruster
- **Characteristics:**
  - Ultra-deep bass (20-60Hz)
  - Subtle modulation (2Hz)
  - Seamless loop
- **Trigger:** When player holds thrust key (W/Up)
- **Volume:** 0.6 (quieter for continuous play)

## Usage

### Initialization

```go
import "astroboy4/systems/audio"

// Initialize Raylib audio device first
rl.InitAudioDevice()
defer rl.CloseAudioDevice()

// Create audio manager
audioMgr, err := audio.NewAudioManager()
if err != nil {
    // Handle error
}
defer audioMgr.Cleanup()
```

### Playing Sounds

```go
// Shoot sound (one-shot)
audioMgr.PlayShoot()

// Explosion sound (one-shot)
audioMgr.PlayExplosion()

// Thruster sound (looping)
audioMgr.StartThruster()        // Start looping
audioMgr.UpdateThruster()       // Call in game loop to maintain loop
audioMgr.StopThruster()         // Stop looping
```

### Volume Control

```go
// Set master volume (0.0 to 1.0)
audioMgr.SetMasterVolume(0.8)

// Set individual sound volumes
audioMgr.SetSoundVolume(audio.SoundShoot, 0.7)
audioMgr.SetSoundVolume(audio.SoundExplosion, 0.8)
audioMgr.SetSoundVolume(audio.SoundThruster, 0.6)
```

## Sound Generation Details

### Shoot Sound Algorithm
1. **Duration:** 0.3 seconds
2. **Envelope:** 
   - First 50%: Exponential decay
   - Last 50%: Linear fade to zero
3. **Frequency Components:**
   - 60Hz tone (exponentially decreasing)
   - 40Hz tone (exponentially decreasing)
   - Low-frequency noise
4. **Mix:** 40% tone1 + 30% tone2 + 30% noise

### Explosion Sound Algorithm
1. **Duration:** 1.0 seconds
2. **Envelope:** Exponential decay (factor: 1.5)
3. **Frequency Components:**
   - 200Hz rumble
   - 350Hz punch
   - 150Hz mid rumble
   - 80Hz bass
   - Pseudo-random noise
4. **Mix:** 25% rumbles + 50% noise
5. **Amplitude:** 0.8 (loud!)

### Thruster Sound Algorithm
1. **Duration:** 2.0 seconds (seamless loop)
2. **Envelope:** Constant with subtle modulation
3. **Frequency Components:**
   - 30Hz very deep bass
   - 45Hz low rumble
   - 60Hz subtle harmonic
   - 20Hz ultra-deep bass
   - Low-frequency engine noise
4. **Modulation:** 2Hz sine wave (±0.05 amplitude)
5. **Mix:** 80% engine tones + 20% noise
6. **Base Amplitude:** 0.15 (quiet for continuous play)

## Future Expansion

The audio folder structure supports adding:
- `music.go` - Background music system
- `spatial_audio.go` - 3D positional audio
- `audio_mixer.go` - Advanced mixing and effects
- `sound_loader.go` - External sound file loading
- Additional procedural sounds (power-ups, UI, etc.)

## Technical Notes

### Anti-Spam Protection
- Sounds won't play if already playing
- Prevents audio glitches from rapid firing

### Thruster Loop Management
- `StartThruster()` - Activates looping
- `UpdateThruster()` - Maintains loop (call each frame)
- `StopThruster()` - Deactivates looping
- Seamless 2-second loop with phase-aligned frequencies

### Memory Management
- Global sample arrays prevent GC overhead
- Samples generated once at initialization
- Proper cleanup with `Cleanup()` method

## Performance

- **Memory:** ~300KB for all sound samples
- **CPU:** Negligible (sounds generated once)
- **Audio Quality:** 16-bit 44.1kHz (CD quality)

## Dependencies

- `github.com/gen2brain/raylib-go/raylib` - Raylib audio functions
- Go standard library (`math`, `unsafe`)
