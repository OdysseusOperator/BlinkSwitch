// AstroBoy4 Systems - Settings System
// Manages game settings persistence (resolution, fullscreen)
// Settings are saved to user config directory as JSON

package systems

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Settings represents the game configuration
type Settings struct {
	ResolutionIndex int  `json:"resolutionIndex"` // Index into AvailableResolutions
	Fullscreen      bool `json:"fullscreen"`      // Fullscreen mode
}

// SettingsManager manages loading, saving, and applying game settings
type SettingsManager struct {
	currentSettings Settings
	pendingSettings Settings // Settings being edited in UI (not yet applied)
	previousState   int      // Store previous game state to return to after settings
}

// NewSettingsManager creates a new settings manager with defaults
func NewSettingsManager() *SettingsManager {
	defaults := getDefaultSettings()
	return &SettingsManager{
		currentSettings: defaults,
		pendingSettings: defaults,
		previousState:   0, // StateMenu
	}
}

// getDefaultSettings returns sensible default settings
func getDefaultSettings() Settings {
	return Settings{
		ResolutionIndex: 3, // 1280x720 (index 3 in AvailableResolutions)
		Fullscreen:      false,
	}
}

// getSettingsFilePath returns the path to the settings file
func getSettingsFilePath() (string, error) {
	configDir, err := os.UserConfigDir()
	if err != nil {
		return "", fmt.Errorf("error getting config directory: %v", err)
	}

	astroboyDir := filepath.Join(configDir, "astroboy4")
	err = os.MkdirAll(astroboyDir, 0755)
	if err != nil {
		return "", fmt.Errorf("error creating config directory: %v", err)
	}

	return filepath.Join(astroboyDir, "settings.json"), nil
}

// LoadSettings loads settings from JSON file, returns defaults if file doesn't exist
func (sm *SettingsManager) LoadSettings() Settings {
	settingsPath, err := getSettingsFilePath()
	if err != nil {
		fmt.Printf("Settings: %v, using defaults\n", err)
		return getDefaultSettings()
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		// File doesn't exist or can't be read - use defaults
		fmt.Println("Settings: No settings file found, using defaults")
		return getDefaultSettings()
	}

	var settings Settings
	err = json.Unmarshal(data, &settings)
	if err != nil {
		fmt.Printf("Settings: Error parsing settings file: %v, using defaults\n", err)
		return getDefaultSettings()
	}

	// Validate and fix any invalid values
	sm.validateSettings(&settings)

	fmt.Printf("Settings: Loaded from %s\n", settingsPath)
	sm.currentSettings = settings
	sm.pendingSettings = settings
	return settings
}

// SaveSettings saves settings to JSON file
func (sm *SettingsManager) SaveSettings(settings Settings) error {
	settingsPath, err := getSettingsFilePath()
	if err != nil {
		return err
	}

	// Validate before saving
	sm.validateSettings(&settings)

	data, err := json.MarshalIndent(settings, "", "  ")
	if err != nil {
		return fmt.Errorf("error marshaling settings: %v", err)
	}

	err = os.WriteFile(settingsPath, data, 0644)
	if err != nil {
		return fmt.Errorf("error writing settings file: %v", err)
	}

	fmt.Printf("Settings: Saved to %s\n", settingsPath)
	sm.currentSettings = settings
	return nil
}

// validateSettings ensures all settings values are within valid ranges
func (sm *SettingsManager) validateSettings(settings *Settings) {
	// Clamp resolution index to valid range
	if settings.ResolutionIndex < 0 {
		settings.ResolutionIndex = 0
	}
	if settings.ResolutionIndex >= len(AvailableResolutions) {
		settings.ResolutionIndex = len(AvailableResolutions) - 1
	}
}

// ApplySettings applies settings to the game (resolution, fullscreen)
func (sm *SettingsManager) ApplySettings(settings Settings) {
	sm.validateSettings(&settings)

	// Get the target resolution
	res := AvailableResolutions[settings.ResolutionIndex]

	// Handle fullscreen state
	isCurrentlyFullscreen := rl.IsWindowFullscreen()

	if settings.Fullscreen && !isCurrentlyFullscreen {
		// Enter fullscreen
		rl.ToggleFullscreen()
		fmt.Println("Settings: Entered fullscreen mode")
	} else if !settings.Fullscreen && isCurrentlyFullscreen {
		// Exit fullscreen
		rl.ToggleFullscreen()
		fmt.Println("Settings: Exited fullscreen mode")
	}

	// Apply resolution (only matters in windowed mode)
	if !settings.Fullscreen {
		currentWidth := rl.GetScreenWidth()
		currentHeight := rl.GetScreenHeight()

		if int(currentWidth) != res.Width || int(currentHeight) != res.Height {
			rl.SetWindowSize(res.Width, res.Height)
			fmt.Printf("Settings: Resolution changed to %s\n", res.Label)
		}
	}

	sm.currentSettings = settings
}

// GetCurrentSettings returns the currently active settings
func (sm *SettingsManager) GetCurrentSettings() Settings {
	return sm.currentSettings
}

// GetPendingSettings returns the settings being edited in the UI
func (sm *SettingsManager) GetPendingSettings() Settings {
	return sm.pendingSettings
}

// SetPendingSettings updates the pending settings (UI changes)
func (sm *SettingsManager) SetPendingSettings(settings Settings) {
	sm.pendingSettings = settings
}

// StartEditing prepares for editing settings (copy current to pending)
func (sm *SettingsManager) StartEditing(previousState int) {
	sm.pendingSettings = sm.currentSettings
	sm.previousState = previousState
}

// ApplyPendingSettings applies the pending settings and saves them
func (sm *SettingsManager) ApplyPendingSettings() error {
	sm.ApplySettings(sm.pendingSettings)
	return sm.SaveSettings(sm.pendingSettings)
}

// DiscardPendingSettings discards pending changes and reverts to current
func (sm *SettingsManager) DiscardPendingSettings() {
	sm.pendingSettings = sm.currentSettings
}

// GetPreviousState returns the state to return to after settings
func (sm *SettingsManager) GetPreviousState() int {
	return sm.previousState
}

// CycleResolution cycles to the next resolution (for UI controls)
func (sm *SettingsManager) CycleResolution(forward bool) {
	if forward {
		sm.pendingSettings.ResolutionIndex++
		if sm.pendingSettings.ResolutionIndex >= len(AvailableResolutions) {
			sm.pendingSettings.ResolutionIndex = 0 // Wrap around
		}
	} else {
		sm.pendingSettings.ResolutionIndex--
		if sm.pendingSettings.ResolutionIndex < 0 {
			sm.pendingSettings.ResolutionIndex = len(AvailableResolutions) - 1 // Wrap around
		}
	}
}

// ToggleFullscreen toggles the fullscreen setting (in pending settings)
func (sm *SettingsManager) ToggleFullscreen() {
	sm.pendingSettings.Fullscreen = !sm.pendingSettings.Fullscreen
}

// GetCurrentResolution returns the current resolution info
func (sm *SettingsManager) GetCurrentResolution() Resolution {
	return AvailableResolutions[sm.currentSettings.ResolutionIndex]
}

// GetPendingResolution returns the pending resolution info
func (sm *SettingsManager) GetPendingResolution() Resolution {
	return AvailableResolutions[sm.pendingSettings.ResolutionIndex]
}
