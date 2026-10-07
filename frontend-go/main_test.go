package main

import (
	"os"
	"runtime"
	"strings"
	"testing"
	"unsafe"

	"github.com/TotallyGamerJet/clay"
)

func TestNativeWaylandSelectionPreservesSession(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("Wayland selection applies to Linux")
	}
	for _, display := range []string{":1", ""} {
		t.Run("DISPLAY="+display, func(t *testing.T) {
			t.Setenv("DISPLAY", display)
			t.Setenv("WAYLAND_DISPLAY", "wayland-1")
			if err := configureWindowPlatform(); err != nil {
				t.Fatal(err)
			}
			if os.Getenv("DISPLAY") != "" || os.Getenv("WAYLAND_DISPLAY") != "wayland-1" {
				t.Fatal("native selection must preserve Wayland and disable X11 fallback")
			}
		})
	}
}

func TestNativeWaylandSelectionRequiresSession(t *testing.T) {
	if runtime.GOOS != "linux" {
		t.Skip("Wayland selection applies to Linux")
	}
	t.Setenv("DISPLAY", ":1")
	t.Setenv("WAYLAND_DISPLAY", "")
	if err := configureWindowPlatform(); err == nil {
		t.Fatal("native selection must reject a missing Wayland session")
	}
	if os.Getenv("DISPLAY") != ":1" {
		t.Fatal("failed selection must not change X11 session")
	}
}

func TestSwitcherContentStartsAtTop(t *testing.T) {
	arena := clay.CreateArenaWithCapacityAndMemory(make([]byte, clay.MinMemorySize()))
	clay.Initialize(arena, clay.Dimensions{Width: float32(width), Height: float32(height)}, clay.ErrorHandler{ErrorHandlerFunction: func(err clay.ErrorData) { t.Error(err) }})
	clay.SetMeasureTextFunction(func(value clay.StringSlice, config *clay.TextElementConfig, _ unsafe.Pointer) clay.Dimensions {
		return clay.Dimensions{Width: float32(len(value.String())) * float32(config.FontSize) / 2, Height: float32(config.FontSize)}
	}, unsafe.Pointer(nil))
	for _, size := range []clay.Dimensions{{Width: 720, Height: 430}, {Width: 1200, Height: 900}} {
		clay.SetLayoutDimensions(size)
		for _, count := range []int{0, 1, 12} {
			f := frontend{}
			for i := 0; i < count; i++ {
				f.filtered = append(f.filtered, item{Title: "Window", AppName: "App"})
			}
			clay.BeginLayout()
			f.draw()
			commands := clay.EndLayout()
			found := false
			helpFound := false
			resultIndex := 0
			for command := range commands.Iter() {
				if command.CommandType != clay.RENDER_COMMAND_TYPE_TEXT {
					continue
				}
				value := command.RenderData.Text.StringContents.String()
				if strings.HasPrefix(value, "query:") {
					found = true
					if command.BoundingBox.Y != 0 {
						t.Errorf("%d results: query Y = %v, want 0", count, command.BoundingBox.Y)
					}
				} else if strings.Contains(value, "Window") {
					wantY := float32(42 + resultIndex*26)
					if command.BoundingBox.Y != wantY {
						t.Errorf("%+v, %d results: result %d Y = %v, want %v", size, count, resultIndex, command.BoundingBox.Y, wantY)
					}
					resultIndex++
				} else if strings.HasPrefix(value, "Enter to switch") {
					helpFound = true
					wantY := size.Height - 20 - 16
					if command.BoundingBox.Y != wantY {
						t.Errorf("%+v, %d results: help Y = %v, want %v at bottom", size, count, command.BoundingBox.Y, wantY)
					}
				}
			}
			if !found {
				t.Errorf("%d results: query missing", count)
			}
			if resultIndex != count || !helpFound {
				t.Errorf("%+v: got %d of %d results; help found = %v", size, resultIndex, count, helpFound)
			}
		}
	}
}
