//go:build !linux || !wayland || !cgo

package main

func probeRenderViewport() string {
	return "RENDER CHECK unavailable: build with -tags wayland on Linux with CGO enabled"
}
