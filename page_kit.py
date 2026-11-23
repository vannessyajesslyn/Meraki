"""Shared building blocks for the Assignments and Projects pages.

Both pages work like HomePage / TimerPage (so controller.py treats them the same):

    page.update(dt)          page.render() -> PIL image
    page.click(x, y)         -> "home" when the home button is clicked
    page.hover(x, y)         -> "hand2", "xterm" or "arrow"
    page.key(char, keysym)   typing into the text boxes
    page.scroll(steps)       mouse wheel (+1 = down, -1 = up)

All layout numbers are in the homepage's base size (493 x 877) and get
multiplied by the window scale, so the pages line up with the homepage.

Every frame is drawn at 2x size and shrunk, so edges and text look smooth.
"""
import os

from PIL import Image, ImageDraw

from homepage import (BASE_H, BASE_W, CREAM, PINK, PINK_EDGE, PLUM, ROSE,
                      clamp01, cutout_white_bg, ease_out_cubic, load_font)

# ---- colours (same pink theme as the homepage) ----
PAGE_BG = (255, 240, 244)
CARD_BG = (255, 255, 255)
SOFT = (176, 140, 154)          # grey-pink for hints and placeholders
URGENT = (214, 64, 90)          # due soon / overdue
DONE_GREY = (178, 160, 168)
BAR_BG = (251, 226, 233)
BAR_FILL = (236, 128, 162)

SS = 2                          # draw at 2x, then shrink -> smooth edges
HOME_CENTER, HOME_SIZE = (444, 834), 58
MAX_CHARS = 60
LIST_PAD = 10                   # space between the list edge and the first card


def fit_text(text, font, max_w):
    """Cut `text` with '...' so it fits in max_w pixels."""
    if font.getlength(text) <= max_w:
        return text
    while text and font.getlength(text + "...") > max_w:
        text = text[:-1]
    return text + "..."


class TextField:
    """A one-line text box you can click and type into."""

    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.text = ""

    def type_key(self, char, keysym):
        """Returns "submit" for Enter, "next" for Tab, "cancel" for Esc."""
        if keysym in ("Return", "KP_Enter"):
            return "submit"
        if keysym in ("Tab", "ISO_Left_Tab"):
            return "next"
        if keysym == "Escape":
            return "cancel"
        if keysym == "BackSpace":
            self.text = self.text[:-1]
        elif char and len(char) == 1 and char.isprintable() and len(self.text) < MAX_CHARS:
            self.text += char
        return None


