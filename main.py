"""Meraki - a cozy study companion.

Run:  python main.py

Tech stack: Python 3 + tkinter (window and mouse events) + Pillow (drawing,
animation, fonts). homepage.py draws every frame; this file only shows the
frame in a window and passes mouse clicks back to it.
"""
import os
import sys
import time
import tkinter as tk

from PIL import ImageTk

from homepage import BASE_H, HomePage
from storage import load_json, save_json

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SETTINGS_FILE = os.path.join(HERE, "settings.json")
FRAME_MS = 15

# Shown until the real pages exist. Replace each message with a call that
# opens the page (assignments tracker, study timer, project manager).
COMING_SOON = {
    "assignments": "Assignments Tracker is coming soon!",
    "timer": "Study Timer is coming soon!",
    "projects": "Project Manager is coming soon!",
    "user": "Sign up & settings are coming soon!",
}


class MerakiApp:
    def __init__(self, root):
        self.root = root
        root.title("Meraki")
        root.resizable(False, False)

        self.settings = load_json(SETTINGS_FILE, {})
        scale = max(0.7, min(1.6, (root.winfo_screenheight() - 140) / BASE_H))
        # the tutorial opens by itself the first time the app is launched
        first_time = not self.settings.get("tutorial_done", False)
        self.page = HomePage(ASSETS, scale, show_tutorial=first_time)

        self.canvas = tk.Canvas(root, width=self.page.W, height=self.page.H,
                                highlightthickness=0, bd=0, bg="black")
        self.canvas.pack()
        self.image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)

        self.photo = None
        self.last = time.perf_counter()
        self.tick()

    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.1)
        self.last = now
        self.page.update(dt)
        if self.page.needs_redraw():
            self.photo = ImageTk.PhotoImage(self.page.render())   # keep a reference!
            self.canvas.itemconfig(self.image_id, image=self.photo)
        self.root.after(FRAME_MS, self.tick)

    def on_motion(self, event):
        self.canvas.config(cursor=self.page.hover(event.x, event.y))

    def on_click(self, event):
        action = self.page.click(event.x, event.y)
        if action == "tutorial_done":
            self.settings["tutorial_done"] = True
            save_json(SETTINGS_FILE, self.settings)
        elif action in COMING_SOON:
            self.page.show_toast(COMING_SOON[action])


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        try:                                   # sharper window on high-DPI screens
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    app_root = tk.Tk()
    MerakiApp(app_root)
    app_root.mainloop()
