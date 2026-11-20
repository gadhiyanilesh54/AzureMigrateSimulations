"""Generate the Innovation Studio card image for AI Feasibility Assessment."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "docs" / "demo"
OUTPUT = DEMO_DIR / "Innovation_Studio_AI_Feasibility_Banner.png"
AZURE_LOGO = DEMO_DIR / "assets" / "azure-logo.png"

WIDTH = 1600
HEIGHT = 900

NAVY = (6, 27, 44)
NAVY_2 = (11, 41, 66)
AZURE = (0, 120, 212)
CYAN = (80, 230, 255)
PURPLE = (134, 97, 197)
MINT = (45, 212, 167)
WHITE = (248, 250, 252)
TEXT = (231, 238, 245)
MUTED = (157, 179, 200)
LINE = (49, 83, 109)

FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_SEMIBOLD = Path("C:/Windows/Fonts/seguisb.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int] | tuple[int, int, int],
    outline: tuple[int, int, int, int] | tuple[int, int, int] | None = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def add_glow(image: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int]) -> None:
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    x, y = center
    glow_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(radius // 2))
    image.alpha_composite(glow)


def draw_network(image: Image.Image) -> None:
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    center = (1260, 465)
    nodes = [
        (1260, 215, "BUSINESS", CYAN),
        (1470, 340, "DATA", MINT),
        (1470, 590, "INTEGRATION", AZURE),
        (1260, 715, "ECONOMICS", (255, 185, 0)),
        (1050, 590, "DELIVERY", PURPLE),
        (1050, 340, "GOVERNANCE", (255, 107, 107)),
    ]

    for x, y, _, color in nodes:
        draw.line((center[0], center[1], x, y), fill=(*color, 120), width=4)

    draw.ellipse((1110, 315, 1410, 615), fill=(12, 48, 74, 235), outline=(*CYAN, 220), width=4)
    draw.ellipse((1150, 355, 1370, 575), fill=(9, 36, 58, 255), outline=(*PURPLE, 160), width=3)
    draw.text((1260, 425), "DECIDE", font=font(FONT_BOLD, 39), fill=WHITE, anchor="mm")
    draw.text((1260, 477), "with evidence", font=font(FONT_REGULAR, 23), fill=MUTED, anchor="mm")
    draw.text((1260, 518), "not assumptions", font=font(FONT_SEMIBOLD, 21), fill=CYAN, anchor="mm")

    for x, y, label, color in nodes:
        draw.ellipse((x - 57, y - 57, x + 57, y + 57), fill=(11, 41, 66, 245), outline=(*color, 235), width=4)
        draw.ellipse((x - 12, y - 12, x + 12, y + 12), fill=(*color, 255))
        draw.text((x, y + 82), label, font=font(FONT_SEMIBOLD, 15), fill=TEXT, anchor="mm")

    image.alpha_composite(layer)


def main() -> None:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (*NAVY, 255))
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            horizontal = x / (WIDTH - 1)
            vertical = y / (HEIGHT - 1)
            blend = min(1.0, 0.55 * horizontal + 0.25 * vertical)
            pixels[x, y] = tuple(
                round(NAVY[index] * (1 - blend) + NAVY_2[index] * blend)
                for index in range(3)
            ) + (255,)

    add_glow(image, (1470, 40), 360, AZURE)
    add_glow(image, (1040, 820), 320, PURPLE)

    mesh = Image.new("RGBA", image.size, (0, 0, 0, 0))
    mesh_draw = ImageDraw.Draw(mesh)
    for x in range(0, WIDTH, 80):
        mesh_draw.line((x, 0, x, HEIGHT), fill=(80, 230, 255, 12), width=1)
    for y in range(0, HEIGHT, 80):
        mesh_draw.line((0, y, WIDTH, y), fill=(80, 230, 255, 10), width=1)
    image.alpha_composite(mesh)

    draw = ImageDraw.Draw(image)

    rounded_rectangle(draw, (86, 70, 1514, 830), 36, (6, 27, 44, 196), (*LINE, 210), 2)

    logo = Image.open(AZURE_LOGO).convert("RGBA")
    logo.thumbnail((84, 84), Image.Resampling.LANCZOS)
    image.alpha_composite(logo, (108, 103))
    draw.text((215, 122), "AZURE MIGRATE", font=font(FONT_BOLD, 26), fill=WHITE)
    draw.text((215, 158), "HACKATHON 2026", font=font(FONT_SEMIBOLD, 17), fill=CYAN)

    badge_text = "WORKING SIMULATOR PROTOTYPE"
    badge_font = font(FONT_SEMIBOLD, 16)
    badge_box = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_width = badge_box[2] - badge_box[0] + 48
    rounded_rectangle(draw, (1468 - badge_width, 106, 1468, 156), 25, (0, 120, 212, 55), (*CYAN, 170), 2)
    draw.text((1444, 131), badge_text, font=badge_font, fill=CYAN, anchor="rm")

    draw.text((112, 275), "AI FEASIBILITY", font=font(FONT_BOLD, 74), fill=WHITE)
    draw.text((112, 358), "ASSESSMENT", font=font(FONT_BOLD, 74), fill=CYAN)

    subtitle = "From application intelligence to an actionable\nAI modernization decision"
    draw.multiline_text((116, 475), subtitle, font=font(FONT_REGULAR, 31), fill=TEXT, spacing=12)

    draw.line((116, 603, 830, 603), fill=(*LINE, 255), width=2)

    steps = [
        ("01", "DISCOVER", AZURE),
        ("02", "QUALIFY", CYAN),
        ("03", "DESIGN", PURPLE),
        ("04", "PROVE", MINT),
    ]
    x = 116
    for index, (number, label, color) in enumerate(steps):
        rounded_rectangle(draw, (x, 642, x + 160, 706), 16, (11, 41, 66, 245), (*color, 180), 2)
        draw.text((x + 22, 674), number, font=font(FONT_BOLD, 17), fill=color, anchor="lm")
        draw.text((x + 62, 674), label, font=font(FONT_SEMIBOLD, 18), fill=WHITE, anchor="lm")
        if index < len(steps) - 1:
            draw.line((x + 170, 674, x + 197, 674), fill=(*MUTED, 180), width=3)
            draw.polygon(((x + 197, 674), (x + 187, 667), (x + 187, 681)), fill=(*MUTED, 180))
        x += 205

    draw.text(
        (116, 764),
        "Observed evidence  •  Human-reviewed  •  Explicit gaps and production gates",
        font=font(FONT_REGULAR, 18),
        fill=MUTED,
    )

    draw_network(image)

    output = image.convert("RGB")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    output.save(OUTPUT, format="PNG", optimize=True)
    print(f"Banner: {OUTPUT}")
    print(f"Dimensions: {output.width}x{output.height}")
    print(f"Size: {OUTPUT.stat().st_size / (1024 * 1024):.2f} MB")


if __name__ == "__main__":
    main()