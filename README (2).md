# Meraki

A cozy, aesthetic study companion. Click the clock, the books or the sticky notes on the bookshelf to open your study tools.

## Run it

```
pip install -r requirements.txt
python main.py
```

Python 3.9+ (tkinter comes with the standard Python installer). The tutorial opens by itself the first time; click the tutorial badge (top right, next to the user icon) to replay it.

## Folder layout

```
main.py             window + mouse events (tkinter)
controller.py       which page is showing, what each click does, timer events
homepage.py         home page: intro animation, tutorial, clickable hotspots
timer_page.py       study timer page (TV video, buttons, sounds, home button)
study_timer.py      pomodoro logic: 50/10 x2 -> 20 long break, 2-hour guard
sound.py            looping white-noise / rain mp3 player
storage.py          load_json / save_json used by every module
assignment_tracker.py, project_manager.py   (logic modules)
assets/             images, tv_loop.mp4, fonts/ (Winkle), sounds/ (mp3s)
make_preview.py     optional: records meraki_preview.mp4 of the app flow
```

## What each click does

| Click | Opens |
|---|---|
| Alarm clock | Study Timer |
| Books | Assignments Tracker (coming soon) |
| Sticky notes | Project Manager (coming soon) |
| User icon | Sign up / settings (coming soon) |
| Tutorial badge | Replays the 4-step tutorial |

## Study timer page

Cycle: **focus session 50:00 -> small break 10:00 -> focus session 50:00 -> small break 10:00 -> long break 20:00**. The label above the countdown shows which one you are in. When the long break ends, the whole pomodoro is done: the timer returns to 50:00, the TV stops and a "great job" pop-up appears.

| Button | What it does |
|---|---|
| start / pause | Starts or pauses the countdown |
| reset (circular arrow) | Restarts the current countdown from its full length |
| skip (arrow + bar) | Jumps to the next phase |
| white noise / rain sounds | Loops that mp3 (press again to stop; choosing the other one switches) |
| home (bottom right) | Back to the homepage. The countdown keeps running in the background |

- The TV loops `assets/tv_loop.mp4` until the pomodoro is done. To use another clip, replace that file (and `tv_still.jpg`, the fallback picture).
- If you study 2 hours in a row without reaching a long break, a pop-up says "Take a break for 20 minutes, you deserve it!" and the timer jumps to the long break.
- Fonts: Times New Roman everywhere, except the countdown digits (Winkle).

## Tech stack

- **Python + tkinter**: the window, mouse clicks and the animation loop (`root.after`).
- **Pillow**: draws every frame (zoom, fade, spotlight overlay, speech bubbles, buttons, fonts).
- **opencv-python**: reads the TV video frame by frame. Without it, the TV shows a still picture.
- **pygame (mixer)**: streams and loops the mp3s. Without it, `ffplay` is used if installed; otherwise the sound buttons show a message.
- **JSON files** (via `storage.py`): settings and study stats.

## Font license

Winkle is by createshaa and is **for personal use only** (see `assets/fonts/Winkle-License.txt`). Ask the author for a commercial license before using it in anything commercial.
