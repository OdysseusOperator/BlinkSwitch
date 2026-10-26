package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"
	"time"
)

func TestTestCommandLoadsWindowPicker(t *testing.T) {
	f := &frontend{query: "/test", client: &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		switch r.URL.Path {
		case "/screenassign/windows":
			return ruleResponse(`[{"hwnd":42,"title":"Editor","app_name":"editor"}]`, 200), nil
		case "/screenassign/monitors":
			if r.URL.Query().Get("connected_only") != "true" {
				t.Error("must request connected monitors")
			}
			return ruleResponse(`[{"id":"screen-b","width":1920,"height":1080}]`, 200), nil
		}
		return nil, fmt.Errorf("unexpected path: %s", r.URL.Path)
	})}}
	f.executeCommand()
	if f.view != viewTestWindows || f.test == nil {
		t.Fatal("/test did not open picker")
	}
	select {
	case result := <-f.test.results:
		f.test.results <- result
	case <-time.After(time.Second):
		t.Fatal("picker did not load")
	}
	f.pollTestResult()
	if f.test.busy || len(f.test.windows) != 1 || len(f.test.monitors) != 1 || len(f.viewRows) != 1 {
		t.Fatalf("invalid picker state: %+v", f.test)
	}
	f.selected = 8
	f.filter()
	if f.selected != 8 {
		t.Fatal("background switcher refresh changed picker selection")
	}
	f.view = viewTestActions
	f.test.results <- testResult{err: fmt.Errorf("Workspace unavailable")}
	f.pollTestResult()
	if f.status != "Workspace unavailable" {
		t.Fatalf("missing error: %s", f.status)
	}
}

func TestOneShotWindowActions(t *testing.T) {
	for index, want := range []map[string]any{
		{"hwnd": float64(42), "action": "screen", "monitor_id": "screen-b"},
		{"hwnd": float64(42), "action": "workspace", "workspace": float64(3)},
		{"hwnd": float64(42), "action": "maximize"},
	} {
		t.Run(fmt.Sprint(index), func(t *testing.T) {
			requests := make(chan map[string]any, 2)
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/screenassign/test-window-action" || r.Method != http.MethodPost {
					t.Errorf("unexpected request: %s %s", r.Method, r.URL.Path)
				}
				var payload map[string]any
				if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
					t.Error(err)
				}
				requests <- payload
				w.WriteHeader(http.StatusOK)
			}))
			defer server.Close()
			client := &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
				r.URL.Scheme = "http"
				r.URL.Host = server.Listener.Addr().String()
				return http.DefaultTransport.RoundTrip(r)
			})}
			f := &frontend{client: client, selected: index, test: &windowTest{
				window: item{HWND: 42}, monitors: []testMonitor{{ID: "screen-b"}}, workspace: 3, results: make(chan testResult, 1),
			}}
			f.runTestAction()
			f.runTestAction() // Ignore repeated Enter while the first operation is pending.
			select {
			case got := <-requests:
				if !reflect.DeepEqual(got, want) {
					t.Fatalf("got %v, want %v", got, want)
				}
			case <-time.After(time.Second):
				t.Fatal("operation did not run")
			}
			select {
			case result := <-f.test.results:
				if result.err != nil {
					t.Fatal(result.err)
				}
			case <-time.After(time.Second):
				t.Fatal("operation did not finish")
			}
			if len(requests) != 0 {
				t.Fatal("duplicate operation")
			}
		})
	}
}
