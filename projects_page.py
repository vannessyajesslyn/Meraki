"""Project Manager page (opened by clicking the sticky notes on the homepage).

Green scrapbook style: cream grid paper with a gingham-taped clip
(assets/projects_bg.jpg). Each project is a scrap of paper whose progress
bar fills up with gingham tape; finished projects get a green star sticker.

    - write a project name and press ADD (or Enter)
    - the new project opens straight away: type its sub-tasks, Enter after each
    - click a project card to open / close its sub-tasks

Uses project_manager.py for the data; this file only draws and handles clicks.
"""
from homepage import load_font
from page_kit import PageBase, TextField, fit_text
from project_manager import ProjectManager
from scrap_kit import (FADED, GREEN, GREEN_DARK, dashed, gingham_bar, mono, paper,
                       pen_circle, pen_field, pen_x, seed_of, stamp_button, star, tape, wobble)

HEADER_H = 96          # project card: name, percent, gingham progress bar
TASK_H = 32            # one sub-task row
ADD_ROW_H = 50         # "add a sub-task" row at the bottom of an open project
CARD_STYLES = ["mint", "butter", "white", "sage"]
GREEN_TAPE = (190, 214, 170)
FORM = (60, 128, 433, 210)


class ProjectsPage(PageBase):
    TITLE = "Projects"
    BACKGROUND = "projects_bg.jpg"
    LIST_TOP = 240
    SCROLLBAR = GREEN
    TOAST = ((253, 250, 238), GREEN_DARK, GREEN_DARK)
    TOAST_FONT = staticmethod(mono)
    HOME_CENTER = (66, 822)            # bottom-left (the stars are bottom-right)

    def __init__(self, assets_dir, scale, save_file):
        super().__init__(assets_dir, scale)
        self.manager = ProjectManager(save_file)
        self.f_project = TextField("e.g. I2P final project")
        self.f_task = TextField("type a small step...")
        self.open_index = 0 if self.manager.projects else None   # the expanded project

    # ---------------- actions ----------------
    def on_click(self, name):
        projects = self.manager.projects
        if name == "field_project":
            self.focus = self.f_project
        elif name == "add_project":
            self.add_project()
        elif name == "field_task":
            self.focus = self.f_task
        elif name == "add_task":
            self.add_task()
        elif name.startswith("open_"):
            i = int(name[5:])
            self.open_index = None if self.open_index == i else i
            self.f_task.text = ""
            self.scroll(0)
        elif name.startswith("delp_"):
            i = int(name[5:])
            removed = projects[i].name
            self.manager.remove_project(i)
            if self.open_index is not None:
                if self.open_index == i:
                    self.open_index = None
                elif self.open_index > i:
                    self.open_index -= 1
            self.show_toast(f"Deleted \"{removed[:22]}\"")
            self.scroll(0)
        elif name.startswith("task_"):
            p, t = map(int, name[5:].split("_"))
            project = projects[p]
            project.toggle_subtask(t)
            self.manager.save()                     # sub-task changes don't save by themselves
            if project.is_complete():
                self.show_toast("Project complete. Great job!", 3.0)
        elif name.startswith("delt_"):
            p, t = map(int, name[5:].split("_"))
            projects[p].remove_subtask(t)
            self.manager.save()
            self.scroll(0)

    def on_field_action(self, field, action):
        if action == "submit":
            if field is self.f_project:
                self.add_project()
            else:
                self.add_task()

    def add_project(self):
        name = self.f_project.text.strip()
        if not name:
            self.focus = self.f_project
            self.show_toast("Write a project name first")
            return
        self.manager.add_project(name)
        self.f_project.text = ""
        self.open_index = len(self.manager.projects) - 1     # open the new one
        self.f_task.text = ""
        self.focus = self.f_task                    # ready to type its first sub-task
        self.show_toast("Now add its small steps!")

    def add_task(self):
        if self.open_index is None:
            return
        name = self.f_task.text.strip()
        if not name:
            self.focus = self.f_task
            return
        self.manager.projects[self.open_index].add_subtask(name)
        self.manager.save()
        self.f_task.text = ""
        self.focus = self.f_task                    # stay in the box to add the next one

    # ---------------- header: title + the "new project" card ----------------
    def draw_title(self, d):
        u = self.u
        d.text((246.5 * u, 104 * u), "my projects", font=mono(27 * u), fill=GREEN_DARK, anchor="mm")
        star(d, 138, 101, 12, u, rotate=-80)
        star(d, 356, 103, 9, u, rotate=-100, fill=(140, 172, 108))

    def draw_header(self, d):
        u, c = self.u, self.canvas
        x0, y0, x1, y1 = FORM
        paper(c, x0, y0, x1, y1, u, "cream", seed=21, line_start=y0 + 22, line_gap=20)
        tape(c, x0 + 6, y0 + 8, 44, 14, u, angle=40, color=GREEN_TAPE)
        tape(c, x1 - 6, y0 + 8, 44, 14, u, angle=-40, color=GREEN_TAPE)

        line_y = y0 + 42
        d.text(((x0 + 18) * u, (line_y - 4) * u), "new project:", font=mono(13 * u),
               fill=GREEN_DARK, anchor="ls")
        pen_field(self, d, "field_project", self.f_project, x0 + 124, x1 - 92, line_y)
        add = (x1 - 82, line_y - 22, x1 - 16, line_y + 4)
        stamp_button(d, add, "+ ADD", u, hot=self.hover_name == "add_project", color=GREEN_DARK, size=13)
        self.add_hit("add_project", *add)
        d.text(((x0 + 18) * u, (y1 - 18) * u), "big project -> small steps -> tick them off",
               font=mono(10.5 * u), fill=FADED, anchor="lm")

        projects = self.manager.projects
        if projects:
            n = len(projects)
            done = sum(1 for p in projects if p.is_complete())
            d.text((64 * u, 228 * u), f"{n} project{'' if n == 1 else 's'}  /  {done} complete",
                   font=mono(13 * u), fill=GREEN_DARK, anchor="lm")

    # ---------------- the project cards ----------------
    def draw_list(self, d, y):
        u, c = self.u, self.canvas
        top = y
        projects = self.manager.projects
        if not projects:
            paper(c, 120, y + 20, 373, y + 116, u, "butter", seed=4)
            star(d, 136, y + 26, 14, u, rotate=-75)
            d.text((246 * u, (y + 58) * u), "no projects yet!", font=mono(16 * u), fill=GREEN_DARK,
                   anchor="mm")
            d.text((246 * u, (y + 84) * u), "add a big one on the card above", font=mono(11 * u),
                   fill=FADED, anchor="mm")
            return 130
        for i, p in enumerate(projects):
            is_open = self.open_index == i
            h = HEADER_H + (len(p.subtasks) * TASK_H + ADD_ROW_H if is_open else 0)
            s = seed_of(p.name) + i
            dx = wobble(s, 4)
            x0, x1 = 60 + dx, 433 + dx
            paper(c, x0, y, x1, y + h, u, CARD_STYLES[s % len(CARD_STYLES)], seed=s)
            self.add_hit(f"open_{i}", x0, y, x1, y + HEADER_H)     # click the card to open/close
            if p.is_complete():
                star(d, x0 + 12, y + 6, 20, u, rotate=-70 + wobble(s, 10))
            else:
                tape(c, x0 + 14, y + 4, 42, 13, u, angle=-36 + wobble(s + 2, 8), color=GREEN_TAPE)
            self._draw_header(d, i, p, x0, x1, y, is_open)
            if is_open:
                self._draw_subtasks(d, i, p, x0, x1, y + HEADER_H)
            y += h + 14
        return y - top

    def _draw_header(self, d, i, p, x0, x1, y, is_open):
        u, c = self.u, self.canvas
        complete = p.is_complete()
        name_font = load_font(18 * u, True)
        name = fit_text(p.name, name_font, (x1 - x0 - 130) * u)
        d.text(((x0 + 24) * u, (y + 32) * u), name, font=name_font, fill=GREEN_DARK, anchor="ls")
        if complete:
            w = name_font.getlength(name) / u
            d.text(((x0 + 32 + w) * u, (y + 31) * u), "done!", font=mono(12 * u), fill=GREEN, anchor="ls")

        pct = round(p.progress() * 100)
        d.text(((x1 - 44) * u, (y + 32) * u), f"{pct}%", font=mono(19 * u),
               fill=GREEN if complete else GREEN_DARK, anchor="rs")
        pen_x(d, x1 - 22, y + 24, u, hot=self.hover_name == f"delp_{i}")
        self.add_hit(f"delp_{i}", x1 - 34, y + 12, x1 - 10, y + 36)

        gingham_bar(c, x0 + 24, y + 44, x1 - 24, y + 60, p.progress(), u)

        n = len(p.subtasks)
        count = (f"{sum(1 for t in p.subtasks if t['done'])} of {n} step{'' if n == 1 else 's'} done"
                 if n else "no steps yet")
        d.text(((x0 + 24) * u, (y + 78) * u), count, font=mono(11.5 * u), fill=FADED, anchor="lm")
        hot = self.hover_name == f"open_{i}"
        label = "hide steps -" if is_open else "show steps +"
        d.text(((x1 - 24) * u, (y + 78) * u), label, font=mono(11.5 * u),
               fill=GREEN if hot else GREEN_DARK, anchor="rm")

    def _draw_subtasks(self, d, i, p, x0, x1, y):
        u = self.u
        dashed(d, x0 + 20, x1 - 20, y - 2, u, color=(176, 186, 150))
        for t, task in enumerate(p.subtasks):
            cy = y + TASK_H / 2
            name = f"task_{i}_{t}"
            pen_circle(d, x0 + 36, cy, 8, u, task["done"], hot=self.hover_name == name)
            self.add_hit(name, x0 + 22, cy - 13, x0 + 50, cy + 13)
            font = load_font(15 * u)
            text = fit_text(task["name"], font, (x1 - x0 - 110) * u)
            color = (150, 156, 136) if task["done"] else (52, 58, 44)
            d.text(((x0 + 54) * u, cy * u), text, font=font, fill=color, anchor="lm")
            if task["done"]:
                w = font.getlength(text) / u
                d.line([(x0 + 52) * u, (cy + 1) * u, (x0 + 56 + w) * u, (cy - 1) * u], fill=GREEN,
                       width=round(1.6 * u))
            pen_x(d, x1 - 24, cy, u, hot=self.hover_name == f"delt_{i}_{t}", r=5)
            self.add_hit(f"delt_{i}_{t}", x1 - 36, cy - 12, x1 - 12, cy + 12)
            y += TASK_H
        line_y = y + 32
        d.text(((x0 + 30) * u, (line_y - 4) * u), "+", font=mono(17 * u), fill=GREEN, anchor="ls")
        pen_field(self, d, "field_task", self.f_task, x0 + 48, x1 - 86, line_y, size=14)
        add = (x1 - 76, line_y - 22, x1 - 22, line_y + 2)
        stamp_button(d, add, "add", u, hot=self.hover_name == "add_task", color=GREEN_DARK, size=12)
        self.add_hit("add_task", *add)
