"""Meraki home page: intro animation, clickable hotspots and the tutorial.

Everything visual is drawn with Pillow into one picture per frame:

    page = HomePage("assets", scale=1.0)
    page.update(dt)                # advance animations by dt seconds
    image = page.render()          # -> PIL image of the whole window
    action = page.click(x, y)      # -> "timer", "projects", "assignments", ...
    cursor = page.hover(x, y)      # -> "hand2" or "arrow"

main.py shows that picture in a tkinter window; make_preview.py writes the
same frames into a video. All coordinates below are in the ORIGINAL image
size (493 x 877); `scale` only enlarges the window.
"""
import math
import os
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

BASE_W, BASE_H = 493, 877

# ---- colours (theme is built around #FFD1DC) ---------------------------
PINK = (255, 209, 220)          # #FFD1DC
PINK_EDGE = (238, 150, 178)
ROSE = (150, 52, 88)
PLUM = (84, 40, 56)
CREAM = (255, 247, 249)
INK = (58, 58, 74)

# ---- fonts: Times New Roman everywhere ---------------------------------
_REGULAR = [
    "times.ttf", "Times New Roman.ttf", r"C:\Windows\Fonts\times.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Times New Roman.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman.ttf",
    # metric-compatible Times look-alike, used only if Times New Roman is missing
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
    "LiberationSerif-Regular.ttf", "DejaVuSerif.ttf",
]
_BOLD = [
    "timesbd.ttf", "Times New Roman Bold.ttf", r"C:\Windows\Fonts\timesbd.ttf",
    "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    "/Library/Fonts/Times New Roman Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Times_New_Roman_Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "LiberationSerif-Bold.ttf", "DejaVuSerif-Bold.ttf",
]


@lru_cache(maxsize=512)
def load_font(size, bold=False):
    size = max(6, int(round(size)))
    for name in (_BOLD if bold else _REGULAR):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size)
    except TypeError:                      # very old Pillow
        return ImageFont.load_default()


# ---- easing helpers ----------------------------------------------------
def clamp01(x):
    return max(0.0, min(1.0, x))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(x):
    return 1 - (1 - clamp01(x)) ** 3


def ease_in_out(x):
    x = clamp01(x)
    return x * x * (3 - 2 * x)


def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    x = clamp01(x)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def ease_out_bounce(x):
    x = clamp01(x)
    n1, d1 = 7.5625, 2.75
    if x < 1 / d1:
        return n1 * x * x
    if x < 2 / d1:
        x -= 1.5 / d1
        return n1 * x * x + 0.75
    if x < 2.5 / d1:
        x -= 2.25 / d1
        return n1 * x * x + 0.9375
    x -= 2.625 / d1
    return n1 * x * x + 0.984375


# ---- layout of the clickable things (x0, y0, x1, y1, corner radius) ----
HOTSPOTS = {
    "tutorial":    [(366, 18, 422, 74, 14)],
    "user":        [(428, 22, 476, 70, 24)],
    "timer":       [(303, 270, 469, 354, 8)],                      # the clock
    "projects":    [(8, 372, 471, 476, 8)],                        # sticky notes
    "assignments": [(0, -4, 232, 108, 6), (0, 160, 192, 354, 6),   # the books
                    (200, 168, 286, 354, 6)],
}
HIT_ORDER = ["tutorial", "user", "timer", "projects", "assignments"]
USER_CENTER, USER_SIZE = (452, 46), 48
TUT_CENTER, TUT_SIZE = (394, 46), 56
SCREEN_CENTER = (250, 563)                      # laptop screen, for the title

STEPS = [
    dict(target="user",
         title="[Tutorial] Step 1/4: Icon User",
         body="This is your profile. First, you can sign-up so you can manage "
              "your account and change your settings here."),
    dict(target="timer",
         title="[Tutorial] Step 2/4: Study Timer",
         body="This is a place where you can fully lock-in. There'll be a cozy "
              "background playing in a mini TV-player while you start a focus "
              "session. Study using a 50/10 pomodoro and take a break after 2 "
              "sessions."),
    dict(target="projects",
         title="[Tutorial] Step 3/4: Project Manager",
         body="This is a place where you can track all of your projects. Add a "
              "project and manage all the sub-tasks you have to complete under "
              "that project. Tick off each sub-task until your progress bar is "
              "complete."),
    dict(target="assignments",
         title="[Tutorial] Step 4/4: Assignments Tracker",
         body="This is a place where you can track your assignments. Add an "
              "assignment name and check how much time you have left until it "
              "is due."),
]

