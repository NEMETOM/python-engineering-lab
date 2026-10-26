"""Generate a branded 1280x720 YouTube thumbnail template for the FixFlux channel.

Usage:
    python generate_thumbnail.py \
        --headline "LIVE MARKET DATA" \
        --category feature \
        --output thumbnails/video1.png \
        [--visual path/to/screenshot.png] \
        [--logo ../docs/FixFlux-Logo.png] \
        [--headline-font fonts/SpaceGrotesk-Bold.ttf] \
        [--label-font fonts/Inter-ExtraBold.ttf]

Fonts are not bundled here (licensing: download them yourself, both are free/OFL):
    Space Grotesk: https://fonts.google.com/specimen/Space+Grotesk
    Inter:         https://fonts.google.com/specimen/Inter
Place the .ttf files under fixflux/scripts/fonts/ (gitignored) or pass --headline-font /
--label-font explicitly. Falls back to PIL's built-in bitmap font (ugly but functional)
if a font path is missing, so this never hard-crashes a demo prep session.
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CANVAS_SIZE = (1280, 720)

BG_BASE = "#0B0F17"
BG_PANEL = "#131A24"
BORDER_LINE = "#232B36"
TEXT_PRIMARY = "#F5F7FA"
TEXT_MUTED = "#8B96A5"

ACCENTS = {
    "feature": "#00E5FF",
    "observability": "#39FF88",
    "compliance": "#FF6B2C",
}

HEADLINE_ZONE = (64, 180, 680, 540)
VISUAL_ZONE = (700, 110, 1200, 610)
LOGO_ZONE = (1096, 24, 1216, 120)
STRIP_HEIGHT = 10


def _load_font(path: str | None, size: int) -> ImageFont.FreeTypeFont:
    if path and Path(path).exists():
        return ImageFont.truetype(path, size)
    print(f"Warning: font not found at {path!r}, falling back to PIL default bitmap font.")
    return ImageFont.load_default(size=size)


def _draw_grid_texture(draw: ImageDraw.ImageDraw, spacing: int = 40) -> None:
    for x in range(0, CANVAS_SIZE[0], spacing):
        draw.line([(x, 0), (x, CANVAS_SIZE[1])], fill=BORDER_LINE, width=1)
    for y in range(0, CANVAS_SIZE[1], spacing):
        draw.line([(0, y), (CANVAS_SIZE[0], y)], fill=BORDER_LINE, width=1)


def _fit_headline(draw: ImageDraw.ImageDraw, text: str, font_path: str | None, box: tuple[int, int, int, int]) -> ImageFont.FreeTypeFont:
    x0, y0, x1, y1 = box
    max_width, size = x1 - x0, 140
    while size > 40:
        font = _load_font(font_path, size)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 4
    return _load_font(font_path, 40)


def _draw_headline(draw: ImageDraw.ImageDraw, text: str, font_path: str | None) -> None:
    x0, y0, x1, y1 = HEADLINE_ZONE
    font = _fit_headline(draw, text, font_path, HEADLINE_ZONE)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_height = bbox[3] - bbox[1]
    y = y0 + ((y1 - y0) - text_height) // 2
    draw.text((x0, y), text, font=font, fill=TEXT_PRIMARY)


def _draw_visual_panel(image: Image.Image, draw: ImageDraw.ImageDraw, accent: str, visual_path: str | None, label_font_path: str | None) -> None:
    x0, y0, x1, y1 = VISUAL_ZONE
    draw.rounded_rectangle([x0, y0, x1, y1], radius=18, fill=BG_PANEL, outline=accent, width=3)

    if visual_path and Path(visual_path).exists():
        asset = Image.open(visual_path).convert("RGBA")
        pad = 16
        target_w, target_h = (x1 - x0) - 2 * pad, (y1 - y0) - 2 * pad
        asset.thumbnail((target_w, target_h))
        ax = x0 + pad + (target_w - asset.width) // 2
        ay = y0 + pad + (target_h - asset.height) // 2
        image.paste(asset, (ax, ay), asset)
    else:
        font = _load_font(label_font_path, 22)
        placeholder_lines = [
            "{",
            '  "symbol": "EURUSD",',
            '  "best_bid": 1.0899,',
            '  "last_trade_price": 1.09',
            "}",
        ]
        ty = y0 + 40
        for line in placeholder_lines:
            draw.text((x0 + 32, ty), line, font=font, fill=TEXT_MUTED)
            ty += 34


def _draw_logo(image: Image.Image, draw: ImageDraw.ImageDraw, logo_path: str | None) -> None:
    x0, y0, x1, y1 = LOGO_ZONE
    draw.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=BG_PANEL, outline=BORDER_LINE, width=1)
    if logo_path and Path(logo_path).exists():
        logo = Image.open(logo_path).convert("RGBA")
        pad = 10
        logo.thumbnail((x1 - x0 - 2 * pad, y1 - y0 - 2 * pad))
        lx = x0 + ((x1 - x0) - logo.width) // 2
        ly = y0 + ((y1 - y0) - logo.height) // 2
        image.paste(logo, (lx, ly), logo)


def _draw_brand_strip(draw: ImageDraw.ImageDraw, accent: str) -> None:
    w, h = CANVAS_SIZE
    draw.rectangle([0, h - STRIP_HEIGHT, w, h], fill=accent)


def generate(
    headline: str,
    category: str,
    output: str,
    visual: str | None = None,
    logo: str | None = None,
    headline_font: str | None = None,
    label_font: str | None = None,
) -> None:
    accent = ACCENTS.get(category)
    if accent is None:
        raise ValueError(f"category must be one of {list(ACCENTS)}, got {category!r}")

    image = Image.new("RGB", CANVAS_SIZE, BG_BASE)
    draw = ImageDraw.Draw(image)

    _draw_grid_texture(draw)
    _draw_headline(draw, headline.upper(), headline_font)
    _draw_visual_panel(image, draw, accent, visual, label_font)
    _draw_logo(image, draw, logo)
    _draw_brand_strip(draw, accent)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    print(f"Saved {out_path} ({CANVAS_SIZE[0]}x{CANVAS_SIZE[1]})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--headline", required=True, help="Max 3-4 words, will be upper-cased")
    parser.add_argument("--category", required=True, choices=list(ACCENTS), help="Selects the accent color")
    parser.add_argument("--output", required=True, help="Output PNG path")
    parser.add_argument("--visual", help="Path to a screenshot/asset to composite into the right panel")
    parser.add_argument("--logo", default="../docs/FixFlux-Logo.png", help="Path to the FixFlux logo")
    parser.add_argument("--headline-font", default="fonts/SpaceGrotesk-Bold.ttf")
    parser.add_argument("--label-font", default="fonts/Inter-ExtraBold.ttf")
    args = parser.parse_args()

    generate(
        headline=args.headline,
        category=args.category,
        output=args.output,
        visual=args.visual,
        logo=args.logo,
        headline_font=args.headline_font,
        label_font=args.label_font,
    )


if __name__ == "__main__":
    main()
