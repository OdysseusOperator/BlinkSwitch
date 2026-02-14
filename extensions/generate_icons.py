"""Generate simple extension icons with 'S' letter."""

from PIL import Image, ImageDraw, ImageFont


def create_icon(size, output_path):
    """Create a simple icon with 'S' on colored background."""
    # Create image with blue background
    img = Image.new("RGB", (size, size), color="#4A90E2")
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fall back to default if not available
    try:
        # Try common Windows fonts
        font_size = int(size * 0.6)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        # Fall back to default font
        font = ImageFont.load_default()

    # Draw 'S' in white, centered
    text = "S"

    # Get text bounding box for centering
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Calculate position to center text
    x = (size - text_width) // 2 - bbox[0]
    y = (size - text_height) // 2 - bbox[1]

    # Draw text
    draw.text((x, y), text, fill="white", font=font)

    # Save image
    img.save(output_path, "PNG")
    print(f"Created {output_path} ({size}x{size})")


if __name__ == "__main__":
    import os

    icons_dir = "extensions/chromebased-browser/icons"
    os.makedirs(icons_dir, exist_ok=True)

    # Generate all three required sizes
    create_icon(16, f"{icons_dir}/icon16.png")
    create_icon(48, f"{icons_dir}/icon48.png")
    create_icon(128, f"{icons_dir}/icon128.png")

    print("\nAll icons generated successfully!")
