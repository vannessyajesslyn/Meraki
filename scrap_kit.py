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


# ---------------- extra pieces for the Projects page (green theme) ----------------
GREEN = (104, 140, 74)
GREEN_DARK = (62, 84, 46)
GREEN_SOFT = (214, 228, 196)
CREAM_INK = (70, 66, 52)
GREEN_PAPERS = {
    # name: (paper colour, ruled lines?, margin line?)
    "mint": ((232, 241, 222), False, False),
    "cream": ((253, 250, 238), True, False),
    "butter": ((250, 241, 205), False, False),
    "sage": ((220, 230, 206), False, False),
}
PAPERS.update(GREEN_PAPERS)


def star_points(cx, cy, r_out, r_in, u, rotate=-90, n=5):
    import math
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rotate + i * 180 / n)
        pts.append(((cx + r * math.cos(a)) * u, (cy + r * math.sin(a)) * u))
    return pts


def star(d, cx, cy, r, u, fill=GREEN, rotate=-90, outline=(236, 242, 222)):
    """A felt-sticker star like the ones on the background."""
    d.polygon(star_points(cx, cy, r, r * 0.48, u, rotate), fill=fill)
    d.line(star_points(cx, cy, r * 0.72, r * 0.35, u, rotate) +
           [star_points(cx, cy, r * 0.72, r * 0.35, u, rotate)[0]],
           fill=outline, width=max(1, round(1.3 * u)), joint="curve")


@lru_cache(maxsize=8)
def _gingham_tile(px):
    """One repeat of green gingham (checked) fabric, px pixels square."""
    tile = Image.new("RGBA", (px * 2, px * 2), (236, 242, 226, 255))
    over = Image.new("RGBA", tile.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    band = (128, 160, 98, 120)
    d.rectangle([0, 0, px - 1, px * 2], fill=band)          # vertical stripe
    d.rectangle([0, 0, px * 2, px - 1], fill=band)          # horizontal stripe (overlap = darker)
    tile.alpha_composite(over)
    return tile


def gingham_bar(canvas, x0, y0, x1, y1, frac, u):
    """Progress bar: a dashed outline that fills up with gingham tape."""
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=4 * u, fill=(250, 247, 234))
    w = (x1 - x0) * clamp_frac(frac)
    if w > 0.5:
        W, H = max(1, round(w * u)), max(1, round((y1 - y0) * u))
        px = max(2, round(4.4 * u))
        tile = _gingham_tile(px)
        strip = Image.new("RGBA", (W, H))
        for tx in range(0, W, tile.width):
            for ty in range(0, H, tile.height):
                strip.paste(tile, (tx, ty))
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        if frac >= 1:
            md.rounded_rectangle([0, 0, W - 1, H - 1], radius=4 * u, fill=255)
        else:                                               # torn tape end
            z = max(2, round(2.4 * u))
            pts = [(0, 0), (W - z, 0)]
            steps = 5
            for i in range(1, steps + 1):
                pts.append((W - (z if i % 2 == 0 else 0), H * i / steps))
            pts += [(0, H)]
            md.polygon(pts, fill=255)
        canvas.paste(strip.convert("RGB"), (round(x0 * u), round(y0 * u)), mask)
    dashed_rect(d, x0, y0, x1, y1, u, GREEN_DARK)


def dashed_rect(d, x0, y0, x1, y1, u, color, dash=4, gap=3):
    dashed(d, x0, x1, y0, u, color, dash, gap, 1.1)
    dashed(d, x0, x1, y1, u, color, dash, gap, 1.1)
    y = y0
    while y < y1:
        for x in (x0, x1):
            d.line([x * u, y * u, x * u, min(y + dash, y1) * u], fill=color, width=max(1, round(1.1 * u)))
        y += dash + gap


def clamp_frac(f):
    return max(0.0, min(1.0, f))


def pen_circle(d, cx, cy, r, u, checked, hot=False, color=GREEN_DARK, tick=GREEN):
    """Hand-drawn round checkbox with a green tick."""
    if hot:
        d.ellipse([(cx - r - 2) * u, (cy - r - 2) * u, (cx + r + 2) * u, (cy + r + 2) * u], fill=GREEN_SOFT)
    d.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], outline=color,
              width=max(1, round(1.5 * u)))
    if checked:
        pts = [(cx - r * 0.6, cy), (cx - r * 0.1, cy + r * 0.55), (cx + r * 0.95, cy - r * 0.95)]
        d.line([(x * u, y * u) for x, y in pts], fill=tick, width=round(2.6 * u), joint="curve")


def pen_field(page, d, name, fld, x0, x1, line_y, color=GREEN_DARK, focus_color=GREEN, size=15):
    """A 'write on the line' text box for any PageBase page."""
    from page_kit import fit_text
    u = page.u
    focused = page.focus is fld
    d.line([x0 * u, line_y * u, x1 * u, line_y * u], fill=focus_color if focused else (168, 172, 150),
           width=round((1.8 if focused else 1.1) * u))
    font = load_font(size * u, True)
    room = (x1 - x0 - 8) * u
    if fld.text:
        shown = fld.text
        while font.getlength(shown) > room:
            shown = shown[1:]
        d.text(((x0 + 4) * u, (line_y - 4) * u), shown, font=font, fill=color, anchor="ls")
        end = (x0 + 4) * u + font.getlength(shown)
    else:
        ph = mono(12 * u)
        d.text(((x0 + 4) * u, (line_y - 5) * u), fit_text(fld.placeholder, ph, room),
               font=ph, fill=(176, 172, 150), anchor="ls")
        end = (x0 + 4) * u
    if focused and page._blink:
        d.line([end + 1.5 * u, (line_y - 18) * u, end + 1.5 * u, (line_y - 3) * u], fill=focus_color,
               width=round(1.6 * u))
    page.add_hit(name, x0 - 4, line_y - 24, x1, line_y + 6)
