package main

// Raylib's default font atlas contains only ASCII. Include common title text
// and punctuation explicitly; the source font must also contain these glyphs.
// Keep the atlas bounded rather than requesting every Unicode codepoint.
func frontendFontCodepoints() []rune {
	ranges := [][2]rune{
		{0x0020, 0x007E}, // Printable ASCII, including Raylib's '?' fallback.
		{0x00A0, 0x024F}, // Latin-1 supplement and Latin extended A/B.
		{0x0370, 0x052F}, // Greek, Cyrillic, and Cyrillic supplement.
		{0x2000, 0x206F}, // General punctuation: em dash, smart quotes, ellipsis.
		{0x20A0, 0x20CF}, // Currency symbols.
		{0x2190, 0x21FF}, // Arrows.
	}
	var codepoints []rune
	for _, span := range ranges {
		for codepoint := span[0]; codepoint <= span[1]; codepoint++ {
			codepoints = append(codepoints, codepoint)
		}
	}
	return codepoints
}
