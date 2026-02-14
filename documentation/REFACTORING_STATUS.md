# Refactoring Status

## ✅ Completed Steps

### Step 1: Clean Up monitors_config.json
- ✅ Removed all `application_rules` array
- ✅ Kept only `known_monitors`
- ✅ Backup created at `monitors_config.json.backup`

### Step 2: Fix Layout File
- ✅ Changed `dual-screen-home.json` rule from `target_monitor_id` to `target_display: 2`
- ✅ Removed `enabled` field from rule
- ✅ Backup created at `dual-screen-home.json.backup`

### Step 3: Update ConfigManager
- ✅ Removed `application_rules` from default config
- ✅ Removed `_validate_config` check for `application_rules`
- ✅ Removed methods: `add_rule()`, `update_rule()`, `delete_rule()`, `get_rule()`, `get_all_rules()`
- ✅ Removed rule_id normalization logic from `load_config()`
- ✅ Kept only monitor-related methods

### Step 4: Update LayoutManager
- ✅ Added `import uuid` at top
- ✅ Removed `self.saved_rules` from `__init__()`
- ✅ Added `get_active_rules()` method - reads from layout, maps display→monitor_id
- ✅ Simplified `activate_layout()` - removed all config_manager rule manipulation
- ✅ Simplified `deactivate_layout()` - just clears active_layout state
- ✅ Updated `get_active_layout()` to return `rules_count` instead of `rules_created`
- ✅ Fixed `get_layout_preview()` variable name bug (screen_config)

### Step 5: Update WindowManager
- ✅ Added `layout_manager` parameter to `__init__()`
- ✅ Updated `apply_rules()` to call `layout_manager.get_active_rules()`
- ✅ Added check: no layout_manager = no rules applied
- ✅ Added check: no active layout = no rules applied
- ✅ Removed `enabled` check (layout active = all rules active)

### Step 6: Update Service
- ✅ Pass `layout_manager` to `WindowManager` constructor
- ✅ Removed methods: `get_rules()`, `add_rule()`, `delete_rule()`

### Step 7: Update API
- ✅ Removed old endpoints: `GET/POST /rules`, `DELETE /rules/<id>`
- ✅ Updated `POST /layouts/<name>/rules` to accept `target_display`
- ✅ Added validation: target_display must be in screen_requirements
- ✅ Removed target_monitor_id handling
- ✅ Removed enabled field from rules
- ✅ When layout active: reload layout data and apply immediately

## 🚧 Remaining Steps

### Step 8: Update WindowDetailsView (commands.py)
- [ ] Change constructor to receive `active_layout` (not monitors list)
- [ ] Display screens from `active_layout["data"]["screen_requirements"]["screens"]`
- [ ] Track selected display NUMBER (1, 2, 3) not monitor index
- [ ] Update UI to show: "Display 1: ... [vertical]"
- [ ] Update `get_rule_config()` to return `target_display` number

### Step 9: Update frontend/frontend-switcher.py
- [ ] Remove `monitors` parameter from WindowDetailsView instantiation
- [ ] Pass only `active_layout` to WindowDetailsView

### Step 10: Update Layout Validation
- [ ] Change validation in `layout_manager.py` to expect `target_display` field
- [ ] Remove validation for `target_display` field (old field)

## 📊 Files Modified

1. ✅ `monitors_config.json` - Removed application_rules
2. ✅ `layouts/dual-screen-home.json` - Fixed rule format
3. ✅ `window_stuff/config_manager.py` - Removed rule methods
4. ✅ `window_stuff/layout_manager.py` - Added get_active_rules(), simplified activate/deactivate
5. ✅ `window_stuff/window_manager.py` - Use layout_manager
6. ✅ `window_stuff/service.py` - Pass layout_manager, removed rule methods
7. ✅ `window_stuff/api.py` - Removed old endpoints, updated rule endpoint
8. ⏳ `commands.py` - WindowDetailsView (IN PROGRESS)
9. ⏳ `frontend/frontend-switcher.py` - WindowDetailsView instantiation (IN PROGRESS)

## 🧪 Testing Needed

- [ ] No layout active = no rules applied
- [ ] Layout activation = rules apply
- [ ] Layout deactivation = rules stop applying
- [ ] Add rule to active layout = applies immediately
- [ ] monitors_config.json has NO application_rules
- [ ] Rules use target_display not target_monitor_id
- [ ] WindowDetailsView shows displays from layout

## Current Status

**7 out of 10 steps complete (70%)**

Next: Update WindowDetailsView to use active_layout instead of monitors list.
