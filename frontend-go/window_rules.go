package main

import (
	"fmt"
	"net/http"
	"net/url"
	"strings"

	rl "github.com/gen2brain/raylib-go/raylib"
)

type windowRule struct {
	ID              string `json:"rule_id,omitempty"`
	MatchType       string `json:"match_type"`
	MatchValue      string `json:"match_value"`
	TargetSlot      int    `json:"target_slot"`
	TargetWorkspace int    `json:"target_workspace,omitempty"`
	Maximize        any    `json:"maximize"`
	SkipPopups      bool   `json:"skip_popups"`
}

type ruleSlot struct {
	Slot        int    `json:"slot"`
	Description string `json:"description"`
}

type windowRuleEditor struct {
	Layout string
	Window item
	Slots  []ruleSlot
	Rule   windowRule
}

func ruleMatches(window item, rule windowRule) bool {
	value := strings.ToLower(strings.TrimSpace(rule.MatchValue))
	if value == "" {
		return false
	}
	switch rule.MatchType {
	case "exe":
		name := window.ExeName
		if strings.TrimSpace(name) == "" {
			name = window.AppName
		}
		normalize := func(s string) string { return strings.TrimSuffix(strings.ToLower(strings.TrimSpace(s)), ".exe") }
		return normalize(name) == normalize(value)
	case "window_title":
		return strings.Contains(strings.ToLower(window.Title), value)
	case "process_path":
		return strings.ToLower(window.ProcessPath) == value
	}
	return false
}

func (f *frontend) openWindowRule() {
	if f.selected < 0 || f.selected >= len(f.windows) {
		return
	}
	layout := f.activeLayout
	if layout == "" {
		var settings map[string]any
		if err := f.request(http.MethodGet, "/settings", nil, &settings); err != nil {
			f.showStatus(err.Error())
			return
		}
		layout = strings.TrimSuffix(stringValue(settings["default_layout"], ""), ".json")
	}
	if layout == "" {
		f.showStatus("Activate a layout in /layouts before configuring a rule")
		return
	}
	var preview struct {
		Data struct {
			Requirements struct {
				Screens []ruleSlot `json:"screens"`
			} `json:"screen_requirements"`
			Rules []windowRule `json:"rules"`
		} `json:"data"`
	}
	if err := f.request(http.MethodGet, "/layouts/"+url.PathEscape(layout), nil, &preview); err != nil {
		f.showStatus(err.Error())
		return
	}
	if len(preview.Data.Requirements.Screens) == 0 {
		f.showStatus("This layout has no monitor slots")
		return
	}
	window := f.windows[f.selected]
	name := window.ExeName
	if strings.TrimSpace(name) == "" {
		name = window.AppName
	}
	rule := windowRule{MatchType: "exe", MatchValue: name, TargetSlot: preview.Data.Requirements.Screens[0].Slot, TargetWorkspace: 1, Maximize: "unset"}
	if strings.TrimSpace(name) == "" {
		rule.MatchType = "window_title"
		rule.MatchValue = window.Title
	}
	for _, existing := range preview.Data.Rules {
		if ruleMatches(window, existing) {
			rule = existing
			break
		}
	}
	if rule.TargetWorkspace < 1 {
		rule.TargetWorkspace = 1
	}
	switch rule.Maximize {
	case true:
		rule.Maximize = "maximized"
	case false, nil:
		rule.Maximize = "unset"
	}
	f.ruleEditor = &windowRuleEditor{Layout: layout, Window: window, Slots: preview.Data.Requirements.Screens, Rule: rule}
	f.view = viewDetails
	f.selected = 0
	f.rebuildRuleRows()
}

