"""Study Timer page (follows the Meraki design mockup).

Same interface as HomePage, so main/app code can treat all pages the same:

    page = TimerPage("assets", scale, timer)    # timer = study_timer.StudyTimer
    page.update(dt)       page.render() -> PIL image
    page.click(x, y)      -> "home" when the return-home button is clicked
    page.hover(x, y)      -> "hand2" or "arrow"

Layout numbers are in the mockup's own pixels (1080 x 1920); `k` converts
them to the real window size.

Fonts: Times New Roman everywhere, except the countdown (Winkle).
"""
import os
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from homepage import (BASE_H, BASE_W, clamp01, cutout_white_bg, ease_out_cubic,
                      load_font, wrap_text)
from sound import SoundUnavailable

DW, DH = 1080, 1920                      # the mockup size

GREEN = (116, 156, 106)
CARD = (192, 201, 211)
NAVY = (25, 48, 91)
INK = (20, 20, 24)
LIGHT = (226, 233, 245)

CARD_BOX = (28, 224, 1043, 690)
TITLE_CENTER, TITLE_SIZE = (540, 125), 128
LABEL_CENTER, LABEL_SIZE = (552, 290), 48
TIMER_BASELINE, TIMER_CENTER_X = 425, 552
TIMER_SIZE, TIMER_TRACKING, TIMER_BOLD = 128, 8, 0        # Winkle is already chunky; mockup shows "50: 00"
BUTTONS = {"start": (335, 545, 549, 648),
           "reset": (566, 545, 666, 648),
           "skip": (684, 545, 786, 648)}
PILLS = {"white_noise": (15, 1418, 507, 1510),
         "rain": (520, 1418, 1012, 1510)}
PILL_TEXT = {"white_noise": "white noise", "rain": "rain sounds"}
TV_BOX = (20, 723, 1060, 1409)           # the TV clip is a crop of the mockup
HOME_CENTER, HOME_HEIGHT = (905, 1735), 280
POPUP_BOX = (140, 640, 940, 1080)
POPUP_OK = (440, 955, 640, 1043)
TOAST_CENTER = (410, 1650)

WINKLE = os.path.join("fonts", "Winkle-Regular.ttf")


@lru_cache(maxsize=16)
def load_winkle(path, size):
    try:
        return ImageFont.truetype(path, max(6, round(size)))
    except OSError:                       # font file missing -> Times New Roman
        return load_font(size, True)


class LoopVideo:
    """Plays assets/tv_loop.mp4 forever (needs opencv-python). Without
    opencv it shows a still picture of the TV instead."""

    def __init__(self, video_path, still_path, size):
        self.size = size
        self.frame = None
        self.cap = None
        self.cv2 = None
        self.acc = 0.0
        self.fps = 24.0
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if cap.isOpened():
                self.cv2, self.cap = cv2, cap
                self.fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
                self._read(0)
        except ImportError:
            pass
        if self.frame is None:
            self.frame = Image.open(still_path).convert("RGB").resize(size, Image.LANCZOS)

    def _read(self, skip):
        cv2, cap = self.cv2, self.cap
        for _ in range(skip):                              # drop frames if we fell behind
            if not cap.grab():
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ok, bgr = cap.read()
        if not ok:                                         # end of the 1-minute clip -> loop
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, bgr = cap.read()
        if ok:
            small = cv2.resize(bgr, self.size, interpolation=cv2.INTER_AREA)
            self.frame = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))

    def advance(self, dt):
        """Move the video forward by dt seconds. Returns True if the picture changed."""
        if self.cap is None:
            return False
        self.acc += dt
        n = int(self.acc * self.fps)
        if n <= 0:
            return False
        self.acc -= n / self.fps
        self._read(min(n, 6) - 1)
        return True


