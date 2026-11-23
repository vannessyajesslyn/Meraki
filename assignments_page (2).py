"""Assignments Tracker page (opened by clicking the books on the homepage).

Scrapbook style: grid-paper background (assets/assignments_bg.jpg), a taped
piece of lined paper for adding assignments, and every assignment is a torn
scrap of paper. Click a scrap to open its details note.

Uses assignment_tracker.py for the data; this file only draws and handles clicks.
"""
from datetime import datetime

from assignment_tracker import DATE_FORMAT, AssignmentTracker
from homepage import BASE_W, load_font, wrap_text
from page_kit import PageBase, TextField, fit_text
from scrap_kit import (FADED, INK, RED_PEN, TAPES, dashed, mono, paper, pen_box,
                       pen_x, seed_of, stamp_button, tape, wobble)

URGENT = (200, 40, 48)
CARD_STYLES = ["white", "kraft", "sticky", "pink"]

# the "add an assignment" scrap of lined paper
FORM = (54, 206, 472, 378)
FORM_LINES = (FORM[1] + 40, FORM[1] + 80, FORM[1] + 120)   # writing lines for the 3 boxes
FIELD_X0, FIELD_X1 = 140, 456
ADD_BTN = (372, FORM[3] - 34, 456, FORM[3] - 10)

# details pop-up
POP_X0, POP_X1 = 50, 443


def parse_due(text):
    """Accepts '2026-11-30 23:59', '2026/11/30 23:59' or just '2026-11-30' (= 23:59).
    Returns the text in DATE_FORMAT, or raises ValueError."""
    text = " ".join(text.replace("/", "-").split())
    if len(text) <= 10:
        text += " 23:59"
    datetime.strptime(text, DATE_FORMAT)          # raises ValueError if it's wrong
    return text


