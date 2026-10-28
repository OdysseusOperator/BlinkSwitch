package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"
)

func TestFocusFrontendWaitsForMappingAndRetriesFocus(t *testing.T) {
	var lookups, focusCalls atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/windows":
			if lookups.Add(1) == 1 {
				w.Write([]byte(`[]`))
				return
			}
			w.Write([]byte(`[{"title":"Other frontend","hwnd":11},{"title":"Our frontend","hwnd":42}]`))
		case "/focus-window-only":
			var payload struct {
				HWND int64 `json:"hwnd"`
			}
			if r.Method != http.MethodPost || r.Header.Get("Content-Type") != "application/json" {
				t.Error("expected JSON POST")
			}
			if err := json.NewDecoder(r.Body).Decode(&payload); err != nil || payload.HWND != 42 {
				t.Errorf("focused wrong window: %+v, %v", payload, err)
			}
			if focusCalls.Add(1) == 1 {
				w.WriteHeader(http.StatusInternalServerError)
			}
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
		}
	}))
	defer server.Close()
	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()
	if err := focusFrontend(ctx, server.Client(), server.URL, "Our frontend"); err != nil {
		t.Fatal(err)
	}
	if lookups.Load() != 3 || focusCalls.Load() != 2 {
		t.Fatalf("lookups=%d focusCalls=%d", lookups.Load(), focusCalls.Load())
	}
}

func TestFocusFrontendRejectsInvalidLookup(t *testing.T) {
	for _, test := range []struct {
		name   string
		status int
		body   string
	}{
		{"missing", 200, `[]`},
		{"malformed", 200, `{`},
		{"failed", 503, `[]`},
		{"ambiguous", 200, `[{"title":"ours","hwnd":1},{"title":"ours","hwnd":2}]`},
	} {
		t.Run(test.name, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if r.URL.Path != "/windows" {
					t.Error("must not request focus for invalid lookup")
				}
				w.WriteHeader(test.status)
				w.Write([]byte(test.body))
			}))
			defer server.Close()
			if err := focusFrontendAttempt(context.Background(), server.Client(), server.URL, "ours"); err == nil {
				t.Fatal("expected lookup error")
			}
		})
	}
}

func TestFocusFrontendCancellation(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		cancel() // Hiding the frontend cancels discovery before any focus request.
		w.Write([]byte(`[]`))
	}))
	defer server.Close()
	defer cancel()
	if err := focusFrontend(ctx, server.Client(), server.URL, "ours"); err != context.Canceled {
		t.Fatalf("expected cancellation, got %v", err)
	}
}

func TestFocusFrontendDeadline(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`[]`))
	}))
	defer server.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
	defer cancel()
	if err := focusFrontend(ctx, server.Client(), server.URL, "ours"); err == nil {
		t.Fatal("expected bounded discovery timeout")
	}
}