class TimerPage:
    def __init__(self, assets_dir, scale, timer):
        self.timer = timer
        self.W, self.H = round(BASE_W * scale), round(BASE_H * scale)
        self.k = self.W / DW
        k = self.k
        self.assets = assets_dir

        self.f_label = load_font(LABEL_SIZE * k, True)
        self.f_timer = load_winkle(os.path.join(assets_dir, WINKLE), TIMER_SIZE * k)
        self.base = self._build_base()

        tv_size = (round((TV_BOX[2] - TV_BOX[0]) * k), round((TV_BOX[3] - TV_BOX[1]) * k))
        self.video = LoopVideo(os.path.join(assets_dir, "tv_loop.mp4"),
                               os.path.join(assets_dir, "tv_still.jpg"), tv_size)
        self.tv_mask = self._feather_mask(tv_size)
        self.home_icon = cutout_white_bg(os.path.join(assets_dir, "home.png"))

        self.hover_name = None
        self.dirty = True
        self.toast_text, self.toast_left, self.toast_total = None, 0.0, 1.0
        self.popup, self.popup_t = None, 0.0
        self._sprites = {}
        self._last_key = None

    # ================= public API =================
    @property
    def playing(self):
        """The TV plays until the whole pomodoro is done."""
        return not self.timer.finished

    def needs_redraw(self):
        return self.dirty

    def show_toast(self, text, seconds=2.4):
        self.toast_text, self.toast_left, self.toast_total = text, seconds, seconds
        self.dirty = True

    def show_popup(self, text):
        self.popup, self.popup_t = text, 0.0
        self.dirty = True

    def update(self, dt):
        if self.playing and self.video.advance(dt):
            self.dirty = True
        if self.toast_left > 0:
            self.toast_left -= dt
            self.dirty = True
        if self.popup is not None:
            self.popup_t += dt
            if self.popup_t < 0.4:                     # fade-in
                self.dirty = True
        key = (self.timer.time_text(), self.timer.phase, self.timer.running,
               self.timer.sound.current)
        if key != self._last_key:
            self._last_key = key
            self.dirty = True

    def hover(self, x, y):
        old = self.hover_name
        self.hover_name = self._hit(x, y)
        if old != self.hover_name:
            self.dirty = True
        return "hand2" if self.hover_name else "arrow"

    def click(self, x, y):
        name = self._hit(x, y)
        t = self.timer
        if name == "ok":
            self.popup = None
        elif name == "start":
            t.toggle()
        elif name == "reset":
            t.reset()
        elif name == "skip":
            t.skip()
        elif name in PILLS:
            try:
                t.toggle_sound(name)
            except SoundUnavailable as problem:
                self.show_toast(str(problem), 4.0)
        elif name == "home":
            self.hover_name = None
            return "home"
        self.dirty = True
        return None

    # ================= hit testing =================
    def _home_rect(self):
        k = self.k
        h = HOME_HEIGHT * k
        w = h * self.home_icon.width / self.home_icon.height
        cx, cy = HOME_CENTER[0] * k, HOME_CENTER[1] * k
        return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2

    def _hit(self, x, y):
        k = self.k

        def inside(box):
            return box[0] * k <= x <= box[2] * k and box[1] * k <= y <= box[3] * k

        if self.popup is not None:
            return "ok" if inside(POPUP_OK) else None
        for name, box in list(BUTTONS.items()) + list(PILLS.items()):
            if inside(box):
                return name
        hx0, hy0, hx1, hy1 = self._home_rect()
        if hx0 <= x <= hx1 and hy0 <= y <= hy1:
            return "home"
        return None

    # ================= drawing =================
    def render(self):
        self.dirty = False
        k, t = self.k, self.timer
        frame = self.base.copy()
        d = ImageDraw.Draw(frame)

        # label above the countdown + the countdown itself (Winkle)
        d.text((LABEL_CENTER[0] * k, LABEL_CENTER[1] * k), t.phase_label(),
               font=self.f_label, fill=NAVY, anchor="mm")
        self._draw_countdown(d, t.time_text().replace(":", ": "))   # mockup shows "50: 00"

        # buttons
        for name, box in BUTTONS.items():
            sprite = self._button(name, self.hover_name == name, t.running)
            frame.paste(sprite, (round(box[0] * k), round(box[1] * k)), sprite)

        # TV (the clip has soft edges so it blends into the green page)
        frame.paste(self.video.frame, (round(TV_BOX[0] * k), round(TV_BOX[1] * k)), self.tv_mask)

        # white noise / rain pills
        for name, box in PILLS.items():
            sprite = self._pill(name, t.sound.current == name, self.hover_name == name)
            frame.paste(sprite, (round(box[0] * k), round(box[1] * k)), sprite)

        # return-to-homepage button
        home = self._home_sprite(self.hover_name == "home")
        cx, cy = HOME_CENTER[0] * k, HOME_CENTER[1] * k
        frame.paste(home, (round(cx - home.width / 2), round(cy - home.height / 2)), home)

        if self.toast_left > 0:
            self._draw_toast(frame)
        if self.popup is not None:
            self._draw_popup(frame)
        return frame

    def _draw_countdown(self, d, text):
        k = self.k
        font, track = self.f_timer, TIMER_TRACKING * k
        widths = [font.getlength(c) for c in text]
        total = sum(widths) + track * (len(text) - 1)
        x = TIMER_CENTER_X * k - total / 2
        for ch, w in zip(text, widths):
            d.text((x, TIMER_BASELINE * k), ch, font=font, fill=INK, anchor="ls",
                   stroke_width=round(TIMER_BOLD * k), stroke_fill=INK)
            x += w + track

    # ---- static background: green page, title, card ----
    def _build_base(self):
        k = self.k
        base = Image.new("RGB", (self.W, self.H), GREEN)
        x0, y0, x1, y1 = CARD_BOX
        card = self._sprite(x1 - x0, y1 - y0, lambda d, s: d.rounded_rectangle(
            [0, 0, (x1 - x0) * s - 1, (y1 - y0) * s - 1], radius=58 * s, fill=CARD + (255,)))
        base.paste(card, (round(x0 * k), round(y0 * k)), card)
        ImageDraw.Draw(base).text((TITLE_CENTER[0] * k, TITLE_CENTER[1] * k), "Study Timer",
                                  font=load_font(TITLE_SIZE * k, True), fill=INK, anchor="mm")
        return base

    def _sprite(self, w, h, draw_fn):
        """Draw a shape at 3x size (smooth edges), shrink it, return RGBA.
        draw_fn(draw, s): s converts mockup pixels to canvas pixels."""
        ss, k = 3, self.k
        img = Image.new("RGBA", (max(1, round(w * k * ss)), max(1, round(h * k * ss))), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(img), k * ss)
        return img.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)

    def _feather_mask(self, size):
        f = 7 * self.k
        mask = Image.new("L", size, 0)
        ImageDraw.Draw(mask).rectangle([f, f, size[0] - f, size[1] - f], fill=255)
        return mask.filter(ImageFilter.GaussianBlur(f / 2.2))

    # ---- buttons ----
    def _button(self, name, hover, running):
        key = ("btn", name, hover, running if name == "start" else None)
        if key in self._sprites:
            return self._sprites[key]
        x0, y0, x1, y1 = BUTTONS[name]
        w, h = x1 - x0, y1 - y0

        def draw(d, s):
            cx, cy = w * s / 2, h * s / 2
            if name == "start":
                d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=30 * s,
                                    fill=((40, 68, 118) if hover else NAVY) + (255,),
                                    outline=(78, 106, 160, 255), width=round(4 * s))
                label = "pause" if running else "start"
                font = load_font(40 * s, True)
                tw = font.getlength(label)
                gap, icon_w = 20 * s, 38 * s
                left = cx - (icon_w + gap + tw) / 2
                ic = left + icon_w / 2
                if running:                                   # pause icon: two bars
                    for bx in (ic - 8 * s, ic + 8 * s):
                        d.rounded_rectangle([bx - 4.5 * s, cy - 19 * s, bx + 4.5 * s, cy + 19 * s],
                                            radius=3 * s, fill=LIGHT + (255,))
                else:                                          # play icon: outlined triangle
                    d.polygon([(ic - 15 * s, cy - 21 * s), (ic - 15 * s, cy + 21 * s), (ic + 19 * s, cy)],
                              outline=LIGHT + (255,), width=round(4 * s))
                d.text((left + icon_w + gap, cy), label, font=font, fill=LIGHT, anchor="lm")
                return
            d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=32 * s,
                                fill=((206, 215, 227) if hover else (196, 205, 216)) + (255,),
                                outline=((150, 168, 195) if hover else (208, 217, 230)) + (255,),
                                width=round(3 * s))
            dark, lw = (28, 32, 48, 255), round(5 * s)
            if name == "reset":                                # circular arrow
                r = 19 * s
                d.arc([cx - r, cy - r, cx + r, cy + r], start=285, end=225, fill=dark, width=lw)
                px, py = cx + r * 0.26, cy - r * 0.97          # arrow head at the top of the arc
                d.polygon([(px - 11 * s, py - 4 * s), (px + 5 * s, py - 14 * s), (px + 4 * s, py + 9 * s)],
                          fill=dark)
            else:                                              # skip: triangle + bar
                d.polygon([(cx - 17 * s, cy - 18 * s), (cx - 17 * s, cy + 18 * s), (cx + 8 * s, cy)],
                          outline=dark, width=lw)
                d.line([(cx + 15 * s, cy - 19 * s), (cx + 15 * s, cy + 19 * s)], fill=dark, width=lw)

        self._sprites[key] = self._sprite(w, h, draw)
        return self._sprites[key]

    def _pill(self, name, active, hover):
        key = ("pill", name, active, hover)
        if key in self._sprites:
            return self._sprites[key]
        x0, y0, x1, y1 = PILLS[name]
        w, h = x1 - x0, y1 - y0
        fill = ((40, 68, 118) if hover else NAVY) if active else ((206, 214, 224) if hover else CARD)

        def draw(d, s):
            d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=h * s / 2, fill=fill + (255,),
                                outline=((78, 106, 160) if active else (172, 184, 200)) + (255,),
                                width=round(3 * s))
            d.text((w * s / 2, h * s / 2), PILL_TEXT[name], font=load_font(46 * s, True),
                   fill=LIGHT if active else INK, anchor="mm")

        self._sprites[key] = self._sprite(w, h, draw)
        return self._sprites[key]

    def _home_sprite(self, hover):
        key = ("home", hover)
        if key not in self._sprites:
            h = round(HOME_HEIGHT * self.k * (1.07 if hover else 1.0))
            w = round(h * self.home_icon.width / self.home_icon.height)
            self._sprites[key] = self.home_icon.resize((w, h), Image.LANCZOS)
        return self._sprites[key]

    # ---- toast + pop-up ----
    def _draw_toast(self, frame):
        key = ("toast", self.toast_text)
        if key not in self._sprites:
            font = load_font(38 * self.k * 3, True)
            w = round(font.getlength(self.toast_text) / (self.k * 3) + 80)
            self._sprites[key] = self._sprite(w, 84, lambda d, s: (
                d.rounded_rectangle([0, 0, w * s - 1, 84 * s - 1], radius=42 * s, fill=CARD + (255,),
                                    outline=NAVY + (255,), width=round(3 * s)),
                d.text((w * s / 2, 84 * s / 2), self.toast_text, font=load_font(38 * s, True),
                       fill=NAVY, anchor="mm")))
        img = self._sprites[key]
        age = self.toast_total - self.toast_left
        a = min(ease_out_cubic(age / 0.2), clamp01(self.toast_left / 0.4))
        alpha = img.getchannel("A").point(lambda v: int(v * a))
        pos = (round(TOAST_CENTER[0] * self.k - img.width / 2),
               round(TOAST_CENTER[1] * self.k - img.height / 2))
        frame.paste(img, pos, alpha)

    def _draw_popup(self, frame):
        k = self.k
        a = clamp01(self.popup_t / 0.2)
        frame.paste((0, 0, 0), (0, 0), Image.new("L", frame.size, int(255 * 0.5 * a)))
        hover = self.hover_name == "ok"
        key = ("popup", self.popup, hover)
        if key not in self._sprites:
            x0, y0, x1, y1 = POPUP_BOX
            w, h = x1 - x0, y1 - y0
            ox0, oy0, ox1, oy1 = POPUP_OK

            def draw(d, s):
                d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=56 * s, fill=CARD + (255,),
                                    outline=NAVY + (255,), width=round(5 * s))
                font = load_font(56 * s, True)
                lines = wrap_text(self.popup, font, (w - 120) * s)
                top = (oy0 - y0) / 2 - len(lines) * 36 + 8
                for i, line in enumerate(lines):
                    d.text((w * s / 2, (top + 36 + i * 72) * s), line, font=font, fill=NAVY, anchor="mm")
                bx0, by0 = (ox0 - x0) * s, (oy0 - y0) * s
                d.rounded_rectangle([bx0, by0, bx0 + (ox1 - ox0) * s, by0 + (oy1 - oy0) * s],
                                    radius=44 * s, fill=((40, 68, 118) if hover else NAVY) + (255,))
                d.text((bx0 + (ox1 - ox0) * s / 2, by0 + (oy1 - oy0) * s / 2), "OK",
                       font=load_font(46 * s, True), fill=LIGHT, anchor="mm")

            self._sprites[key] = self._sprite(w, h, draw)
        img = self._sprites[key]
        alpha = img.getchannel("A").point(lambda v: int(v * a))
        frame.paste(img, (round(POPUP_BOX[0] * k), round(POPUP_BOX[1] * k)), alpha)
