package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

const (
	frontendWindowMarker = "__SCREENY_WINDOW_SWITCHER_UNIQUE_MARKER__"
	frontendFocusTimeout = 2 * time.Second
	frontendFocusRetry   = 100 * time.Millisecond
)

// COSMIC IDs belong to the backend helper, not Raylib. A process-specific title
// lets us discover our own ID without selecting a side-by-side test frontend.
var frontendWindowTitle = fmt.Sprintf("%s [%d]", frontendWindowMarker, os.Getpid())

func focusFrontend(ctx context.Context, client *http.Client, baseURL, title string) error {
	ticker := time.NewTicker(frontendFocusRetry)
	defer ticker.Stop()
	var lastErr error
	for {
		if ctx.Err() != nil {
			if ctx.Err() == context.Canceled {
				return context.Canceled
			}
			return fmt.Errorf("window %q: %w (last attempt: %v)", title, ctx.Err(), lastErr)
		}
		lastErr = focusFrontendAttempt(ctx, client, baseURL, title)
		if lastErr == nil {
			return nil
		}
		select {
		case <-ctx.Done():
		case <-ticker.C:
		}
	}
}

func focusFrontendAttempt(ctx context.Context, client *http.Client, baseURL, title string) error {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/windows", nil)
	if err != nil {
		return err
	}
	response, err := client.Do(request)
	if err != nil {
		return err
	}
	var windows []struct {
		Title string `json:"title"`
		HWND  int64  `json:"hwnd"`
	}
	err = json.NewDecoder(response.Body).Decode(&windows)
	response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("window lookup: HTTP %d", response.StatusCode)
	}
	if err != nil {
		return err
	}
	var id int64
	for _, window := range windows {
		if window.Title == title {
			if id != 0 {
				return fmt.Errorf("ambiguous frontend title %q", title)
			}
			id = window.HWND
		}
	}
	if id == 0 {
		return fmt.Errorf("frontend not mapped yet")
	}
	body := strings.NewReader(fmt.Sprintf(`{"hwnd":%d}`, id))
	request, err = http.NewRequestWithContext(ctx, http.MethodPost, baseURL+"/focus-window-only", body)
	if err != nil {
		return err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err = client.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("focus window %d: HTTP %d", id, response.StatusCode)
	}
	return nil
}
