"""Background sounds for the study timer: white noise and rain (looping mp3s).

    player = AmbientPlayer()
    player.toggle("rain")          # starts looping the rain mp3 (stops white noise)
    player.toggle("rain")          # stops it again

Uses pygame's mixer (pip install pygame). If pygame is missing it tries
ffplay (comes with ffmpeg). If neither works, toggle() raises
SoundUnavailable so the page can tell the user.
"""
import atexit
import os
import shutil
import subprocess

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")
SOUNDS = {
    "white_noise": os.path.join(SOUND_DIR, "white_noise.mp3"),
    "rain": os.path.join(SOUND_DIR, "rain.mp3"),
}


class SoundUnavailable(Exception):
    """No way to play audio on this computer."""


class AmbientPlayer:
    def __init__(self, sounds=None):
        self.sounds = sounds or SOUNDS
        self.current = None            # "rain", "white_noise" or None
        self._pygame = None
        self._proc = None
        atexit.register(self.stop)

    # ---- backends ----
    def _start_pygame(self, path):
        if self._pygame is None:
            import pygame
            pygame.mixer.init()
            self._pygame = pygame
        self._pygame.mixer.music.load(path)
        self._pygame.mixer.music.play(loops=-1)          # -1 = repeat forever

    def _start_ffplay(self, path):
        exe = shutil.which("ffplay")
        if exe is None:
            raise SoundUnavailable("Install pygame (pip install pygame) to hear sounds.")
        self._proc = subprocess.Popen(
            [exe, "-nodisp", "-loglevel", "quiet", "-loop", "0", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # ---- public API ----
    def play(self, kind):
        path = self.sounds[kind]
        self.stop()
        try:
            self._start_pygame(path)
        except Exception:                                 # pygame missing or no audio device
            self._pygame = None
            self._start_ffplay(path)
        self.current = kind

    def stop(self):
        if self._pygame is not None:
            try:
                self._pygame.mixer.music.stop()
            except Exception:
                pass
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        self.current = None

    def toggle(self, kind):
        """Turn `kind` on (switching off the other one) or off if it is already playing.
        Returns the sound that is playing now, or None."""
        if self.current == kind:
            self.stop()
        else:
            self.play(kind)
        return self.current
