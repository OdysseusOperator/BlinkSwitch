# 🎯 REFACTORING PLAN: Layout-Only Rule Architecture

## Decisions Confirmed ✅
- ✅ Rules have `rule_id` for debugging
- ✅ Rules apply immediately when added to active layout
- ✅ Remove all existing rules from `monitors_config.json`
- ✅ Layout active = all rules in that layout are active (no per-rule enable/disable)

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Layout Files (layouts/*.json)                  │
│  ┌───────────────────────────────────────────┐  │
│  │ "rules": [                                │  │
│  │   {                                       │  │
│  │     "rule_id": "rule_abc123",            │  │
│  │     "match_type": "exe",                 │  │
│  │     "match_value": "chrome.exe",         │  │
│  │     "target_display": 2,  ← Logical!     │  │
│  │     "fullscreen": true,                  │  │
│  │     "maximize": false                    │  │
│  │   }                                       │  │
│  │ ]                                         │  │
│  └───────────────────────────────────────────┘  │
│  Single source of truth ✓                       │
└──────────────┬──────────────────────────────────┘
               │
               ├─ User activates layout
               ▼
┌─────────────────────────────────────────────────┐
│  LayoutManager.active_layout                    │
│  ┌───────────────────────────────────────────┐  │
│  │ display_map = {1: "monitor_abc",         │  │
│  │                2: "monitor_xyz"}          │  │
│  │                                           │  │
│  │ get_active_rules():                      │  │
│  │   • Read from layout file                │  │
│  │   • Map target_display → monitor_id      │  │
│  │   • Return runtime rules                 │  │
│  └───────────────────────────────────────────┘  │
└──────────────┬──────────────────────────────────┘
               │
               ├─ Every 5 seconds (service loop)
               ├─ OR immediately (apply_rules_now)
               ▼
┌─────────────────────────────────────────────────┐
│  WindowManager.apply_rules()                    │
│  • Gets rules from layout_manager               │
│  • Finds matching windows                       │
│  • Moves/resizes windows                        │
└─────────────────────────────────────────────────┘

monitors_config.json
  ├─ known_monitors: [...]  ← Monitor detection history
  └─ application_rules: REMOVED ✗
```

---

## 📋 Implementation Steps

### Step 1: Clean Up monitors_config.json
Remove all `application_rules` array, keep only `known_monitors`

### Step 2: Update ConfigManager
Remove rule-related methods: `add_rule()`, `update_rule()`, `delete_rule()`, `get_all_rules()`

### Step 3: Add get_active_rules() to LayoutManager
New method that reads rules from active layout and resolves display numbers to monitor IDs

### Step 4: Simplify Layout Activation/Deactivation
Remove all code that copies rules to/from `monitors_config.json`

### Step 5: Update WindowManager
Change to use `layout_manager.get_active_rules()` instead of `config_manager.get_all_rules()`

### Step 6: Update Service
Pass `layout_manager` to `WindowManager` constructor

### Step 7: Fix Layout Rule Data Model
Change from `target_monitor_id` to `target_display` (logical display number)

### Step 8: Update API Endpoint
Accept `target_display` instead of `target_monitor_id`, validate against screen_requirements

### Step 9: Update WindowDetailsView
Show displays from layout's screen_requirements, return `target_display` in rule config

### Step 10: Update frontend/frontend-switcher.py
Remove `monitors` parameter from WindowDetailsView instantiation

---

## 🧪 Testing Checklist

- [ ] No layout active = no rules applied
- [ ] Layout activation = rules apply within 5 seconds
- [ ] Layout deactivation = rules stop applying
- [ ] Add rule to active layout = applies immediately
- [ ] `monitors_config.json` has NO `application_rules`
- [ ] Rules in layouts use `target_display` not `target_monitor_id`
- [ ] Display mapping works correctly (logical not physical)

---

## 📁 Files Modified

1. `monitors_config.json` - Remove application_rules
2. `layouts/dual-screen-home.json` - Fix rule format
3. `window_stuff/config_manager.py` - Remove rule methods
4. `window_stuff/layout_manager.py` - Add get_active_rules(), simplify activate/deactivate
5. `window_stuff/window_manager.py` - Use layout_manager
6. `window_stuff/service.py` - Pass layout_manager
7. `window_stuff/api.py` - Update rule endpoint
8. `commands.py` - Update WindowDetailsView
9. `frontend/frontend-switcher.py` - Update WindowDetailsView instantiation

**Total: 9 files**
