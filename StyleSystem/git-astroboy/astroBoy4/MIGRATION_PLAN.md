# AstroBoy3 → AstroBoy4 Migration Plan

**Project Goal:** Create an improved/streamlined version of AstroBoy3 with mission system as high priority

**Status:** Phase 1 Complete - Ready for Phase 2  
**Last Updated:** February 13, 2026

**Recent Completion:** Game State Enhancement (Phase 1.6) - Complete state machine with pause menu, ESC navigation, velocity preservation across all state transitions. **PHASE 1 FULLY COMPLETE!**

---

## Table of Contents
1. [Project Structure](#project-structure)
2. [Migration Status](#migration-status)
3. [Phase 1: Core Gameplay Systems](#phase-1-core-gameplay-systems)
4. [Phase 2: Content Systems](#phase-2-content-systems)
5. [Phase 3: Polish & Enhancement](#phase-3-polish--enhancement)
6. [Phase 4: Code Quality & Refinement](#phase-4-code-quality--refinement)
7. [Effort Estimates](#effort-estimates)

---

## Project Structure

### Recommended Hybrid Structure

```
astroBoy4/
├── main.go                    # Game loop, init, high-level coordination (~600-800 lines)
├── go.mod / go.sum
├── build.bat
├── systems/
│   ├── types.go              # Shared types (expand from current)
│   ├── constants.go          # NEW - All game constants
│   ├── ship.go               # NEW - Ship physics + rendering
│   ├── asteroid_manager.go   # ✅ Keep current
│   ├── asteroid_spawner.go   # ✅ Keep current (or merge with manager)
│   ├── collision.go          # NEW - Advanced collision detection
│   ├── shop.go               # NEW - Shop/upgrade system
│   ├── mission.go            # NEW - Mission system
│   ├── audio.go              # NEW - Procedural audio
│   ├── mothership.go         # ✅ Keep/enhance current
│   ├── radar.go              # ✅ Keep/enhance current
│   ├── ui.go                 # NEW - Clay UI helpers + button system
│   └── settings.go           # NEW - Persistent settings
├── gameobjects/
│   ├── asteroid_base.go      # ✅ Keep current
│   ├── asteroid_sphere.go    # ✅ Keep current
│   ├── asteroid_cube.go      # ✅ Keep current
│   ├── asteroid_pyramid.go   # ✅ Keep current
│   └── asteroid_octahedron.go # ✅ Keep current
├── missions/                  # NEW - Lua mission files
│   ├── mission1.lua
│   ├── mission2.lua
│   ├── mission3.lua
│   └── mission4.lua
└── lib/                       # DLLs
```

### Why This Structure?
- **main.go stays manageable** - UI rendering, game loop, state management
- **Systems are self-contained** - Each system in its own file
- **Easy to find code** - Want ship physics? Look in systems/ship.go
- **Better than AstroBoy3's split** - Avoids spreading related code across multiple files
- **Cleaner than current** - Prevents main.go from becoming 2000+ lines

---

## Migration Status

### ✅ COMPLETED (Already in AstroBoy4)
- [x] Basic ship movement and rendering
- [x] Asteroid spawning with multiple shapes (sphere, cube, pyramid, octahedron)
- [x] Asteroid splitting system
- [x] Bullet shooting and basic collision (circle-circle)
- [x] Score tracking
- [x] Basic game states (Menu, Playing, GameOver, Mothership, Shop, Settings, Paused)
- [x] Mothership system with docking
- [x] Radar/minimap system
- [x] Clay UI integration (basic menus)
- [x] 3D camera and asteroid rendering
- [x] **Core Types & Constants System** (Phase 1.1)
- [x] **Procedural Audio System** (Phase 1.4)
- [x] **Advanced Collision System** (Phase 1.2) - SAT polygon-polygon, 2-tier detection, debug visualization
- [x] **Enhanced Ship Physics System** (Phase 1.3) - Momentum-based movement, multi-shot weapons, fire rate upgrades, thruster animation
- [x] **Shop & Upgrade System** (Phase 1.5) - Credits system, dynamic pricing, keyboard-navigated shop UI, multi-shot/fire rate upgrades
- [x] **Game State Enhancement** (Phase 1.6) - Pause menu, ESC navigation, velocity preservation, state transitions
- [x] **Settings System with Persistence** (Phase 2.2) - Resolution selector, fullscreen toggle, JSON persistence

### 🎯 IN PROGRESS
- None currently

### 📋 PLANNED
- See phases below

---

## Phase 1: Core Gameplay Systems ✅ COMPLETE

**Goal:** Essential systems for engaging gameplay  
**Estimated Time:** 27-36 hours  
**Status:** ✅ **ALL TASKS COMPLETED**

---

### 1.1 Core Types & Constants System ✅

**Priority:** ⚠️ CRITICAL (Foundation)  
**Files:** `systems/constants.go`, `systems/types.go`  
**Effort:** 2-3 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/core/constants.go`, `types.go`

#### Tasks
- [x] Create `systems/constants.go` with all game constants:
  - [x] Frame rate and timing (TargetFPS = 60)
  - [x] Weapon system (cooldown, bullet speed/lifetime)
  - [x] Ship physics (acceleration, max speed, drag, rotation)
  - [x] Collision impulse strength (120.0)
  - [x] Radar configuration (size: 150, range: 1000)
  - [x] UI layout constants (margins, panel sizes)
  - [x] Motion blur frames (5 frames)
  - [x] Color palette system:
    - Background colors (space, menus)
    - UI colors (panels, borders)
    - Text colors (title, highlight, success, warning, danger, info)
    - Ship colors (yellow with outline)
    - Mothership colors (blue-gray hull, cyan indicators)
    - Mission status colors
    - Radar colors
  - [x] Available resolutions (6 presets: 640x480 to 1920x1080)

- [x] Expand `systems/types.go` with missing types:
  - [x] `Vector2` - For collision calculations
  - [x] `Resolution` - Screen resolution definition
  - [x] `BoundingBox` - AABB for fast collision pre-filtering
  - [x] `DebugCollision` - Visualization data
  - [x] `ClayButton` - UI button with state tracking

- [x] Update existing code to use new constants (remove magic numbers)

#### Testing Checklist
- [x] All magic numbers replaced with named constants
- [x] Code compiles with new types
- [x] No regression in existing functionality

#### Implementation Notes
- Successfully ported all constants from AstroBoy3
- Updated main.go, asteroid_manager.go, radar.go, mothership.go
- Build successful (3.2MB executable)
- All systems now use centralized constants for easy tuning

---

### 1.2 Advanced Collision System ✅

**Priority:** ⚠️ CRITICAL (Better gameplay feel)  
**File:** `systems/collision.go`  
**Effort:** 6-8 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/collision_system_clay.go`, `collision_handler.go`

#### Tasks
- [x] Port collision algorithms from AstroBoy3:
  - [x] **AABB (Axis-Aligned Bounding Box)** - Fast pre-filtering
  - [x] **Circle-Circle** - Current bullet collision (keep)
  - [x] **Point-in-Triangle** - Barycentric coordinate algorithm
  - [x] **Triangle-Circle Hybrid** - Ship vs asteroid collision (replaced with SAT)
  - [x] **SAT (Separating Axis Theorem)** - Polygon vs polygon
  - [x] Point-to-line-segment distance helper
  - [x] Geometric transformation helpers (rotation, world space)

- [x] Add debug visualization system:
  - [x] Toggle with F1 key
  - [x] Draw collision shapes (circles, triangles, polygons)
  - [x] Color-code collision types (Blue=AABB, Green=No Hit, Red=Hit)
  - [x] Show collision points and polygons
  - [x] Debug statistics overlay (TIER 1/2/SAT checks, collision count)

- [x] Integration:
  - [x] Refactored bullet collision from AsteroidManager to CollisionSystem
  - [x] Ship-asteroid collision uses SAT for pixel-perfect accuracy
  - [x] Collision response with impulse (120.0 units) maintained
  - [x] Performance optimization with AABB early exits

#### Testing Checklist
- [x] Bullet-asteroid collisions use 2-tier detection (AABB → projected polygon)
- [x] Ship-asteroid collisions use SAT polygon-polygon with pixel-perfect accuracy
- [x] Debug mode (F1) shows exact collision shapes being tested
- [x] Debug overlay shows collision statistics and performance metrics
- [x] All collision logic centralized in CollisionSystem

#### Implementation Notes
- Bullet collision moved from `asteroid_manager.go` to `collision.go` via `BulletAsteroidCollision()` method
- Ship collision upgraded from triangle-circle to full SAT polygon-polygon via `ShipAsteroidCollisionSAT()` method
- Debug visualization shows:
  - Blue circles: AABB bounding boxes (TIER 1)
  - Green polygons: Projected asteroid shapes (no collision)
  - Red polygons: Collision detected
  - Yellow points: Bullet positions
  - Light blue triangles: Ship shape
- Debug overlay displays real-time statistics:
  - Asteroid/bullet counts
  - TIER 1 checks (AABB pre-filtering)
  - TIER 2 checks (projected polygon tests)
  - SAT checks (polygon-polygon tests)
  - Total collisions detected
- Collision system tracks statistics automatically for performance monitoring
- Build successful: astroboy4.exe (3.4MB)

---

### 1.3 Enhanced Ship Physics System ✅

**Priority:** 🔥 HIGH (Better game feel)  
**File:** `systems/ship.go`  
**Effort:** 4-5 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/ship_physics_clay.go`

#### Tasks
- [x] Extract ship code from main.go into `systems/ship.go`

- [x] Port enhancements from AstroBoy3:
  - [x] Thruster flame animation with randomization
  - [x] Proper momentum-based movement
  - [x] Velocity preservation for pause/shop transitions
  - [x] Impulse system for collision response
  - [x] Drag factor (configurable)
  - [x] Optional speed limiting

- [x] Create Ship struct with methods:
  - [x] `Update(deltaTime)` - Physics update
  - [x] `HandleInput(deltaTime)` - WASD/arrow input
  - [x] `DrawShip(screenX, screenY)` - Draw ship + thruster effects
  - [x] `Shoot()` - Spawn bullets with spread for multi-shot
  - [x] `ApplyImpulse(vx, vy)` - Collision response
  - [x] `GetPosition()`, `GetVelocity()`, etc. - Accessors

- [x] Add thruster particle effects:
  - [x] Simple flame animation when thrusting
  - [x] Randomized particle positions (length variation)
  - [x] Proper orientation based on ship rotation
  - [x] Color variation (orange/red gradient)

- [x] Integrate weapon upgrades:
  - [x] Multi-shot with spread pattern (±15° per bullet)
  - [x] Fire rate cooldown with upgrade levels
  - [x] Weapon cooldown tracking
  - [x] Test keys (1=multi-shot, 2=fire rate) for testing before shop

#### Physics Constants
- Thrust Force: 300.0
- Rotation Speed: 5.0 rad/s (from constants)
- Drag Factor: 0.99 (slight momentum loss)
- Collision Radius: 8 units

#### Multi-Shot Formula
```
Bullets = 1 + MultiShotLevel
Spread = ±15° distributed evenly
Example: Level 2 = 3 bullets at -15°, 0°, +15°
```

#### Fire Rate Formula
```
Base Cooldown = 0.5s (2 shots/sec)
Cooldown = 0.5 * (0.95 ^ FireRateLevel)
Min Cooldown = 0.05s (20 shots/sec max)
```

#### Testing Checklist
- [x] Ship feels responsive with improved momentum
- [x] Thruster effect animates with randomization
- [x] Multi-shot upgrade works (bullets spread correctly)
- [x] Fire rate upgrade decreases cooldown
- [x] Collision impulse uses existing system
- [x] Physics feels like space (momentum preserved)
- [x] HUD displays weapon stats (multi-shot count, fire rate)

#### Implementation Notes
- Created complete `ShipPhysics` struct in `systems/ship.go`
- Ship now handles all its own input, update, and rendering
- Weapon system with cooldown and upgrade levels
- Multi-shot spreads bullets evenly across angle range
- Fire rate uses exponential reduction (5% per level)
- Thruster flame has random length (10-18 units) and color variation
- Test keys: Press 1 for multi-shot upgrade, 2 for fire rate upgrade
- HUD shows current weapon stats in real-time
- Build successful: astroboy4.exe (3.43 MB)

---

### 1.4 Procedural Audio System ✅

**Priority:** 🔥 HIGH (Major juice factor)  
**Files:** `systems/audio/audio_manager.go`, `procedural_sounds.go`, `sound_types.go`  
**Effort:** 4-6 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/audio_system_raylib.go`

#### Tasks
- [x] Port procedural audio generation from AstroBoy3:
  - [x] **Shoot Sound** (0.3s duration)
    - 30-60Hz bass tones
    - Exponential decay envelope
    - Smooth fadeout
  - [x] **Explosion Sound** (1.0s duration)
    - 80-350Hz rumble + noise
    - Multi-frequency impact
    - Loud initial hit
  - [x] **Thruster Sound** (2.0s seamless loop)
    - 20-60Hz ultra-deep bass
    - Subtle modulation
    - Seamless looping

- [x] Implement sound generation:
  - [x] 16-bit PCM audio at 44.1kHz
  - [x] Memory-efficient global sample arrays
  - [x] Proper waveform generation

- [x] Create AudioManager struct with methods:
  - [x] `NewAudioManager()` - Initialize and generate all sound samples
  - [x] `PlayShoot()` - Weapon firing sound
  - [x] `PlayExplosion()` - Asteroid destruction
  - [x] `StartThruster()` - Start looping engine sound
  - [x] `UpdateThruster()` - Maintain thruster loop
  - [x] `StopThruster()` - Stop engine sound
  - [x] `SetSoundVolume(soundType, volume)` - Volume control per sound
  - [x] `SetMasterVolume(volume)` - Master volume control
  - [x] `Cleanup()` - Free audio resources

- [x] Add sound state tracking:
  - [x] Don't play if already playing (prevent spam)
  - [x] Track looping sounds separately

- [x] Integration with game events:
  - [x] Shoot sound on bullet spawn
  - [x] Explosion sound on asteroid split/destroy
  - [x] Thruster sound when W/Up key held

#### Testing Checklist
- [x] Shoot sound plays on bullet fire
- [x] Explosion sound plays on asteroid destruction
- [x] Thruster sound loops smoothly when accelerating
- [x] No audio glitches or crackling
- [x] Sounds don't overlap/spam
- [x] Volume levels are balanced

#### Implementation Notes
- Created organized folder structure: `systems/audio/`
- Separated concerns: sound_types, procedural_sounds, audio_manager
- Room for future expansion (music, spatial audio, etc.)
- Fully procedural - no external audio files needed
- See `systems/audio/README.md` for detailed documentation

---

### 1.5 Shop & Upgrade System ✅

**Priority:** 🔥 HIGH (Core progression)  
**File:** `systems/shop.go`  
**Effort:** 8-10 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/shop_upgrade_system_clay.go`

#### Tasks
- [x] Port upgrade system from AstroBoy3:
  - [x] **Multi-Shot Upgrade**
    - Formula: 1 + upgradeLevel bullets
    - Spread angle calculation (±15° distributed evenly)
    - Dynamic pricing (30% increase per level)
  - [x] **Fire Rate Upgrade**
    - Base cooldown: 0.5s
    - Reduction: 5% per level (0.95^level formula)
    - Min cooldown: 0.05s (20 shots/sec max)
    - Dynamic pricing (40% increase per level)

- [x] Create ShopSystem struct with methods:
  - [x] `GetUpgradeList()` - Returns upgrade info based on ship state and credits
  - [x] `PurchaseUpgrade()` - Buy upgrade logic with credit deduction
  - [x] `SelectNext/SelectPrevious()` - Keyboard navigation
  - [x] `GetSelectedIndex()` - Track selected upgrade

- [x] Design shop UI with Clay:
  - [x] Vertical list layout showing all upgrades
  - [x] Price display with affordability indicator (green/red)
  - [x] Current level / next level display
  - [x] Upgrade descriptions with stats
  - [x] Selected upgrade highlighted in green
  - [x] Keyboard navigation (UP/DOWN/ENTER/SPACE/ESC)

- [x] Game state integration:
  - [x] Add `StateShop` to game state enum
  - [x] Add "UPGRADES" button in mothership menu
  - [x] Connect upgrades to ship weapon system
  - [x] Add credits tracking (10 per asteroid)
  - [x] Display credits in HUD and shop

- [x] Ship integration:
  - [x] Multi-shot already integrated in ship.go
  - [x] Fire rate already integrated in ship.go
  - [x] Credits awarded on asteroid destruction

- [x] ESC key handling:
  - [x] Disabled default ESC-to-quit behavior
  - [x] ESC in shop returns to mothership
  - [x] ESC in main menu quits game
  - [x] Alt+F4 works everywhere

#### Upgrade Formulas
```
Multi-Shot:
  Bullets = 1 + level
  Starting Price = 30 credits
  Price = base * (1.3 ^ level)
  Spread angle = ±15° distributed evenly
  Example: Level 2 = 3 bullets at -15°, 0°, +15°

Fire Rate:
  Cooldown = 0.5 * (0.95 ^ level)
  Min cooldown = 0.05s
  Starting Price = 40 credits
  Price = base * (1.4 ^ level)
  Example: Level 5 = 2.56 shots/sec
```

#### Testing Checklist
- [x] Can open shop from mothership "UPGRADES" button
- [x] Upgrades display correctly with prices
- [x] Can purchase upgrades when affordable
- [x] Can't purchase when insufficient credits
- [x] Multi-shot fires correct number of bullets with spread
- [x] Fire rate cooldown decreases with upgrades
- [x] Prices increase correctly per level (30% and 40%)
- [x] UI is clear and responsive
- [x] Credits displayed in HUD (gold color)
- [x] ESC properly navigates back to mothership

#### Implementation Notes
- Created `systems/shop.go` with ShopSystem struct
- Credits separate from score (both earn 10 per asteroid)
- Start with 100 credits for testing
- Shop UI shows 2 upgrades with full descriptions
- Visual feedback: Green = can afford, Red = cannot afford
- Navigation: UP/DOWN to select, ENTER/SPACE to buy, ESC to exit
- Removed temporary test keys (1 and 2)
- Full integration with ship weapon systems
- Build successful: astroboy4.exe (3.45 MB)

---

### 1.6 Game State Enhancement ✅

**Priority:** 🔶 MEDIUM-HIGH (Better flow)  
**File:** `main.go` (update existing state machine)  
**Effort:** 3-4 hours  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/game_state_system.go`

#### Tasks
- [x] Add new game states to enum:
  - [x] `StateShop` - Upgrade interface
  - [x] `StatePaused` - Paused gameplay
  - [x] `StateMissions` - Mission selection (deferred to Phase 2.1)
  - [x] `StateSettings` - Settings menu

- [x] Enhance state machine:
  - [x] Button-based state transitions
  - [x] Ship velocity storage for pause/resume
  - [x] State-specific update methods
  - [x] State-specific render methods

- [x] Add ESC key handling:
  - [x] ESC in `StatePlaying` → `StatePaused`
  - [x] ESC in menus → Go back
  - [x] ESC in `StateShop` → `StateMothership`
  - [x] ESC in `StateSettings` → Previous state

- [x] Create pause menu with Clay UI:
  - [x] "Resume" button → `StatePlaying`
  - [x] "Restart" button → Restart game (bonus feature)
  - [x] "Main Menu" button → `StateMenu`

- [x] Update mothership menu:
  - [x] "Upgrades" button → `StateShop`
  - [x] "Missions" button → `StateMissions` (deferred to Phase 2.1)
  - [x] "Undock" button → `StatePlaying`

#### State Transition Diagram
```
Menu ↔ Settings
Menu → Playing ↔ Paused ↔ Settings
Playing ↔ Mothership ↔ Shop
Mothership ↔ Missions (when Phase 2.1 complete)
Playing → GameOver → Menu
```

#### Testing Checklist
- [x] ESC pauses game correctly
- [x] Can resume from pause
- [x] Can enter shop from mothership
- [x] Can navigate between all states
- [x] Ship velocity preserved correctly
- [x] No state transition bugs

#### Implementation Notes
- Complete state machine with all transitions working
- Pause menu includes Resume, Restart, and Main Menu buttons
- Ship velocity properly stored and restored on pause/resume and dock/undock
- ESC key navigation works across all states (disabled default quit behavior)
- StateMissions enum will be added in Phase 2.1 when mission system is implemented
- "Missions" button in mothership menu deferred to Phase 2.1

---

## Phase 2: Content Systems

**Goal:** Essential content for replayability  
**Estimated Time:** 19-25 hours

---

### 2.1 Mission System with Lua Integration

**Priority:** 🔥 HIGH (Your specific request)  
**File:** `systems/mission.go`, `missions/*.lua`  
**Effort:** 10-15 hours  
**Reference:** `astroBoy3/src/systems/mission_system_raylib.go`

#### Tasks
- [ ] Install Lua integration:
  - [ ] Add `github.com/yuin/gopher-lua` to go.mod
  - [ ] Test basic Lua script loading

- [ ] Port mission system from AstroBoy3:
  - [ ] Lua script loading and parsing
  - [ ] Mission structure (ID, Name, Description, Places, TimeLimit)
  - [ ] Waypoint system (coordinates, distance tracking)
  - [ ] Multi-waypoint missions
  - [ ] Sub-mission support
  - [ ] Time limit enforcement
  - [ ] Progress tracking (current waypoint, completion %)
  - [ ] Checkpoint system

- [ ] Create MissionSystem struct with methods:
  - [ ] `Initialize(directory)` - Load all .lua missions
  - [ ] `GetAvailableMissions()` - Return mission list
  - [ ] `GetActiveMission()` - Return current mission
  - [ ] `StartMission(missionID)` - Activate mission
  - [ ] `UpdateMission(deltaTime, shipX, shipY)` - Check progress
  - [ ] `RenderMissionUI()` - Mission selection terminal
  - [ ] `RenderActiveHUD(x, y)` - In-game mission display
  - [ ] `CheckWaypointReached(shipX, shipY)` - Distance check
  - [ ] `CompleteMission()` - Handle completion
  - [ ] `FailMission()` - Handle failure (time limit)
  - [ ] `GetCurrentWaypoint()` - Return active waypoint
  - [ ] `GetDistanceToWaypoint(shipX, shipY)` - Calculate distance

- [ ] Design mission selection UI with Clay:
  - [ ] Scrollable mission list (terminal theme)
  - [ ] Mission details panel
  - [ ] TAB key for expanded view
  - [ ] Mission status indicators:
    - Available (white)
    - Active (yellow)
    - Completed (green)
  - [ ] Keyboard selection (1-4 number keys)
  - [ ] "Accept Mission" button
  - [ ] "Back" button to mothership

- [ ] Design active mission HUD:
  - [ ] Top-right panel (350x120)
  - [ ] Mission name and current objective
  - [ ] Distance to waypoint (with units)
  - [ ] Time remaining (if timed mission)
  - [ ] Progress indicator (Waypoint N of M)

- [ ] Add mission visualization in world:
  - [ ] Waypoint markers on radar
  - [ ] Directional arrows (like mothership indicator)
  - [ ] Distance text display
  - [ ] Waypoint highlight when near

- [ ] Create fallback missions (if Lua files missing):
  - [ ] Simple patrol mission
  - [ ] Collection mission
  - [ ] Survival mission

- [ ] Create example Lua mission files:
  - [ ] `missions/mission1.lua` - Simple waypoint
  - [ ] `missions/mission2.lua` - Multi-waypoint patrol
  - [ ] `missions/mission3.lua` - Timed delivery
  - [ ] `missions/mission4.lua` - Complex multi-objective

#### Lua Mission File Structure
```lua
mission = {
    id = 1,
    name = "Patrol Route Alpha",
    title = "Sector Patrol",
    description = "Visit all patrol waypoints in sector alpha.",
    places = {
        {name = "Waypoint 1", x = 500, y = 300},
        {name = "Waypoint 2", x = -400, y = 600},
        {name = "Waypoint 3", x = 200, y = -500}
    },
    timeLimit = 180, -- 3 minutes (optional)
    restrictions = nil -- Optional restrictions
}
```

#### Mission Types to Support
1. **Simple Waypoint** - Go to location
2. **Multi-Waypoint** - Visit locations in order
3. **Timed** - Complete within time limit
4. **Survival** - Stay alive for duration
5. **Collection** - Destroy N asteroids

#### Testing Checklist
- [ ] Lua missions load correctly
- [ ] Can view mission list in terminal
- [ ] Can accept missions
- [ ] Waypoint indicators appear in world
- [ ] Distance tracking works correctly
- [ ] Mission completes when all waypoints reached
- [ ] Time limits work (if specified)
- [ ] HUD displays mission info clearly
- [ ] Can have multiple missions available
- [ ] Fallback missions work if Lua files missing
- [ ] Radar shows mission waypoints
- [ ] Direction arrows point to waypoints

---

### 2.2 Settings System with Persistence ✅

**Priority:** 🔶 MEDIUM (Quality of life)  
**File:** `systems/settings.go`  
**Effort:** 4-5 hours (actual: ~3 hours)  
**Status:** ✅ **COMPLETED**  
**Reference:** `astroBoy3/src/systems/settings_system_clay.go`

#### Tasks
- [x] Create simplified settings system:
  - [x] Settings struct (ResolutionIndex, Fullscreen) - Simplified, no VSync/MSAA/MotionBlur
  - [x] JSON serialization/deserialization
  - [x] User config directory (`%APPDATA%\astroboy4\settings.json` on Windows)
  - [x] Default settings fallback (1280x720, windowed)
  - [x] Resolution validation (clamp to valid range)

- [x] Create SettingsManager struct with methods:
  - [x] `LoadSettings()` - Load from JSON file
  - [x] `SaveSettings()` - Save to JSON file
  - [x] `ApplySettings()` - Apply to Raylib (resolution, fullscreen)
  - [x] `CycleResolution()` - Navigate resolution options
  - [x] `ToggleFullscreen()` - Toggle fullscreen
  - [x] `StartEditing()` - Begin editing (copy current to pending)
  - [x] `ApplyPendingSettings()` - Apply and save pending changes
  - [x] `DiscardPendingSettings()` - Cancel changes

- [x] Design settings UI with Clay:
  - [x] Resolution selector with < > buttons
  - [x] Fullscreen toggle button (ON/OFF with color coding)
  - [x] "Apply" button (green)
  - [x] "Back" button (red)
  - [x] Keyboard navigation support (LEFT/RIGHT, F, ENTER, ESC)
  - [x] Mouse click support

- [x] Integration:
  - [x] Add `StateSettings` to game state enum
  - [x] Settings button in main menu
  - [x] Auto-save settings on exit
  - [x] Load settings on startup (before window init)
  - [x] Apply resolution before InitWindow

#### Settings File Format
```json
{
  "resolutionIndex": 3,
  "fullscreen": false
}
```

#### Resolution Options
- 0: 640x480
- 1: 800x600
- 2: 1024x768
- 3: 1280x720 (default)
- 4: 1600x900
- 5: 1920x1080

#### Implementation Notes
- Simplified settings: Only resolution and fullscreen (user requested no VSync/MSAA)
- Settings load before window initialization to set correct initial resolution
- Pending settings pattern: Changes aren't applied until "Apply" clicked
- ESC discards changes and returns to menu
- Settings auto-save on game exit
- Build successful: astroboy4.exe (4.2 MB)
- Settings file created at: `%APPDATA%\astroboy4\settings.json`

---

### 2.3 Enhanced UI System

**Priority:** 🔶 MEDIUM (Better UX)  
**File:** `systems/ui.go`  
**Effort:** 5-6 hours  
**Reference:** `astroBoy3/src/ui/ui_buttons_clay.go`, `menu_button_setup.go`

#### Tasks
- [ ] Port button system from AstroBoy3:
  - [ ] Button state tracking (hovered, clicked)
  - [ ] Clay pointer state integration
  - [ ] Button rendering with hover effects
  - [ ] Action-based button system
  - [ ] ID-based button identification

- [ ] Port menu button setup:
  - [ ] State-specific button layouts
  - [ ] Dynamic label generation
  - [ ] Responsive positioning
  - [ ] Button action routing

- [ ] Create UIManager struct with methods:
  - [ ] `AddButton(id, label, x, y, width, height, action)`
  - [ ] `ClearButtons()`
  - [ ] `RenderButtons()` - Draw all with Clay
  - [ ] `HandleInput()` - Check mouse/keyboard
  - [ ] `GetButtonAction()` - Return clicked action
  - [ ] `SetupMenuButtons(state)` - Configure for state

- [ ] Button visual states:
  - [ ] Default: Medium gray (100, 100, 100)
  - [ ] Hovered: Light gray (150, 150, 150)
  - [ ] Clicked: Dark gray (80, 80, 80)
  - [ ] Disabled: Very dark gray (50, 50, 50)

- [ ] Button presets for menus:
  - [ ] Main menu buttons
  - [ ] Pause menu buttons
  - [ ] Settings menu buttons
  - [ ] Mothership menu buttons
  - [ ] Shop buttons
  - [ ] Mission terminal buttons
  - [ ] Game over buttons

#### Testing Checklist
- [ ] Buttons respond to hover
- [ ] Buttons respond to click
- [ ] Button actions trigger correctly
- [ ] Button layouts look good in all states
- [ ] Keyboard navigation works (optional)
- [ ] Disabled buttons don't respond to clicks

---

## Phase 3: Polish & Enhancement

**Goal:** Optional improvements for better experience  
**Estimated Time:** 3-4 hours

---

### 3.1 Enhanced HUD System

**Priority:** 🔶 MEDIUM (Better info display)  
**File:** `main.go` (update render functions) or `systems/hud.go`  
**Effort:** 3-4 hours  
**Reference:** `astroBoy3/src/systems/game_renderer.go`

#### Tasks
- [ ] Port HUD elements from AstroBoy3:
  - [ ] **Top-left panel:**
    - Score and credits display
    - Weapon level (multi-shot, fire rate)
    - Ship stats (speed, velocity vector)
    - Bullet count / Asteroid count
  - [ ] **Top-right panel (mission active):**
    - Mission name
    - Current objective
    - Distance to waypoint
    - Time remaining
  - [ ] **Bottom-left:**
    - Controls reminder (toggle with key?)
  - [ ] **Bottom-right:**
    - Enhanced radar (already exists)

- [ ] Enhance radar system:
  - [ ] Add mission waypoint markers (yellow)
  - [ ] Color coding:
    - Ship: Red
    - Asteroids: Gray
    - Mothership: Green
    - Waypoints: Yellow
  - [ ] Add range indicator circle

- [ ] Add mothership direction indicator:
  - [ ] Arrow pointing to mothership (when off-screen)
  - [ ] Distance text
  - [ ] Pulsing effect when nearby

- [ ] Add debug toggles:
  - [ ] F2: Toggle FPS counter
  - [ ] F1: Toggle debug overlay

- [ ] Debug overlay info:
  - [ ] Ship position (X, Y)
  - [ ] Ship velocity (VX, VY, Speed)
  - [ ] Asteroid count
  - [ ] Bullet count
  - [ ] Current state
  - [ ] Active mission (if any)
  - [ ] Collision debug shapes

#### Testing Checklist
- [ ] HUD displays all info clearly
- [ ] HUD doesn't obstruct gameplay
- [ ] Radar shows all objects correctly
- [ ] Direction indicator points correctly
- [ ] FPS counter works (F2)
- [ ] Debug overlay works (F1)
- [ ] Info is readable at all resolutions

---

## Phase 4: Code Quality & Refinement

**Goal:** Production-ready codebase  
**Estimated Time:** 7-10 hours (was 11-14 hours)

---

### 4.1 Code Organization & Cleanup

**Priority:** 🔶 MEDIUM (Maintainability)  
**Effort:** 4-6 hours

#### Tasks
- [ ] Refactor main.go:
  - [ ] Keep at ~600-800 lines max
  - [ ] Move game logic to systems
  - [ ] Clear separation of concerns
  - [ ] Clean imports

- [ ] Review all systems for consistency:
  - [ ] Naming conventions (camelCase unexported, PascalCase exported)
  - [ ] Error handling patterns
  - [ ] Resource cleanup (defer pattern)
  - [ ] Comments and documentation

- [ ] Add file headers to all files:
```go
// AstroBoy4 Systems - [System Name]
// [Purpose description]
// [Key features]
```

- [ ] Code cleanup:
  - [ ] Remove dead code
  - [ ] Remove completed TODOs
  - [ ] Fix compiler warnings
  - [ ] Ensure all systems use constants

- [ ] Dependency review:
  - [ ] Check all imports are necessary
  - [ ] Update go.mod
  - [ ] Run `go mod tidy`

#### Testing Checklist
- [ ] Code compiles with no warnings
- [ ] All systems use constants
- [ ] File headers are consistent
- [ ] No dead code remains
- [ ] Dependencies are clean

---

### 4.2 Documentation

**Priority:** 🔶 MEDIUM (Future maintenance)  
**Effort:** 3-4 hours

#### Tasks
- [ ] Update `AGENTS.md` with AstroBoy4:
  - [ ] Project structure
  - [ ] Build instructions
  - [ ] System descriptions
  - [ ] Testing procedures

- [ ] Document all systems:
  - [ ] File header comments
  - [ ] Public API documentation
  - [ ] Complex algorithm explanations

- [ ] Document game mechanics:
  - [ ] Upgrade formulas
  - [ ] Balancing values
  - [ ] Mission Lua API
  - [ ] Settings file format

- [ ] Create `README.md` for AstroBoy4:
  - [ ] Game description
  - [ ] Controls
  - [ ] How to build
  - [ ] How to run
  - [ ] Features list
  - [ ] Mission creation guide

- [ ] Create mission authoring guide:
  - [ ] Lua API reference
  - [ ] Example missions
  - [ ] Best practices

#### Documentation Checklist
- [ ] AGENTS.md updated
- [ ] All systems documented
- [ ] README.md created
- [ ] Mission guide created
- [ ] Upgrade formulas documented

---

## Effort Estimates

### Time Breakdown by Phase
- **Phase 1 (Core):** ~~27-36 hours~~ ✅ **COMPLETE**
  - 1.1 Constants: ~~2-3h~~ ✅ DONE
  - 1.2 Collision: ~~6-8h~~ ✅ DONE (8h actual)
  - 1.3 Ship: ~~4-5h~~ ✅ DONE (5h actual)
  - 1.4 Audio: ~~4-6h~~ ✅ DONE
  - 1.5 Shop: ~~8-10h~~ ✅ DONE (9h actual)
  - 1.6 States: ~~3-4h~~ ✅ DONE

- **Phase 2 (Content):** 16-21 hours (was 19-25 hours)
  - 2.1 Missions: 10-15h
  - 2.2 Settings: ~~4-5h~~ ✅ DONE (~3h actual)
  - 2.3 UI: 5-6h

- **Phase 3 (Polish):** 3-4 hours
  - 3.1 HUD: 3-4h

- **Phase 4 (Quality):** 7-10 hours
  - 4.1 Cleanup: 4-6h
  - 4.2 Docs: 3-4h

**Total Remaining:** 26-35 hours (was 56-75 hours total, Phase 1 complete)

### Development Timeline (Remaining)
- **Full-time (40h/week):** 0.7-0.9 weeks
- **Part-time (10h/week):** 2.6-3.5 weeks
- **Hobby (5h/week):** 5-7 weeks

### Milestones
1. ✅ **Milestone 1:** Core systems → Playable with progression (Phase 1) **COMPLETE**
2. 🎯 **Milestone 2:** Content systems → Full-featured game (Phase 2) **CURRENT**
3. 🚀 **Milestone 3:** Polish → Polished experience (Phase 3)
4. 🛠️ **Milestone 4:** Code quality → Production-ready (Phase 4)

---

## What NOT to Migrate

**Streamlined Improvements - Skip These:**
- ❌ Test files (`test_shop_upgrade_system.go`) - Not needed
- ❌ Overly complex debug visualization - Simple version OK
- ❌ Every single color constant - Use fewer colors
- ❌ Multiple render/update file split - Keep together

**Optional Features - Removed from Plan:**
- ❌ Motion Blur - Performance cost, not worth it
- ❌ 3D cube in menu - Not essential
- ⚠️ Advanced debug overlay - Basic version OK

---

## Development Guidelines

### Code Style
- Follow Go conventions (gofmt)
- Use camelCase for unexported, PascalCase for exported
- Add comments for complex logic
- Use defer for cleanup
- Handle errors properly

### Performance Targets
- 60 FPS minimum
- < 100MB memory usage
- Fast startup (< 2 seconds)
- Smooth audio (no crackling)

### Testing Strategy
- Test after each feature
- Manual gameplay testing
- Performance profiling
- Edge case testing

---

## Notes

**Strengths to Preserve from AstroBoy3:**
- Excellent code organization
- Clean separation of concerns
- Proper resource management
- Delta time-based updates
- Settings persistence

**Improvements in AstroBoy4:**
- Simpler file structure
- Better 3D asteroid rendering
- More asteroid shape variety
- Cleaner main.go

**Key Design Decisions:**
- Hybrid structure (not full AstroBoy3 split)
- Mission system is high priority
- Focus on streamlined/improved version
- Keep what works, improve what doesn't

---

**Last Updated:** February 13, 2026  
**Status:** ✅ Phase 1 FULLY COMPLETE (All 6 tasks) | Phase 2.2 Complete | Ready for Phase 2.1 (Mission System)
