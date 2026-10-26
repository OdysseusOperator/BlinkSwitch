package main

import (
	"fmt"
	"net/http"
	"os"
	"time"
)

type ruleState struct {
	Configured bool              `json:"configured"`
	Layout     string            `json:"layout_name"`
	Assignment map[string]string `json:"assignment"`
}

func (f *frontend) configureRules(layout string, assignment map[string]string) error {
	var name any
	if layout != "" {
		name = layout
	}
	var state ruleState
	if err := f.request(http.MethodPut, "/rule-enforcement", map[string]any{"layout_name": name, "assignment": assignment}, &state); err != nil {
		return err
	}
	f.activeLayout = state.Layout
	return nil
}

func (f *frontend) initializeRuleState() {
	var state ruleState
	if err := f.request(http.MethodGet, "/rule-enforcement", nil, &state); err != nil {
		f.showStatus(err.Error())
		return
	}
	f.activeLayout = state.Layout
	if state.Configured {
		return
	}
	var settings map[string]any
	if err := f.request(http.MethodGet, "/settings", nil, &settings); err != nil {
		f.showStatus(err.Error())
		return
	}
	layout := stringValue(settings["default_layout"], "")
	if layout != "" {
		if err := f.configureRules(layout, loadAssignments()[layout]); err != nil {
			f.showStatus(err.Error())
		}
	}
}

// Only visibility and state synchronization run here. Rule ticks belong to the backend.
func (f *frontend) startRuleStateSync(stop <-chan struct{}, visibility <-chan bool, states chan ruleState) {
	path := fmt.Sprintf("/rule-enforcement/clients/go-%d-%d", os.Getpid(), time.Now().UnixNano())
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()
	visible := false
	for {
		select {
		case <-stop:
			return
		case visible = <-visibility:
		case <-ticker.C:
			var state ruleState
			if err := f.request(http.MethodPut, path, map[string]any{"visible": visible}, &state); err != nil {
				continue
			}
			select {
			case states <- state:
			default:
			}
		}
	}
}
