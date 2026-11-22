"""Optional helper: records the home page flow (intro -> tutorial -> home)
into meraki_preview.mp4 using the SAME HomePage code the app uses.

    python make_preview.py            (needs ffmpeg installed, or imageio-ffmpeg)
"""
import os
import shutil
import subprocess

from PIL import Image, ImageDraw

from homepage import STEPS, HomePage, clamp01, ease_in_out

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "meraki_preview.mp4")
FPS = 30
SCALE = 1.46                      # 493x877 -> 720x1280


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
    d = ImageDraw.Draw(img)
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=ss)
    return img.resize((size, size), Image.LANCZOS)


class Recorder:
    def __init__(self, page, path):
        self.page = page
        self.dt = 1 / FPS
        self.cursor = None
        self.ripples = []                       # [x, y, age]
        self.sprite = make_cursor(page.S)
        self.proc = subprocess.Popen(
            [ffmpeg_path(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{page.W}x{page.H}", "-r", str(FPS), "-i", "-", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", path],
            stdin=subprocess.PIPE)

    def step(self):
        page = self.page
        page.update(self.dt)
        if self.cursor:
            page.hover(*self.cursor)
        frame = page.render().convert("RGBA")
        d = ImageDraw.Draw(frame)
        for r in self.ripples:
            r[2] += self.dt
            k = clamp01(r[2] / 0.45)
            radius = (8 + 30 * k) * page.S / 1.46
            d.ellipse([r[0] - radius, r[1] - radius, r[0] + radius, r[1] + radius],
                      outline=(255, 255, 255, int(230 * (1 - k))), width=3)
        self.ripples = [r for r in self.ripples if r[2] < 0.45]
        if self.cursor:
            frame.alpha_composite(self.sprite, (round(self.cursor[0]), round(self.cursor[1])))
        self.proc.stdin.write(frame.convert("RGB").tobytes())

    def wait(self, seconds):
        for _ in range(round(seconds * FPS)):
            self.step()

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
        action = self.page.click(*self.cursor)
        self.wait(0.15)
        return action

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def main():
    page = HomePage(os.path.join(HERE, "assets"), SCALE, show_tutorial=True)
    rec = Recorder(page, OUT)

    while page.phase != "tutorial":              # intro animation plays by itself
        rec.step()
    rec.wait(0.6)

    rec.cursor = (page.W * 0.62, page.H * 0.5)   # the "student" appears
    for i in range(len(STEPS)):
        rec.wait(3.0)                            # time to read the bubble
        rec.move(page.button_center("next"), 0.8)
        rec.wait(0.3)
        rec.click()
        rec.wait(0.35)
    rec.wait(0.8)                                # tutorial fades out -> homepage

    for name in ("assignments", "timer", "projects", "tutorial"):
        rec.move(page.hotspot_center(name), 0.8)  # hover each clickable thing
        rec.wait(0.8)
    rec.wait(1.2)
    rec.close()
    print("saved", OUT)


if __name__ == "__main__":
    main()
