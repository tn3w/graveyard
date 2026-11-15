#!/usr/bin/env python3
"""Generate per-crawler SEO pages, robots.txt, sitemap.xml from crawlers.json."""

from __future__ import annotations

from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

W, H = 1280, 640
INK = (13, 12, 10)
PAPER = (243, 236, 216)
PAPER_2 = (235, 225, 198)
ACCENT = (255, 91, 31)
EMOJIS = ["🤖", "🕷️", "🐛", "🦗", "🐞", "🪲", "👾", "🛰️", "🔍", "📡", "🐜", "🦠", "🐍"]

OUT = Path(__file__).parent / "banner.png"


def find_font(
    candidates: list[str], size: int
) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def find_emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    for path in [
        "/usr/share/fonts/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/TTF/NotoColorEmoji.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return None


def gradient_bg() -> Image.Image:
    image = Image.new("RGB", (W, H), PAPER)
    pixels = image.load()
    if pixels is None:
        return image
    for y in range(H):
        ratio = y / H
        red = int(PAPER[0] * (1 - ratio) + PAPER_2[0] * ratio)
        green = int(PAPER[1] * (1 - ratio) + PAPER_2[1] * ratio)
        blue = int(PAPER[2] * (1 - ratio) + PAPER_2[2] * ratio)
        for x in range(W):
            pixels[x, y] = (red, green, blue)
    return image


def draw_dots(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for y in range(0, H, 22):
        for x in range(0, W, 22):
            draw.ellipse((x, y, x + 2, y + 2), fill=(0, 0, 0, 46))


def draw_emojis(image: Image.Image) -> None:
    font = find_emoji_font(109)
    if font is None:
        return
    random.seed(4)
    placed = []
    size = 120
    min_gap = 220
    attempts = 0
    safe_zones = [
        (40, 40, 360, 130),
        (40, H - 70, W - 40, H - 40),
    ]

    def in_safe(x: int, y: int) -> bool:
        return any(
            zx0 <= x + size and x <= zx1 and zy0 <= y + size and y <= zy1
            for zx0, zy0, zx1, zy1 in safe_zones
        )

    while len(placed) < 11 and attempts < 800:
        attempts += 1
        x = random.randint(40, W - size - 40)
        y = random.randint(40, H - size - 40)
        if in_safe(x, y):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < min_gap**2 for px, py in placed):
            continue
        placed.append((x, y))

    for x, y in placed:
        emoji = random.choice(EMOJIS)
        layer = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((0, 0), emoji, font=font, embedded_color=True)
        layer = layer.resize((size, size), Resampling.LANCZOS)
        alpha = layer.split()[3].point(lambda value: int(value * 0.22))
        layer.putalpha(alpha)
        image.paste(layer, (x, y), layer)


def draw_blip(
    draw: ImageDraw.ImageDraw, top_left: tuple[int, int], radius: int = 9
) -> None:
    x, y = top_left
    draw.ellipse((x + 3, y + 3, x + radius * 2 + 3, y + radius * 2 + 3), fill=INK)
    draw.ellipse(
        (x, y, x + radius * 2, y + radius * 2), fill=ACCENT, outline=INK, width=2
    )


def draw_text(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)

    serif_bold = find_font(
        [
            "/usr/share/fonts/TTF/Fraunces-Black.ttf",
            "/usr/share/fonts/truetype/fraunces/Fraunces-Black.ttf",
            "/usr/share/fonts/TTF/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
        ],
        160,
    )
    serif_italic = find_font(
        [
            "/usr/share/fonts/TTF/Fraunces-BlackItalic.ttf",
            "/usr/share/fonts/truetype/fraunces/Fraunces-BlackItalic.ttf",
            "/usr/share/fonts/TTF/DejaVuSerif-BoldItalic.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif-BoldItalic.ttf",
        ],
        160,
    )
    body = find_font(
        [
            "/usr/share/fonts/TTF/Fraunces-Regular.ttf",
            "/usr/share/fonts/truetype/fraunces/Fraunces-Regular.ttf",
            "/usr/share/fonts/TTF/DejaVuSerif.ttf",
            "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
        ],
        38,
    )
    mono = find_font(
        [
            "/usr/share/fonts/TTF/JetBrainsMono-Bold.ttf",
            "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
            "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
        ],
        22,
    )

    margin_x = 80
    logo_text = "CRAWLERDEX"
    text_bbox = draw.textbbox((0, 0), logo_text, font=mono)
    text_h = text_bbox[3] - text_bbox[1]
    text_y = 80
    blip_radius = 9
    blip_y = int(text_y + text_bbox[1] + text_h // 2 - blip_radius)
    draw_blip(draw, (margin_x, blip_y), blip_radius)
    draw.text((margin_x + blip_radius * 2 + 12, text_y), logo_text, font=mono, fill=INK)

    title_y = 200
    crawler_text = "Crawler"
    draw.text((margin_x, title_y), crawler_text, font=serif_bold, fill=INK)
    crawler_w = draw.textlength(crawler_text, font=serif_bold)
    draw.text((margin_x + crawler_w + 8, title_y), "dex.", font=serif_italic, fill=ACCENT)

    slogan_y = title_y + 180
    draw.text((margin_x, slogan_y), "the living ", font=body, fill=INK)
    pre_w = draw.textlength("the living ", font=body)
    bestiary_box = (
        margin_x + pre_w - 6,
        slogan_y - 2,
        margin_x + pre_w + draw.textlength("bestiary", font=body) + 12,
        slogan_y + 50,
    )
    draw.rectangle(bestiary_box, fill=INK)
    draw.text((margin_x + pre_w + 2, slogan_y), "bestiary", font=body, fill=PAPER)
    after_x = margin_x + pre_w + draw.textlength("bestiary", font=body) + 18
    draw.text((after_x, slogan_y), " of bots.", font=body, fill=INK)

    foot_y = H - 70
    draw.text(
        (margin_x, foot_y),
        "1500+ crawlers · regex patterns · live block-rate",
        font=mono,
        fill=INK,
    )
    repo = "crawlerdex.tn3w.dev"
    repo_w = draw.textlength(repo, font=mono)
    draw.text((W - margin_x - repo_w, foot_y), repo, font=mono, fill=INK)


def draw_border(image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    inset = 18
    draw.rectangle((inset, inset, W - inset, H - inset), outline=INK, width=4)


def main() -> None:
    image = gradient_bg()
    draw_dots(image)
    draw_emojis(image)
    draw_border(image)
    draw_text(image)
    image.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({W}x{H})")


if __name__ == "__main__":
    main()
