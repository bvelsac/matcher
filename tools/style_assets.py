"""Build the image assets of the visual style (docs/visual-style.md) from the reference images.

    python tools/style_assets.py

Needs Pillow, which the application itself does not use. Writes:

    static/img/eye.png    the eye from docs/img/eye-reference.png, reduced to coarse pixels and
                          mapped onto the palette with ordered dithering; the browser enlarges it
                          without smoothing (image-rendering: pixelated) and the CSS fades it.
                          Background of the login page
    static/img/bg-*.png   the same treatment for parts cut from docs/img/style-reference.webp,
                          one per screen (CROPS below)
    static/img/grain.png  a tile of loose pink pixels, laid over surfaces for grit
    static/img/edge.png   a strip of pixels that thins out from top to bottom, under the navbar;
                          used as a mask, so the CSS gives it the accent colour of the screen.
                          Drawn at its display size (2x2 blocks), so the mask is never smoothed
"""
import os
import random

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Palette from the reference images, dark to light.
RAMP = ["#030001", "#1c0719", "#612d58", "#cf8dc9", "#ffc0fc"]
PINK = (255, 192, 252)

# 4x4 Bayer matrix for ordered dithering, values 0..15.
BAYER = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


# Parts of docs/img/style-reference.webp (left, top, right, bottom), one background per screen.
CROPS = {
    "dashboard": (760, 250, 1500, 710),         # eye and eyebrow
    "interpreters": (0, 640, 720, 1100),        # hand on the microphone
    "interpreter-form": (1150, 560, 1890, 1020),  # beard
    "meetings": (540, 820, 1280, 1280),         # mouth and cigarette
    "meeting-form": (380, 380, 1120, 840),      # nose
    "error": (560, 0, 1300, 460),               # forehead and eyebrow
    "bookings": (1100, 20, 1840, 480),          # brow and hair, right
    "booking-form": (700, 850, 1445, 1310),     # lips and chin
    "invoices": (1170, 960, 1910, 1420),        # cheek, lower right
    "invoice-form": (320, 170, 1060, 630),      # dark profile and nose
    "worklists": (1000, 300, 1740, 760),        # temple and ear
}


def hex_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def dither(source, name, width=200):
    """Reduce an image to `width` coarse pixels and map it onto RAMP with ordered dithering."""
    source = source.convert("L")
    height = round(source.height * width / source.width)
    small = source.resize((width, height), Image.BOX)
    ramp = [hex_rgb(c) for c in RAMP]
    steps = len(ramp) - 1
    out = Image.new("RGB", small.size)
    pixels = small.load()
    target = out.load()
    for y in range(height):
        for x in range(width):
            level = pixels[x, y] / 255 * steps
            low = min(int(level), steps - 1)
            threshold = (BAYER[y % 4][x % 4] + 0.5) / 16
            index = low + 1 if level - low > threshold else low
            target[x, y] = ramp[index]
    out.save(os.path.join(ROOT, "static", "img", name), optimize=True)


def eye():
    dither(Image.open(os.path.join(ROOT, "docs", "img", "eye-reference.png")), "eye.png")


def screen_backgrounds():
    reference = Image.open(os.path.join(ROOT, "docs", "img", "style-reference.webp"))
    for name, box in CROPS.items():
        dither(reference.crop(box), "bg-{}.png".format(name))


def grain(size=64, density=0.06, seed=7):
    rng = random.Random(seed)
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for y in range(size):
        for x in range(size):
            if rng.random() < density:
                tile.putpixel((x, y), PINK + (rng.choice((90, 150, 255)),))
    tile.save(os.path.join(ROOT, "static", "img", "grain.png"), optimize=True)


def edge(width=128, seed=11):
    rng = random.Random(seed)
    rows = [1.0, 0.7, 0.45, 0.25, 0.12, 0.05]
    strip = Image.new("RGBA", (width, len(rows)), (0, 0, 0, 0))
    for y, density in enumerate(rows):
        for x in range(width):
            if rng.random() < density:
                strip.putpixel((x, y), PINK + (255,))
    strip = strip.resize((width * 2, len(rows) * 2), Image.NEAREST)
    strip.save(os.path.join(ROOT, "static", "img", "edge.png"), optimize=True)


if __name__ == "__main__":
    eye()
    screen_backgrounds()
    grain()
    edge()
