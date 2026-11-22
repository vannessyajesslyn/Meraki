# Meraki

A cozy, aesthetic study companion. Click the books, the clock and the sticky notes on the bookshelf to open your study tools.

## Run it

```
pip install -r requirements.txt
python main.py
```

Python 3.9+ (tkinter comes with the standard Python installer). The tutorial opens by itself the first time; click the tutorial badge (top right, next to the user icon) to replay it.

## Folder layout

```
main.py             window + mouse events (tkinter)
homepage.py         all drawing/animation: intro, tutorial, hotspots (Pillow)
study_timer.py      50/10 pomodoro logic + 2-hour overwork guard
sound.py            rain / white-noise loop for the timer
storage.py          load_json / save_json used by every module
assignment_tracker.py, project_manager.py   (logic modules)
assets/homepage.png, assets/tutorial.png
make_preview.py     optional: records meraki_preview.mp4 of the home page flow
```

## What each part does

| Click | Opens |
|---|---|
| Books | Assignments Tracker |
| Clock | Study Timer |
| Sticky notes | Project Manager |
| User icon | Sign up / settings |
| Tutorial badge | Replays the 4-step tutorial |

Pages are not connected yet: `COMING_SOON` in `main.py` shows a small message. To connect a page, replace that message with code that opens it.

## Tech stack

- **Python + tkinter**: the window, mouse clicks and the animation loop (`root.after`).
- **Pillow**: draws every frame (zoom, fade, bounce, spotlight overlay, speech bubbles) and loads the Times New Roman font.
- **JSON files** (via `storage.py`): saves assignments, projects, study stats and settings.
- **Standard library only for sound** (`wave`, `winsound`/`afplay`/`aplay`).

## Study timer rules

50 min study, 10 min break, 50 min study, then a 20 min long break, repeating. If someone studies 2 hours without a long break, the timer shows "Take a break for 20 minutes, you deserve it!" and switches to a long break.
