"""Optional helper: records the app flow (homepage -> study timer -> homepage)
into meraki_preview.mp4 using the SAME code the app uses.

    python make_preview.py            (needs ffmpeg installed, or imageio-ffmpeg)

The video is silent and uses temporary settings/stat files, so it never
touches your real save files.
"""
import json
import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw

import timer_page as tp
from controller import AppController
from homepage import clamp01, ease_in_out

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "meraki_preview.mp4")
FPS = 30
SCALE = 1.46                      # 493x877 -> 720x1280


class NullSound:
    """Stands in for the real audio player (the video has no sound)."""
    current = None

    def toggle(self, kind):
        self.current = None if self.current == kind else kind
        return self.current

    def stop(self):
        self.current = None


def ffmpeg_path():
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def make_cursor(scale):
    ss, size = 4, int(26 * scale)
    img = Image.new("RGBA", (size * ss, size * ss), (0, 0, 0, 0))
    pts = [(0, 0), (0, 17), (4.5, 13), (8, 21), (11, 19.5), (7.5, 12), (13, 12)]
    pts = [(x * scale * ss + 2 * ss, y * scale * ss + 2 * ss) for x, y in pts]
    ImageDraw.Draw(img).polygon(pts, fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=ss)
    return img.resize((size, size), Image.LANCZOS)


class Recorder:
    def __init__(self, app, path):
        self.app = app
        self.dt = 1 / FPS
        self.cursor = None
        self.ripples = []                       # [x, y, age]
        self.sprite = make_cursor(app.home.S)
        self.proc = subprocess.Popen(
            [ffmpeg_path(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{app.W}x{app.H}", "-r", str(FPS), "-i", "-", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
            stdin=subprocess.PIPE)

    def step(self, timer_speed=1.0):
        app = self.app
        app.update(self.dt, timer_dt=self.dt * timer_speed)   # countdown advances in video time
        if self.cursor:
            app.hover(*self.cursor)
        frame = app.render().convert("RGBA")
        d = ImageDraw.Draw(frame)
        for r in self.ripples:
            r[2] += self.dt
            k = clamp01(r[2] / 0.45)
            radius = 8 + 30 * k
            d.ellipse([r[0] - radius, r[1] - radius, r[0] + radius, r[1] + radius],
                      outline=(255, 255, 255, int(230 * (1 - k))), width=3)
        self.ripples = [r for r in self.ripples if r[2] < 0.45]
        if self.cursor:
            frame.alpha_composite(self.sprite, (round(self.cursor[0]), round(self.cursor[1])))
        self.proc.stdin.write(frame.convert("RGB").tobytes())

    def wait(self, seconds, timer_speed=1.0):
        for _ in range(round(seconds * FPS)):
            self.step(timer_speed)

    def move(self, target, seconds):
        start = self.cursor
        n = max(1, round(seconds * FPS))
        for i in range(1, n + 1):
            k = ease_in_out(i / n)
            self.cursor = (start[0] + (target[0] - start[0]) * k,
                           start[1] + (target[1] - start[1]) * k)
            self.step()

    def click(self):
        self.ripples.append([self.cursor[0], self.cursor[1], 0.0])
        action = self.app.click(*self.cursor)
        self.wait(0.15)
        return action

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def main():
    tmp = tempfile.mkdtemp()
    settings = os.path.join(tmp, "settings.json")
    json.dump({"tutorial_done": True}, open(settings, "w"))      # no tutorial in this video
    app = AppController(os.path.join(HERE, "assets"), SCALE, settings,
                        os.path.join(tmp, "stats.json"), sound=NullSound())
    app.home.skip_intro()
    rec = Recorder(app, OUT)
    k = app.timer_page.k

    def at(name):                                 # window position of a timer-page button
        box = {**tp.BUTTONS, **tp.PILLS}[name]
        return (box[0] + box[2]) / 2 * k, (box[1] + box[3]) / 2 * k

    rec.wait(1.0)
    rec.cursor = (app.W * 0.55, app.H * 0.55)
    rec.move(app.home.hotspot_center("timer"), 0.9)       # the alarm clock
    rec.wait(0.6)
    rec.click()                                           # -> study timer page
    rec.wait(1.5)

    rec.move(at("start"), 0.8); rec.click()               # start: 50:00 counts down
    rec.wait(3.5)
    rec.move(at("white_noise"), 0.8); rec.click(); rec.wait(1.4)   # sound buttons
    rec.move(at("rain"), 0.5); rec.click(); rec.wait(1.4)
    rec.move(at("skip"), 0.7); rec.click(); rec.wait(2.2)          # skip -> small break
    rec.move(at("reset"), 0.4); rec.click(); rec.wait(1.2)         # reset the break
    rec.move(at("start"), 0.4); rec.click(); rec.wait(2.0)
    rec.move(at("skip"), 0.4); rec.click(); rec.wait(2.0)          # next focus session

    hx0, hy0, hx1, hy1 = app.timer_page._home_rect()      # return-to-homepage button
    rec.move(((hx0 + hx1) / 2, (hy0 + hy1) / 2), 1.0)
    rec.wait(0.6)
    rec.click()
    rec.wait(1.8)
    rec.close()
    print("saved", OUT)


if __name__ == "__main__":
    main()
