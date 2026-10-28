package main

import "testing"

func TestFrontendFontCodepoints(t *testing.T) {
	codepoints := frontendFontCodepoints()
	loaded := make(map[rune]bool, len(codepoints))
	for _, codepoint := range codepoints {
		if loaded[codepoint] {
			t.Fatalf("duplicate glyph U+%04X", codepoint)
		}
		if codepoint < 32 || (codepoint >= 0x7F && codepoint < 0xA0) {
			t.Fatalf("unexpected control glyph U+%04X", codepoint)
		}
		loaded[codepoint] = true
	}
	for codepoint := rune(32); codepoint <= 126; codepoint++ {
		if !loaded[codepoint] {
			t.Errorf("missing ASCII glyph %q", codepoint)
		}
	}
	for _, codepoint := range "YouTube — Mozilla Firefox ‘quotes’ “quotes” … – café € Ελληνικά Русский →" {
		if !loaded[codepoint] {
			t.Errorf("missing title glyph %q (U+%04X)", codepoint, codepoint)
		}
	}
	if len(codepoints) > 2048 {
		t.Fatalf("font atlas unexpectedly large: %d glyphs", len(codepoints))
	}
}
