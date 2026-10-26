package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
)

type ruleTransport func(*http.Request) (*http.Response, error)

func (fn ruleTransport) RoundTrip(r *http.Request) (*http.Response, error) { return fn(r) }

func ruleResponse(body string, status int) *http.Response {
	return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: make(http.Header)}
}

func TestWindowRuleFlow(t *testing.T) {
	var saved windowRule
	f := frontend{view: viewWindows, windows: []item{{Title: "First", AppName: "first"}, {Title: "Editor", AppName: "editor"}}, selected: 1}
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		switch r.Method + " " + r.URL.Path {
		case "GET /screenassign/settings":
			return ruleResponse(`{"default_layout":"work"}`, 200), nil
		case "GET /screenassign/layouts/work":
			return ruleResponse(`{"data":{"screen_requirements":{"screens":[{"slot":2,"description":"Main"},{"slot":5}]},"rules":[]}}`, 200), nil
		case "POST /screenassign/layouts/work/rules":
			if err := json.NewDecoder(r.Body).Decode(&saved); err != nil {
				t.Fatal(err)
			}
			return ruleResponse(`{"success":true}`, 200), nil
		case "GET /screenassign/windows":
			return ruleResponse(`[]`, 200), nil
		}
		return nil, fmt.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
	})}
	f.openWindowRule()
	if f.view != viewDetails || f.ruleEditor.Window.Title != "Editor" {
		t.Fatalf("did not open selected window: %+v", f)
	}
	f.selected = 1
	f.changeRuleOption()
	f.selected = len(f.ruleEditor.Slots)
	f.changeRuleOption()
	f.saveWindowRule()
	if saved.MatchValue != "editor" || saved.TargetSlot != 5 || saved.TargetWorkspace != 2 || saved.Maximize != "unset" {
		t.Fatalf("wrong saved rule: %+v", saved)
	}
	if f.view != viewWindows {
		t.Fatal("save should return to windows")
	}
}

func TestWindowRuleExistingAndSaveFailure(t *testing.T) {
	f := frontend{activeLayout: "work", windows: []item{{Title: "Editor", ExeName: "EDITOR.EXE"}}}
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		if r.Method == http.MethodPost {
			return ruleResponse(`{"error":"cannot save"}`, 500), nil
		}
		return ruleResponse(`{"data":{"screen_requirements":{"screens":[{"slot":1}]},"rules":[{"rule_id":"existing","match_type":"exe","match_value":"editor","target_slot":1,"maximize":true,"skip_popups":true}]}}`, 200), nil
	})}
	f.openWindowRule()
	if f.ruleEditor == nil || f.ruleEditor.Rule.ID != "existing" || f.ruleEditor.Rule.Maximize != "maximized" || !f.ruleEditor.Rule.SkipPopups {
		t.Fatal("existing rule not prepopulated")
	}
	f.saveWindowRule()
	if f.view != viewDetails || !strings.Contains(f.status, "cannot save") {
		t.Fatal("failed save must keep editor and show error")
	}
}

func TestWindowRuleRequiresLayout(t *testing.T) {
	f := frontend{view: viewWindows, windows: []item{{Title: "Editor"}}}
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) { return ruleResponse(`{}`, 200), nil })}
	f.openWindowRule()
	if f.view != viewWindows || f.ruleEditor != nil || !strings.Contains(f.status, "Activate a layout") {
		t.Fatal("missing layout should show actionable feedback")
	}
	f.windows = nil
	f.openWindowRule() // An empty list must not panic.
}

func TestRuleMatching(t *testing.T) {
	window := item{Title: "My Document", AppName: "editor", ProcessPath: "/usr/bin/editor"}
	for _, rule := range []windowRule{{MatchType: "exe", MatchValue: "EDITOR.EXE"}, {MatchType: "window_title", MatchValue: "document"}, {MatchType: "process_path", MatchValue: "/usr/bin/editor"}} {
		if !ruleMatches(window, rule) {
			t.Errorf("expected match: %+v", rule)
		}
	}
	if ruleMatches(window, windowRule{MatchType: "window_title", MatchValue: ""}) {
		t.Fatal("empty title must not match")
	}
	if nextMaximize(nextMaximize(nextMaximize("unset"))) != "unset" {
		t.Fatal("maximize cycle must wrap")
	}
}
