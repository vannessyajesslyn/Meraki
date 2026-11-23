"""Scrapbook-style drawing helpers: torn paper, washi tape, soft shadows,
pen check marks and a typewriter font. Used by assignments_page.py.

All functions take base units (the homepage's 493 x 877 size) and `u`,
which turns base units into pixels on the canvas being drawn.
"""
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from homepage import load_font

# ---- colours: pencil-on-paper look to match the grid background ----
INK = (44, 44, 52)
FADED = (128, 122, 116)
RED_PEN = (192, 52, 58)
BLUE_LINE = (196, 212, 234)
MARGIN_RED = (236, 170, 170)

PAPERS = {
    # name: (paper colour, ruled lines?, margin line?)
    "lined": ((253, 252, 246), True, True),
    "kraft": ((228, 208, 176), False, False),
    "sticky": ((251, 241, 192), False, False),
    "pink": ((250, 226, 230), True, False),
    "white": ((248, 247, 243), False, False),
}
TAPES = [(236, 196, 206), (196, 214, 232), (222, 214, 190), (204, 226, 206)]

# ---- typewriter font (Courier New is on Windows and macOS) ----
_MONO = [
    "courbd.ttf", "Courier New Bold.ttf", r"C:\Windows\Fonts\courbd.ttf",
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/Library/Fonts/Courier New Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    "LiberationMono-Bold.ttf", "DejaVuSansMono-Bold.ttf",
]


@lru_cache(maxsize=256)
def mono(size):
    size = max(6, int(round(size)))
    for name in _MONO:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return load_font(size, True)


def torn_polygon(x0, y0, x1, y1, u, seed, jag=2.4, step=7):
    """Rectangle with ragged top and bottom edges (like ripped paper)."""
    rnd = random.Random(seed)
    top, bottom = [], []
    n = max(2, int((x1 - x0) / step))
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        top.append((x * u, (y0 + rnd.uniform(0, jag)) * u))
        bottom.append((x * u, (y1 - rnd.uniform(0, jag)) * u))
    return top + bottom[::-1]


def paper(canvas, x0, y0, x1, y1, u, style="lined", seed=0, line_start=None,
          line_gap=20, shadow=True):
    """Draw a torn scrap of paper with a soft shadow. Returns the polygon."""
    color, ruled, margin = PAPERS[style]
    poly = torn_polygon(x0, y0, x1, y1, u, seed)
    if shadow:
        _shadow(canvas, poly, u)
    d = ImageDraw.Draw(canvas)
    d.polygon(poly, fill=color)
    if ruled:
        y = line_start if line_start is not None else y0 + 26
        while y < y1 - 6:
            d.line([x0 * u, y * u, x1 * u, y * u], fill=BLUE_LINE, width=max(1, round(0.9 * u)))
            y += line_gap
    if margin:
        d.line([(x0 + 26) * u, (y0 + 3) * u, (x0 + 26) * u, (y1 - 3) * u], fill=MARGIN_RED,
               width=max(1, round(1.1 * u)))
    return poly


def _shadow(canvas, poly, u):
    """Soft shadow under a paper scrap (blurred on a small image = fast)."""
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    pad = round(10 * u)
    left, top = int(min(xs)) - pad, int(min(ys)) - pad
    w, h = int(max(xs)) - left + pad, int(max(ys)) - top + pad
    k = 4                                          # blur at 1/4 size
    mask = Image.new("L", (max(1, w // k), max(1, h // k)), 0)
    off = 2.2 * u
    ImageDraw.Draw(mask).polygon([((x - left) / k, (y - top + off) / k) for x, y in poly], fill=95)
    mask = mask.filter(ImageFilter.GaussianBlur(3.2 * u / k)).resize((w, h), Image.BILINEAR)
    canvas.paste((40, 36, 44), (left, top), mask)


def tape(canvas, cx, cy, w, h, u, angle=0, color=(236, 196, 206), alpha=175):
    """A strip of washi tape (see-through, with zig-zag ends)."""
    W, H = max(2, round(w * u)), max(2, round(h * u))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    z = max(2, round(2.5 * u))
    left = [(0 if i % 2 == 0 else z, H * i / 6) for i in range(7)]
    right = [(W - (0 if i % 2 == 0 else z), H * i / 6) for i in range(7)]
    d.polygon(left + right[::-1], fill=color + (alpha,))
    for i in range(1, 4):                           # faint stripes
        x = W * i / 4
        d.line([x, 0, x, H], fill=(255, 255, 255, 40), width=max(1, round(2 * u)))
    img = img.rotate(angle, resample=Image.BICUBIC, expand=True)
    canvas.paste(img, (round(cx * u - img.width / 2), round(cy * u - img.height / 2)), img)


def pen_box(d, cx, cy, size, u, checked, hot=False):
    """Hand-drawn checkbox; ticked with a red pen check mark."""
    r = size / 2
    if hot:
        d.rectangle([(cx - r - 2) * u, (cy - r - 2) * u, (cx + r + 2) * u, (cy + r + 2) * u],
                    fill=(255, 236, 232))
    d.rectangle([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], outline=INK,
                width=max(1, round(1.6 * u)))
    if checked:
        pts = [(cx - r * 0.75, cy - r * 0.05), (cx - r * 0.1, cy + r * 0.7), (cx + r * 1.15, cy - r * 1.15)]
        d.line([(x * u, y * u) for x, y in pts], fill=RED_PEN, width=round(2.8 * u), joint="curve")


def pen_x(d, cx, cy, u, hot=False, r=6):
    col = RED_PEN if hot else FADED
    for a, b in (((cx - r, cy - r), (cx + r, cy + r)), ((cx - r, cy + r), (cx + r, cy - r))):
        d.line([a[0] * u, a[1] * u, b[0] * u, b[1] * u], fill=col, width=round(1.8 * u))


def dashed(d, x0, x1, y, u, color=INK, dash=5, gap=4, width=1.2):
    x = x0
    while x < x1:
        d.line([x * u, y * u, min(x + dash, x1) * u, y * u], fill=color, width=max(1, round(width * u)))
        x += dash + gap


def stamp_button(d, rect, label, u, hot=False, color=RED_PEN, size=14):
    """A rubber-stamp style button: pen outline, typewriter label."""
    x0, y0, x1, y1 = rect
    if hot:
        d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=5 * u, fill=color)
    d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=5 * u, outline=color,
                        width=round(1.8 * u))
    d.text(((x0 + x1) / 2 * u, (y0 + y1) / 2 * u), label, font=mono(size * u),
           fill=(255, 252, 246) if hot else color, anchor="mm")


def wobble(seed, amount):
    """Small fixed random offset so scraps don't look perfectly lined up."""
    return random.Random(seed).uniform(-amount, amount)


def seed_of(text):
    return sum(ord(c) * (i + 1) for i, c in enumerate(text)) % 10007