# ---- intro timeline (seconds) ------------------------------------------
TITLE = "Meraki"
T_TYPE_START, T_PER_CHAR = 0.8, 0.2
T_TEXT_FADE = 3.1                    # title starts fading here (0.5 s)
T_ZOOM_START, T_ZOOM_LEN = 3.3, 1.5  # smooth zoom-out
T_ICONS = 4.1                        # icons fade in (0.6 s)
INTRO_END = 5.0
T_AUTO_TUTORIAL = INTRO_END + 0.6
INTRO_ZOOM = 1.47
DARK_ALPHA = 0.68                    # how dark the tutorial backdrop is


def wrap_text(text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and font.getlength(trial) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


class HomePage:
    def __init__(self, assets_dir, scale=1.0, show_tutorial=True):
        self.S = scale
        self.W = round(BASE_W * scale)
        self.H = round(BASE_H * scale)
        bg = Image.open(os.path.join(assets_dir, "homepage.png")).convert("RGB")
        self.bg = bg.resize((self.W, self.H), Image.LANCZOS)
        self.black = Image.new("RGB", (self.W, self.H), (0, 0, 0))

        self.user_icon = self._make_user_icon()
        self.tut_icon = self._make_tutorial_icon(os.path.join(assets_dir, "tutorial.png"))

        # state
        self.t = 0.0
        self.phase = "intro"                 # intro -> home <-> tutorial
        self.auto_tutorial = show_tutorial
        self.dirty = True
        self.hover_name = None
        self.hover_btn = None
        self.tut_step = 0
        self.tut_prev = None
        self.tut_t = 0.0
        self.tut_open_t = 0.0
        self.tut_closing = False
        self.tut_close_t = 0.0
        self.toast_text = None
        self.toast_left = 0.0

        self._mask_cache, self._ring_cache = {}, {}
        self._bubble_cache, self._toast_cache = {}, {}

    # ================= public API =================
    @property
    def animating(self):
        return self.phase in ("intro", "tutorial") or self.toast_left > 0

    def needs_redraw(self):
        return self.dirty or self.animating

    def skip_intro(self):
        self.t = max(self.t, INTRO_END)

    def show_toast(self, text, seconds=2.2):
        self.toast_text, self.toast_left = text, seconds
        self.dirty = True

    def open_tutorial(self):
        self.phase = "tutorial"
        self.tut_step, self.tut_prev = 0, None
        self.tut_t = self.tut_open_t = 0.0
        self.tut_closing = False
        self.hover_name = self.hover_btn = None
        self.dirty = True

    def update(self, dt):
        self.t += dt
        if self.phase == "intro":
            self.dirty = True
            if self.t >= INTRO_END:
                self.phase = "home"
        if self.phase == "home" and self.auto_tutorial and self.t >= T_AUTO_TUTORIAL:
            self.auto_tutorial = False
            self.open_tutorial()
        if self.phase == "tutorial":
            self.tut_t += dt
            self.tut_open_t += dt
            if self.tut_closing:
                self.tut_close_t += dt
                if self.tut_close_t >= 0.3:
                    self.phase, self.tut_closing = "home", False
                    self.dirty = True
        if self.toast_left > 0:
            self.toast_left -= dt
            self.dirty = True

    def click(self, x, y):
        """Returns an action string or None."""
        if self.phase == "intro":
            self.skip_intro()
            return None
        if self.phase == "tutorial":
            if self.tut_closing:
                return None
            btn = self._button_at(x, y)
            last = self.tut_step == len(STEPS) - 1
            if btn == "next" and not last:
                self._go_step(self.tut_step + 1)
            elif btn == "back" and self.tut_step > 0:
                self._go_step(self.tut_step - 1)
            elif btn == "skip" or (btn == "next" and last):
                self.tut_closing, self.tut_close_t = True, 0.0
                self.hover_btn = None
                return "tutorial_done"
            return None
        name = self._hotspot_at(x, y)
        if name == "tutorial":
            self.open_tutorial()
            return None
        return name                              # "user", "timer", "projects", "assignments" or None

    def hover(self, x, y):
        old = (self.hover_name, self.hover_btn)
        self.hover_name = self.hover_btn = None
        if self.phase == "tutorial" and not self.tut_closing:
            self.hover_btn = self._button_at(x, y)
        elif self.phase == "home":
            self.hover_name = self._hotspot_at(x, y)
        if old != (self.hover_name, self.hover_btn):
            self.dirty = True
        return "hand2" if (self.hover_name or self.hover_btn) else "arrow"

    def button_center(self, name):
        """Screen position of a tutorial button (used by the preview video)."""
        x0, y0, x1, y1 = self._bubble(self.tut_step, None)["buttons"][name]
        return (x0 + x1) / 2, (y0 + y1) / 2

    def hotspot_center(self, name):
        x0, y0, x1, y1, _ = HOTSPOTS[name][0]
        return (x0 + x1) / 2 * self.S, (y0 + y1) / 2 * self.S

    def render(self):
        self.dirty = False
        if self.phase == "intro":
            frame = self._render_intro()
        else:
            frame = self._scene(1.0)
            if self.hover_name:
                self._draw_hover(frame, self.hover_name)
        if self.phase == "tutorial":
            self._draw_tutorial(frame)
        if self.toast_left > 0:
            self._draw_toast(frame)
        return frame

    # ================= hit testing =================
    def _hotspot_at(self, x, y):
        bx, by = x / self.S, y / self.S
        for name in HIT_ORDER:
            for x0, y0, x1, y1, _ in HOTSPOTS[name]:
                if x0 <= bx <= x1 and y0 <= by <= y1:
                    return name
        return None

    def _button_at(self, x, y):
        for name, (x0, y0, x1, y1) in self._bubble(self.tut_step, None)["buttons"].items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return None

    def _go_step(self, index):
        self.tut_prev, self.tut_step, self.tut_t = self.tut_step, index, 0.0
        self.dirty = True

    # ================= icons =================
    def _shadowed(self, icon, blur=4, offset=2, opacity=90):
        S = self.S
        m = round(blur * S * 2)
        w, h = icon.size
        canvas = Image.new("RGBA", (w + 2 * m, h + 2 * m), (0, 0, 0, 0))
        shadow = Image.new("L", canvas.size, 0)
        shadow.paste(icon.getchannel("A").point(lambda v: v * opacity // 255), (m, m + round(offset * S)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur * S))
        canvas.paste((60, 30, 45), mask=shadow)
        canvas.alpha_composite(icon, (m, m))
        return canvas, m

    def _make_user_icon(self):
        S, ss = self.S, 4
        size = round(USER_SIZE * S)
        N = size * ss
        disk = Image.new("L", (N, N), 0)
        ImageDraw.Draw(disk).ellipse([0, 0, N - 1, N - 1], fill=255)
        layer = Image.new("RGBA", (N, N), (255, 255, 255, 0))
        d = ImageDraw.Draw(layer)
        d.ellipse([0, 0, N - 1, N - 1], fill=PINK + (255,))
        person = (168, 72, 104, 255)
        d.ellipse([N * 0.5 - N * 0.17, N * 0.20, N * 0.5 + N * 0.17, N * 0.20 + N * 0.34], fill=person)
        d.ellipse([N * 0.5 - N * 0.33, N * 0.60, N * 0.5 + N * 0.33, N * 1.20], fill=person)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), disk))
        ImageDraw.Draw(layer).ellipse([N * 0.025, N * 0.025, N * 0.975, N * 0.975],
                                      outline=(255, 255, 255, 255), width=round(N * 0.05))
        icon = layer.resize((size, size), Image.LANCZOS)
        return self._shadowed(icon)

    def _make_tutorial_icon(self, path):
        S = self.S
        im = Image.open(path)
        if im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 255:
            alpha = im.getchannel("A")                      # already transparent
            bbox = alpha.getbbox()
            im = im.crop(bbox)
        else:
            rgb = im.convert("RGB")
            ink = rgb.convert("L").point(lambda v: 255 if v < 245 else 0)
            x0, y0, x1, y1 = ink.getbbox()
            rgb = rgb.crop((x0 - 4, y0 - 4, x1 + 4, y1 + 4))
            marker = (255, 0, 255)
            flooded = rgb.copy()
            ImageDraw.floodfill(flooded, (0, 0), marker, thresh=40)   # white outside the badge
            keep = ImageChops.difference(flooded, Image.new("RGB", rgb.size, marker))
            alpha = keep.convert("L").point(lambda v: 255 if v > 0 else 0)
            alpha = alpha.filter(ImageFilter.GaussianBlur(1.0))
            im = rgb.convert("RGBA")
            im.putalpha(alpha)
        w = round(TUT_SIZE * S)
        h = round(w * im.height / im.width)
        return self._shadowed(im.resize((w, h), Image.LANCZOS))

    def _scene(self, icon_alpha):
        scene = self.bg.copy()
        if icon_alpha > 0:
            S = self.S
            for (icon, m), (cx, cy) in ((self.user_icon, USER_CENTER), (self.tut_icon, TUT_CENTER)):
                pos = (round(cx * S - icon.width / 2), round(cy * S - icon.height / 2))
                a = icon.getchannel("A")
                if icon_alpha < 1:
                    a = a.point(lambda v: int(v * icon_alpha))
                scene.paste(icon.convert("RGB"), pos, a)
        return scene

    # ================= intro =================
    def _intro_view(self, t):
        """(x0, y0, view_w, view_h) in base units: starts zoomed on the laptop."""
        q = ease_in_out((t - T_ZOOM_START) / T_ZOOM_LEN)        # 0 -> 1, smooth zoom-out
        zoom = lerp(INTRO_ZOOM, 1.0, q)
        cx = lerp(SCREEN_CENTER[0], BASE_W / 2, q)
        cy = lerp(SCREEN_CENTER[1], BASE_H / 2, q)
        vw, vh = BASE_W / zoom, BASE_H / zoom
        x0 = min(max(cx - vw / 2, 0), BASE_W - vw)
        y0 = min(max(cy - vh / 2, 0), BASE_H - vh)
        return x0, y0, vw, vh

    def _render_intro(self):
        S, t = self.S, self.t
        icon_alpha = ease_in_out((t - T_ICONS) / 0.6)
        scene = self._scene(icon_alpha)
        x0, y0, vw, vh = self._intro_view(t)
        if vw < BASE_W - 0.01:
            box = (max(0.0, x0 * S), max(0.0, y0 * S),
                   min(float(self.W), (x0 + vw) * S), min(float(self.H), (y0 + vh) * S))
            frame = scene.resize((self.W, self.H), Image.BICUBIC, box=box)
        else:
            frame = scene
        # darkness: fade in from black, keep the room dim while typing, then brighten
        dim = 0.55 * (1 - ease_in_out((t - T_ZOOM_START) / T_ZOOM_LEN))
        dim = max(dim, 1 - ease_in_out(t / 0.7) * (1 - 0.55)) if t < 0.7 else dim
        if dim > 0.003:
            frame = Image.blend(frame, self.black, min(dim, 1.0))
        # typewriter title on the laptop screen
        fade = ease_in_out((t - T_TEXT_FADE) / 0.5)
        if fade < 1:
            self._draw_title(frame, x0, y0, vw, fade, dim)
        return frame

    def _draw_title(self, frame, x0, y0, vw, fade, dim):
        k = self.W / vw                                  # base units -> pixels (zoom included)
        font = load_font(54 * k)
        typed = int(max(0.0, self.t - T_TYPE_START) / T_PER_CHAR) + (1 if self.t >= T_TYPE_START else 0)
        typed = min(typed, len(TITLE))
        full_w = font.getlength(TITLE)
        ascent, descent = font.getmetrics()
        px = (SCREEN_CENTER[0] - x0) * k - full_w / 2
        py = (SCREEN_CENTER[1] - y0) * k - (ascent + descent) / 2
        screen = int(255 * (1 - dim))
        color = tuple(int(lerp(c, screen, fade)) for c in INK)
        d = ImageDraw.Draw(frame)
        d.text((px, py), TITLE[:typed], font=font, fill=color)
        done = typed >= len(TITLE)
        blink = (not done) or int(self.t * 2) % 2 == 0
        if blink:
            cx = px + font.getlength(TITLE[:typed]) + 3 * k
            d.rectangle([cx, py + 0.12 * (ascent + descent), cx + 2.2 * k, py + 0.95 * (ascent + descent)],
                        fill=color)

    # ================= hover / toast =================
    def _draw_hover(self, frame, name):
        S = self.S
        over = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        for x0, y0, x1, y1, r in HOTSPOTS[name]:
            d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S,
                                fill=(255, 255, 255, 60), outline=PINK + (235,), width=max(2, round(2.5 * S)))
        frame.paste(over.convert("RGB"), (0, 0), over.getchannel("A"))

    def _toast_image(self, text):
        if text in self._toast_cache:
            return self._toast_cache[text]
        S, ss = self.S, 3
        font = load_font(15 * S * ss, True)
        w = int(font.getlength(text) + 40 * S * ss)
        h = int(36 * S * ss)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=PINK + (255,),
                            outline=PINK_EDGE + (255,), width=2 * ss)
        asc, desc = font.getmetrics()
        d.text((w / 2, h / 2), text, font=font, fill=PLUM, anchor="mm")
        img = img.resize((w // ss, h // ss), Image.LANCZOS)
        self._toast_cache[text] = img
        return img

    def _draw_toast(self, frame):
        img = self._toast_image(self.toast_text)
        age = 2.2 - self.toast_left
        a = min(ease_out_cubic(age / 0.2), clamp01(self.toast_left / 0.4))
        alpha = img.getchannel("A").point(lambda v: int(v * a))
        lift = round((1 - ease_out_cubic(age / 0.2)) * 10 * self.S)
        pos = ((self.W - img.width) // 2, round(self.H - 62 * self.S) + lift)
        frame.paste(img.convert("RGB"), pos, alpha)

    # ================= tutorial =================
    def _holes(self, name, pad=6):
        S = self.S
        return [((x0 - pad) * S, (y0 - pad) * S, (x1 + pad) * S, (y1 + pad) * S, (r + pad) * S)
                for x0, y0, x1, y1, r in HOTSPOTS[name]]

    def _mask(self, name):
        """255 = dark, 0 = spotlight hole (soft edge)."""
        if name not in self._mask_cache:
            m = Image.new("L", (self.W, self.H), 255)
            d = ImageDraw.Draw(m)
            for x0, y0, x1, y1, r in self._holes(name):
                d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=0)
            self._mask_cache[name] = m.filter(ImageFilter.GaussianBlur(3.0 * self.S))
        return self._mask_cache[name]

    def _ring(self, name):
        """Pink outline + glow around the spotlight (cached masks)."""
        if name not in self._ring_cache:
            S, ss = self.S, 2
            big = Image.new("L", (self.W * ss, self.H * ss), 0)
            d = ImageDraw.Draw(big)
            for x0, y0, x1, y1, r in self._holes(name, pad=8):
                d.rounded_rectangle([x0 * ss, y0 * ss, x1 * ss, y1 * ss], radius=r * ss,
                                    outline=255, width=max(2, round(2.6 * S * ss)))
            ring = big.resize((self.W, self.H), Image.LANCZOS)
            glow = ring.filter(ImageFilter.GaussianBlur(5 * S)).point(lambda v: min(255, v * 2))
            self._ring_cache[name] = (ring, glow)
        return self._ring_cache[name]

    def _tut_factor(self):
        f = ease_out_cubic(self.tut_open_t / 0.35)
        if self.tut_closing:
            f *= 1 - ease_in_out(self.tut_close_t / 0.3)
        return f

    def _draw_tutorial(self, frame):
        f = self._tut_factor()
        step = STEPS[self.tut_step]
        cur = self._mask(step["target"])
        prev = (Image.new("L", cur.size, 255) if self.tut_prev is None
                else self._mask(STEPS[self.tut_prev]["target"]))
        e = ease_in_out(self.tut_t / 0.45)
        mask = cur if e >= 1 else Image.blend(prev, cur, e)
        k = DARK_ALPHA * f
        frame.paste((0, 0, 0), (0, 0), mask.point(lambda v: int(v * k)))

        ring, glow = self._ring(step["target"])
        pulse = 0.7 + 0.3 * (0.5 + 0.5 * math.sin(2 * math.pi * self.t / 1.4))
        a = f * pulse * e
        frame.paste(PINK, (0, 0), glow.point(lambda v: int(v * 0.55 * a)))
        frame.paste(PINK, (0, 0), ring.point(lambda v: int(v * a)))

        rec = self._bubble(self.tut_step, self.hover_btn)
        img = rec["img"]
        p = ease_out_back(self.tut_t / 0.38)
        s = 0.8 + 0.2 * p
        alpha = img.getchannel("A").point(lambda v: int(v * clamp01(self.tut_t / 0.22) * f))
        tip_x, tip_y = rec["tip"]
        if abs(s - 1) > 0.002:
            size = (max(1, round(img.width * s)), max(1, round(img.height * s)))
            img, alpha = img.resize(size, Image.BICUBIC), alpha.resize(size, Image.BICUBIC)
            pos = (round(tip_x + (rec["pos"][0] - tip_x) * s), round(tip_y + (rec["pos"][1] - tip_y) * s))
        else:
            pos = rec["pos"]
        frame.paste(img.convert("RGB"), pos, alpha)

    def _bubble(self, index, hover):
        """The speech bubble for one step (cached): image, position, tail tip, button rects."""
        key = (index, hover)
        if key in self._bubble_cache:
            return self._bubble_cache[key]
        S, ss = self.S, 3
        u = S * ss
        step = STEPS[index]
        f_title, f_body = load_font(15.5 * u, True), load_font(14.5 * u)
        f_btn, f_small = load_font(14 * u, True), load_font(13 * u)
        BW, PAD, MARG, TH = 336, 17, 16, 15
        text_w = (BW - 2 * PAD) * u
        t_lines = wrap_text(step["title"], f_title, text_w)
        b_lines = wrap_text(step["body"], f_body, text_w)
        LT, LB = 19, 18.5

        # vertical layout inside the bubble (base units)
        y_title = PAD
        y_sep = y_title + len(t_lines) * LT + 3
        y_body = y_sep + 8
        y_dots = y_body + len(b_lines) * LB + 14
        y_btn = y_dots + 14
        BH = y_btn + 30 + PAD

        # where to put it: below the highlighted thing if it fits, otherwise above
        boxes = [r for r in HOTSPOTS[step["target"]]]
        tx0, ty0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        tx1, ty1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        tail_up = ty1 + 6 + TH + BH <= BASE_H - 12
        body_y = ty1 + 6 + TH if tail_up else ty0 - 6 - TH - BH
        body_x = min(max((tx0 + tx1) / 2 - BW / 2, 12), BASE_W - 12 - BW)
        tail_x = min(max((tx0 + tx1) / 2 - body_x, 28), BW - 28)

        cw, ch = round((BW + 2 * MARG) * u), round((BH + 2 * MARG + TH) * u)
        ox, oy = MARG * u, (MARG + (TH if tail_up else 0)) * u
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))

        def box(x0, y0, x1, y1):                       # bubble-local base units -> canvas px
            return [ox + x0 * u, oy + y0 * u, ox + x1 * u, oy + y1 * u]

        # soft shadow
        sh = Image.new("L", (cw, ch), 0)
        ImageDraw.Draw(sh).rounded_rectangle(box(0, 5, BW, BH + 5), radius=18 * u, fill=110)
        sh = sh.filter(ImageFilter.GaussianBlur(7 * u))
        canvas.paste((70, 30, 50), mask=sh)
        d = ImageDraw.Draw(canvas)
        d.rounded_rectangle(box(0, 0, BW, BH), radius=18 * u, fill=PINK + (255,),
                            outline=PINK_EDGE + (255,), width=round(2 * u))
        # tail pointing at the highlighted thing
        if tail_up:
            base_y, tip_y_local, side = 0, -TH, 1
        else:
            base_y, tip_y_local, side = BH, BH + TH, -1
        tri = [(ox + (tail_x - 11) * u, oy + (base_y + side * 1) * u),
               (ox + tail_x * u, oy + tip_y_local * u),
               (ox + (tail_x + 11) * u, oy + (base_y + side * 1) * u)]
        d.polygon(tri, fill=PINK + (255,))
        d.line([tri[0], tri[1], tri[2]], fill=PINK_EDGE + (255,), width=round(2 * u), joint="curve")
        d.rectangle(box(tail_x - 10, base_y - 1.5, tail_x + 10, base_y + 1.5), fill=PINK + (255,))

        # text
        y = y_title
        for line in t_lines:
            d.text((ox + PAD * u, oy + y * u), line, font=f_title, fill=ROSE)
            y += LT
        d.line([ox + PAD * u, oy + y_sep * u, ox + (BW - PAD) * u, oy + y_sep * u],
               fill=(255, 245, 248, 255), width=round(1.6 * u))
        y = y_body
        for line in b_lines:
            d.text((ox + PAD * u, oy + y * u), line, font=f_body, fill=PLUM)
            y += LB
        # progress dots
        n = len(STEPS)
        for i in range(n):
            cx = BW / 2 + (i - (n - 1) / 2) * 16
            r = 4.2 if i == index else 3.4
            d.ellipse(box(cx - r, y_dots - r + 5, cx + r, y_dots + r + 5),
                      fill=ROSE + (255,) if i == index else (255, 244, 247, 255),
                      outline=PINK_EDGE + (255,), width=round(1.2 * u))

        # buttons
        last = index == n - 1
        buttons = {}

        def text_w_base(txt, font):
            return font.getlength(txt) / u

        next_label = "Complete" if last else "Next"
        nw = text_w_base(next_label, f_btn) + 32
        nx1 = BW - PAD
        buttons["next"] = (nx1 - nw, y_btn, nx1, y_btn + 30)
        if index > 0:
            bw = text_w_base("Back", f_btn) + 26
            buttons["back"] = (nx1 - nw - 8 - bw, y_btn, nx1 - nw - 8, y_btn + 30)
        if not last:
            sw = text_w_base("Skip tour", f_small)
            buttons["skip"] = (PAD, y_btn + 4, PAD + sw, y_btn + 26)

        for name, (bx0, by0, bx1, by1) in buttons.items():
            hot = hover == name
            if name == "next":
                d.rounded_rectangle(box(bx0, by0, bx1, by1), radius=15 * u,
                                    fill=(255, 232, 240, 255) if hot else CREAM + (255,),
                                    outline=ROSE + (255,), width=round(1.6 * u))
                d.text((ox + (bx0 + bx1) / 2 * u, oy + (by0 + by1) / 2 * u), next_label,
                       font=f_btn, fill=ROSE, anchor="mm")
            elif name == "back":
                if hot:
                    d.rounded_rectangle(box(bx0, by0, bx1, by1), radius=15 * u, fill=(255, 232, 240, 255))
                d.text((ox + (bx0 + bx1) / 2 * u, oy + (by0 + by1) / 2 * u), "Back",
                       font=f_btn, fill=PLUM, anchor="mm")
            else:
                col = ROSE if hot else (140, 90, 108)
                cy = oy + (by0 + by1) / 2 * u
                d.text((ox + bx0 * u, cy), "Skip tour", font=f_small, fill=col, anchor="lm")
                d.line([ox + bx0 * u, cy + 8 * u, ox + bx1 * u, cy + 8 * u], fill=col, width=round(1 * u))

        small = canvas.resize((round(cw / ss), round(ch / ss)), Image.LANCZOS)
        px = round((body_x - MARG) * S)
        py = round((body_y - MARG - (TH if tail_up else 0)) * S)
        screen_buttons = {name: ((body_x + b[0]) * S, (body_y + b[1]) * S,
                                 (body_x + b[2]) * S, (body_y + b[3]) * S)
                          for name, b in buttons.items()}
        tip = (round((body_x + tail_x) * S), round((body_y + tip_y_local) * S))
        rec = dict(img=small, pos=(px, py), tip=tip, buttons=screen_buttons)
        self._bubble_cache[key] = rec
        return rec