func (f *frontend) rebuildRuleRows() {
	e := f.ruleEditor
	f.viewTitle = "Window Rule - " + e.Layout
	f.viewRows = []string{}
	for _, slot := range e.Slots {
		marker := "[ ]"
		if slot.Slot == e.Rule.TargetSlot {
			marker = "[*]"
		}
		f.viewRows = append(f.viewRows, fmt.Sprintf("%s Slot %d: %s", marker, slot.Slot, slot.Description))
	}
	f.viewRows = append(f.viewRows,
		fmt.Sprintf("Workspace: %d", e.Rule.TargetWorkspace),
		fmt.Sprintf("Match: %s = %s", e.Rule.MatchType, e.Rule.MatchValue),
		fmt.Sprintf("Maximize: %v", e.Rule.Maximize),
		fmt.Sprintf("Skip popups: %t", e.Rule.SkipPopups),
		"Save rule",
	)
	f.viewHelp = "Enter change | W workspace | M maximize | S save | Esc back"
	if e.Rule.ID != "" {
		f.viewHelp += " | D delete"
	}
}

func (f *frontend) changeRuleOption() {
	e := f.ruleEditor
	n := len(e.Slots)
	if f.selected < n {
		e.Rule.TargetSlot = e.Slots[f.selected].Slot
	} else {
		switch f.selected - n {
		case 0:
			e.Rule.TargetWorkspace = e.Rule.TargetWorkspace%9 + 1
		case 1:
			// Preserve the identity of existing rules: the backend upserts by match,
			// not rule ID. Changing it would silently leave the old rule behind.
			if e.Rule.MatchType == "window_title" && e.Rule.ID == "" {
				f.textInput = true
				f.textValue = e.Rule.MatchValue
			} else if e.Rule.ID == "" {
				e.Rule.MatchType = "window_title"
				e.Rule.MatchValue = e.Window.Title
			} else {
				f.showStatus("Existing rule match is preserved; delete it to change match type")
			}
		case 2:
			e.Rule.Maximize = nextMaximize(e.Rule.Maximize)
		case 3:
			e.Rule.SkipPopups = !e.Rule.SkipPopups
		case 4:
			f.saveWindowRule()
			return
		}
	}
	f.rebuildRuleRows()
}

func nextMaximize(value any) string {
	switch value {
	case "unset":
		return "maximized"
	case "maximized":
		return "not_maximized"
	default:
		return "unset"
	}
}

func (f *frontend) handleRuleInput() {
	if f.ruleEditor == nil {
		return
	}
	if rl.IsKeyPressed(rl.KeyEnter) {
		f.changeRuleOption()
		return
	}
	if rl.IsKeyPressed(rl.KeyS) {
		f.saveWindowRule()
		return
	}
	if rl.IsKeyPressed(rl.KeyD) {
		f.deleteWindowRule()
		return
	}
	if rl.IsKeyPressed(rl.KeyW) {
		f.ruleEditor.Rule.TargetWorkspace = f.ruleEditor.Rule.TargetWorkspace%9 + 1
	}
	if rl.IsKeyPressed(rl.KeyM) {
		f.ruleEditor.Rule.Maximize = nextMaximize(f.ruleEditor.Rule.Maximize)
	}
	if rl.IsKeyPressed(rl.KeyP) {
		f.ruleEditor.Rule.SkipPopups = !f.ruleEditor.Rule.SkipPopups
	}
	f.rebuildRuleRows()
}

func (f *frontend) saveWindowRule() {
	e := f.ruleEditor
	if strings.TrimSpace(e.Rule.MatchValue) == "" {
		f.showStatus("Rule match cannot be empty")
		return
	}
	if err := f.request(http.MethodPost, "/layouts/"+url.PathEscape(e.Layout)+"/rules", e.Rule, nil); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.openView(viewWindows)
	f.showStatus("Window rule saved")
}

func (f *frontend) deleteWindowRule() {
	e := f.ruleEditor
	if e.Rule.ID == "" {
		return
	}
	if err := f.request(http.MethodDelete, "/layouts/"+url.PathEscape(e.Layout)+"/rules/"+url.PathEscape(e.Rule.ID), nil, nil); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.openView(viewWindows)
	f.showStatus("Window rule deleted")
}