class AssignmentsPage(PageBase):
    TITLE = "Assignments"
    BACKGROUND = "assignments_bg.jpg"
    LIST_TOP, LIST_BOTTOM = 404, 800
    SCROLLBAR = (150, 144, 138)
    TOAST = ((253, 252, 246), INK, INK)
    TOAST_FONT = staticmethod(mono)

    def __init__(self, assets_dir, scale, save_file):
        super().__init__(assets_dir, scale)
        self.tracker = AssignmentTracker(save_file)
        self.f_title = TextField("e.g. Calculus homework")
        self.f_due = TextField("YYYY-MM-DD HH:MM")
        self.f_notes = TextField("optional")
        self.fields = [self.f_title, self.f_due, self.f_notes]
        self.detail = None                         # the Assignment shown in the pop-up
        self._minute = None

    def update(self, dt):
        super().update(dt)
        minute = datetime.now().strftime("%H:%M")  # "time left" changes every minute
        if minute != self._minute:
            self._minute = minute
            self.dirty = True

    def key(self, char, keysym):
        if self.detail is not None:
            if keysym == "Escape":
                self.detail = None
                self.dirty = True
            return
        super().key(char, keysym)

    # ---------------- actions ----------------
    def _index(self, a):
        return self.tracker.assignments.index(a)

    def on_click(self, name):
        if self.detail is not None:                # pop-up is open
            a = self.detail
            if name == "pop_done":
                self.tracker.toggle_done(self._index(a))
                self.show_toast("Marked as done!" if a.done else "Back on the to-do list")
            elif name == "pop_delete":
                self.tracker.remove(self._index(a))
                self.detail = None
                self.show_toast("Deleted")
                self.scroll(0)
            elif name in ("pop_close", "pop_bg"):
                self.detail = None
            return
        if name == "field_title":
            self.focus = self.f_title
        elif name == "field_due":
            self.focus = self.f_due
        elif name == "field_notes":
            self.focus = self.f_notes
        elif name == "add":
            self.add_assignment()
        elif name.startswith("done_"):
            self.tracker.toggle_done(int(name[5:]))
        elif name.startswith("del_"):
            self.tracker.remove(int(name[4:]))
            self.show_toast("Deleted")
            self.scroll(0)
        elif name.startswith("open_"):
            self.detail = self.tracker.assignments[int(name[5:])]

    def on_field_action(self, field, action):
        if action == "submit":
            self.add_assignment()
        elif action == "next":
            self.focus = self.fields[(self.fields.index(field) + 1) % len(self.fields)]

    def add_assignment(self):
        title = self.f_title.text.strip()
        if not title:
            self.focus = self.f_title
            self.show_toast("Write the assignment name first")
            return
        try:
            due = parse_due(self.f_due.text)
        except ValueError:
            self.focus = self.f_due
            self.show_toast("Due date should look like 2026-11-30 23:59", 3.5)
            return
        self.tracker.add(title, due, self.f_notes.text.strip())
        for f in self.fields:
            f.text = ""
        self.focus = None
        self.show_toast("Pinned to your board!")

    # ---------------- header: title + the taped "add" scrap ----------------
    def draw_title(self, d):
        u = self.u
        d.text((BASE_W / 2 * u, 182 * u), "my assignments", font=mono(27 * u), fill=INK, anchor="mm")
        dashed(d, 150, 343, 197, self.u, color=RED_PEN, dash=7, gap=4, width=1.6)

    def draw_header(self, d):
        u, c = self.u, self.canvas
        x0, y0, x1, y1 = FORM
        paper(c, x0, y0, x1, y1, u, "lined", seed=7, line_start=y0 + 20)
        tape(c, (x0 + x1) / 2, y0 + 2, 86, 18, u, angle=-3, color=TAPES[0])

        labels = ("what:", "due:", "notes:")
        fields = (("field_title", self.f_title), ("field_due", self.f_due),
                  ("field_notes", self.f_notes))
        for label, (name, fld), line_y in zip(labels, fields, FORM_LINES):
            d.text(((x0 + 34) * u, (line_y - 4) * u), label, font=mono(14 * u), fill=INK, anchor="ls")
            self._pen_field(d, name, fld, line_y)

        d.text(((x0 + 34) * u, (y1 - 22) * u), "date like 2026-11-30 18:00",
               font=mono(10.5 * u), fill=FADED, anchor="lm")
        stamp_button(d, ADD_BTN, "+ ADD", u, hot=self.hover_name == "add")
        self.add_hit("add", *ADD_BTN)

        items = self.tracker.assignments
        if items:
            done = sum(1 for a in items if a.done)
            d.text((58 * u, 392 * u), f"{len(items) - done} to do  /  {done} done",
                   font=mono(13 * u), fill=INK, anchor="lm")

    def _pen_field(self, d, name, fld, line_y):
        """A 'write on the line' text box."""
        u = self.u
        focused = self.focus is fld
        d.line([FIELD_X0 * u, line_y * u, FIELD_X1 * u, line_y * u],
               fill=RED_PEN if focused else (150, 160, 178), width=round((1.8 if focused else 1.1) * u))
        font = load_font(16 * u, True)
        room = (FIELD_X1 - FIELD_X0 - 8) * u
        if fld.text:
            shown = fld.text
            while font.getlength(shown) > room:
                shown = shown[1:]
            d.text(((FIELD_X0 + 4) * u, (line_y - 4) * u), shown, font=font, fill=INK, anchor="ls")
            end = (FIELD_X0 + 4) * u + font.getlength(shown)
        else:
            ph = mono(12.5 * u)
            d.text(((FIELD_X0 + 4) * u, (line_y - 5) * u), fit_text(fld.placeholder, ph, room),
                   font=ph, fill=(178, 172, 166), anchor="ls")
            end = (FIELD_X0 + 4) * u
        if focused and self._blink:
            d.line([end + 1.5 * u, (line_y - 19) * u, end + 1.5 * u, (line_y - 3) * u], fill=RED_PEN,
                   width=round(1.6 * u))
        self.add_hit(name, FIELD_X0 - 50, line_y - 26, FIELD_X1, line_y + 6)

    # ---------------- the list of scraps ----------------
    def draw_list(self, d, y):
        u, c = self.u, self.canvas
        top = y
        items = self.tracker.sorted_list()
        if not items:
            paper(c, 120, y + 20, 373, y + 112, u, "sticky", seed=3)
            tape(c, 246, y + 22, 64, 16, u, angle=4, color=TAPES[1])
            d.text((246 * u, (y + 56) * u), "nothing due yet!", font=mono(16 * u), fill=INK, anchor="mm")
            d.text((246 * u, (y + 82) * u), "add one on the note above", font=mono(11.5 * u),
                   fill=FADED, anchor="mm")
            return 130
        for a in items:
            i = self._index(a)
            s = seed_of(a.title + a.deadline.strftime(DATE_FORMAT))
            h = 80 if a.description else 62
            dx = wobble(s, 5)
            x0, x1 = 56 + dx, 470 + dx
            style = CARD_STYLES[s % len(CARD_STYLES)]
            paper(c, x0, y, x1, y + h, u, style, seed=s)
            self.add_hit(f"open_{i}", x0, y, x1, y + h)          # whole scrap -> details
            tape(c, x0 + 14, y + 4, 40, 13, u, angle=-38 + wobble(s + 1, 8),
                 color=TAPES[s % len(TAPES)])

            cy = y + 26
            pen_box(d, x0 + 26, cy, 15, u, a.done, hot=self.hover_name == f"done_{i}")
            self.add_hit(f"done_{i}", x0 + 12, cy - 14, x0 + 40, cy + 14)

            ink = (150, 144, 138) if a.done else INK
            title_font = load_font(17 * u, True)
            title = fit_text(a.title, title_font, 300 * u)
            d.text(((x0 + 46) * u, (cy + 6) * u), title, font=title_font, fill=ink, anchor="ls")
            if a.done:                                           # crossed out in pen
                w = title_font.getlength(title) / u
                d.line([(x0 + 44) * u, (cy + 1) * u, (x0 + 48 + w) * u, (cy - 1) * u],
                       fill=RED_PEN, width=round(1.6 * u))

            if a.done:
                left, col = "done!", RED_PEN
            else:
                left = a.time_left_text()
                col = URGENT if (a.is_urgent() or left == "Overdue!") else INK
            f_meta = mono(12 * u)
            d.text(((x0 + 46) * u, (y + 46) * u), left, font=f_meta, fill=col, anchor="lm")
            lw = f_meta.getlength(left) / u
            d.text(((x0 + 46 + lw + 10) * u, (y + 46) * u), a.deadline.strftime("due %a %d %b %H:%M"),
                   font=mono(11 * u), fill=FADED, anchor="lm")
            if a.description:
                note = fit_text("notes: " + a.description, mono(11 * u), 330 * u)
                d.text(((x0 + 46) * u, (y + 64) * u), note, font=mono(11 * u), fill=FADED, anchor="lm")

            if self.hover_name == f"open_{i}":
                d.text(((x1 - 12) * u, (y + h - 9) * u), "details >", font=mono(10.5 * u),
                       fill=RED_PEN, anchor="rm")
            pen_x(d, x1 - 22, y + 18, u, hot=self.hover_name == f"del_{i}")
            self.add_hit(f"del_{i}", x1 - 34, y + 6, x1 - 10, y + 30)
            y += h + 14
        return y - top

    # ---------------- details pop-up ----------------
    def draw_overlay(self, d):
        a = self.detail
        if a is None:
            return
        if a not in self.tracker.assignments:      # deleted somewhere else
            self.detail = None
            return
        u, c = self.u, self.canvas
        # dim everything and catch clicks outside the note
        c.paste((20, 20, 28), (0, 0), _dim_mask(c.size))
        self._hits = []
        self.add_hit("pop_bg", 0, 0, BASE_W, 877)

        f_title = load_font(22 * u, True)
        title_lines = wrap_text(a.title, f_title, (POP_X1 - POP_X0 - 60) * u)[:3]
        f_note = load_font(15 * u)
        note_lines = (wrap_text(a.description, f_note, (POP_X1 - POP_X0 - 76) * u)[:7]
                      if a.description else [])
        h = 70 + len(title_lines) * 28 + 118 + max(1, len(note_lines)) * 22 + 70
        y0 = max(110, (877 - h) / 2 - 20)
        y1 = y0 + h
        paper(c, POP_X0, y0, POP_X1, y1, u, "sticky", seed=seed_of(a.title) + 5)
        tape(c, (POP_X0 + POP_X1) / 2, y0 + 2, 96, 20, u, angle=2, color=TAPES[0])
        tape(c, POP_X1 - 10, y1 - 8, 54, 16, u, angle=-40, color=TAPES[2])

        x = POP_X0 + 30
        y = y0 + 34
        d.text((x * u, y * u), "ASSIGNMENT DETAILS", font=mono(12 * u), fill=FADED, anchor="lm")
        pen_x(d, POP_X1 - 26, y, u, hot=self.hover_name == "pop_close", r=7)
        self.add_hit("pop_close", POP_X1 - 42, y - 16, POP_X1 - 10, y + 16)
        y += 24
        for line in title_lines:
            d.text((x * u, (y + 20) * u), line, font=f_title, fill=INK, anchor="ls")
            y += 28
        dashed(d, x, POP_X1 - 30, y + 6, u, color=FADED)
        y += 28

        if a.done:
            left, col = "done!", RED_PEN
        else:
            left = a.time_left_text()
            col = URGENT if (a.is_urgent() or left == "Overdue!") else INK
        rows = [("due", a.deadline.strftime("%A %d %B %Y, %H:%M"), INK),
                ("left", left, col),
                ("status", "finished" if a.done else "still to do", INK)]
        for label, value, color in rows:
            d.text((x * u, y * u), label, font=mono(13 * u), fill=FADED, anchor="lm")
            d.text(((x + 74) * u, y * u), value, font=mono(14 * u), fill=color, anchor="lm")
            y += 26
        y += 6
        d.text((x * u, y * u), "notes", font=mono(13 * u), fill=FADED, anchor="lm")
        y += 6
        if note_lines:
            for line in note_lines:
                d.text(((x + 8) * u, (y + 18) * u), line, font=f_note, fill=INK, anchor="ls")
                d.line([(x + 4) * u, (y + 22) * u, (POP_X1 - 30) * u, (y + 22) * u],
                       fill=(226, 214, 160), width=max(1, round(u)))
                y += 22
        else:
            d.text(((x + 8) * u, (y + 16) * u), "(no notes)", font=mono(12 * u), fill=FADED, anchor="ls")
            y += 22

        by = y1 - 52
        done_rect = (x, by, x + 150, by + 30)
        del_rect = (POP_X1 - 30 - 110, by, POP_X1 - 30, by + 30)
        stamp_button(d, done_rect, "not done" if a.done else "mark done", u,
                     hot=self.hover_name == "pop_done", color=INK, size=13)
        stamp_button(d, del_rect, "delete", u, hot=self.hover_name == "pop_delete", size=13)
        self.add_hit("pop_done", *done_rect)
        self.add_hit("pop_delete", *del_rect)


def _dim_mask(size, _cache={}):
    if size not in _cache:
        from PIL import Image
        _cache[size] = Image.new("L", size, 110)
    return _cache[size]
