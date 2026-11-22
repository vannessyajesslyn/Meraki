"""Study timer logic for Meraki (same style as assignment_tracker.py and
project_manager.py: plain classes, to_dict/from_dict, JSON save file).

Cycle (Pomodoro 50/10):
    50 min study -> 10 min break -> 50 min study -> 20 min long break -> repeat

Overwork guard: if the student studies 2 hours in a row without a long
break (e.g. they skipped breaks), the timer shows
"Take a break for 20 minutes, you deserve it!" and jumps to a long break.

This file has no GUI code. The timer page just calls:
    timer.update()           every ~200 ms  -> returns a list of events
    timer.toggle()           start / pause button
    timer.skip(), timer.reset(), timer.toggle_rain()
and reads timer.time_text(), timer.phase_label(), timer.progress(), ...
"""
import time
from datetime import date

from sound import RainPlayer
from storage import load_json, save_json

SAVE_FILE = "study_stats.json"

STUDY_MIN = 50
BREAK_MIN = 10
LONG_BREAK_MIN = 20
OVERWORK_LIMIT = 2 * 60 * 60          # seconds of studying without a long break
OVERWORK_MESSAGE = "Take a break for 20 minutes, you deserve it!"

# one full cycle, in order
CYCLE = [
    ("study", STUDY_MIN * 60),
    ("break", BREAK_MIN * 60),
    ("study", STUDY_MIN * 60),
    ("long_break", LONG_BREAK_MIN * 60),
]
LABELS = {"study": "Focus Time", "break": "Short Break", "long_break": "Long Break"}

# events returned by tick()/update()
PHASE_CHANGED = "phase_changed"       # (PHASE_CHANGED, "break")
OVERWORK = "overwork"                 # (OVERWORK, OVERWORK_MESSAGE)


class StudyTimer:
    def __init__(self, save_file=SAVE_FILE, rain=None):
        self.save_file = save_file
        self.rain = rain if rain is not None else RainPlayer()

        self.phase_index = 0
        self.remaining = float(CYCLE[0][1])
        self.running = False
        self.study_since_long_break = 0.0     # seconds, for the overwork guard
        self._last_update = None

        # today's totals (saved to disk)
        self.today = date.today().isoformat()
        self.studied_today = 0.0              # seconds
        self.sessions_today = 0
        self._load()

    # ---------------- saving ----------------
    def to_dict(self):
        return {"date": self.today,
                "studied_seconds": round(self.studied_today),
                "sessions": self.sessions_today}

    def _load(self):
        data = load_json(self.save_file, {})
        if data.get("date") == self.today:
            self.studied_today = float(data.get("studied_seconds", 0))
            self.sessions_today = int(data.get("sessions", 0))

    def save(self):
        save_json(self.save_file, self.to_dict())

    # ---------------- current phase ----------------
    @property
    def phase(self):
        return CYCLE[self.phase_index][0]

    def phase_label(self):
        return LABELS[self.phase]

    def phase_total(self):
        return CYCLE[self.phase_index][1]

    def session_text(self):
        """'Session 1/2' while studying, otherwise what comes next."""
        if self.phase == "study":
            number = 1 if self.phase_index == 0 else 2
            return f"Session {number}/2"
        return "Rest up" if self.phase == "break" else "Long rest - you earned it"

    def time_text(self):
        secs = max(0, int(self.remaining + 0.999))
        return f"{secs // 60:02d}:{secs % 60:02d}"

    def progress(self):
        """0.0 -> 1.0 through the current phase."""
        total = self.phase_total()
        return 1.0 - max(0.0, self.remaining) / total

    def studied_text(self):
        minutes = int(self.studied_today // 60)
        return f"{minutes // 60}h {minutes % 60}m studied today"

    # ---------------- controls ----------------
    def start(self):
        self.running = True
        self._last_update = time.monotonic()

    def pause(self):
        self.running = False
        self._last_update = None
        self.save()

    def toggle(self):
        if self.running:
            self.pause()
        else:
            self.start()
        return self.running

    def reset(self):
        """Restart the current phase from its full length."""
        self.remaining = float(self.phase_total())
        self.pause()

    def skip(self):
        """Jump to the next phase of the cycle."""
        return self._next_phase(completed=False)

    def toggle_rain(self):
        """Turn the rain sound on/off. Returns True if it is now playing."""
        return self.rain.toggle()

    # ---------------- time passing ----------------
    def update(self):
        """Call regularly from the GUI; measures real elapsed time."""
        now = time.monotonic()
        if not self.running or self._last_update is None:
            self._last_update = now
            return []
        dt = now - self._last_update
        self._last_update = now
        return self.tick(dt)

    def tick(self, seconds):
        """Advance the timer by `seconds`. Returns a list of events."""
        events = []
        if not self.running:
            return events
        while seconds > 0:
            step = min(seconds, self.remaining)
            self.remaining -= step
            seconds -= step
            if self.phase == "study":
                self.studied_today += step
                self.study_since_long_break += step
                if self.study_since_long_break >= OVERWORK_LIMIT:
                    events.append((OVERWORK, OVERWORK_MESSAGE))
                    events += self._jump_to_long_break()
                    continue
            if self.remaining <= 0:
                events += self._next_phase(completed=True)
        return events

    # ---------------- phase changes ----------------
    def _next_phase(self, completed):
        if self.phase == "study" and completed:
            self.sessions_today += 1
        if self.phase == "long_break" and completed:
            self.study_since_long_break = 0.0      # a real long break was taken
        self._set_phase((self.phase_index + 1) % len(CYCLE))
        self.save()
        return [(PHASE_CHANGED, self.phase)]

    def _jump_to_long_break(self):
        self._set_phase(len(CYCLE) - 1)
        self.save()
        return [(PHASE_CHANGED, self.phase)]

    def _set_phase(self, index):
        self.phase_index = index
        self.remaining = float(CYCLE[index][1])


if __name__ == "__main__":
    # quick terminal demo: fast-forwards a whole study day
    t = StudyTimer(save_file="demo_stats.json")
    t.start()
    for _ in range(4 * 60 * 60):
        for ev in t.tick(1):
            print(f"{t.studied_text():>26} | {ev[0]}: {ev[1]}")
