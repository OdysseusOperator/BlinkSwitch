//go:build !windows

package main

func startHotkeyListener(_ chan<- struct{}) {}
