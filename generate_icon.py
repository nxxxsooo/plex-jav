#!/usr/bin/env python3
"""
Generate plex-jav Docker icon programmatically using Pillow.
1024x1024 PNG, squircle shape, Plex orange + Japanese aesthetic.
"""

from PIL import Image, ImageDraw, ImageFont
import math

# Canvas settings
SIZE = 1024
CENTER = (SIZE // 2, SIZE // 2)
RADIUS = SIZE // 2 - 20

# Colors (Plex orange + dark theme)
BG_DARK = "#0A0A0A"
BG_DARKER = "#050505"
PLEX_ORANGE = "#E5A00D"
PLEX_ORANGE_DARK = "#CC7B19"
PLEX_ORANGE_LIGHT = "#FFC145"
JAPANESE_RED = "#BC002D"


def draw_squircle(draw, xy, radius, fill):
    """Draw a squircle (rounded square) using Bezier curves."""
    x0, y0, x1, y1 = xy
    w = x1 - x0
    h = y1 - y0
    r = radius

    # Draw rounded rectangle with smooth corners
    draw.rounded_rectangle(xy, radius=r, fill=fill)


def draw_background(canvas):
    """Draw dark gradient background."""
    draw = ImageDraw.Draw(canvas)

    # Base dark background
    draw_squircle(draw, (40, 40, SIZE - 40, SIZE - 40), radius=220, fill=BG_DARK)

    # Add subtle radial gradient effect with darker center
    for i in range(200, 0, -5):
        alpha = int(255 * (i / 200) * 0.15)
        overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        draw_ov.ellipse(
            (CENTER[0] - i, CENTER[1] - i, CENTER[0] + i, CENTER[1] + i),
            fill=(0, 0, 0, alpha),
        )
        canvas.paste(overlay, mask=overlay)

    return canvas


def draw_film_element(draw):
    """Draw a stylized film strip element."""
    # Main film strip - diagonal
    film_width = 120
    film_height = 420

    # Rotate film strip by 15 degrees
    angle = math.radians(-15)

    # Calculate film strip position
    cx, cy = CENTER
    film_x = cx - film_width // 2
    film_y = cy - film_height // 2 - 40

    # Draw film strip base
    draw.rounded_rectangle(
        (film_x, film_y, film_x + film_width, film_y + film_height),
        radius=15,
        fill=PLEX_ORANGE_DARK,
    )

    # Draw film perforations
    perfo_size = 16
    perfo_spacing = 36
    start_y = film_y + 30

    for i in range(10):
        y_pos = start_y + i * perfo_spacing
        # Left perforations
        draw.rectangle(
            (film_x + 18, y_pos, film_x + 18 + perfo_size, y_pos + perfo_size),
            fill=BG_DARK,
        )
        # Right perforations
        draw.rectangle(
            (
                film_x + film_width - 18 - perfo_size,
                y_pos,
                film_x + film_width - 18,
                y_pos + perfo_size,
            ),
            fill=BG_DARK,
        )


def draw_torii_gate(draw):
    """Draw a minimalist, geometric torii gate silhouette."""
    cx, cy = CENTER

    # Torii dimensions
    post_width = 32
    post_height = 180
    top_beam_width = 320
    top_beam_height = 40
    middle_beam_width = 220
    middle_beam_height = 28

    # Position torii to the right of center
    torii_x = cx + 160
    torii_y = cy - 40

    # Draw posts (slightly angled)
    # Left post
    draw.polygon(
        [
            (torii_x - post_width // 2 - 15, torii_y + post_height),
            (torii_x - post_width // 2 + 15, torii_y + post_height),
            (torii_x - post_width // 2 + 5, torii_y - 20),
            (torii_x - post_width // 2 - 5, torii_y - 20),
        ],
        fill=PLEX_ORANGE,
    )

    # Right post
    draw.polygon(
        [
            (torii_x + post_width // 2 - 15, torii_y + post_height),
            (torii_x + post_width // 2 + 15, torii_y + post_height),
            (torii_x + post_width // 2 - 5, torii_y - 20),
            (torii_x + post_width // 2 + 5, torii_y - 20),
        ],
        fill=PLEX_ORANGE,
    )

    # Draw middle beam (nuki)
    draw.rounded_rectangle(
        (
            torii_x - middle_beam_width // 2,
            torii_y + 30,
            torii_x + middle_beam_width // 2,
            torii_y + 30 + middle_beam_height,
        ),
        radius=8,
        fill=PLEX_ORANGE_DARK,
    )

    # Draw top beam (kasagi) with slight curve
    draw.rounded_rectangle(
        (
            torii_x - top_beam_width // 2,
            torii_y - 50,
            torii_x + top_beam_width // 2,
            torii_y - 50 + top_beam_height,
        ),
        radius=12,
        fill=PLEX_ORANGE_LIGHT,
    )

    # Draw top decorative bar (shimaki)
    draw.rectangle(
        (
            torii_x - top_beam_width // 2 + 20,
            torii_y - 70,
            torii_x + top_beam_width // 2 - 20,
            torii_y - 60,
        ),
        fill=PLEX_ORANGE,
    )


def draw_play_button(draw):
    """Draw a subtle play button triangle."""
    cx, cy = CENTER

    # Position play button to the left of center
    play_x = cx - 160
    play_y = cy + 40

    # Play button triangle
    triangle_size = 90
    draw.polygon(
        [
            (play_x - triangle_size // 2, play_y - triangle_size // 2),
            (play_x - triangle_size // 2, play_y + triangle_size // 2),
            (play_x + triangle_size // 2 + 10, play_y),
        ],
        fill=PLEX_ORANGE_LIGHT,
    )


def draw_jav_text(draw):
    """Draw 'JAV' as a design element."""
    cx, cy = CENTER

    # Use a bold sans-serif font, or fallback to default
    try:
        # Try to use a system font
        font = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue-Bold.ttf", 140)
    except:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial Bold.ttf", 140)
        except:
            font = ImageFont.load_default()

    text = "JAV"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Position text below center
    text_x = cx - text_width // 2
    text_y = cy + 280

    # Draw text with orange gradient fill
    draw.text((text_x, text_y), text, font=font, fill=PLEX_ORANGE)


def draw_sakura_accent(draw):
    """Draw a tiny, subtle cherry blossom accent."""
    cx, cy = CENTER
    sakura_x = cx + 240
    sakura_y = cy - 200

    # Draw 5-petal sakura
    petal_count = 5
    petal_radius = 18
    center_radius = 6

    for i in range(petal_count):
        angle = math.radians(i * (360 / petal_count) - 90)
        px = sakura_x + math.cos(angle) * 16
        py = sakura_y + math.sin(angle) * 16
        draw.ellipse(
            (
                px - petal_radius,
                py - petal_radius,
                px + petal_radius,
                py + petal_radius,
            ),
            fill=JAPANESE_RED,
        )

    # Center
    draw.ellipse(
        (
            sakura_x - center_radius,
            sakura_y - center_radius,
            sakura_x + center_radius,
            sakura_y + center_radius,
        ),
        fill="#FFE0E0",
    )


def main():
    # Create canvas with transparent background
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # 1. Draw background squircle
    draw_background(canvas)

    # 2. Draw design elements
    draw_film_element(draw)
    draw_torii_gate(draw)
    draw_play_button(draw)
    draw_jav_text(draw)
    draw_sakura_accent(draw)

    # Save the final icon
    output_path = "/Users/mingjian/Documents/sync/GitHub/plex-jav/plex-jav-icon.png"
    canvas.save(output_path, "PNG")
    print(f"Icon generated successfully at: {output_path}")


if __name__ == "__main__":
    main()
