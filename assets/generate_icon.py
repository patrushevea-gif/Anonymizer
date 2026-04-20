"""Generate assets/icon.ico — black background, stylized "AR" mark.

Run once, output committed to the repo. The .ico contains multiple sizes so
Windows picks the right one for the context (taskbar, file explorer, title bar).

Usage:
    python assets/generate_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZES = (16, 24, 32, 48, 64, 128, 256)
ASSETS = Path(__file__).resolve().parent


def _pick_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render_frame(size: int) -> Image.Image:
    # Near-black background matching the app primary color.
    img = Image.new("RGBA", (size, size), (10, 10, 10, 255))
    draw = ImageDraw.Draw(img)

    # A subtle accent underline so the mark doesn't look flat.
    accent = (0, 212, 255, 255)
    stroke = max(1, size // 32)
    margin = max(1, size // 10)
    y = size - margin - stroke
    draw.rectangle(
        (margin, y, size - margin, y + stroke),
        fill=accent,
    )

    # "AR" letters — 62% of icon height, centered.
    font = _pick_font(int(size * 0.62))
    text = "AR"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - max(1, size // 24)  # shift up slightly
    draw.text((tx, ty), text, font=font, fill=(240, 240, 240, 255))
    return img


def main() -> None:
    # PIL's ICO writer accepts a single base image + a list of target thumbnail
    # sizes; it downsamples from the base for each. Render at the largest size
    # and let it downscale so we get one crisp render plus clean thumbnails.
    base = _render_frame(256)
    out = ASSETS / "icon.ico"
    base.save(out, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Wrote {out} with sizes {SIZES}")


if __name__ == "__main__":
    main()
