//go:build windows

package main

import (
	"unsafe"

	"golang.org/x/sys/windows"
)

const (
	wmHotkey = 0x0312
	modAlt   = 0x0001
	vkSpace  = 0x20
)

type nativeMessage struct {
	hwnd    uintptr
	message uint32
	wParam  uintptr
	lParam  uintptr
	time    uint32
	pointX  int32
	pointY  int32
}

func startHotkeyListener(toggle chan<- struct{}) {
	user32 := windows.NewLazySystemDLL("user32.dll")
	registerHotKey := user32.NewProc("RegisterHotKey")
	unregisterHotKey := user32.NewProc("UnregisterHotKey")
	getMessage := user32.NewProc("GetMessageW")

	go func() {
		result, _, _ := registerHotKey.Call(0, 1, modAlt, vkSpace)
		if result == 0 {
			return
		}
		defer unregisterHotKey.Call(0, 1)

		var message nativeMessage
		for {
			result, _, _ := getMessage.Call(uintptr(unsafe.Pointer(&message)), 0, 0, 0)
			if int32(result) <= 0 {
				return
			}
			if message.message == wmHotkey && message.wParam == 1 {
				select {
				case toggle <- struct{}{}:
				default:
				}
			}
		}
	}()
}
