package main

import (
	"fmt"
	"os"

	rl "github.com/gen2brain/raylib-go/raylib"
)

// Accessed only on the rendering thread, including Clay's measurement callback.
var fontsBySize = map[uint16]rl.Font{}

func fontForSize(size uint16) rl.Font {
	if font, ok := fontsBySize[size]; ok {
		return font
	}
	font := rl.LoadFontEx(fontPath, int32(size), frontendFontCodepoints())
	if font.Texture.ID == 0 || font.Texture.ID == currentFont.Texture.ID {
		fmt.Fprintf(os.Stderr, "Could not load font %s at %dpx; using default\n", fontPath, size)
		font = currentFont
	} else {
		rl.SetTextureFilter(font.Texture, rl.FilterPoint)
	}
	fontsBySize[size] = font
	return font
}

func unloadFrontendFonts() {
	for size, font := range fontsBySize {
		if font.Texture.ID != currentFont.Texture.ID {
			rl.UnloadFont(font)
		}
		delete(fontsBySize, size)
	}
}
