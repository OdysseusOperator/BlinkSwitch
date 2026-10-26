package main

import (
	"fmt"
	"net/http"

	rl "github.com/gen2brain/raylib-go/raylib"
)

type testMonitor struct {
	ID     string `json:"id"`
	Name   string `json:"name"`
	Width  int    `json:"width"`
	Height int    `json:"height"`
}

type testResult struct {
	windows  []item
	monitors []testMonitor
	loading  bool
	err      error
}

// Workers only send results; all UI state remains owned by the main thread.
type windowTest struct {
	windows   []item
	monitors  []testMonitor
	window    item
	screen    int
	workspace int
	busy      bool
	results   chan testResult
}

func (f *frontend) loadTestWindows() {
	t := &windowTest{workspace: 1, busy: true, results: make(chan testResult, 1)}
	f.test = t
	f.viewTitle = "Test - select a window"
	f.viewRows = []string{"Loading windows and screens..."}
	f.viewHelp = "Enter select | Esc close"
	go func() {
		r := testResult{loading: true}
		r.err = f.request(http.MethodGet, "/windows", nil, &r.windows)
		if r.err == nil {
			r.err = f.request(http.MethodGet, "/monitors?connected_only=true", nil, &r.monitors)
		}
		t.results <- r
	}()
}

func (f *frontend) pollTestResult() {
	t := f.test
	if t == nil {
		return
	}
	select {
	case r := <-t.results:
		t.busy = false
		if r.loading {
			t.windows, t.monitors = r.windows, r.monitors
			if f.view == viewTestWindows {
				f.viewRows = nil
				for _, w := range t.windows {
					f.viewRows = append(f.viewRows, label(w))
				}
				if len(f.viewRows) == 0 {
					f.viewRows = []string{"No windows available"}
				}
			}
		}
		if r.err != nil {
			f.showStatus(r.err.Error())
		} else if !r.loading {
			f.showStatus("Test operation completed")
		}
	default:
	}
}

func (f *frontend) rebuildTestRows() {
	t := f.test
	screen := "No connected screens"
	if len(t.monitors) > 0 {
		m := t.monitors[t.screen]
		screen = fmt.Sprintf("%d: %s (%dx%d)", t.screen+1, stringValue(m.Name, m.ID), m.Width, m.Height)
	}
	f.viewTitle = "Test - " + label(t.window)
	f.viewRows = []string{"Move to screen: " + screen, fmt.Sprintf("Move to workspace: %d", t.workspace), "Maximize"}
	f.viewHelp = "Left/Right destination | Enter run | Esc back (no undo)"
}

func (f *frontend) handleTestInput() {
	t := f.test
	if t == nil || t.busy {
		return
	}
	if f.view == viewTestWindows {
		if rl.IsKeyPressed(rl.KeyEnter) && f.selected >= 0 && f.selected < len(t.windows) {
			t.window = t.windows[f.selected]
			f.view = viewTestActions
			f.selected = 0
			f.rebuildTestRows()
		}
		return
	}
	delta := 0
	if rl.IsKeyPressed(rl.KeyLeft) {
		delta = -1
	}
	if rl.IsKeyPressed(rl.KeyRight) {
		delta = 1
	}
	if f.selected == 0 && len(t.monitors) > 0 {
		t.screen = (t.screen + delta + len(t.monitors)) % len(t.monitors)
	}
	if f.selected == 1 {
		t.workspace = max(1, t.workspace+delta)
	}
	f.rebuildTestRows()
	if rl.IsKeyPressed(rl.KeyEnter) {
		f.runTestAction()
	}
}

func (f *frontend) runTestAction() {
	t := f.test
	if t == nil || t.busy {
		return
	}
	payload := map[string]any{"hwnd": t.window.HWND}
	switch f.selected {
	case 0:
		if len(t.monitors) == 0 {
			f.showStatus("No connected screens")
			return
		}
		payload["action"], payload["monitor_id"] = "screen", t.monitors[t.screen].ID
	case 1:
		payload["action"], payload["workspace"] = "workspace", t.workspace
	case 2:
		payload["action"] = "maximize"
	default:
		return
	}
	t.busy = true
	f.showStatus("Running test operation...")
	go func() { t.results <- testResult{err: f.request(http.MethodPost, "/test-window-action", payload, nil)} }()
}
