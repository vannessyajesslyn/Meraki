"""Meraki - a cozy study companion.

Run:  python main.py

Tech stack: Python 3 + tkinter (window and mouse events), Pillow (drawing and
animation), opencv-python (plays the TV video) and pygame (loops the
white-noise / rain mp3s).

controller.py decides which page is showing and what each click does; the
pages (homepage.py, timer_page.py, assignments_page.py,
projects_page.py) draw every frame. This file only shows
those frames in a window and passes the mouse to the controller.
"""
import os
import sys
import time
import tkinter as tk

from PIL import ImageTk

from controller import AppController
from homepage import BASE_H

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
SETTINGS_FILE = os.path.join(HERE, "settings.json")
STATS_FILE = os.path.join(HERE, "study_stats.json")
FRAME_MS = 15


class MerakiApp:
    def __init__(self, root):
        self.root = root
        root.title("Meraki")
        root.resizable(False, False)

        scale = max(0.7, min(1.6, (root.winfo_screenheight() - 140) / BASE_H))
        self.app = AppController(ASSETS, scale, SETTINGS_FILE, STATS_FILE)

        self.canvas = tk.Canvas(root, width=self.app.W, height=self.app.H,
                                highlightthickness=0, bd=0, bg="black")
        self.canvas.pack()
        self.image_id = self.canvas.create_image(0, 0, anchor="nw")
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        root.bind("<Key>", self.on_key)                      # typing in the text boxes
        root.bind("<MouseWheel>", self.on_wheel)             # Windows / macOS scrolling
        root.bind("<Button-4>", lambda e: self.app.scroll(-1))   # Linux scroll up
        root.bind("<Button-5>", lambda e: self.app.scroll(1))    # Linux scroll down

        self.photo = None
        self.last = time.perf_counter()
        self.tick()

    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.1)
        self.last = now
        self.app.update(dt)
        if self.app.needs_redraw():
            self.photo = ImageTk.PhotoImage(self.app.render())   # keep a reference!
            self.canvas.itemconfig(self.image_id, image=self.photo)
        self.root.after(FRAME_MS, self.tick)

    def on_motion(self, event):
        self.canvas.config(cursor=self.app.hover(event.x, event.y))

    def on_click(self, event):
        self.app.click(event.x, event.y)

    def on_key(self, event):
        self.app.key(event.char, event.keysym)
        return "break"                                   # stop Tab from moving tkinter focus

    def on_wheel(self, event):
        if event.delta:
            self.app.scroll(-1 if event.delta > 0 else 1)


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
