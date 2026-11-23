"""Which page is showing and what every click does.

main.py (tkinter) and make_preview.py (video) both drive the app through
this one class, so they behave exactly the same:

    app = AppController("assets", scale, "settings.json", "study_stats.json")
    app.update(dt)            # every frame
    image = app.render()      # PIL image of the current page
    app.click(x, y)           # clicks / hover are passed to the current page
    cursor = app.hover(x, y)

The study timer lives here (not inside a page) so a running countdown keeps
going while you look at another page.
"""
from PIL import Image

import study_timer as st
from homepage import HomePage, clamp01, ease_in_out
from sound import AmbientPlayer
from storage import load_json, save_json
from timer_page import TimerPage

# pages that don't exist yet: the click just shows a small message
COMING_SOON = {
    "assignments": "Assignments Tracker is coming soon!",
    "projects": "Project Manager is coming soon!",
    "user": "Sign up & settings are coming soon!",
}
PHASE_MESSAGE = {
    "study": "Focus time. You've got this!",
    "break": "Time for a small break.",
    "long_break": "Long break time. You deserve it!",
}
FADE_SECONDS = 0.28


class AppController:
    def __init__(self, assets_dir, scale, settings_file, stats_file, sound=None):
        self.settings_file = settings_file
        self.settings = load_json(settings_file, {})
        first_time = not self.settings.get("tutorial_done", False)

        self.timer = st.StudyTimer(save_file=stats_file,
                                   sound=sound if sound is not None else AmbientPlayer())
        self.home = HomePage(assets_dir, scale, show_tutorial=first_time)
        self.timer_page = TimerPage(assets_dir, scale, self.timer)
        self.pages = {"home": self.home, "timer": self.timer_page}
        self.current = "home"
        self.W, self.H = self.home.W, self.home.H

        self._last_frame = None
        self._fade_from = None
        self._fade_t = 0.0

    @property
    def page(self):
        return self.pages[self.current]

    # ---------------- every frame ----------------
    def update(self, dt, timer_dt=None):
        """timer_dt=None: the countdown follows the real clock (the app).
        A number of seconds: advance it by exactly that much (used for videos/tests)."""
        events = self.timer.update() if timer_dt is None else self.timer.tick(timer_dt)
        for event in events:
            self._on_timer_event(event)
        self.page.update(dt)
        if self._fade_from is not None:
            self._fade_t += dt
            if self._fade_t >= FADE_SECONDS:
                self._fade_from = None

    def needs_redraw(self):
        return self.page.needs_redraw() or self._fade_from is not None

    def render(self):
        frame = self.page.render()
        if self._fade_from is not None:
            frame = Image.blend(self._fade_from, frame, ease_in_out(clamp01(self._fade_t / FADE_SECONDS)))
        else:
            self._last_frame = frame
        return frame

    # ---------------- mouse ----------------
    def hover(self, x, y):
        return self.page.hover(x, y)

    def click(self, x, y):
        action = self.page.click(x, y)
        if self.current == "home":
            if action == "timer":
                self.goto("timer")
            elif action == "tutorial_done":
                self.settings["tutorial_done"] = True
                save_json(self.settings_file, self.settings)
            elif action in COMING_SOON:
                self.home.show_toast(COMING_SOON[action])
        elif action == "home":
            self.goto("home")
        return action

    def goto(self, name):
        if name == self.current:
            return
        self._fade_from, self._fade_t = self._last_frame, 0.0
        self.current = name
        self.page.hover_name = None
        self.page.dirty = True

    # ---------------- study timer events ----------------
    def _on_timer_event(self, event):
        kind, value = event
        if kind == st.PHASE_CHANGED:
            self.page.show_toast(PHASE_MESSAGE[value])
        elif kind in (st.OVERWORK, st.SET_DONE):
            self.timer_page.show_popup(value)           # waits on the timer page until OK
            if self.current != "timer":
                self.home.show_toast(value, 4.0)
