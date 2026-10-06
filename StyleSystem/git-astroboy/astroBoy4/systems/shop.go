// AstroBoy4 Systems - Shop and Upgrade System
// Manages weapon upgrades, pricing, and shop UI
// Ported and adapted from astroBoy3/src/systems/shop_upgrade_system_clay.go

package systems

import (
	"fmt"
	"math"
)

// UpgradeType represents different types of upgrades available in the shop
type UpgradeType int

const (
	UpgradeMultiShot UpgradeType = iota
	UpgradeFireRate
)

// UpgradeInfo contains information about an upgrade for display in the shop
type UpgradeInfo struct {
	Type         UpgradeType
	Name         string
	Description  string
	CurrentLevel int
	NextLevel    int
	Price        int
	CanAfford    bool
}

// ShopSystem manages weapon upgrades and shop functionality
type ShopSystem struct {
	// Pricing (starts low, increases with each purchase)
	multiShotPrice int
	fireRatePrice  int

	// Selected upgrade in UI
	selectedIndex int
}

// NewShopSystem creates a new shop and upgrade management system
func NewShopSystem() *ShopSystem {
	return &ShopSystem{
		multiShotPrice: 30, // Starting price for multi-shot
		fireRatePrice:  40, // Starting price for fire rate (higher because more powerful)
		selectedIndex:  0,
	}
}

// GetUpgradeList returns the list of available upgrades based on ship state and credits
func (ss *ShopSystem) GetUpgradeList(ship *ShipPhysics, credits int) []UpgradeInfo {
	upgrades := []UpgradeInfo{
		{
			Type:         UpgradeMultiShot,
			Name:         "Multi-Shot",
			Description:  fmt.Sprintf("Fire %d bullets simultaneously. Wider coverage, more damage.", ship.GetMultiShotCount()+1),
			CurrentLevel: ship.GetMultiShotLevel(),
			NextLevel:    ship.GetMultiShotLevel() + 1,
			Price:        ss.multiShotPrice,
			CanAfford:    credits >= ss.multiShotPrice,
		},
		{
			Type:         UpgradeFireRate,
			Name:         "Fire Rate",
			Description:  fmt.Sprintf("Shoot faster! Currently %.2f shots/sec. Next: %.2f shots/sec.", 1.0/ship.GetFireRateCooldown(), 1.0/ss.getNextFireRateCooldown(ship)),
			CurrentLevel: ship.GetFireRateLevel(),
			NextLevel:    ship.GetFireRateLevel() + 1,
			Price:        ss.fireRatePrice,
			CanAfford:    credits >= ss.fireRatePrice,
		},
	}

	return upgrades
}

// getNextFireRateCooldown calculates what the cooldown would be after upgrading
func (ss *ShopSystem) getNextFireRateCooldown(ship *ShipPhysics) float32 {
	baseCooldown := float32(0.5)
	minCooldown := float32(0.05)
	nextLevel := ship.GetFireRateLevel() + 1

	cooldown := baseCooldown * float32(math.Pow(0.95, float64(nextLevel)))
	if cooldown < minCooldown {
		cooldown = minCooldown
	}

	return cooldown
}

// PurchaseUpgrade attempts to purchase an upgrade
// Returns true if purchase was successful, false if not enough credits
func (ss *ShopSystem) PurchaseUpgrade(upgradeType UpgradeType, ship *ShipPhysics, credits *int) bool {
	switch upgradeType {
	case UpgradeMultiShot:
		if *credits >= ss.multiShotPrice {
			*credits -= ss.multiShotPrice
			ship.UpgradeMultiShot()
			// Increase price by 30%
			ss.multiShotPrice = int(float64(ss.multiShotPrice) * 1.3)
			return true
		}

	case UpgradeFireRate:
		if *credits >= ss.fireRatePrice {
			*credits -= ss.fireRatePrice
			ship.UpgradeFireRate()
			// Increase price by 40% (fire rate is more powerful)
			ss.fireRatePrice = int(float64(ss.fireRatePrice) * 1.4)
			return true
		}
	}

	return false
}

// GetSelectedIndex returns the currently selected upgrade index
func (ss *ShopSystem) GetSelectedIndex() int {
	return ss.selectedIndex
}

// SetSelectedIndex sets the currently selected upgrade index
func (ss *ShopSystem) SetSelectedIndex(index int) {
	ss.selectedIndex = index
}

// SelectNext moves selection to next upgrade (wraps around)
func (ss *ShopSystem) SelectNext(upgradeCount int) {
	ss.selectedIndex++
	if ss.selectedIndex >= upgradeCount {
		ss.selectedIndex = 0
	}
}

// SelectPrevious moves selection to previous upgrade (wraps around)
func (ss *ShopSystem) SelectPrevious(upgradeCount int) {
	ss.selectedIndex--
	if ss.selectedIndex < 0 {
		ss.selectedIndex = upgradeCount - 1
	}
}