class PageBase:
    """Everything the two list pages have in common: title, home button,
    text boxes, toast message, scrolling list area and hit testing."""

    TITLE = ""
    LIST_TOP, LIST_BOTTOM = 270, 792          # the scrolling area (base units)
    BACKGROUND = None                         # e.g. "assignments_bg.jpg" in assets/ (None = plain pink)
    SCROLLBAR = PINK_EDGE
    TOAST = (PINK, PINK_EDGE, PLUM)           # fill, outline, text
    TOAST_FONT = None                         # function(size) -> font; None = Times New Roman bold

    def __init__(self, assets_dir, scale):
        self.S = scale
        self.W, self.H = round(BASE_W * scale), round(BASE_H * scale)
        self.u = scale * SS                   # base units -> pixels on the 2x canvas
        self.home_icon = self._load_home_icon(os.path.join(assets_dir, "home.png"))
        self.bg = self._load_background(assets_dir)
        self.canvas = None                    # the 2x picture being drawn (during render)

        self.hover_name = None
        self.dirty = True
        self.focus = None                     # the TextField being typed in
        self.scroll_y = 0.0
        self.content_h = 0.0
        self.t = 0.0
        self._blink = True
        self.toast_text, self.toast_left, self.toast_total = None, 0.0, 1.0
        self._hits = []                       # (name, x0, y0, x1, y1) filled while drawing

    # ================= public API (same as the other pages) =================
    def needs_redraw(self):
        return self.dirty

    def show_toast(self, text, seconds=2.4):
        self.toast_text, self.toast_left, self.toast_total = text, seconds, seconds
        self.dirty = True

    def update(self, dt):
        self.t += dt
        blink = int(self.t * 2) % 2 == 0      # text cursor blinks twice a second
        if self.focus is not None and blink != self._blink:
            self.dirty = True
        self._blink = blink
        if self.toast_left > 0:
            self.toast_left -= dt
            self.dirty = True

    def hover(self, x, y):
        old = self.hover_name
        self.hover_name = self._hit(x, y)
        if old != self.hover_name:
            self.dirty = True
        if self.hover_name in (None, "pop_bg"):
            return "arrow"
        return "xterm" if self.hover_name.startswith("field") else "hand2"

    def click(self, x, y):
        name = self._hit(x, y)
        self.dirty = True
        if name == "home":
            self.focus = None
            self.hover_name = None
            return "home"
        self.focus = None                     # clicking anywhere else leaves the text box
        if name is not None:
            self.on_click(name)
        return None

    def key(self, char, keysym):
        if self.focus is None:
            return
        result = self.focus.type_key(char, keysym)
        if result == "cancel":
            self.focus = None
        elif result is not None:
            self.on_field_action(self.focus, result)
        self.t, self._blink = 0.0, True       # keep the cursor visible while typing
        self.dirty = True

    def scroll(self, steps):
        view = self.LIST_BOTTOM - self.LIST_TOP
        max_scroll = max(0.0, self.content_h - view)
        self.scroll_y = min(max(self.scroll_y + steps * 40, 0.0), max_scroll)
        self.dirty = True

    # ================= for the pages to fill in =================
    def on_click(self, name):
        pass

    def on_field_action(self, field, action):
        pass

    def draw_header(self, d):
        pass

    def draw_list(self, d, y):
        """Draw the list starting at base y. Return the total height used."""
        return 0

    def draw_title(self, d):
        d.text((BASE_W / 2 * self.u, 46 * self.u), self.TITLE,
               font=load_font(34 * self.u, True), fill=ROSE, anchor="mm")

    def draw_overlay(self, d):
        """Pop-ups go here (drawn on top of everything)."""
        pass

    # ================= drawing =================
    def render(self):
        self.dirty = False
        self._hits = []
        u = self.u
        canvas = self.bg.copy()
        self.canvas = canvas
        d = ImageDraw.Draw(canvas)

        # 1) the list (may run past the top/bottom; we cover that next)
        list_hits_start = len(self._hits)
        self.content_h = self.draw_list(d, self.LIST_TOP + LIST_PAD - self.scroll_y) + 2 * LIST_PAD
        # keep list clicks only where the list is actually visible
        self._hits[list_hits_start:] = [
            (n, x0, max(y0, self.LIST_TOP), x1, min(y1, self.LIST_BOTTOM))
            for n, x0, y0, x1, y1 in self._hits[list_hits_start:]
            if y1 > self.LIST_TOP and y0 < self.LIST_BOTTOM]

        # 2) cover anything that scrolled outside the list area (with the background)
        top = (0, 0, canvas.width, round(self.LIST_TOP * u))
        bottom = (0, round(self.LIST_BOTTOM * u), canvas.width, canvas.height)
        for box in (top, bottom):
            canvas.paste(self.bg.crop(box), box)
        self._draw_fade(canvas)

        # 3) header (title + form) and footer (home button) on top
        self.draw_title(d)
        self.draw_header(d)
        self._draw_scrollbar(d)
        self._draw_home(canvas, d)
        self.draw_overlay(d)

        frame = canvas.resize((self.W, self.H), Image.LANCZOS)
        if self.toast_left > 0:
            self._draw_toast(frame)
        return frame

    def _draw_fade(self, canvas):
        """Soft fade where the list meets the header and footer."""
        u, n = self.u, 14
        for i in range(n):
            a = 1 - i / n
            for y in (self.LIST_TOP + i, self.LIST_BOTTOM - 1 - i):
                box = (0, round(y * u), canvas.width, round((y + 1) * u))
                canvas.paste(Image.blend(canvas.crop(box), self.bg.crop(box), a * 0.85), box)

    def _draw_scrollbar(self, d):
        view = self.LIST_BOTTOM - self.LIST_TOP
        if self.content_h <= view:
            return
        u = self.u
        frac = view / self.content_h
        bar_h = max(30, view * frac)
        top = self.LIST_TOP + (view - bar_h) * (self.scroll_y / (self.content_h - view))
        d.rounded_rectangle([481 * u, top * u, 486 * u, (top + bar_h) * u], radius=3 * u,
                            fill=self.SCROLLBAR)

    def _load_background(self, assets_dir):
        size = (round(self.W * SS), round(self.H * SS))
        if self.BACKGROUND:
            try:
                img = Image.open(os.path.join(assets_dir, self.BACKGROUND)).convert("RGB")
                return img.resize(size, Image.LANCZOS)
            except OSError:
                pass                          # picture missing -> plain background
        return Image.new("RGB", size, PAGE_BG)

    def _load_home_icon(self, path):
        try:
            return cutout_white_bg(path)
        except (OSError, TypeError, ValueError):
            return None                       # no home.png -> a drawn button is used

    def _draw_home(self, canvas, d):
        u = self.u
        hot = self.hover_name == "home"
        size = HOME_SIZE * (1.07 if hot else 1.0)
        cx, cy = HOME_CENTER
        if self.home_icon is not None:
            h = round(size * u)
            w = round(h * self.home_icon.width / self.home_icon.height)
            icon = self.home_icon.resize((w, h), Image.LANCZOS)
            canvas.paste(icon, (round(cx * u - w / 2), round(cy * u - h / 2)), icon)
            half_w = w / u / 2
        else:
            half_w = 48
            self.pill(d, (cx - half_w, cy - 20, cx + half_w, cy + 20), "home", hot)
        self.add_hit("home", cx - half_w, cy - size / 2, cx + half_w, cy + size / 2)

    def _draw_toast(self, frame):
        S = self.S
        fill, edge, ink = self.TOAST
        font = self.TOAST_FONT(14 * S) if self.TOAST_FONT else load_font(15 * S, True)
        w, h = int(font.getlength(self.toast_text) + 40 * S), int(36 * S)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(img)
        dd.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=fill + (255,),
                             outline=edge + (255,), width=2)
        dd.text((w / 2, h / 2), self.toast_text, font=font, fill=ink, anchor="mm")
        age = self.toast_total - self.toast_left
        a = min(ease_out_cubic(age / 0.2), clamp01(self.toast_left / 0.4))
        alpha = img.getchannel("A").point(lambda v: int(v * a))
        frame.paste(img.convert("RGB"), ((self.W - w) // 2, round(self.H - 108 * S)), alpha)

    # ================= small drawing helpers (base units in, 2x pixels out) =================
    def add_hit(self, name, x0, y0, x1, y1):
        self._hits.append((name, x0, y0, x1, y1))

    def _hit(self, x, y):
        bx, by = x / self.S, y / self.S
        for name, x0, y0, x1, y1 in reversed(self._hits):    # last drawn = on top
            if x0 <= bx <= x1 and y0 <= by <= y1:
                return name
        return None

    def box(self, x0, y0, x1, y1):
        u = self.u
        return [x0 * u, y0 * u, x1 * u, y1 * u]

    def card(self, d, x0, y0, x1, y1, radius=16):
        d.rounded_rectangle(self.box(x0, y0, x1, y1), radius=radius * self.u, fill=CARD_BG,
                            outline=(248, 206, 218), width=round(1.5 * self.u))

    def field(self, d, name, fld, x0, y0, x1, y1):
        """Draw a TextField and make it clickable as `name` (must start with 'field')."""
        u = self.u
        focused = self.focus is fld
        d.rounded_rectangle(self.box(x0, y0, x1, y1), radius=10 * u, fill=CREAM,
                            outline=ROSE if focused else (240, 196, 210),
                            width=round((2 if focused else 1.4) * u))
        font = load_font(15 * u)
        pad, cy = 12, (y0 + y1) / 2
        room = (x1 - x0 - 2 * pad) * u
        if fld.text:
            shown = fld.text
            while font.getlength(shown) > room - 4 * u:       # show the end while typing
                shown = shown[1:]
            d.text(((x0 + pad) * u, cy * u), shown, font=font, fill=PLUM, anchor="lm")
            end = (x0 + pad) * u + font.getlength(shown)
        else:
            d.text(((x0 + pad) * u, cy * u), fit_text(fld.placeholder, font, room),
                   font=font, fill=SOFT, anchor="lm")
            end = (x0 + pad) * u
        if focused and self._blink:
            d.line([end + 1.5 * u, (cy - 9) * u, end + 1.5 * u, (cy + 9) * u], fill=ROSE,
                   width=round(1.6 * u))
        self.add_hit(name, x0, y0, x1, y1)

    def pill(self, d, rect, label, hot, primary=True, size=15):
        u = self.u
        if primary:
            fill, text = ((176, 70, 108) if hot else ROSE), CREAM
        else:
            fill, text = ((255, 226, 236) if hot else CREAM), ROSE
        d.rounded_rectangle(self.box(*rect), radius=(rect[3] - rect[1]) / 2 * u, fill=fill,
                            outline=ROSE, width=round(1.5 * u))
        d.text(((rect[0] + rect[2]) / 2 * u, (rect[1] + rect[3]) / 2 * u), label,
               font=load_font(size * u, True), fill=text, anchor="mm")

    def checkbox(self, d, name, cx, cy, checked, size=22):
        u, r = self.u, size / 2
        hot = self.hover_name == name
        if checked:
            d.rounded_rectangle(self.box(cx - r, cy - r, cx + r, cy + r), radius=7 * u,
                                fill=ROSE, outline=ROSE, width=round(1.6 * u))
            pts = [(cx - r * 0.5, cy + r * 0.02), (cx - r * 0.12, cy + r * 0.42),
                   (cx + r * 0.55, cy - r * 0.38)]
            d.line([(x * u, y * u) for x, y in pts], fill=CREAM, width=round(2.6 * u),
                   joint="curve")
        else:
            d.rounded_rectangle(self.box(cx - r, cy - r, cx + r, cy + r), radius=7 * u,
                                fill=(255, 226, 236) if hot else CREAM, outline=PINK_EDGE,
                                width=round(1.8 * u))
        self.add_hit(name, cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6)

    def delete_button(self, d, name, cx, cy, r=11):
        u = self.u
        hot = self.hover_name == name
        if hot:
            d.ellipse(self.box(cx - r, cy - r, cx + r, cy + r), fill=(255, 226, 236))
        a = r * 0.42
        col = URGENT if hot else SOFT
        for (x0, y0, x1, y1) in ((cx - a, cy - a, cx + a, cy + a), (cx - a, cy + a, cx + a, cy - a)):
            d.line([x0 * u, y0 * u, x1 * u, y1 * u], fill=col, width=round(2 * u))
        self.add_hit(name, cx - r, cy - r, cx + r, cy + r)

    def text(self, d, xy, text, size, color, bold=False, anchor="la", max_w=None):
        font = load_font(size * self.u, bold)
        if max_w is not None:
            text = fit_text(text, font, max_w * self.u)
        d.text((xy[0] * self.u, xy[1] * self.u), text, font=font, fill=color, anchor=anchor)
        return font.getlength(text) / self.u
